const root = document.querySelector('#news-root');
const updated = document.querySelector('#updated-at');
const nav = document.querySelector('#category-nav');

function formatDate(value){
  if(!value) return '';
  const date = new Date(value);
  if(Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('pl-PL',{dateStyle:'medium',timeStyle:'short'}).format(date);
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

  const topSection=renderSection('Dzisiaj warto wiedzieć',top,true);
  const moreSection=renderSection('Jeszcze warto zobaczyć',more,false);
  if(topSection) root.appendChild(topSection);
  if(moreSection) root.appendChild(moreSection);

  if(!top.length && !more.length){
    root.innerHTML='<p class="empty">Brak wiadomości. Uruchom workflow generujący dane.</p>';
  }
}

fetch('./data/news.json',{cache:'no-store'})
  .then(r=>{if(!r.ok) throw new Error('Brak pliku news.json'); return r.json();})
  .then(render)
  .catch(err=>{
    root.innerHTML='<p class="empty">'+err.message+'</p>';
    updated.textContent='Brak danych';
  });
