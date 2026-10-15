import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync('script.js', 'utf8');
const styles = fs.readFileSync('styles.css', 'utf8');

function functionSource(name) {
  const search = 'function ' + name + '(';
  const start = source.indexOf(search);
  assert.notEqual(start, -1, 'Missing function: ' + name);
  const following = source.indexOf('\nfunction ', start + search.length);
  return source.slice(start, following === -1 ? undefined : following);
}

function control(id, direction) {
  const classes = new Set();
  const attributes = {};
  return {
    dataset: direction
      ? {feedbackId:id,feedbackDirection:direction}
      : {itemId:id},
    classList: {
      toggle(name, enabled) { if (enabled) classes.add(name); else classes.delete(name); },
      contains(name) { return classes.has(name); },
    },
    attributes,
    setAttribute(key, value) { attributes[key] = String(value); },
    textContent:''
  };
}

function harness() {
  const item = {
    url:'https://example.com/article-1', category:'Nauka', topics:['Mars','Badania']
  };
  const other = {
    url:'https://example.com/article-2', category:'Nauka', topics:['Mars','Kosmos']
  };
  const more=control(item.url, 'more'), less=control(item.url,'less');
  const save=control(item.url);
  let savedCalls=0, voteCalls=0, panelCalls=0;
  const context={
    feedbackState:{},
    savedItems:[],
    userPreferences: { categories: {Nauka:6}, topics: {mars:8} },
    itemId: story => story.url,
    normalizeTopic: word => String(word).toLowerCase(),
    document: { querySelectorAll(selector) {
      if(selector==='[data-feedback-id]') return [more,less];
      if(selector==='.save-button[data-item-id]') return [save];
      throw Error('Unexpected selector: '+selector);
    } },
    saveFeedback() {voteCalls++},
    saveSaved() {savedCalls++},
    renderSavedPanel() {panelCalls++},
    render() { throw Error('Feedback must not rebuild the article list'); },
    activeData:{}
  };
  vm.createContext(context);
  const methods = [
    'feedbackDirection','nextFeedbackDirection','explicitFeedback',
    'learnedFeedbackBoost','updateFeedbackButtons','applyFeedback',
    'isSaved','updateSaveButtons','toggleSaved'
  ];
  vm.runInContext(methods.map(functionSource).join('\n'),context,{filename:'script.js'});
  return {context,item,other,more,less,save,
    counters:()=>({savedCalls,voteCalls,panelCalls})};
}

test('plus vote can be toggled off without changes to manual preferences or live feed',()=>{
  const {context,item,more,less,counters}=harness();
  const manual=JSON.stringify(context.userPreferences);
  context.applyFeedback(item,'more');
  assert.equal(context.feedbackDirection(item),'more');
  assert.equal(more.attributes['aria-pressed'],'true');
  assert.equal(less.attributes['aria-pressed'],'false');
  assert.equal(context.learnedFeedbackBoost(item)>0,true);
  context.applyFeedback(item,'more');
  assert.equal(context.feedbackDirection(item),null);
  assert.equal(more.attributes['aria-pressed'],'false');
  assert.equal(context.learnedFeedbackBoost(item),0);
  assert.equal(JSON.stringify(context.userPreferences),manual);
  assert.equal(counters().voteCalls,2);
});

test('switching plus to minus is a replacement, never accumulates slider changes',()=>{
  const {context,item,other,more,less}=harness();
  const weight=context.userPreferences.categories.Nauka;
  context.applyFeedback(item,'more');
  assert.ok(context.learnedFeedbackBoost(other)>0);
  context.applyFeedback(item,'less');
  assert.equal(context.feedbackDirection(item),'less');
  assert.ok(context.learnedFeedbackBoost(other)<0);
  assert.equal(more.attributes['aria-pressed'],'false');
  assert.equal(less.attributes['aria-pressed'],'true');
  assert.equal(context.userPreferences.categories.Nauka,weight);
  context.applyFeedback(item,'less');
  assert.equal(context.learnedFeedbackBoost(other),0);
});

test('save button updates in place without changing article node or rerendering',()=>{
  const {context,item,save,counters}=harness();
  context.toggleSaved(item);
  assert.equal(context.savedItems.length,1);
  assert.equal(save.textContent,'Zapisano');
  assert.equal(save.attributes['aria-pressed'],'true');
  context.toggleSaved(item);
  assert.equal(context.savedItems.length,0);
  assert.equal(save.textContent,'Zapisz');
  assert.equal(save.attributes['aria-pressed'],'false');
  assert.equal(counters().panelCalls,2);
});

test('legacy feedback votes are still recognized',()=>{
  const {context,item}=harness();
  context.feedbackState[item.url]='more';
  assert.equal(context.feedbackDirection(item),'more');
  assert.equal(context.explicitFeedback(item),10);
  context.applyFeedback(item,'more');
  assert.equal(context.feedbackDirection(item),null);
});

test('article click handler ignores selected text and the expanded digest',()=>{
  assert.match(source,/event\.target\.closest\('button,a,input,select,textarea,\.news-digest'\)/);
  assert.match(source,/window\.getSelection\?\.\(\)\?\.toString\(\)\.trim\(\)/);
  assert.doesNotMatch(functionSource('applyFeedback'),/\bif\(activeData\)\s*render\(activeData\)/);
  assert.doesNotMatch(functionSource('toggleSaved'),/\bif\(activeData\)\s*render\(activeData\)/);
});

test('cards do not translate on hover and neighboring grid items do not stretch',()=>{
  assert.doesNotMatch(styles,/\.news-card:hover\{transform:translateY\(/);
  assert.match(styles,/\.news-grid\{[^}]*align-items:start/);
  assert.match(styles,/\.top-day-grid\{[^}]*align-items:start/);
});
