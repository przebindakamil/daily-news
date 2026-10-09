const root = document.querySelector('#news-root');
const nav = document.querySelector('#category-nav');
const updated = document.querySelector('#updated-at');

function slugify(value=''){
  return value.toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g,'')
    .replace(/ł/g,'l')
    .replace(/[^a-z0-9]+/g,'-')
    .replace(/^-|-$/g,'');
}

function formatDate(value){
  if(!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('pl-PL',{dateStyle:'medium',timeStyle:'short'}).format(date);
}

function countLabel(count){
  if(count===1) return '1 wiadomość';
  const lastTwo=count%100, last=count%10;
  if(last>=2 && last<=4 && !(lastTwo>=12 && lastTwo<=14)) return count+' wiadomości';
  return count+' wiadomości';
}

function render(data){
  const groups = data.categories || [];
  updated.textContent = data.generated_at ? 'Aktualizacja: ' + formatDate(data.generated_at) : 'Brak daty aktualizacji';
  nav.innerHTML = '';
  root.innerHTML = '';

  groups.forEach((group,index)=>{
    const id=slugify(group.name);

    const button=document.createElement('button');
    button.className='category-button' + (index===0?' active':'');
    button.textContent=group.name;
    button.addEventListener('click',()=>document.querySelector('#'+id)?.scrollIntoView({behavior:'smooth'}));
    nav.appendChild(button);

    const section=document.createElement('section');
    section.className='news-section';
    section.id=id;

    const head=document.createElement('div');
    head.className='section-head';
    const heading=document.createElement('h2');
    heading.textContent=group.name;
    const count=document.createElement('span');
    count.className='section-count';
    count.textContent=countLabel(group.items?.length||0);
    head.append(heading,count);

    const grid=document.createElement('div');
    grid.className='news-grid';

    (group.items||[]).forEach(item=>{
      const card=document.createElement('article');
      card.className='news-card';

      const meta=document.createElement('div');
      meta.className='news-meta';
      const source=document.createElement('span');
      source.textContent=item.source||'Źródło';
      const date=document.createElement('span');
      date.textContent=item.published_at?formatDate(item.published_at):'';
      meta.append(source,date);

      const title=document.createElement('h3');
      title.textContent=item.title||'Bez tytułu';

      const summary=document.createElement('p');
      summary.textContent=item.summary||'';

      const link=document.createElement('a');
      link.className='news-link';
      link.target='_blank';
      link.rel='noopener noreferrer';
      link.textContent='Czytaj u źródła';
      link.href=item.url||'#';

      card.append(meta,title,summary,link);
      grid.appendChild(card);
    });

    section.append(head,grid);
    root.appendChild(section);
  });

  if(!groups.length){
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

window.addEventListener('scroll',()=>{
  const sections=[...document.querySelectorAll('.news-section')];
  let active=sections[0]?.id;
  sections.forEach(section=>{
    if(section.getBoundingClientRect().top<160) active=section.id;
  });
  [...nav.children].forEach(btn=>btn.classList.toggle('active',slugify(btn.textContent)===active));
},{passive:true});
