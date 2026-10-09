const root = document.querySelector('#news-root');
const updated = document.querySelector('#updated-at');
const nav = document.querySelector('#category-nav');
const dayNav = document.querySelector('#day-nav');
const archiveToggle = document.querySelector('#archive-toggle');
const archiveList = document.querySelector('#archive-list');

const preferencesToggle = document.querySelector('#preferences-toggle');
const preferencesPanel = document.querySelector('#preferences-panel');
const preferencesList = document.querySelector('#preferences-list');
const preferencesReset = document.querySelector('#preferences-reset');
const preferencesVolume = document.querySelector('#preferences-volume');
const preferencesBubble = document.querySelector('#preferences-bubble');

const onboardingPanel = document.querySelector('#onboarding-panel');
const onboardingTopics = document.querySelector('#onboarding-topics');
const onboardingVolume = document.querySelector('#onboarding-volume');
const onboardingBubble = document.querySelector('#onboarding-bubble');
const onboardingSave = document.querySelector('#onboarding-save');
const onboardingStatus = document.querySelector('#onboarding-status');

const PREFS_KEY = 'daily-news-user-preferences-v2';
const FEEDBACK_KEY = 'daily-news-feedback-v1';

const CATEGORIES = [
  'AI i technologia',
  'Piłka nożna',
  'Sport i trening',
  'Finanse i biznes',
  'Polska i świat',
  'Nauka',
  'Motoryzacja',
  'Podróże',
  'Kultura'
];

const VOLUME_LIMITS = {
  short: 5,
  standard: 9,
  more: 15
};

function defaultPreferences(){
  return {
    onboarded: false,
    categories: Object.fromEntries(CATEGORIES.map(category => [category, 5])),
    enabledCategories: Object.fromEntries(CATEGORIES.map(category => [category, true])),
    topics: {},
    volume: 'standard',
    outsideBubble: true
  };
}

let archiveDates = [];
let activeDate = null;
let activeData = null;

function loadJson(key, fallback){
  try {
    const value = JSON.parse(localStorage.getItem(key) || '');
    return value && typeof value === 'object' ? value : fallback;
  } catch (_) {
    return fallback;
  }
}

let userPreferences = {...defaultPreferences(), ...loadJson(PREFS_KEY, {})};
userPreferences.categories = {...defaultPreferences().categories, ...(userPreferences.categories || {})};
userPreferences.enabledCategories = {...defaultPreferences().enabledCategories, ...(userPreferences.enabledCategories || {})};
userPreferences.topics = userPreferences.topics || {};
let feedbackState = loadJson(FEEDBACK_KEY, {});

function savePreferences(){
  localStorage.setItem(PREFS_KEY, JSON.stringify(userPreferences));
}

function saveFeedback(){
  localStorage.setItem(FEEDBACK_KEY, JSON.stringify(feedbackState));
}

function formatDate(value){
  if(!value) return '';
  const date = new Date(value);
  if(Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('pl-PL',{dateStyle:'medium',timeStyle:'short'}).format(date);
}

function formatDayLabel(dateString, index){
  if(index===0) return 'Dzisiaj';
  if(index===1) return 'Wczoraj';
  const date=new Date(dateString+'T12:00:00');
  return new Intl.DateTimeFormat('pl-PL',{day:'numeric',month:'short'}).format(date);
}

function formatArchiveDay(dateString){
  const date=new Date(dateString+'T12:00:00');
  return new Intl.DateTimeFormat('pl-PL',{weekday:'short',day:'numeric',month:'long',year:'numeric'}).format(date);
}

function normalizeTopic(value=''){
  return value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').trim();
}

function itemId(item){
  return item.url || item.title || JSON.stringify(item);
}

function editorialScore(item){
  const raw = Number(item.editorial_score);
  return Number.isFinite(raw) && raw > 0 ? Math.min(10, raw) : 7;
}

function isCategoryEnabled(category){
  return userPreferences.enabledCategories?.[category] !== false;
}

function categoryWeight(item){
  return Number(userPreferences.categories?.[item.category] ?? 5);
}

function topicAffinity(item){
  const topics = Array.isArray(item.topics) ? item.topics : [];
  if(!topics.length) return 5;
  const scores = topics.map(topic => Number(userPreferences.topics?.[normalizeTopic(topic)] ?? 5));
  return scores.reduce((a,b)=>a+b,0) / scores.length;
}

function explicitFeedback(item){
  const value = feedbackState[itemId(item)];
  if(value === 'more') return 10;
  if(value === 'less') return 0;
  return 5;
}

function personalizedScore(item){
  return (
    editorialScore(item) * .58 +
    categoryWeight(item) * .22 +
    topicAffinity(item) * .12 +
    explicitFeedback(item) * .08
  );
}

function currentDailyLimit(){
  return VOLUME_LIMITS[userPreferences.volume] || VOLUME_LIMITS.standard;
}

function applyFeedback(item, direction){
  const id = itemId(item);
  feedbackState[id] = direction;
  saveFeedback();

  const delta = direction === 'more' ? .8 : -.8;
  const category = item.category;
  if(category){
    const current = Number(userPreferences.categories?.[category] ?? 5);
    userPreferences.categories[category] = Math.max(0, Math.min(10, current + delta * .35));
  }

  (item.topics || []).forEach(topic=>{
    const key = normalizeTopic(topic);
    const current = Number(userPreferences.topics?.[key] ?? 5);
    userPreferences.topics[key] = Math.max(0, Math.min(10, current + delta));
  });

  savePreferences();
  renderPreferences();
  if(activeData) render(activeData);
}

function recordSourceClick(item){
  const category = item.category;
  if(category){
    const current = Number(userPreferences.categories?.[category] ?? 5);
    userPreferences.categories[category] = Math.min(10, current + .08);
  }
  (item.topics || []).forEach(topic=>{
    const key = normalizeTopic(topic);
    const current = Number(userPreferences.topics?.[key] ?? 5);
    userPreferences.topics[key] = Math.min(10, current + .12);
  });
  savePreferences();
}

function storyCard(item, featured=false){
  const card=document.createElement('article');
  card.className='news-card' + (featured?' featured':'');

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

  const why=document.createElement('p');
  why.className='why-it-matters';
  if(item.why_it_matters){
    why.innerHTML='<strong>Dlaczego warto wiedzieć:</strong> ';
    why.append(document.createTextNode(item.why_it_matters));
  }

  const topics=document.createElement('div');
  topics.className='news-topics';
  (item.topics||[]).slice(0,4).forEach(topic=>{
    const tag=document.createElement('span');
    tag.textContent=topic;
    topics.appendChild(tag);
  });

  const feedback=document.createElement('div');
  feedback.className='feedback-actions';
  const more=document.createElement('button');
  more.type='button';
  more.textContent='Więcej takich';
  more.className='feedback-button';
  const less=document.createElement('button');
  less.type='button';
  less.textContent='Mniej takich';
  less.className='feedback-button';
  const current=feedbackState[itemId(item)];
  if(current==='more') more.classList.add('active');
  if(current==='less') less.classList.add('active');
  more.addEventListener('click',()=>applyFeedback(item,'more'));
  less.addEventListener('click',()=>applyFeedback(item,'less'));
  feedback.append(more,less);

  const footer=document.createElement('div');
  footer.className='news-footer';
  const date=document.createElement('span');
  date.textContent=item.published_at?formatDate(item.published_at):'';
  const link=document.createElement('a');
  link.className='news-link';
  link.target='_blank';
  link.rel='noopener noreferrer';
  link.textContent='Czytaj u źródła';
  link.href=item.url||'#';
  link.addEventListener('click',()=>recordSourceClick(item));
  footer.append(date,link);

  card.append(meta,title,summary);
  if(item.why_it_matters) card.append(why);
  if((item.topics||[]).length) card.append(topics);
  card.append(feedback,footer);
  return card;
}

function renderSection(title, items, featured=false, className=''){
  if(!items?.length) return null;
  const section=document.createElement('section');
  section.className='news-section' + (featured?' primary-section':'') + (className?' '+className:'');
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
  items.forEach((item,index)=>grid.appendChild(storyCard(item,featured && index===0)));

  section.append(head,grid);
  return section;
}

function splitPersonalized(items){
  const limit = Math.min(currentDailyLimit(), items.length);
  const enabled = items
    .filter(item=>isCategoryEnabled(item.category))
    .sort((a,b)=>personalizedScore(b)-personalizedScore(a));

  const reserveBubble = userPreferences.outsideBubble && limit > 2 ? 1 : 0;
  const personalLimit = Math.max(1, limit - reserveBubble);
  const selected = enabled.slice(0, personalLimit);
  const used = new Set(selected.map(itemId));

  let outsideBubble = null;
  if(userPreferences.outsideBubble){
    const bubbleCandidates = items
      .filter(item=>!used.has(itemId(item)))
      .filter(item=>!isCategoryEnabled(item.category) || categoryWeight(item)<=5)
      .sort((a,b)=>editorialScore(b)-editorialScore(a));
    outsideBubble = bubbleCandidates[0] || null;
    if(outsideBubble) used.add(itemId(outsideBubble));
  }

  if(!outsideBubble && selected.length < limit){
    const fallback = enabled.find(item=>!used.has(itemId(item)));
    if(fallback){
      selected.push(fallback);
      used.add(itemId(fallback));
    }
  }

  const forYouCount = Math.min(selected.length, currentDailyLimit() <= 5 ? 4 : 5);
  const forYou = selected.slice(0, forYouCount);
  const rest = selected.slice(forYouCount);

  return {forYou,outsideBubble,rest};
}

function render(data){
  activeData=data;
  updated.textContent=data.generated_at?'Aktualizacja: '+formatDate(data.generated_at):'Brak daty aktualizacji';
  root.innerHTML='';
  nav.innerHTML='';

  const all=[...(data.top_stories||[]),...(data.more_stories||[])];
  if(!all.length){
    root.innerHTML='<p class="empty">Brak wiadomości dla tego dnia.</p>';
    return;
  }

  const {forYou,outsideBubble,rest}=splitPersonalized(all);
  const visible=[...forYou,...rest,...(outsideBubble?[outsideBubble]:[])];
  const categories=[...new Set(visible.map(x=>x.category).filter(Boolean))];

  categories.forEach(category=>{
    const chip=document.createElement('span');
    chip.className='category-chip';
    chip.textContent=category;
    nav.appendChild(chip);
  });

  const isToday=activeDate===archiveDates[0];
  const personalSection=renderSection(isToday?'Dla Ciebie':'Najlepiej dopasowane',forYou,true);
  if(personalSection) root.appendChild(personalSection);

  if(outsideBubble){
    const bubble=renderSection('Poza twoją bańką',[outsideBubble],false,'outside-bubble-section');
    if(bubble) root.appendChild(bubble);
  }

  const restSection=renderSection('Jeszcze warto zobaczyć',rest,false);
  if(restSection) root.appendChild(restSection);

  if(!forYou.length && !outsideBubble && !rest.length){
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
    button.className='day-button' + (date===activeDate?' active':'');
    button.textContent=formatDayLabel(date,index);
    button.addEventListener('click',()=>loadBriefing(date));
    dayNav.appendChild(button);
  });

  archiveList.innerHTML='';
  archiveDates.forEach(date=>{
    const button=document.createElement('button');
    button.type='button';
    button.className='archive-day' + (date===activeDate?' active':'');
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
  [
    ['short','Krótko','około 5'],
    ['standard','Standard','około 9'],
    ['more','Więcej','do 15']
  ].forEach(([key,label,detail])=>{
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

function renderPreferences(){
  if(!preferencesList) return;
  preferencesList.innerHTML='';

  CATEGORIES.forEach(category=>{
    const row=document.createElement('div');
    row.className='preference-row';

    const toggle=document.createElement('input');
    toggle.type='checkbox';
    toggle.className='category-enable';
    toggle.checked=isCategoryEnabled(category);
    toggle.setAttribute('aria-label','Włącz '+category);

    const name=document.createElement('span');
    name.textContent=category;

    const input=document.createElement('input');
    input.type='range';
    input.min='0';
    input.max='10';
    input.step='1';
    input.value=String(Math.round(userPreferences.categories?.[category] ?? 5));
    input.disabled=!toggle.checked;

    const value=document.createElement('output');
    value.textContent=input.value;

    toggle.addEventListener('change',()=>{
      userPreferences.enabledCategories[category]=toggle.checked;
      input.disabled=!toggle.checked;
      savePreferences();
      if(activeData) render(activeData);
    });

    input.addEventListener('input',()=>{
      value.textContent=input.value;
      userPreferences.categories[category]=Number(input.value);
      savePreferences();
      if(activeData) render(activeData);
    });

    row.append(toggle,name,input,value);
    preferencesList.appendChild(row);
  });

  renderVolumeOptions(preferencesVolume);
  if(preferencesBubble) preferencesBubble.checked=Boolean(userPreferences.outsideBubble);
}

function setPreferencesOpen(open){
  if(!preferencesPanel) return;
  preferencesPanel.hidden=!open;
  document.body.classList.toggle('preferences-open',open);
}

function setupOnboarding(){
  if(!onboardingPanel || userPreferences.onboarded) return;

  const selected = new Set();
  let selectedVolume='standard';

  onboardingTopics.innerHTML='';
  CATEGORIES.forEach(category=>{
    const button=document.createElement('button');
    button.type='button';
    button.className='onboarding-topic';
    button.textContent=category;
    button.addEventListener('click',()=>{
      if(selected.has(category)){
        selected.delete(category);
        button.classList.remove('active');
      }else{
        selected.add(category);
        button.classList.add('active');
      }
      onboardingSave.disabled=selected.size<3;
      onboardingStatus.textContent=selected.size<3
        ? 'Wybierz jeszcze '+(3-selected.size)
        : 'Wybrano '+selected.size+' tematów';
    });
    onboardingTopics.appendChild(button);
  });

  onboardingVolume?.querySelectorAll('[data-volume]').forEach(button=>{
    button.addEventListener('click',()=>{
      selectedVolume=button.dataset.volume;
      onboardingVolume.querySelectorAll('[data-volume]').forEach(x=>x.classList.toggle('active',x===button));
    });
  });

  onboardingSave?.addEventListener('click',()=>{
    if(selected.size<3) return;

    userPreferences = {
      ...defaultPreferences(),
      onboarded:true,
      categories:Object.fromEntries(CATEGORIES.map(category=>[category,selected.has(category)?8:0])),
      enabledCategories:Object.fromEntries(CATEGORIES.map(category=>[category,selected.has(category)])),
      topics:{},
      volume:selectedVolume,
      outsideBubble:Boolean(onboardingBubble?.checked)
    };

    savePreferences();
    onboardingPanel.hidden=true;
    document.body.classList.remove('onboarding-open');
    renderPreferences();
    if(activeData) render(activeData);
  });

  onboardingPanel.hidden=false;
  document.body.classList.add('onboarding-open');
}

preferencesToggle?.addEventListener('click',()=>setPreferencesOpen(true));
preferencesPanel?.addEventListener('click',event=>{
  if(event.target.closest('[data-close-preferences]')) setPreferencesOpen(false);
});
preferencesBubble?.addEventListener('change',()=>{
  userPreferences.outsideBubble=preferencesBubble.checked;
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
  if(event.key==='Escape' && preferencesPanel && !preferencesPanel.hidden) setPreferencesOpen(false);
});

archiveToggle?.addEventListener('click',()=>{
  const open=archiveList.hidden;
  archiveList.hidden=!open;
  archiveToggle.setAttribute('aria-expanded',String(open));
});

renderPreferences();
setupOnboarding();

fetch('./data/archive/index.json',{cache:'no-store'})
  .then(r=>{if(!r.ok) throw new Error('Brak indeksu archiwum'); return r.json();})
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
