const root = document.querySelector('#news-root');
const updated = document.querySelector('#updated-at');
const nav = document.querySelector('#category-nav');
const dayNav = document.querySelector('#day-nav');
const archiveToggle = document.querySelector('#archive-toggle');
const archiveList = document.querySelector('#archive-list');

let archiveDates = [];
let activeDate = null;

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
  footer.append(date,link);

  card.append(meta,title,summary);
  if(item.why_it_matters) card.append(why);
  card.append(footer);
  return card;
}

function renderSection(title, items, featured=false){
  if(!items?.length) return null;
  const section=document.createElement('section');
  section.className='news-section' + (featured?' primary-section':'');
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

function render(data){
  updated.textContent=data.generated_at?'Aktualizacja: '+formatDate(data.generated_at):'Brak daty aktualizacji';
  root.innerHTML='';
  nav.innerHTML='';

  const top=data.top_stories||[];
  const more=data.more_stories||[];
  const categories=[...new Set([...top,...more].map(x=>x.category).filter(Boolean))];

  categories.forEach(category=>{
    const chip=document.createElement('span');
    chip.className='category-chip';
    chip.textContent=category;
    nav.appendChild(chip);
  });

  const isToday=activeDate===archiveDates[0];
  const topSection=renderSection(isToday?'Dzisiaj warto wiedzieć':'Warto było wiedzieć',top,true);
  const moreSection=renderSection('Jeszcze warto zobaczyć',more,false);
  if(topSection) root.appendChild(topSection);
  if(moreSection) root.appendChild(moreSection);

  if(!top.length && !more.length){
    root.innerHTML='<p class="empty">Brak wiadomości dla tego dnia.</p>';
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

archiveToggle?.addEventListener('click',()=>{
  const open=archiveList.hidden;
  archiveList.hidden=!open;
  archiveToggle.setAttribute('aria-expanded',String(open));
});

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
