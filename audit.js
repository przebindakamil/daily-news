/* Daily News editorial quality dashboard. Data originates in archived audit JSON files. */
const auditView = document.querySelector('#audit-view');
const auditDashboard = document.querySelector('#audit-dashboard');
const auditMessage = document.querySelector('#audit-message');
const auditWeekSelect = document.querySelector('#audit-week-select');
const auditStatusFilter = document.querySelector('#audit-status-filter');
let auditIndexPromise = null;
let auditCurrentReport = null;
const auditReportCache = new Map();

function auditElement(tag, className, value) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (value !== undefined) element.textContent = String(value);
  return element;
}

function auditSafeUrl(value) {
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) ? url.href : null;
  } catch (_) {
    return null;
  }
}

function auditExternalLink(label, url) {
  const safe = auditSafeUrl(url);
  if (!safe) return auditElement('span', 'audit-source-label', label);
  const anchor = auditElement('a', 'audit-source-link', label);
  anchor.href = safe;
  anchor.target = '_blank';
  anchor.rel = 'noopener noreferrer';
  return anchor;
}

function auditDate(value) {
  if (!value) return '—';
  const date = new Date(value + 'T12:00:00');
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('pl-PL', {day:'numeric',month:'short',year:'numeric'}).format(date);
}

function auditPercent(value) {
  return Number.isFinite(Number(value)) && value !== null ? Number(value).toFixed(0) + '%' : '—';
}

function auditStateLabel(value) {
  return ({covered:'Uwzględnione', partial:'Częściowe', missing:'Pominięte'})[value] || 'Do oceny';
}

function auditSelectWeek(week) {
  if (!/^\d{4}-W\d{2}$/.test(week)) return;
  location.hash = '#audit/' + week;
}

function auditRenderMetrics(report) {
  const metrics = report.metrics || {};
  const graded = report.status === 'complete';
  const values = [
    {value: auditPercent(metrics.coverage_percent), label:'Pokrycie ważnych wydarzeń', note:'Próba niezależnych nagłówków'},
    {value: graded ? metrics.audited_events : '—', label:'Wydarzenia w próbie', note:graded?'Zweryfikowane przez model':'Brak pełnego audytu'},
    {value: graded ? metrics.missing : '—', label:'Pominięte', note:graded?'Wśród ocenionych wydarzeń':'Nieocenione'},
    {value: (metrics.issues_available || 0) + '/7', label:'Dni z wydaniem', note:'Kompletność tygodnia'}
  ];
  const root = document.querySelector('#audit-metrics');
  root.replaceChildren();
  for (const item of values) {
    const card = auditElement('div', 'audit-metric');
    card.append(auditElement('strong', 'audit-metric-value', item.value));
    card.append(auditElement('span', 'audit-metric-label', item.label));
    card.append(auditElement('small', 'audit-metric-note', item.note));
    root.append(card);
  }
}

function auditRenderTrend(weeks, selectedWeek) {
  const root = document.querySelector('#audit-trend');
  root.replaceChildren();
  if (!weeks.length) {
    root.append(auditElement('p','audit-empty','Historia będzie pojawiać się co tydzień.'));
    return;
  }
  const chart = auditElement('div','audit-trend-chart');
  for (const row of weeks.slice(0,12).reverse()) {
    const button = auditElement('button','audit-trend-point' + (row.week===selectedWeek?' active':''));
    button.type = 'button';
    button.title = row.week + ': ' + auditPercent(row.coverage_percent);
    button.setAttribute('aria-label',row.week + ' — ' + auditPercent(row.coverage_percent));
    button.addEventListener('click',()=>auditSelectWeek(row.week));
    const barWrap = auditElement('span','audit-trend-track');
    const bar = auditElement('span','audit-trend-fill'+(row.coverage_percent===null?' unknown':''));
    bar.style.height = row.coverage_percent===null ? '8%' : Math.max(3,Number(row.coverage_percent)) + '%';
    barWrap.append(bar);
    button.append(barWrap,auditElement('small','audit-trend-week',row.week.split('-')[1]));
    chart.append(button);
  }
  root.append(chart);
}

function auditRenderCategories(report) {
  const root = document.querySelector('#audit-category-results');
  root.replaceChildren();
  const categories = Object.entries(report.category_results || {})
    .sort((a,b)=>b[1].audited-a[1].audited);
  if (!categories.length) {
    root.append(auditElement('p','audit-empty','Brak pełnych danych źródłowych do oceny kategorii.'));
    return;
  }
  for (const [category, counts] of categories) {
    const row = auditElement('div','audit-category-row');
    const header = auditElement('div','audit-category-head');
    header.append(auditElement('span','',category));
    const score = counts.audited ? (counts.covered + 0.5*counts.partial)/counts.audited*100 : null;
    header.append(auditElement('span','audit-category-percent',auditPercent(score) + ' · ' + counts.audited));
    const track = auditElement('div','audit-category-track');
    const fill = auditElement('span','audit-category-fill');
    fill.style.width = score===null?'0%':Math.min(100,score)+'%';
    track.append(fill);
    row.append(header,track);
    root.append(row);
  }
}

function auditRenderEvents(report) {
  const container = document.querySelector('#audit-events');
  container.replaceChildren();
  const all = Array.isArray(report.events) ? report.events : [];
  const filter = auditStatusFilter.value;
  const selected = all.filter(event=>filter==='all'||event.status===filter);
  if (!selected.length) {
    container.append(auditElement('p','audit-empty',all.length
      ? 'Brak wydarzeń o wybranym statusie.'
      : 'Dla tego tygodnia nie ma pełnego audytu wydarzeń. Wynik nie jest szacowany.'));
    return;
  }
  const sorted = [...selected].sort((a,b)=>{
    const importance = {missing:0,partial:1,covered:2};
    return (importance[a.status]??3)-(importance[b.status]??3)
      || Number(b.importance||0)-Number(a.importance||0);
  });
  for (const event of sorted) {
    const article = auditElement('article','audit-event');
    const row = auditElement('div','audit-event-top');
    row.append(auditElement('span','audit-event-badge status-'+event.status,auditStateLabel(event.status)));
    row.append(auditElement('span','audit-event-meta',event.day+' · '+(event.category||'Inne')));
    article.append(row, auditElement('h4','',event.title || 'Wydarzenie bez tytułu'));
    if (event.why_important) {
      const why = auditElement('p','audit-event-why',event.why_important);
      article.append(why);
    }
    if (event.reason) article.append(auditElement('p','audit-event-reason','Ocena: '+event.reason));
    const footer = auditElement('div','audit-event-footer');
    footer.append(auditExternalLink('Źródło referencyjne ↗',event.url));
    if (event.status !== 'covered') {
      const stage = ({
        ranked_not_published:'W rankingu, poza wydaniem',
        discovered_not_ranked:'Pobrane, odrzucone w rankingu',
        not_confirmed_in_candidate_pool:'Niepotwierdzone w zapisanej puli'
      })[event.pipeline] || 'Etap nieustalony';
      footer.append(auditElement('span','audit-pipeline',stage));
    }
    article.append(footer);
    if (event.matched_stories?.length) {
      const list = auditElement('div','audit-matches');
      list.append(auditElement('strong','', 'Powiązane publikacje'));
      for (const story of event.matched_stories) {
        const line = auditElement('div','');
        line.append(auditElement('span','',auditDate(story.day)+' · '));
        line.append(auditExternalLink(story.title||'Artykuł',story.url));
        list.append(line);
      }
      article.append(list);
    }
    container.append(article);
  }
}

function auditRenderDaily(report) {
  const root = document.querySelector('#audit-daily');
  root.replaceChildren();
  for (const day of report.daily || []) {
    const item = auditElement('div','audit-daily-row');
    item.append(auditElement('span','',auditDate(day.day)));
    const missingEdition=(report.missing_issue_days||[]).includes(day.day);
    const missingSources=(report.missing_coverage_days||[]).includes(day.day);
    item.append(auditElement('strong','',missingEdition?'Brak wydania':day.published+' publikacji'));
    item.append(auditElement('small','',missingSources?'Brak raportu źródeł':day.reference_headlines+' nagłówków referencyjnych'));
    root.append(item);
  }
}

function auditRenderDiagnostics(report) {
  const root = document.querySelector('#audit-diagnostics');
  root.replaceChildren();
  const metrics = report.metrics || {};
  const entries = [
    ['Raporty źródeł', (metrics.coverage_reports_available??0)+'/7'],
    ['Niezależne nagłówki', String(metrics.reference_headlines??0)],
    ['Puste źródła', (metrics.coverage_reports_available??0)>0 ? String(metrics.feed_failures??0) : '—'],
    ['Historie powtarzane', String(metrics.repeated_stories??0)]
  ];
  for (const [label,value] of entries) {
    const row = auditElement('div','audit-diagnostic-row');
    row.append(auditElement('span','',label),auditElement('strong','',value));
    root.append(row);
  }
  if (report.missing_issue_days?.length || report.missing_coverage_days?.length) {
    root.append(auditElement('p','audit-warning',
      'Brakujące dni: wydań — '+(report.missing_issue_days?.join(', ')||'brak')
      +'; raportów źródeł — '+(report.missing_coverage_days?.join(', ')||'brak')+'.'));
  }
  if (report.repeats?.length) {
    const list = auditElement('div','audit-repeats');
    list.append(auditElement('strong','','Powtarzające się materiały'));
    for (const item of report.repeats.slice(0,5)) {
      list.append(auditElement('p','',item.title+' · '+item.days.join(', ')));
    }
    root.append(list);
  }
}

function auditRenderReport(report, index) {
  auditCurrentReport = report;
  const complete = report.status==='complete';
  auditMessage.hidden = false;
  auditMessage.className = 'audit-message '+(complete?'audit-success':'audit-incomplete');
  auditMessage.textContent = complete
    ? 'Audyt zakończony. Wynik dotyczy próby niezależnych wydarzeń, nie wszystkich newsów.'
    : 'Audyt niepełny — '+(report.incomplete_reason||'Nie ma wystarczających danych do obliczenia pokrycia.');
  auditDashboard.hidden = false;
  document.querySelector('#audit-period').textContent =
    auditDate(report.start_date)+' – '+auditDate(report.end_date)+' · '+report.week;
  auditRenderMetrics(report);
  auditRenderTrend(index.weeks||[],report.week);
  auditRenderCategories(report);
  auditRenderEvents(report);
  auditRenderDaily(report);
  auditRenderDiagnostics(report);
  document.querySelector('#audit-methodology').textContent=report.methodology||'Wyniki są szacunkową oceną wyselekcjonowanej próby wiadomości.';
}

async function auditFetchIndex() {
  const result = await fetch('./reports/audits/index.json',{cache:'no-store'});
  if (!result.ok) throw new Error('Brak indeksu audytów.');
  return result.json();
}

async function loadAuditDashboard(requestedWeek) {
  auditMessage.hidden = false;
  auditMessage.className = 'audit-message';
  auditMessage.textContent = 'Wczytywanie audytów…';
  if (!auditIndexPromise) auditIndexPromise = auditFetchIndex().catch(e=>{auditIndexPromise=null;throw e;});
  try {
    const index = await auditIndexPromise;
    const weeks = Array.isArray(index.weeks)?index.weeks:[];
    auditWeekSelect.replaceChildren();
    for (const row of weeks) {
      const option = document.createElement('option');
      option.value = row.week;
      option.textContent = row.week+' · '+auditDate(row.start_date)+' – '+auditDate(row.end_date);
      auditWeekSelect.append(option);
    }
    if (!weeks.length) {
      auditDashboard.hidden = true;
      auditMessage.textContent = 'Pierwszy tygodniowy audyt pojawi się po zakończeniu pełnego tygodnia danych.';
      return;
    }
    const chosen = weeks.find(w=>w.week===requestedWeek) ? requestedWeek : index.latest||weeks[0].week;
    auditWeekSelect.value = chosen;
    if (!auditReportCache.has(chosen)) {
      const response = await fetch('./reports/audits/'+chosen+'.json',{cache:'no-store'});
      if (!response.ok) throw new Error('Nie udało się pobrać raportu '+chosen+'.');
      auditReportCache.set(chosen,await response.json());
    }
    if (!location.hash.startsWith('#audit')) return;
    const visibleWeek = location.hash.startsWith('#audit/') ? location.hash.slice(7) : chosen;
    if (visibleWeek !== chosen) return;
    auditRenderReport(auditReportCache.get(chosen),index);
  } catch (error) {
    auditDashboard.hidden = true;
    auditMessage.hidden = false;
    auditMessage.className = 'audit-message audit-incomplete';
    auditMessage.textContent = 'Nie udało się wczytać audytu: '+error.message;
  }
}

auditWeekSelect?.addEventListener('change',()=>auditSelectWeek(auditWeekSelect.value));
auditStatusFilter?.addEventListener('change',()=>{
  if (auditCurrentReport) auditRenderEvents(auditCurrentReport);
});
