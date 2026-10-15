export const DISCIPLINES = {
  'scientific-data':['科学数据','Scientific data'],
  'scientific-knowledge-models':['科学知识模型','Scientific knowledge models'],
  'scientific-foundation-models':['科学基础模型','Scientific foundation models'],
  'scientific-agents':['科学智能体','Scientific agents'],
  'scientific-evaluation':['科学评测','Scientific evaluation'],
  'autonomous-labs':['自主实验室','Autonomous laboratories'],
  'mathematical-sciences':['AI for 数理科学','AI for Mathematical Sciences'],
  'life-sciences':['AI for 生命科学','AI for Life Sciences'],
  'matter-sciences':['AI for 物质科学','AI for Matter Sciences'],
  'earth-space-sciences':['AI for 地球宇宙科学','AI for Earth & Space Sciences'],
  'information-sciences':['AI for 信息科学','AI for Information Sciences'],
  'social-sciences':['AI for 社会科学','AI for Social Sciences'],
};
export const resolveDiscipline=id=>({mathematics:'mathematical-sciences',physics:'mathematical-sciences',chemistry:'matter-sciences',materials:'matter-sciences',biology:'life-sciences',medicine:'life-sciences',weather:'earth-space-sciences',earth:'earth-space-sciences',communications:'information-sciences',chips:'information-sciences',general:'scientific-agents'}[id]||id);
export function relatedPapers(paper,papers) {
  const tags=paperTags(paper),score=entry=>paperTags(entry).filter(tag=>tags.includes(tag)).length;
  return papers.filter(entry=>entry.id!==paper.id&&score(entry)>0).sort((a,b)=>score(b)-score(a)||a.title?.localeCompare(b.title||'')||0);
}

export const paperTags = p => [...new Set([...(p.tags || []), ...(p.topics || [])])];
export const tagLabel = (tag, lang, translations = {}, englishLabels = {}) => lang === 'en' ? englishLabels[tag] || tag : translations[tag] || englishLabels[tag] || tag;
export function resolveTag(tag, vocabulary = []) {
  const key=value=>value.normalize('NFKC').trim().toLocaleLowerCase().replace(/\s+/g,' ');
  const requested=key(tag);
  return vocabulary.find(t=>[t.id,t.nameEn,t.nameZh,...(t.aliases||[])].some(name=>key(name)===requested))?.id||tag;
}
export function cardAbstract(p, lang) {
  const keys=lang==='en'?['abstract','abstractZh']:['abstractZh','abstract'];
  const key=keys.find(key=>p[key]);
  return {text:key?p[key]:'',isAbstract:key==='abstract'||key==='abstractZh'};
}
export function tagCounts(papers) {
  const counts = new Map();
  for (const p of papers) for (const tag of paperTags(p)) counts.set(tag, (counts.get(tag) || 0) + 1);
  return [...counts].sort((a,b)=>b[1]-a[1] || a[0].localeCompare(b[0]));
}
const LIST_PARAMS = ['discipline', 'q', 'tag', 'subfield', 'venue', 'year', 'saved', 'period', 'date', 'page', 'field', 'match', 'primary', 'sort', 'view', 'arxiv', 'github', 'sessions', 'rooms', 'lang', 'theme'];
export function listReturnUrl(search = '') {
  if (search && !search.startsWith('?')) return 'papers.html';
  const input = new URLSearchParams(search), clean = new URLSearchParams();
  for (const key of LIST_PARAMS) if (input.get(key)) clean.set(key, input.get(key));
  return 'papers.html' + (clean.size ? '?' + clean.toString() : '');
}
export function readingUrl(id, search = '') {
  const params = new URLSearchParams({ id });
  const from = listReturnUrl(search).slice('papers.html'.length);
  if (from) params.set('from', from);
  const input = new URLSearchParams(search);
  for (const key of ['lang', 'theme']) if (input.get(key)) params.set(key, input.get(key));
  return 'paper.html?' + params.toString();
}
export function detailReturnUrl(search = '') {
  const current=new URLSearchParams(search);
  const context=new URLSearchParams(listReturnUrl(current.get('from')||'').split('?')[1]||'');
  for(const key of ['lang','theme']) {
    if(current.get(key))context.set(key,current.get(key));
    else context.delete(key);
  }
  return 'papers.html'+(context.size?'?'+context.toString():'');
}

export function sortPapers(papers, sort = 'default') {
  const entries=[...papers];
  if(sort==='title') entries.sort((a,b)=>a.title.localeCompare(b.title));
  if(sort==='newest'||sort==='oldest') entries.sort((a,b)=>{
    if(!a.published)return b.published?1:0;
    if(!b.published)return -1;
    return sort==='oldest'?a.published.localeCompare(b.published):b.published.localeCompare(a.published);
  });
  return entries;
}
export function paginatePapers(papers,page=1,size=48) {
  size=Math.max(1,Math.min(200,Math.trunc(Number(size))||48));
  const pages=Math.max(1,Math.ceil(papers.length/size));
  page=Math.min(pages,Math.max(1,Math.trunc(Number(page))||1));
  return {page,pages,items:papers.slice((page-1)*size,page*size)};
}
export function arxivLink(paper) {
  for(const candidate of [paper.arxivUrl,paper.paperUrl,paper.pdfUrl,paper.abstractSource]) {
    try {const url=new URL(candidate);if(url.protocol==='https:'&&['arxiv.org','export.arxiv.org'].includes(url.hostname)&&/^\/(abs|pdf)\/.+/.test(url.pathname))return url.href;}catch{}
  }
  return '';
}
export function githubLink(paper) {
  try {const url=new URL(paper.codeUrl);if(url.protocol==='https:'&&url.hostname==='github.com'&&url.pathname.split('/').filter(Boolean).length>=2)return url.href;}catch{}
  return '';
}
function resourceMatches(paper,group,value) {
  if(!value||value==='all')return true;
  if(group==='arxiv') {
    const linked=!!arxivLink(paper),status=paper.arxivStatus||'';
    const review=status.startsWith('probable')||/^needs[ -]review/.test(status);
    const unknown=!linked&&!status&&!!paper.imported;
    return value==='yes'?linked:value==='strict'?linked&&status.startsWith('verified'):value==='review'?review:value==='unknown'?unknown:value==='no'?!linked&&!review&&!unknown:false;
  }
  const linked=!!githubLink(paper);
  const unknown=!linked&&(paper.codeAvailability==='unknown'||(paper.imported&&paper.codeAvailability!=='none'));
  return value==='yes'?linked:value==='page'?linked&&paper.githubSource==='page':value==='unknown'?unknown:value==='no'?!linked&&!unknown:false;
}
export function facetCounts(papers,filters,group,values) {
  const base={...filters,[group]:['sessions','rooms'].includes(group)?[]:'all'};
  return values.map(value=>[value,filterPapers(papers,{...base,[group]:['sessions','rooms'].includes(group)?[value]:value}).length]);
}
export function filterPapers(papers, { query = '', tag = '', topic = '', discipline = '', disciplines: selectedDisciplines = [], matchMode = 'any', primaryOnly = false, searchField = 'all', subfield = '', venue = '', year = '', decision = '', savedOnly = false, saved = [], period = 'all', date = '', arxiv = 'all', github = 'all', sessions = [], rooms = [] } = {}) {
  const terms = Array.from(query.trim().toLocaleLowerCase().matchAll(/"([^"]+)"|(\S+)/g),m=>m[1]||m[2]);
  let start = '', end = '';
  if (['day','week','month'].includes(period) && /^\d{4}-\d{2}-\d{2}$/.test(date)) {
    const anchor = new Date(date+'T00:00:00Z');
    if (!Number.isNaN(anchor.getTime())) {
      if (period==='week') anchor.setUTCDate(anchor.getUTCDate()-((anchor.getUTCDay()+6)%7));
      if (period==='month') anchor.setUTCDate(1);
      start=anchor.toISOString().slice(0,10);
      if (period==='month') anchor.setUTCMonth(anchor.getUTCMonth()+1);
      else anchor.setUTCDate(anchor.getUTCDate()+(period==='week'?7:1));
      end=anchor.toISOString().slice(0,10);
    }
  }
  return papers.filter(p => {
    const values = searchField==='title'?[p.title,p.titleZh]:searchField==='authors'?p.authors||[]:searchField==='abstract'?[p.abstract,p.abstractZh]:searchField==='id'?[p.id]:[p.title, p.titleZh, p.summaryZh, p.summaryEn, p.abstract, p.abstractZh, p.id, p.subfield, p.venue, ...(p.authors || []), ...(p.affiliations || []), ...(p.keywords || []), ...paperTags(p)];
    const text = values.join(' ').toLocaleLowerCase();
    const disciplines = p.disciplines || [];
    const matches=id=>id==='unclassified'?!disciplines.length:(primaryOnly?disciplines[0]===id:disciplines.includes(id));
    return terms.every(term => text.includes(term)) && (!topic || (p.topics || []).includes(topic))
      && (!selectedDisciplines.length || (matchMode==='all'?selectedDisciplines.every(matches):selectedDisciplines.some(matches)))
      && (!tag || paperTags(p).includes(tag))
      && (!discipline || (discipline === 'unclassified' ? !disciplines.length : disciplines.includes(discipline)))
      && (!subfield || p.subfield === subfield) && (!venue || p.venue === venue)
      && (!year || String(p.year || '') === year) && (!decision || (p.decision || 'unknown') === decision)
      && resourceMatches(p,'arxiv',arxiv) && resourceMatches(p,'github',github)
      && (!sessions.length || sessions.includes(p.session||'__unlisted__'))
      && (!rooms.length || rooms.includes(p.room||'__unlisted__'))
      && (!savedOnly || saved.includes(p.id));
  }).filter(p=>!start || (p.published >= start && p.published < end)).sort((a, b) => (b.published || '').localeCompare(a.published || '') || a.title.localeCompare(b.title));
}
