import { DISCIPLINES, filterPapers, readingUrl, paperTags, tagCounts, cardAbstract, tagLabel, resolveTag } from './papers-core.mjs?v=20261012-vocabulary';
const root = document.documentElement, $ = id => document.getElementById(id);
const list = $('paper-list'), message = $('papers-message');
const fields = {q:$('paper-search'),subfield:$('subfield-filter'),venue:$('venue-filter'),year:$('year-filter')};
const savedOnly = $('saved-only'), storageKey = 'ai4s-saved-papers';
let papers = [], saved = [], discipline = '', selectedTag = '', loaded = false, storageAvailable = true;
const cardLanguages = new Map();
let tagTranslations = {};
let tagLabelsEn = {}, tagVocabulary = [];
const tr = (zh,en) => root.lang === 'en' ? en : zh;
try { const v = JSON.parse(localStorage.getItem(storageKey) || '[]'); saved = Array.isArray(v) ? v.filter(id => typeof id === 'string') : []; } catch { storageAvailable = false; }
function node(tag,text,cls) { const el=document.createElement(tag); if(text!==undefined) el.textContent=text; if(cls) el.className=cls; return el; }
function resource(text,url) {
  try { const parsed=new URL(url); if(parsed.protocol!=='https:') return null; const a=node('a',text); a.href=parsed.href; a.target='_blank'; a.rel='noopener noreferrer'; return a; } catch { return null; }
}
function disciplineName(id) { if(id==='unclassified') return tr('待分类','Unclassified'); if(id==='general') return tr(...DISCIPLINES.general); return DISCIPLINES[id] ? 'AI for '+tr(...DISCIPLINES[id]) : id; }
const decisionName = v => !v || v==='unknown' ? tr('未公开 / 未收录','Not available') : v;
function tags(values,cls) { const box=node('div',undefined,'paper-tags'); values.forEach(v=>box.append(node('span',v,cls))); return box; }
function readUrl() {
  const params=new URLSearchParams(location.search);
  for(const [name,el] of Object.entries(fields)) el.value=params.get(name)||'';
  discipline=params.get('discipline')||''; selectedTag=resolveTag(params.get('tag')||'',tagVocabulary); savedOnly.checked=params.get('saved')==='1'; return params.get('paper')||'';
}
function syncUrl() {
  const url=new URL(location.href), values={discipline,tag:selectedTag,saved:savedOnly.checked?'1':'',paper:''};
  url.searchParams.delete('decision');
  for(const [name,el] of Object.entries(fields)) values[name]=el.value.trim();
  for(const [name,value] of Object.entries(values)) { if(value) url.searchParams.set(name,value); else url.searchParams.delete(name); }
  history.replaceState({},'',url);
}
function populateFilters() {
  const subset=papers.filter(p=>!discipline || (discipline==='unclassified'?!p.disciplines?.length:p.disciplines?.includes(discipline)));
  for(const field of ['subfield','venue','year']) {
    const select=fields[field], selected=select.value;
    const values=[...new Set((field==='subfield'?subset:papers).map(p=>String(p[field]||'')).filter(Boolean))].sort();
    if(field==='year') values.reverse(); if(selected&&!values.includes(selected)) values.push(selected);
    select.replaceChildren(); const all=node('option',tr('全部','All')); all.value=''; select.append(all);
    for(const v of values) { const option=node('option',v); option.value=v; select.append(option); }
    select.value=selected;
  }
}
function toggleSave(id) {
  saved=saved.includes(id)?saved.filter(v=>v!==id):[...saved,id];
  try { localStorage.setItem(storageKey,JSON.stringify(saved)); } catch { storageAvailable=false; }
  render(); const buttons=[...list.querySelectorAll('[data-save]')]; (buttons.find(b=>b.dataset.save===id)||buttons[0]||savedOnly).focus();
}
function render() {
  if(!loaded) return;
  populateFilters(); const categories=$('paper-disciplines'); categories.replaceChildren();
  for(const id of ['',...Object.keys(DISCIPLINES),'unclassified']) {
    const count=id?papers.filter(p=>id==='unclassified'?!p.disciplines?.length:p.disciplines?.includes(id)).length:papers.length;
    const b=node('button',undefined,'discipline-button'); b.type='button'; b.dataset.discipline=id;
    b.append(node('span',id?disciplineName(id):tr('全部学科','All disciplines')),node('span',String(count),'discipline-count'));
    b.setAttribute('aria-pressed',String(discipline===id));
    b.addEventListener('click',()=>{discipline=id;fields.subfield.value='';syncUrl();render();[...categories.children].find(b=>b.dataset.discipline===id)?.focus();}); categories.append(b);
  }
  const filters={query:fields.q.value,discipline,subfield:fields.subfield.value,venue:fields.venue.value,year:fields.year.value,savedOnly:savedOnly.checked,saved};
  const filtered=filterPapers(papers,{...filters,tag:selectedTag});
  const tagBox=$('tag-filters'); tagBox.replaceChildren();
  for(const [tag,count] of [['',filterPapers(papers,filters).length],...tagCounts(filterPapers(papers,filters))]) {
    const b=node('button',(tag?tagLabel(tag,root.lang,tagTranslations,tagLabelsEn):tr('全部标签','All tags'))+' · '+count);b.type='button';b.dataset.tag=tag;b.setAttribute('aria-pressed',String(selectedTag===tag));
    b.addEventListener('click',()=>{selectedTag=tag;syncUrl();render();[...tagBox.children].find(b=>b.dataset.tag===tag)?.focus();});tagBox.append(b);
  }
  if(selectedTag && ![...tagBox.children].some(b=>b.dataset.tag===selectedTag)) {const b=node('button',tagLabel(selectedTag,root.lang,tagTranslations,tagLabelsEn)+' · 0');b.type='button';b.setAttribute('aria-pressed','true');b.addEventListener('click',()=>{selectedTag='';syncUrl();render();});tagBox.append(b);}
  const extension=$('keyword-extension');extension.replaceChildren();
  if(fields.q.value.trim()) {
    extension.append(node('span',tr('延伸检索：','Explore: ')));
    for(const [label,url] of [['Google Scholar','https://scholar.google.com/scholar?q='],['arXiv','https://arxiv.org/search/?searchtype=all&query=']]) extension.append(resource(label+' ↗',url+encodeURIComponent(fields.q.value.trim())));
  }
  $('paper-count').textContent=tr(`显示 ${filtered.length} / ${papers.length} 篇论文`,`Showing ${filtered.length} of ${papers.length} papers`);
  $('storage-note').textContent=storageAvailable?tr('收藏仅保存在当前浏览器','Bookmarks stay in this browser'):tr('存储不可用，收藏仅本次有效','Bookmarks last for this visit only');
  $('collection-scope').textContent=papers.some(p=>p.sample)?tr('包含测试样例；收录数不代表会议论文总数。','Includes test entries; counts reflect this collection, not conference totals.'):tr('仅统计本站收录论文。','Counts reflect this collection only.');
  list.replaceChildren(); message.hidden=filtered.length>0; message.textContent=tr('没有匹配的论文。试试清空筛选或更换关键词。','No matching papers. Clear filters or try another keyword.');
  for(const p of filtered) {
    const lang=cardLanguages.get(p.id)||root.lang, ct=(zh,en)=>lang==='en'?en:zh;
    const item=node('article',undefined,'paper-entry');
    item.dataset.paperId=p.id;
    const header=node('div',undefined,'paper-entry-header');
    header.append(tags((p.disciplines?.length?p.disciplines:['unclassified']).map(disciplineName),'discipline-tag'));
    header.append(node('span',[p.venue,p.year,p.subfield].filter(Boolean).join(' · '),'paper-entry-meta'));
    if(p.sample) header.append(node('span',tr('测试样例','Test entry'),'sample-badge'));
    const switcher=node('button',ct('EN','中文'),'card-language');switcher.type='button';switcher.dataset.language=p.id;switcher.setAttribute('aria-label',tr('切换卡片语言：','Switch card language: ')+p.title);
    switcher.addEventListener('click',()=>{cardLanguages.set(p.id,lang==='en'?'zh':'en');render();[...list.querySelectorAll('[data-language]')].find(b=>b.dataset.language===p.id)?.focus();});header.append(switcher);
    const heading=node('h2'), title=node('a',lang==='en'?p.title:p.titleZh||p.title,'paper-title');
    title.href=readingUrl(p.id,location.search);heading.append(title);
    item.append(header,heading);
    if(lang!=='en'&&p.titleZh) item.append(node('p',p.title,'paper-english-title'));
    item.append(node('p',(p.authors||[]).join(' · '),'paper-authors'),node('p',ct('单位：','Affiliations: ')+(p.affiliations?.join(' · ')||ct('待补充','Not available')),'paper-affiliations'));
    const abstract=cardAbstract(p,lang);
    item.append(node('h3',ct('摘要','Abstract'),'card-section-label'),node('p',abstract.text||ct('摘要待补充','Abstract not available'),'paper-intro'));
    if(abstract.text && lang!=='en' && !p.abstractZh) item.append(node('p','暂无中文译文，显示英文原摘要。','translation-note'));
    if(abstract.text && lang==='en' && !p.abstract) item.append(node('p','English abstract unavailable; showing the Chinese translation.','translation-note'));
    if(p.abstractSource) {
      const attribution=node('p',undefined,'translation-note');
      const source=resource(ct('摘要来源 ↗','Abstract source ↗'),p.abstractSource);
      if(source) attribution.append(source);
      if(lang!=='en' && p.abstractZh) attribution.append(document.createTextNode(' · 中文译文'));
      if(p.abstractLicense) {const license=resource(' · CC BY 4.0',p.abstractLicense);if(license) attribution.append(license);}
      item.append(attribution);
    }
    const keywords=node('div',undefined,'paper-tags');keywords.append(node('span',ct('关键词','Keywords'),'tag-label'));
    for(const keyword of [...new Set(p.keywords||[])]) {const b=node('button',keyword);b.type='button';b.addEventListener('click',()=>{fields.q.value=keyword;syncUrl();render();fields.q.focus();});keywords.append(b);}item.append(keywords);
    const tagList=paperTags(p), labels=node('div',undefined,'paper-tags card-tags');labels.append(node('span',ct(`标签 · ${tagList.length}`,`Tags · ${tagList.length}`),'tag-label'));
    for(const tag of tagList) {const b=node('button',tagLabel(tag,lang,tagTranslations,tagLabelsEn));b.type='button';b.setAttribute('aria-pressed',String(selectedTag===tag));b.addEventListener('click',()=>{selectedTag=tag;syncUrl();render();[...$('tag-filters').children].find(b=>b.dataset.tag===tag)?.focus();});labels.append(b);}item.append(labels);
    const footer=node('div',undefined,'paper-entry-footer'), links=node('div',undefined,'paper-entry-links');
    const read=node('a',tr(p.hasNotes?'阅读 AI 解读':'查看论文 · 解读待补充',p.hasNotes?'Read AI summary':'View paper · Summary pending'));
    read.href=readingUrl(p.id,location.search);links.append(read);
    for(const [name,url] of [[tr('论文页面','Paper page'),p.paperUrl||p.forumUrl],['PDF',p.pdfUrl],[p.codeUrl?.startsWith('https://github.com/')?'GitHub':tr('代码','Code'),p.codeUrl]]) {const link=url&&resource(name+' ↗',url);if(link) links.append(link);}
    const save=node('button',saved.includes(p.id)?tr('已收藏','Saved'):tr('收藏','Save'));save.type='button';save.dataset.save=p.id;save.setAttribute('aria-pressed',String(saved.includes(p.id)));save.setAttribute('aria-label',tr('收藏论文：','Save paper: ')+p.title);save.addEventListener('click',()=>toggleSave(p.id));
    footer.append(links,save);item.append(footer);list.append(item);
  }
}
for(const [name,el] of Object.entries(fields)) el.addEventListener(name==='q'?'input':'change',()=>{syncUrl();render();});
savedOnly.addEventListener('change',()=>{syncUrl();render();});
$('clear-filters').addEventListener('click',()=>{for(const el of Object.values(fields)) el.value='';discipline='';selectedTag='';savedOnly.checked=false;syncUrl();render();fields.q.focus();});
new MutationObserver(render).observe(root,{attributes:true,attributeFilter:['lang','data-theme']});
window.addEventListener('popstate',()=>{readUrl();render();});
async function load() {
  message.hidden=false;message.textContent=tr('正在加载论文…','Loading papers…');
  try {
    const response=await fetch('data/papers-index.json', {cache:'no-cache'});if(!response.ok) throw new Error('Load failed');const data=await response.json();
    if(!Array.isArray(data.papers)||data.papers.some(p=>!p.id||!p.title||!Array.isArray(p.authors)||(p.disciplines&&!Array.isArray(p.disciplines)))) throw new Error('Invalid data');
    if(new Set(data.papers.map(p=>p.id)).size!==data.papers.length) throw new Error('Duplicate id');
    papers=data.papers;tagTranslations=data.tagTranslations||{};tagLabelsEn=data.tagLabelsEn||{};tagVocabulary=data.tagVocabulary||[];loaded=true;populateFilters();const id=readUrl();$('data-updated').textContent=data.updated||'—';if(data.updated) $('data-updated').dateTime=data.updated;render();if(id && papers.some(p=>p.id===id)) location.replace(readingUrl(id,location.search));
  } catch {message.replaceChildren(node('p',tr('论文数据暂时无法加载，请重试。','Could not load paper data. Please retry.')));const retry=node('button',tr('重试','Retry'));retry.type='button';retry.addEventListener('click',load);message.append(retry);}
}
load();
