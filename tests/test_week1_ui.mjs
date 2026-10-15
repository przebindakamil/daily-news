import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const script=fs.readFileSync('script.js','utf8');
const html=fs.readFileSync('index.html','utf8');
const css=fs.readFileSync('styles.css','utf8');

function method(name) {
  const expression=new RegExp('(?:^|\\n)((?:async )?function '+name+'\\([^]*?)(?=\\n(?:async )?function |$)','m');
  const match=script.match(expression);
  assert.ok(match,'Method missing: '+name);
  return match[1];
}
function methods(names,settings={}){
  const context={
    localStorage:{setItem(){},getItem(){return null}},
    readState:{},
    unreadOnly:false,
    quickMode:false,
    activeDate:'2026-10-15',
    activeData:{date:'2026-10-15'},
    archiveDates:['2026-10-15','2026-10-14'],
    userPreferences:{preset:null,volume:'standard',outsideBubble:true,diversity:.45,
      enabledCategories:{Nauka:true,Polska:true},categories:{Nauka:8,Polska:5}},
    itemId:story=>story.url||story.title,
    normalizeTopic:text=>text.toLowerCase(),
    document:{querySelectorAll(){return []}},
    location:{href:'https://example.com/daily-news/#today',hash:'#today'},
    window:{},
    ...settings,
  };
  vm.createContext(context);
  vm.runInContext(names.map(method).join('\n'),context);
  return context;
}

test('reading duration is based on digest, not the full external article',()=>{
 const ctx=methods(['estimatedReadingMinutes']);
 assert.equal(ctx.estimatedReadingMinutes({summary:'A short summary'}),1);
 assert.equal(ctx.estimatedReadingMinutes({digest_text:'a '.repeat(220)}),1);
 assert.equal(ctx.estimatedReadingMinutes({digest_text:'a '.repeat(221)}),2);
 assert.equal(ctx.estimatedReadingMinutes({}),null);
});

test('permalink is stable across category sorting and uses archived issue date',()=>{
 const ctx=methods(['articleKey','articleHash','articleLink']);
 const a={url:'https://example.com/a',archive_date:'2026-10-12'};
 const b={url:'https://example.com/b',archive_date:'2026-10-12'};
 assert.match(ctx.articleHash(a),/^#article\/2026-10-12\/[0-9a-f]{16}$/);
 assert.equal(ctx.articleHash(a),ctx.articleHash({...a,title:'Changed headline'}));
 assert.notEqual(ctx.articleHash(a),ctx.articleHash(b));
 assert.equal(ctx.articleLink(a),'https://example.com/daily-news/'+ctx.articleHash(a));
 assert.equal(ctx.articleHash({url:'https://example.com/a'},'bad-date'),'');
});

test('mark read and undo update existing card without rerender or removing it',()=>{
 const link='https://example.com/a';
 const attributes={};
 const classes=new Set();
 const cardClasses=new Set();
 const button={dataset:{readId:link},textContent:'',attributes,
   classList:{toggle(k,on){if(on)classes.add(k);else classes.delete(k)}},
   setAttribute(k,v){attributes[k]=v},
   closest(selector){
     assert.equal(selector,'.news-card');
     return {classList:{toggle(k,on){if(on)cardClasses.add(k);else cardClasses.delete(k)}}};
   }
 };
 const saved=[];
 const ctx=methods(['isRead','toggleRead','filterUnread'],{
   document:{querySelectorAll(q){assert.equal(q,'[data-read-id]');return [button]}},
   localStorage:{setItem(key,value){saved.push([key,value])}},
   READ_KEY:'daily-news-read-v1',
   render(){throw Error('Rerender not allowed while user is reading')}
 });
 const item={url:link};
 assert.equal(ctx.isRead(item),false);
 ctx.toggleRead(item);
 assert.equal(ctx.isRead(item),true);
 assert.equal(button.textContent,'Przeczytane ✓');
 assert.equal(button.attributes['aria-pressed'],'true');
 assert.ok(classes.has('active'));
 assert.ok(cardClasses.has('is-read'));
 ctx.unreadOnly=true;
 assert.equal(ctx.filterUnread([item]).length,0);
 ctx.toggleRead(item);
 assert.equal(ctx.isRead(item),false);
 assert.equal(button.attributes['aria-pressed'],'false');
 assert.equal(ctx.filterUnread([item]).length,1);
 assert.equal(saved.length,2);
});

test('5-minute mode reserves exactly two feed stories after editorial top three',()=>{
 const ctx=methods([
   'editorialScore','isCategoryEnabled','categoryWeight','diversifyItems','splitPersonalized'
 ],{personalizedScore:item=>item.score,READ_KEY:'read'});
 const items=[
  {url:'1',category:'Nauka',score:9,editorial_score:8},
  {url:'2',category:'Nauka',score:8,editorial_score:7},
  {url:'3',category:'Nauka',score:7,editorial_score:6},
  {url:'4',category:'Polska',score:6,editorial_score:6},
 ];
 const short=ctx.splitPersonalized(items,2);
 assert.equal(short.main.length,2);
 assert.equal(short.outsideBubble,null);
 const standard=ctx.splitPersonalized(items,4);
 assert.ok(standard.main.length+(standard.outsideBubble?1:0)<=4);
 assert.match(script,/const desiredCount=quickMode\?5:currentDailyLimit\(\)/);
 assert.match(script,/Math\.max\(0,desiredCount-topOfDay\.length\)/);
});

test('history category date switch and archived empty categories are accessible',()=>{
 assert.match(html,/id="category-date-select"/);
 assert.match(script,/categoryDateSelect\?\.addEventListener\('change'/);
 assert.match(script,/archiveDates\.includes\(date\)&&date!==activeDate/);
 assert.match(script,/card\.addEventListener\('click',\(\)=>\{\s*location\.hash='#category\//);
 assert.doesNotMatch(method('renderCategoriesLanding'),/card\.disabled=!categoryItems\.length/);
 assert.match(method('renderCategoryDates'),/archiveDates\.map\(date=>date\)/);
});

test('single-article route ignores personal ranking, flags and read filters',async()=>{
 let current='';
 const ctx=methods(['applyRoute'],{
  location:{hash:'#article/2026-10-13/0123456789abcdef'},
  setActiveView(view){current=view},
  renderArticleRoute(hash){assert.match(hash,/^#article\//)},
  categoryFromSlug(){return null},
  setActiveViewDefault(){},
 });
 ctx.applyRoute();
 assert.equal(current,'article');
 ctx.location.hash='#categories';ctx.applyRoute();assert.equal(current,'categories');
 ctx.location.hash='#audit';ctx.applyRoute();assert.equal(current,'audit');
 assert.match(method('renderArticleRoute'),/find\(item=>articleKey\(item\)===key\)/);
 assert.match(method('renderArticleRoute'),/if\(location\.hash!==hash\) return/);
});

test('mobile header controls are touch friendly and content cannot overflow',()=>{
 for(const id of ['quick-mode-toggle','unread-only-toggle','category-date-select','article-view']) {
   assert.match(html,new RegExp('id="'+id+'"'));
 }
 assert.match(css,/\.site-header \.main-nav a,\.site-header \.main-nav button\{\s*flex:0 0 auto;min-height:44px/);
 assert.match(css,/\.wrap\{width:calc\(100% - 28px\)\}/);
 assert.match(css,/\.news-card\{min-width:0;overflow-wrap:anywhere\}/);
 assert.match(css,/\.category-tools select\{[^}]*min-height:44px/s);
 assert.match(css,/#article-view\[hidden\]\{display:none!important\}/);
});
