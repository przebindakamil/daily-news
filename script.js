const root = document.querySelector('#news-root');
const updated = document.querySelector('#updated-at');
const nav = document.querySelector('#category-nav');
const categoryClear = document.querySelector('#category-clear');
const dayNav = document.querySelector('#day-nav');
const archiveToggle = document.querySelector('#archive-toggle');
const archiveList = document.querySelector('#archive-list');
const archiveSearchInput = document.querySelector('#archive-search-input');
const archiveSearchStatus = document.querySelector('#archive-search-status');
const archiveSearchResults = document.querySelector('#archive-search-results');

const savedToggle = document.querySelector('#saved-toggle');
const savedCount = document.querySelector('#saved-count');
const savedPanel = document.querySelector('#saved-panel');
const savedList = document.querySelector('#saved-list');

const preferencesToggle = document.querySelector('#preferences-toggle');
const preferencesPanel = document.querySelector('#preferences-panel');
const preferencesList = document.querySelector('#preferences-list');
const preferencesReset = document.querySelector('#preferences-reset');
const preferencesVolume = document.querySelector('#preferences-volume');
const preferencesBubble = document.querySelector('#preferences-bubble');
const preferencesCustomInput = document.querySelector('#preferences-custom-input');
const preferencesCustomAdd = document.querySelector('#preferences-custom-add');
const preferencesCustomList = document.querySelector('#preferences-custom-list');
const preferencesPresets = document.querySelector('#preferences-presets');

const onboardingPanel = document.querySelector('#onboarding-panel');
const onboardingTopics = document.querySelector('#onboarding-topics');
const onboardingVolume = document.querySelector('#onboarding-volume');
const onboardingBubble = document.querySelector('#onboarding-bubble');
const onboardingSave = document.querySelector('#onboarding-save');
const onboardingStatus = document.querySelector('#onboarding-status');
const onboardingCustomInput = document.querySelector('#onboarding-custom-input');
const onboardingCustomAdd = document.querySelector('#onboarding-custom-add');
const onboardingCustomList = document.querySelector('#onboarding-custom-list');
const onboardingPresets = document.querySelector('#onboarding-presets');

const PREFS_KEY = 'daily-news-user-preferences-v2';
const FEEDBACK_KEY = 'daily-news-feedback-v1';
const SAVED_KEY = 'daily-news-saved-v1';

const CATEGORIES = [
  'AI i technologia',
  'Polska',
  'Świat i geopolityka',
  'Piłka nożna',
  'Sport i trening',
  'Zdrowie',
  'Finanse i inwestowanie',
  'Biznes i startupy',
  'Nauka',
  'Kosmos',
  'Motoryzacja',
  'Podróże',
  'Kultura',
  'Gaming',
  'Środowisko i klimat',
  'Praca i kariera',
  'Nieruchomości i dom'
];

const VOLUME_LIMITS = { short: 5, standard: 9, more: 15 };

const PRESETS = {
  omnibus: {
    name: 'Omnibus',
    description: 'Najciekawsze i najważniejsze rzeczy z wielu dziedzin. Duża różnorodność, mało powtórek.',
    categories: CATEGORIES,
    weights: Object.fromEntries(CATEGORIES.map(category => [category, 7])),
    volume: 'standard',
    outsideBubble: true,
    diversity: 0.95
  },
  tech: {
    name: 'Tech & Future',
    description: 'AI, technologia, nauka, kosmos, startupy i cyfrowa przyszłość.',
    categories: ['AI i technologia','Biznes i startupy','Nauka','Kosmos','Praca i kariera'],
    weights: {'AI i technologia':10,'Biznes i startupy':8,'Nauka':8,'Kosmos':7,'Praca i kariera':6},
    volume: 'standard',
    outsideBubble: true,
    diversity: 0.55
  },
  money: {
    name: 'Biznes & Pieniądze',
    description: 'Finanse, inwestowanie, gospodarka, biznes, nieruchomości i rynek pracy.',
    categories: ['Finanse i inwestowanie','Biznes i startupy','Praca i kariera','Nieruchomości i dom','Polska','Świat i geopolityka'],
    weights: {'Finanse i inwestowanie':10,'Biznes i startupy':9,'Praca i kariera':7,'Nieruchomości i dom':7,'Polska':6,'Świat i geopolityka':6},
    volume: 'standard',
    outsideBubble: true,
    diversity: 0.55
  },
  sport: {
    name: 'Sport',
    description: 'Piłka, sport, trening, zdrowie i rzeczy, które pomagają lepiej rozumieć ciało.',
    categories: ['Piłka nożna','Sport i trening','Zdrowie'],
    weights: {'Piłka nożna':10,'Sport i trening':9,'Zdrowie':7},
    volume: 'standard',
    outsideBubble: true,
    diversity: 0.35
  },
  world: {
    name: 'Świat',
    description: 'Polska, geopolityka, gospodarka, klimat i nauka — żeby być dobrze zorientowanym.',
    categories: ['Polska','Świat i geopolityka','Finanse i inwestowanie','Środowisko i klimat','Nauka','Zdrowie'],
    weights: {'Polska':9,'Świat i geopolityka':10,'Finanse i inwestowanie':7,'Środowisko i klimat':7,'Nauka':7,'Zdrowie':6},
    volume: 'standard',
    outsideBubble: true,
    diversity: 0.7
  },
  lifestyle: {
    name: 'Lifestyle & Culture',
    description: 'Podróże, kultura, motoryzacja, gaming, zdrowie i codzienny styl życia.',
    categories: ['Podróże','Kultura','Motoryzacja','Gaming','Zdrowie','Nieruchomości i dom'],
    weights: {'Podróże':9,'Kultura':9,'Motoryzacja':8,'Gaming':7,'Zdrowie':7,'Nieruchomości i dom':6},
    volume: 'standard',
    outsideBubble: true,
    diversity: 0.6
  }
};

function defaultPreferences(){
  return {
    onboarded: false,
    categories: Object.fromEntries(CATEGORIES.map(category => [category, 5])),
    enabledCategories: Object.fromEntries(CATEGORIES.map(category => [category, true])),
    topics: {},
    customInterests: [],
    volume: 'standard',
    outsideBubble: true,
    preset: null,
    diversity: 0.45
  };
}

let archiveDates = [];
let activeDate = null;
let activeData = null;
let activeCategoryFilter = null;

function loadJson(key, fallback){
  try{
    const value=JSON.parse(localStorage.getItem(key)||'');
    return value && typeof value==='object' ? value : fallback;
  }catch(_){
    return fallback;
  }
}

let userPreferences={...defaultPreferences(),...loadJson(PREFS_KEY,{})};
userPreferences.categories={...defaultPreferences().categories,...(userPreferences.categories||{})};
userPreferences.enabledCategories={...defaultPreferences().enabledCategories,...(userPreferences.enabledCategories||{})};
userPreferences.topics=userPreferences.topics||{};
userPreferences.customInterests=Array.isArray(userPreferences.customInterests)?userPreferences.customInterests:[];
let feedbackState=loadJson(FEEDBACK_KEY,{});
let savedItems=loadJson(SAVED_KEY,[]);
if(!Array.isArray(savedItems)) savedItems=[];
let archiveCache=new Map();

function savePreferences(){ localStorage.setItem(PREFS_KEY,JSON.stringify(userPreferences)); }
function saveFeedback(){ localStorage.setItem(FEEDBACK_KEY,JSON.stringify(feedbackState)); }
function saveSaved(){
  localStorage.setItem(SAVED_KEY,JSON.stringify(savedItems));
  renderSavedCount();
}

function formatDate(value){
  if(!value) return '';
  const date=new Date(value);
  if(Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('pl-PL',{dateStyle:'medium',timeStyle:'short'}).format(date);
}

function formatDayLabel(dateString,index){
  if(index===0) return 'Dzisiaj';
  if(index===1) return 'Wczoraj';
  return new Intl.DateTimeFormat('pl-PL',{day:'numeric',month:'short'}).format(new Date(dateString+'T12:00:00'));
}

function formatArchiveDay(dateString){
  return new Intl.DateTimeFormat('pl-PL',{weekday:'short',day:'numeric',month:'long',year:'numeric'}).format(new Date(dateString+'T12:00:00'));
}

function normalizeTopic(value=''){
  return value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ł/g,'l').trim();
}

function itemId(item){ return item.url || item.title || JSON.stringify(item); }

function editorialScore(item){
  const raw=Number(item.editorial_score);
  return Number.isFinite(raw)&&raw>0?Math.min(10,raw):7;
}

function isCategoryEnabled(category){ return userPreferences.enabledCategories?.[category]!==false; }
function categoryWeight(item){ return Number(userPreferences.categories?.[item.category]??5); }

function topicAffinity(item){
  const topics=Array.isArray(item.topics)?item.topics:[];
  if(!topics.length) return 5;
  const scores=topics.map(topic=>Number(userPreferences.topics?.[normalizeTopic(topic)]??5));
  return scores.reduce((a,b)=>a+b,0)/scores.length;
}

function customInterestScore(item){
  const interests=userPreferences.customInterests||[];
  if(!interests.length) return 5;

  const digest=item.digest||{};
  const haystack=normalizeTopic([
    item.title,
    item.summary,
    item.category,
    ...(item.topics||[]),
    digest.what_happened,
    digest.context,
    ...(digest.key_points||[])
  ].filter(Boolean).join(' '));

  let best=0;
  interests.forEach(interest=>{
    const needle=normalizeTopic(interest);
    if(!needle) return;
    if(haystack.includes(needle)){ best=Math.max(best,10); return; }
    const words=needle.split(/\s+/).filter(word=>word.length>2);
    const matches=words.filter(word=>haystack.includes(word)).length;
    if(matches) best=Math.max(best,Math.min(9,5+(matches/Math.max(words.length,1))*4));
  });
  return best||4;
}

function explicitFeedback(item){
  const value=feedbackState[itemId(item)];
  if(value==='more') return 10;
  if(value==='less') return 0;
  return 5;
}

function personalizedScore(item){
  const omnibus = userPreferences.preset === 'omnibus';
  if(omnibus){
    return editorialScore(item)*.67
      + categoryWeight(item)*.08
      + topicAffinity(item)*.06
      + customInterestScore(item)*.12
      + explicitFeedback(item)*.07;
  }

  return editorialScore(item)*.45
    + categoryWeight(item)*.18
    + topicAffinity(item)*.10
    + customInterestScore(item)*.20
    + explicitFeedback(item)*.07;
}

function applyPreset(key){
  const preset=PRESETS[key];
  if(!preset) return;

  userPreferences.enabledCategories=Object.fromEntries(
    CATEGORIES.map(category=>[category,preset.categories.includes(category)])
  );
  userPreferences.categories=Object.fromEntries(
    CATEGORIES.map(category=>[category,Number(preset.weights[category]??(preset.categories.includes(category)?7:0))])
  );
  userPreferences.volume=preset.volume;
  userPreferences.outsideBubble=preset.outsideBubble;
  userPreferences.preset=key;
  userPreferences.diversity=preset.diversity;
}

function diversifyItems(items,limit){
  if(!items.length||limit<=0) return [];
  const diversity=Number(userPreferences.diversity??0.45);
  if(diversity<0.65) return items.slice(0,limit);

  const result=[];
  const used=new Set();
  const counts={};

  // First pass: broad coverage — one item per category.
  for(const item of items){
    if(result.length>=limit) break;
    const category=item.category||'Inne';
    if(counts[category]) continue;
    result.push(item);
    used.add(itemId(item));
    counts[category]=1;
  }

  // Second pass: strongest remaining stories, but cap category repetition.
  const maxPerCategory=diversity>=0.9?2:3;
  for(const item of items){
    if(result.length>=limit) break;
    if(used.has(itemId(item))) continue;
    const category=item.category||'Inne';
    if((counts[category]||0)>=maxPerCategory) continue;
    result.push(item);
    used.add(itemId(item));
    counts[category]=(counts[category]||0)+1;
  }

  return result;
}

function currentDailyLimit(){ return VOLUME_LIMITS[userPreferences.volume]||VOLUME_LIMITS.standard; }

function applyFeedback(item,direction){
  feedbackState[itemId(item)]=direction;
  saveFeedback();

  const delta=direction==='more'?.8:-.8;
  if(item.category){
    const current=Number(userPreferences.categories?.[item.category]??5);
    userPreferences.categories[item.category]=Math.max(0,Math.min(10,current+delta*.35));
  }
  (item.topics||[]).forEach(topic=>{
    const key=normalizeTopic(topic);
    const current=Number(userPreferences.topics?.[key]??5);
    userPreferences.topics[key]=Math.max(0,Math.min(10,current+delta));
  });

  savePreferences();
  renderPreferences();
  if(activeData) render(activeData);
}

function isSaved(item){
  return savedItems.some(saved=>itemId(saved)===itemId(item));
}

function renderSavedCount(){
  if(savedCount) savedCount.textContent=String(savedItems.length);
}

function toggleSaved(item){
  const id=itemId(item);
  const index=savedItems.findIndex(saved=>itemId(saved)===id);
  if(index>=0){
    savedItems.splice(index,1);
  }else{
    savedItems.unshift({...item,saved_at:new Date().toISOString()});
  }
  saveSaved();
  renderSavedPanel();
  if(activeData) render(activeData);
}

function renderSavedPanel(){
  if(!savedList) return;
  savedList.innerHTML='';
  if(!savedItems.length){
    const empty=document.createElement('p');
    empty.className='empty';
    empty.textContent='Nie masz jeszcze zapisanych materiałów.';
    savedList.appendChild(empty);
    return;
  }

  savedItems.forEach(item=>{
    const row=document.createElement('article');
    row.className='saved-item';

    const meta=document.createElement('div');
    meta.className='saved-item-meta';
    meta.textContent=[item.category,item.source].filter(Boolean).join(' · ');

    const title=document.createElement('h3');
    title.textContent=item.title||'Bez tytułu';

    const actions=document.createElement('div');
    actions.className='saved-item-actions';

    const source=document.createElement('a');
    source.href=item.url||'#';
    source.target='_blank';
    source.rel='noopener noreferrer';
    source.textContent='Źródło ↗';
    source.addEventListener('click',()=>recordSourceClick(item));

    const remove=document.createElement('button');
    remove.type='button';
    remove.textContent='Usuń';
    remove.addEventListener('click',()=>toggleSaved(item));

    actions.append(source,remove);
    row.append(meta,title,actions);
    savedList.appendChild(row);
  });
}

function setSavedOpen(open){
  if(!savedPanel) return;
  savedPanel.hidden=!open;
  document.body.classList.toggle('preferences-open',open);
}

function recordSourceClick(item){
  if(item.category){
    const current=Number(userPreferences.categories?.[item.category]??5);
    userPreferences.categories[item.category]=Math.min(10,current+.08);
  }
  (item.topics||[]).forEach(topic=>{
    const key=normalizeTopic(topic);
    const current=Number(userPreferences.topics?.[key]??5);
    userPreferences.topics[key]=Math.min(10,current+.12);
  });
  savePreferences();
}

function createDigest(item){
  const panel=document.createElement('div');
  panel.className='news-digest';
  panel.hidden=true;

  const label=document.createElement('p');
  label.className='digest-label';
  label.textContent='Wiedza w pigułce';
  panel.appendChild(label);

  const text=(item.digest_text||'').trim();

  if(text){
    const body=document.createElement('div');
    body.className='digest-prose';

    const paragraphs=text
      .split(/\n\s*\n/)
      .map(part=>part.trim())
      .filter(Boolean);

    (paragraphs.length?paragraphs:[text]).forEach(part=>{
      const p=document.createElement('p');
      p.textContent=part;
      body.appendChild(p);
    });

    panel.appendChild(body);
  }else if(item.summary){
    const body=document.createElement('div');
    body.className='digest-prose';
    const p=document.createElement('p');
    p.textContent=item.summary;
    body.appendChild(p);
    panel.appendChild(body);
  }

  const sourceRow=document.createElement('div');
  sourceRow.className='digest-source-row';

  const note=document.createElement('span');
  note.textContent=item.full_text_used
    ? 'Skrót przygotowany na podstawie treści artykułu'
    : 'Skrót na podstawie dostępnych danych';

  const link=document.createElement('a');
  link.className='news-link';
  link.target='_blank';
  link.rel='noopener noreferrer';
  link.href=item.url||'#';
  link.textContent='Czytaj pełny materiał u źródła';
  link.addEventListener('click',event=>{
    event.stopPropagation();
    recordSourceClick(item);
  });

  sourceRow.append(note,link);
  panel.appendChild(sourceRow);
  return panel;
}

function storyCard(item,featured=false){
  const card=document.createElement('article');
  card.className='news-card'+(featured?' featured':'');
  card.tabIndex=0;
  card.setAttribute('role','button');
  card.setAttribute('aria-expanded','false');

  const meta=document.createElement('div');
  meta.className='news-meta';
  const category=document.createElement('span');
  category.className='news-category';
  category.textContent=item.category||'Wiadomość';
  const source=document.createElement('span');
  source.textContent=item.source||'Źródło';
  meta.append(category,source);

  const title=document.createElement('h3');
  title.textContent=item.title||'Bez tytułu';

  const summary=document.createElement('p');
  summary.className='news-summary';
  summary.textContent=item.summary||'';

  const topics=document.createElement('div');
  topics.className='news-topics';
  (item.topics||[]).slice(0,4).forEach(topic=>{
    const tag=document.createElement('span');
    tag.textContent=topic;
    topics.appendChild(tag);
  });

  const feedback=document.createElement('div');
  feedback.className='feedback-actions';

  const saveButton=document.createElement('button');
  saveButton.type='button';
  saveButton.className='feedback-button save-button'+(isSaved(item)?' active':'');
  saveButton.textContent=isSaved(item)?'Zapisano':'Zapisz';
  saveButton.addEventListener('click',event=>{
    event.stopPropagation();
    toggleSaved(item);
  });
  const more=document.createElement('button');
  more.type='button';
  more.textContent='+';
  more.title='Więcej takich';
  more.setAttribute('aria-label','Więcej takich');
  more.className='feedback-button feedback-button-positive';
  const less=document.createElement('button');
  less.type='button';
  less.textContent='−';
  less.title='Mniej takich';
  less.setAttribute('aria-label','Mniej takich');
  less.className='feedback-button feedback-button-negative';
  const current=feedbackState[itemId(item)];
  if(current==='more') more.classList.add('active');
  if(current==='less') less.classList.add('active');
  more.addEventListener('click',event=>{event.stopPropagation();applyFeedback(item,'more');});
  less.addEventListener('click',event=>{event.stopPropagation();applyFeedback(item,'less');});
  feedback.append(saveButton,more,less);

  const footer=document.createElement('div');
  footer.className='news-footer';
  const date=document.createElement('span');
  date.textContent=item.published_at?formatDate(item.published_at):'';
  const expandHint=document.createElement('span');
  expandHint.className='expand-hint';
  expandHint.textContent='Kliknij po wiedzę w pigułce';
  footer.append(date,expandHint);

  const digest=createDigest(item);

  function toggleDigest(){
    const open=digest.hidden;
    digest.hidden=!open;
    card.classList.toggle('expanded',open);
    card.setAttribute('aria-expanded',String(open));
    expandHint.textContent=open?'Zwiń':'Kliknij po wiedzę w pigułce';
  }

  card.addEventListener('click',event=>{
    if(event.target.closest('button,a,input')) return;
    toggleDigest();
  });
  card.addEventListener('keydown',event=>{
    if((event.key==='Enter'||event.key===' ')&&!event.target.closest('button,a,input')){
      event.preventDefault();
      toggleDigest();
    }
  });

  card.append(meta,title,summary);
  if((item.topics||[]).length) card.append(topics);
  card.append(feedback,footer,digest);
  return card;
}

function renderSection(title,items,featured=false,className=''){
  if(!items?.length) return null;
  const section=document.createElement('section');
  section.className='news-section'+(featured?' primary-section':'')+(className?' '+className:'');
  const head=document.createElement('div');
  head.className='section-head';
  const heading=document.createElement('h2');
  heading.textContent=title;
  const count=document.createElement('span');
  count.className='section-count';
  count.textContent=items.length===1?'1 materiał':items.length+' materiałów';
  head.append(heading,count);

  const grid=document.createElement('div');
  grid.className=featured?'news-grid featured-grid':'news-grid';
  items.forEach((item,index)=>grid.appendChild(storyCard(item,featured&&index===0)));
  section.append(head,grid);
  return section;
}

function splitPersonalized(items){
  const limit=Math.min(currentDailyLimit(),items.length);
  const enabled=items
    .filter(item=>isCategoryEnabled(item.category))
    .sort((a,b)=>personalizedScore(b)-personalizedScore(a));

  const isOmnibus=userPreferences.preset==='omnibus';
  const reserveBubble=!isOmnibus&&userPreferences.outsideBubble&&limit>2?1:0;
  const mainLimit=Math.max(1,limit-reserveBubble);
  const main=diversifyItems(enabled,mainLimit);
  const used=new Set(main.map(itemId));

  let outsideBubble=null;
  if(!isOmnibus&&userPreferences.outsideBubble){
    const candidates=items
      .filter(item=>!used.has(itemId(item)))
      .filter(item=>!isCategoryEnabled(item.category)||categoryWeight(item)<=5)
      .sort((a,b)=>editorialScore(b)-editorialScore(a));
    outsideBubble=candidates[0]||null;
  }

  if(!outsideBubble&&main.length<limit){
    for(const item of enabled){
      if(main.length>=limit) break;
      if(used.has(itemId(item))) continue;
      main.push(item);
      used.add(itemId(item));
    }
  }

  return {main,outsideBubble};
}

function renderCategoryNav(all){
  if(!nav) return;
  nav.innerHTML='';

  const available=new Set(all.map(item=>item.category).filter(Boolean));
  const enabled=CATEGORIES.filter(category=>isCategoryEnabled(category) && available.has(category));

  if(activeCategoryFilter && !enabled.includes(activeCategoryFilter)){
    activeCategoryFilter=null;
  }

  enabled.forEach(category=>{
    const button=document.createElement('button');
    button.type='button';
    button.className='category-chip'+(activeCategoryFilter===category?' active':'');
    button.textContent=category;
    button.addEventListener('click',()=>{
      activeCategoryFilter=activeCategoryFilter===category?null:category;
      render(activeData);
    });
    nav.appendChild(button);
  });

  if(categoryClear){
    categoryClear.hidden=!activeCategoryFilter;
    categoryClear.textContent=activeCategoryFilter?'Pokaż wszystko':'';
  }

  const toolbar=nav.closest('.topic-toolbar');
  if(toolbar) toolbar.hidden=!enabled.length;
}

function render(data){
  activeData=data;
  updated.textContent=data.generated_at?'Aktualizacja: '+formatDate(data.generated_at):'Brak daty aktualizacji';
  root.innerHTML='';

  const allRaw=[...(data.top_stories||[]),...(data.more_stories||[])];
  if(!allRaw.length){
    if(nav) nav.innerHTML='';
    root.innerHTML='<p class="empty">Brak wiadomości dla tego dnia.</p>';
    return;
  }

  renderCategoryNav(allRaw);

  const all=activeCategoryFilter
    ? allRaw.filter(item=>item.category===activeCategoryFilter)
    : allRaw;

  const {main,outsideBubble}=splitPersonalized(all);
  const isToday=activeDate===archiveDates[0];
  const isOmnibus=userPreferences.preset==='omnibus';
  const mainTitle=isToday
    ? (isOmnibus?'Dzisiaj warto wiedzieć':'Dla Ciebie')
    : (isOmnibus?'Warto było wiedzieć':'Najlepiej dopasowane');

  const mainSection=renderSection(mainTitle,main,true);
  if(mainSection) root.appendChild(mainSection);

  if(outsideBubble){
    const bubble=renderSection('Poza twoją bańką',[outsideBubble],false,'outside-bubble-section');
    if(bubble) root.appendChild(bubble);
  }

  if(!main.length&&!outsideBubble){
    root.innerHTML='<p class="empty">Brak materiałów w wybranych kategoriach. Zmień zainteresowania w „Dostosuj”.</p>';
  }
}

async function loadBriefing(date){
  activeDate=date;
  renderDayNavigation();
  root.innerHTML='<p class="loading">Ładowanie briefingu…</p>';
  try{
    const response=await fetch('./data/archive/'+date+'.json',{cache:'no-store'});
    if(!response.ok) throw new Error('Nie udało się wczytać tego dnia.');
    render(await response.json());
  }catch(err){
    root.innerHTML='<p class="empty">'+err.message+'</p>';
  }
}

function renderDayNavigation(){
  dayNav.innerHTML='';
  archiveDates.slice(0,5).forEach((date,index)=>{
    const button=document.createElement('button');
    button.type='button';
    button.className='day-button'+(date===activeDate?' active':'');
    button.textContent=formatDayLabel(date,index);
    button.addEventListener('click',()=>loadBriefing(date));
    dayNav.appendChild(button);
  });

  archiveList.innerHTML='';
  archiveDates.forEach(date=>{
    const button=document.createElement('button');
    button.type='button';
    button.className='archive-day'+(date===activeDate?' active':'');
    button.textContent=formatArchiveDay(date);
    button.addEventListener('click',()=>{
      archiveList.hidden=true;
      archiveToggle.setAttribute('aria-expanded','false');
      loadBriefing(date);
      window.scrollTo({top:0,behavior:'smooth'});
    });
    archiveList.appendChild(button);
  });
}

function renderVolumeOptions(container){
  if(!container) return;
  container.innerHTML='';
  [['short','Krótko','około 5'],['standard','Standard','około 9'],['more','Więcej','do 15']]
    .forEach(([key,label,detail])=>{
      const button=document.createElement('button');
      button.type='button';
      button.dataset.volume=key;
      button.className=userPreferences.volume===key?'active':'';
      button.innerHTML=label+' <span>'+detail+'</span>';
      button.addEventListener('click',()=>{
        userPreferences.volume=key;
        savePreferences();
        renderPreferences();
        if(activeData) render(activeData);
      });
      container.appendChild(button);
    });
}

function addCustomInterest(value,target=userPreferences.customInterests){
  const clean=value.trim().replace(/\s+/g,' ');
  if(clean.length<2) return false;
  if(target.some(item=>normalizeTopic(item)===normalizeTopic(clean))) return false;
  target.push(clean.slice(0,60));
  return true;
}

function renderCustomInterestList(container,items,onRemove){
  if(!container) return;
  container.innerHTML='';
  items.forEach((interest,index)=>{
    const chip=document.createElement('span');
    chip.className='custom-interest-chip';
    const text=document.createElement('span');
    text.textContent=interest;
    const remove=document.createElement('button');
    remove.type='button';
    remove.textContent='×';
    remove.setAttribute('aria-label','Usuń '+interest);
    remove.addEventListener('click',()=>onRemove(index));
    chip.append(text,remove);
    container.appendChild(chip);
  });
}

function renderPresetCards(container,onSelect){
  if(!container) return;
  container.innerHTML='';

  Object.entries(PRESETS).forEach(([key,preset])=>{
    const button=document.createElement('button');
    button.type='button';
    button.className='preset-card'+(userPreferences.preset===key?' active':'');
    button.dataset.preset=key;

    const top=document.createElement('span');
    top.className='preset-card-top';

    const name=document.createElement('strong');
    name.textContent=preset.name;

    const badge=document.createElement('span');
    badge.className='preset-badge';
    badge.textContent=key==='omnibus'?'Polecany':preset.categories.length+' tematów';

    top.append(name,badge);

    const description=document.createElement('span');
    description.className='preset-description';
    description.textContent=preset.description;

    button.append(top,description);
    button.addEventListener('click',()=>onSelect(key));
    container.appendChild(button);
  });
}

function syncPresetButtons(){
  document.querySelectorAll('.preset-card').forEach(button=>{
    button.classList.toggle('active',button.dataset.preset===userPreferences.preset);
  });
}

function renderPreferences(){
  if(!preferencesList) return;
  preferencesList.innerHTML='';

  renderPresetCards(preferencesPresets,key=>{
    applyPreset(key);
    savePreferences();
    activeCategoryFilter=null;
    renderPreferences();
    if(activeData) render(activeData);
  });

  CATEGORIES.forEach(category=>{
    const row=document.createElement('div');
    row.className='preference-row';

    const toggle=document.createElement('input');
    toggle.type='checkbox';
    toggle.className='category-enable';
    toggle.checked=isCategoryEnabled(category);

    const name=document.createElement('span');
    name.textContent=category;

    const input=document.createElement('input');
    input.type='range';
    input.min='0'; input.max='10'; input.step='1';
    input.value=String(Math.round(userPreferences.categories?.[category]??5));
    input.disabled=!toggle.checked;

    const value=document.createElement('output');
    value.textContent=input.value;

    toggle.addEventListener('change',()=>{
      userPreferences.enabledCategories[category]=toggle.checked;
      userPreferences.preset=null;
      input.disabled=!toggle.checked;
      if(!toggle.checked && activeCategoryFilter===category) activeCategoryFilter=null;
      savePreferences();
      if(activeData) render(activeData);
    });

    input.addEventListener('input',()=>{
      value.textContent=input.value;
      userPreferences.categories[category]=Number(input.value);
      userPreferences.preset=null;
      savePreferences();
      if(activeData) render(activeData);
    });

    row.append(toggle,name,input,value);
    preferencesList.appendChild(row);
  });

  renderVolumeOptions(preferencesVolume);
  if(preferencesBubble) preferencesBubble.checked=Boolean(userPreferences.outsideBubble);
  renderCustomInterestList(preferencesCustomList,userPreferences.customInterests,index=>{
    userPreferences.customInterests.splice(index,1);
    userPreferences.preset=null;
    savePreferences();
    renderPreferences();
    if(activeData) render(activeData);
  });
}

function wireCustomInput(input,button,callback){
  if(!input||!button) return;
  const add=()=>{
    if(callback(input.value)){
      input.value='';
    }
  };
  button.addEventListener('click',add);
  input.addEventListener('keydown',event=>{
    if(event.key==='Enter'){
      event.preventDefault();
      add();
    }
  });
}

function setPreferencesOpen(open){
  if(!preferencesPanel) return;
  preferencesPanel.hidden=!open;
  document.body.classList.toggle('preferences-open',open);
}

function setupOnboarding(){
  if(!onboardingPanel||userPreferences.onboarded) return;

  const selected=new Set();
  const custom=[];
  let selectedVolume='standard';
  let selectedPreset=null;

  function refreshOnboardingSelection(){
    onboardingTopics?.querySelectorAll('.onboarding-topic').forEach(button=>{
      button.classList.toggle('active',selected.has(button.textContent));
    });
    onboardingSave.disabled=selected.size<3;
    onboardingStatus.textContent=selected.size<3
      ? 'Wybierz jeszcze '+(3-selected.size)
      : (selectedPreset?PRESETS[selectedPreset].name+' · '+selected.size+' tematów':'Wybrano '+selected.size+' tematów');
    onboardingVolume?.querySelectorAll('[data-volume]').forEach(button=>{
      button.classList.toggle('active',button.dataset.volume===selectedVolume);
    });
    onboardingPresets?.querySelectorAll('.preset-card').forEach(button=>{
      button.classList.toggle('active',button.dataset.preset===selectedPreset);
    });
  }

  onboardingTopics.innerHTML='';
  CATEGORIES.forEach(category=>{
    const button=document.createElement('button');
    button.type='button';
    button.className='onboarding-topic';
    button.textContent=category;
    button.addEventListener('click',()=>{
      selectedPreset=null;
      if(selected.has(category)) selected.delete(category);
      else selected.add(category);
      refreshOnboardingSelection();
    });
    onboardingTopics.appendChild(button);
  });

  renderPresetCards(onboardingPresets,key=>{
    const preset=PRESETS[key];
    selectedPreset=key;
    selected.clear();
    preset.categories.forEach(category=>selected.add(category));
    selectedVolume=preset.volume;
    if(onboardingBubble) onboardingBubble.checked=preset.outsideBubble;
    refreshOnboardingSelection();
  });

  const renderOnboardingCustom=()=>renderCustomInterestList(onboardingCustomList,custom,index=>{
    custom.splice(index,1);
    renderOnboardingCustom();
  });
  wireCustomInput(onboardingCustomInput,onboardingCustomAdd,value=>{
    const added=addCustomInterest(value,custom);
    if(added) renderOnboardingCustom();
    return added;
  });

  onboardingVolume?.querySelectorAll('[data-volume]').forEach(button=>{
    button.addEventListener('click',()=>{
      selectedVolume=button.dataset.volume;
      selectedPreset=null;
      refreshOnboardingSelection();
    });
  });

  onboardingSave?.addEventListener('click',()=>{
    if(selected.size<3) return;
    if(selectedPreset){
      userPreferences={...defaultPreferences(),onboarded:true,customInterests:[...custom]};
      applyPreset(selectedPreset);
      userPreferences.onboarded=true;
      userPreferences.customInterests=[...custom];
    }else{
      userPreferences={
        ...defaultPreferences(),
        onboarded:true,
        categories:Object.fromEntries(CATEGORIES.map(category=>[category,selected.has(category)?8:0])),
        enabledCategories:Object.fromEntries(CATEGORIES.map(category=>[category,selected.has(category)])),
        topics:{},
        customInterests:[...custom],
        volume:selectedVolume,
        outsideBubble:Boolean(onboardingBubble?.checked),
        preset:null,
        diversity:0.45
      };
    }
    savePreferences();
    onboardingPanel.hidden=true;
    document.body.classList.remove('onboarding-open');
    renderPreferences();
    if(activeData) render(activeData);
  });

  onboardingPanel.hidden=false;
  document.body.classList.add('onboarding-open');
}

wireCustomInput(preferencesCustomInput,preferencesCustomAdd,value=>{
  const added=addCustomInterest(value);
  if(added){
    savePreferences();
    renderPreferences();
    if(activeData) render(activeData);
  }
  return added;
});

async function loadArchiveForSearch(){
  if(!archiveDates.length) return [];
  const missing=archiveDates.filter(date=>!archiveCache.has(date));

  await Promise.all(missing.map(async date=>{
    try{
      const response=await fetch('./data/archive/'+date+'.json',{cache:'no-store'});
      if(!response.ok) return;
      const data=await response.json();
      archiveCache.set(date,data);
    }catch(_){}
  }));

  return archiveDates.flatMap(date=>{
    const data=archiveCache.get(date);
    if(!data) return [];
    return [...(data.top_stories||[]),...(data.more_stories||[])]
      .map(item=>({...item,archive_date:date}));
  });
}

function searchText(item){
  const digest=item.digest||{};
  return normalizeTopic([
    item.title,
    item.summary,
    item.why_it_matters,
    item.category,
    item.source,
    ...(item.topics||[]),
    digest.what_happened,
    digest.context,
    digest.what_next,
    ...(digest.key_points||[])
  ].filter(Boolean).join(' '));
}

async function runArchiveSearch(query){
  if(!archiveSearchResults||!archiveSearchStatus) return;
  const clean=normalizeTopic(query);

  if(clean.length<2){
    archiveSearchResults.hidden=true;
    archiveSearchResults.innerHTML='';
    archiveSearchStatus.textContent='';
    return;
  }

  archiveSearchStatus.textContent='Szukam…';
  const items=await loadArchiveForSearch();
  const words=clean.split(/\s+/).filter(Boolean);

  const results=items
    .filter(item=>{
      const haystack=searchText(item);
      return words.every(word=>haystack.includes(word));
    })
    .sort((a,b)=>String(b.archive_date).localeCompare(String(a.archive_date)))
    .slice(0,30);

  archiveSearchStatus.textContent=results.length
    ? results.length+' wyników'
    : 'Brak wyników';

  archiveSearchResults.innerHTML='';
  archiveSearchResults.hidden=false;

  if(!results.length){
    const empty=document.createElement('p');
    empty.className='empty';
    empty.textContent='Spróbuj innego hasła.';
    archiveSearchResults.appendChild(empty);
    return;
  }

  const heading=document.createElement('div');
  heading.className='section-head search-results-head';
  const h=document.createElement('h2');
  h.textContent='Wyniki wyszukiwania';
  heading.appendChild(h);

  const grid=document.createElement('div');
  grid.className='news-grid';
  results.forEach(item=>{
    const card=storyCard(item,false);
    const badge=document.createElement('span');
    badge.className='archive-result-date';
    badge.textContent=formatArchiveDay(item.archive_date);
    card.prepend(badge);
    grid.appendChild(card);
  });

  archiveSearchResults.append(heading,grid);
}

let archiveSearchTimer=null;
archiveSearchInput?.addEventListener('input',()=>{
  clearTimeout(archiveSearchTimer);
  archiveSearchTimer=setTimeout(()=>runArchiveSearch(archiveSearchInput.value),220);
});

savedToggle?.addEventListener('click',()=>{
  renderSavedPanel();
  setSavedOpen(true);
});
savedPanel?.addEventListener('click',event=>{
  if(event.target.closest('[data-close-saved]')) setSavedOpen(false);
});

categoryClear?.addEventListener('click',()=>{
  activeCategoryFilter=null;
  if(activeData) render(activeData);
});

preferencesToggle?.addEventListener('click',()=>setPreferencesOpen(true));
preferencesPanel?.addEventListener('click',event=>{
  if(event.target.closest('[data-close-preferences]')) setPreferencesOpen(false);
});
preferencesBubble?.addEventListener('change',()=>{
  userPreferences.outsideBubble=preferencesBubble.checked;
  userPreferences.preset=null;
  savePreferences();
  if(activeData) render(activeData);
});
preferencesReset?.addEventListener('click',()=>{
  userPreferences=defaultPreferences();
  userPreferences.onboarded=true;
  feedbackState={};
  savePreferences();
  saveFeedback();
  renderPreferences();
  if(activeData) render(activeData);
});

document.addEventListener('keydown',event=>{
  if(event.key==='Escape'&&preferencesPanel&&!preferencesPanel.hidden) setPreferencesOpen(false);
});

archiveToggle?.addEventListener('click',()=>{
  const open=archiveList.hidden;
  archiveList.hidden=!open;
  archiveToggle.setAttribute('aria-expanded',String(open));
});

renderSavedCount();
renderSavedPanel();
renderPreferences();
setupOnboarding();

fetch('./data/archive/index.json',{cache:'no-store'})
  .then(r=>{if(!r.ok) throw new Error('Brak indeksu archiwum');return r.json();})
  .then(index=>{
    archiveDates=index.dates||[];
    if(!archiveDates.length) throw new Error('Archiwum jest puste');
    activeDate=index.latest||archiveDates[0];
    renderDayNavigation();
    return loadBriefing(activeDate);
  })
  .catch(async()=>{
    try{
      const response=await fetch('./data/current.json',{cache:'no-store'});
      if(!response.ok) throw new Error();
      const data=await response.json();
      activeDate=data.date||null;
      archiveDates=activeDate?[activeDate]:[];
      renderDayNavigation();
      render(data);
    }catch{
      root.innerHTML='<p class="empty">Brak danych do wyświetlenia.</p>';
      updated.textContent='Brak danych';
    }
  });
