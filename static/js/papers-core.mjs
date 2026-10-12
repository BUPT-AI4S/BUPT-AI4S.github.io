export const DISCIPLINES = {
  general: ['通用 AI', 'General AI'],
  mathematics: ['数学', 'Mathematics'], physics: ['物理', 'Physics'], chemistry: ['化学', 'Chemistry'],
  materials: ['材料', 'Materials'], biology: ['生物', 'Biology'], medicine: ['医学', 'Medicine'],
  weather: ['气象', 'Weather & Climate'], communications: ['通信', 'Communications'],
  earth: ['地球科学', 'Earth Science'], chips: ['芯片', 'Chips'], other: ['其他学科', 'Other disciplines'],
};

export const paperTags = p => [...new Set([...(p.tags || []), ...(p.topics || [])])];
export const tagLabel = (tag, lang, translations = {}) => lang === 'en' ? tag : translations[tag] || tag;
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
const LIST_PARAMS = ['discipline', 'q', 'tag', 'subfield', 'venue', 'year', 'saved', 'lang', 'theme'];
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

export function filterPapers(papers, { query = '', tag = '', topic = '', discipline = '', subfield = '', venue = '', year = '', decision = '', savedOnly = false, saved = [] } = {}) {
  const terms = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  return papers.filter(p => {
    const text = [p.title, p.titleZh, p.summaryZh, p.summaryEn, p.abstract, p.abstractZh, p.id, p.subfield, p.venue, ...(p.authors || []), ...(p.affiliations || []), ...(p.keywords || []), ...paperTags(p)].join(' ').toLocaleLowerCase();
    const disciplines = p.disciplines || [];
    return terms.every(term => text.includes(term)) && (!topic || (p.topics || []).includes(topic))
      && (!tag || paperTags(p).includes(tag))
      && (!discipline || (discipline === 'unclassified' ? !disciplines.length : disciplines.includes(discipline)))
      && (!subfield || p.subfield === subfield) && (!venue || p.venue === venue)
      && (!year || String(p.year || '') === year) && (!decision || (p.decision || 'unknown') === decision)
      && (!savedOnly || saved.includes(p.id));
  }).sort((a, b) => (b.published || '').localeCompare(a.published || '') || a.title.localeCompare(b.title));
}
