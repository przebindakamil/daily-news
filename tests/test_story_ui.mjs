import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const script=fs.readFileSync('script.js','utf8');
const html=fs.readFileSync('index.html','utf8');
const css=fs.readFileSync('styles.css','utf8');
function method(name){
  const pattern=new RegExp('(?:^|\\n)((?:async )?function '+name+'\\([^]*?)(?=\\n(?:async )?function |$)');
  const match=script.match(pattern);
  assert.ok(match, 'Missing method '+name);
  return match[1];
}

test('following and unfollowing updates UI state without rerendering articles',()=>{
  const state={};
  const attributes={};
  const classes=new Set();
  const button={
    dataset:{watchId:'s-followed'},
    setAttribute(k,v){attributes[k]=v},
    classList:{toggle(k,on){if(on)classes.add(k);else classes.delete(k)}},
    textContent:''
  };
  const ctx={
    watchedStories:state,
    WATCH_KEY:'daily-news-watched-story-v1',
    localStorage:{setItem(k,v){assert.equal(k,ctx.WATCH_KEY);assert.ok(v.includes('s-followed')||v==='{}')}},
    document:{querySelectorAll(q){assert.equal(q,'[data-watch-id]');return [button]}},
    render(){throw Error('Must not rebuild DOM')},
  };
  vm.createContext(ctx);
  vm.runInContext([method('isWatched'),method('toggleWatched')].join('\n'),ctx);
  const item={story_id:'s-followed'};
  ctx.toggleWatched(item);
  assert.equal(ctx.isWatched(item),true);
  assert.equal(button.textContent,'Obserwujesz ✓');
  assert.equal(attributes['aria-pressed'],'true');
  ctx.toggleWatched(item);
  assert.equal(ctx.isWatched(item),false);
  assert.equal(button.textContent,'Obserwuj historię');
  assert.equal(attributes['aria-pressed'],'false');
});

test('other sources come from stored links without pretending independent confirmation',()=>{
  const fn=method('createStoryContext');
  assert.match(fn,/Inne publikacje o tej historii/);
  assert.match(fn,/różnych domen wydawców/);
  assert.match(fn,/to nie oznacza niezależnego potwierdzenia faktów/);
  assert.match(fn,/rel='noopener noreferrer'|a\.rel='noopener noreferrer'/);
  assert.match(fn,/Wcześniej w tej sprawie · oś czasu/);
  assert.match(fn,/W nowszym materiale/);
  assert.match(fn,/articleHash\(\{\.\.\.entry,archive_date:entry\.date\}\)/);
  assert.doesNotMatch(fn,/innerHTML\s*=\s*entry\./);
});

test('weekly recap uses a public JSON file and remains separate from private admin',()=>{
  assert.match(html,/id="week-view"/);
  assert.match(html,/id="week-root"/);
  assert.match(html,/data-view-link="week"/);
  assert.match(script,/fetch\('\.\/data\/rewind\/latest\.json'/);
  assert.match(script,/if\(hash==='#week'\)/);
  assert.match(script,/if\(location\.hash!=='#week'\) return/);
  assert.doesNotMatch(method('renderWeeklyRewind'),/secure\/audits|audit-password|AUDIT_PASSWORD/);
});

test('history UX has layout styles and watcher activity has its own section',()=>{
  assert.match(script,/Aktualizacje obserwowanych/);
  assert.match(script,/item\.is_update&&isWatched\(item\)/);
  assert.match(css,/\.story-timeline\{/);
  assert.match(css,/\.watch-button\.active\{/);
  assert.match(css,/\.week-view\[hidden\]\{display:none!important\}/);
});
