import { DISCIPLINES, filterPapers, sortPapers, paginatePapers, readingUrl, paperTags, tagCounts, tagLabel, resolveTag, resolveDiscipline, facetCounts, arxivLink, githubLink } from './papers-core.mjs?v=20261015-import1';
const root=document.documentElement, $=id=>document.getElementById(id);
const tr=(zh,en)=>root.lang==='en'?en:zh;
const fields={q:$('paper-search'),subfield:$('subfield-filter'),venue:$('venue-filter'),year:$('year-filter')};
const savedOnly=$('saved-only'), primary=$('primary-only'), searchField=$('search-field'), sort=$('paper-sort');
const list=$('paper-list'), message=$('papers-message'), storageKey='ai4s-saved-papers';
let papers=[],saved=[],selected=[],selectedTag='',matchMode='any',view='cards',loaded=false,storageAvailable=true;
let translations={},englishLabels={},vocabulary=[];
let arxiv='all',github='all',sessions=[],rooms=[],page=1;
const arxivOptions=[['all','全部','All'],['yes','有 arXiv','Has arXiv'],['strict','严格验证（标题+作者）','Verified (title + authors)'],['review','可能匹配 / 待核对','Possible match / Needs review'],['no','未找到 arXiv','No arXiv found'],['unknown','未收录 arXiv 信息','arXiv not recorded']];
const githubOptions=[['all','全部','All'],['yes','有 GitHub','Has GitHub'],['page','官网页面提供','Linked from official page'],['no','无 GitHub','No GitHub'],['unknown','未收录代码信息','Code not recorded']];
const missing='__unlisted__';
function facetValues(key){const values=[...new Set(papers.map(p=>p[key]).filter(Boolean))].sort((a,b)=>a.localeCompare(b,undefined,{numeric:true}));if(papers.some(p=>!p[key]))values.push(missing);return values;}
function sessionLabel(value){return value===missing?tr('未收录场次','Session not listed'):root.lang==='en'?value:value.replace(/^Poster Session\s*/i,'场次 ');}
function roomLabel(value){return value===missing?tr('未收录会场','Room not listed'):value;}
const expanded=new Set();
function node(tag,text,cls){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(cls)el.className=cls;return el;}
function icon(name){
  const paths={star:'m12 3 2.8 5.7 6.3.9-4.6 4.4 1.1 6.3-5.6-3-5.6 3 1.1-6.3L3 9.6l6.2-.9Z',external:'M14 3h7v7M21 3 10 14M10 3H3v18h18v-7',file:'M14 3H5v18h14V8l-5-5Zm0 0v6h5',code:'m8 7-5 5 5 5m8-10 5 5-5 5m-3-13-2 20',calendar:'M5 5h14v16H5ZM8 2v6m8-6v6M5 11h14',chevron:'m8 10 4 4 4-4'};
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');
  const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',paths[name]||paths.external);svg.append(path);return svg;
}
function button(text,cls,action){const b=node('button',text,cls);b.type='button';b.addEventListener('click',action);return b;}
function paperLink(id,text){const a=node('a',text);a.href=readingUrl(id,location.search);a.target='_blank';a.rel='noopener noreferrer';return a;}
function resource(label,url,name='external'){
  try{const parsed=new URL(url);if(parsed.protocol!=='https:')return null;const a=node('a');a.href=parsed.href;a.target='_blank';a.rel='noopener noreferrer';a.append(icon(name),document.createTextNode(label));return a;}catch{return null;}
}
function disciplineLabel(id,lang=root.lang){if(id==='unclassified')return lang==='en'?'Unclassified':'待分类';const value=DISCIPLINES[id];return value?value[lang==='en'?1:0]:id;}
function colorClass(p){const id=p.disciplines?.[0]||'general';return ['matter-sciences','life-sciences'].includes(id)?'area-green':['earth-space-sciences','mathematical-sciences'].includes(id)?'area-teal':'area-blue';}
function readUrl(){
  const params=new URLSearchParams(location.search);
  for(const [key,el] of Object.entries(fields))el.value=params.get(key)||'';
  selected=(params.get('discipline')||'').split(',').map(resolveDiscipline).filter(id=>DISCIPLINES[id]);
  selectedTag=resolveTag(params.get('tag')||'',vocabulary);savedOnly.checked=params.get('saved')==='1';primary.checked=params.get('primary')==='1';
  page=Math.max(1,parseInt(params.get('page'),10)||1);
  matchMode=params.get('match')==='all'?'all':'any';view=['list','table'].includes(params.get('view'))?params.get('view'):'cards';
  arxiv=arxivOptions.some(([value])=>value===params.get('arxiv'))?params.get('arxiv'):'all';github=githubOptions.some(([value])=>value===params.get('github'))?params.get('github'):'all';
  sessions=(params.get('sessions')||'').split('|').filter(value=>facetValues('session').includes(value));rooms=(params.get('rooms')||'').split('|').filter(value=>facetValues('room').includes(value));
  searchField.value=['title','authors','abstract','id'].includes(params.get('field'))?params.get('field'):'all';
  sort.value=['newest','oldest','title'].includes(params.get('sort'))?params.get('sort'):'default';return params.get('paper');
}
function syncUrl(){
  const url=new URL(location.href),values={discipline:selected.join(','),tag:selectedTag,saved:savedOnly.checked?'1':'',primary:primary.checked?'1':'',match:matchMode==='all'?'all':'',view:view==='cards'?'':view,field:searchField.value==='all'?'':searchField.value,sort:sort.value==='default'?'':sort.value,arxiv:arxiv==='all'?'':arxiv,github:github==='all'?'':github,sessions:sessions.join('|'),rooms:rooms.join('|'),page:page>1?String(page):''};
  for(const [key,el] of Object.entries(fields))values[key]=el.value.trim();
  for(const key of ['period','date','paper','decision'])url.searchParams.delete(key);
  for(const [key,value] of Object.entries(values))value?url.searchParams.set(key,value):url.searchParams.delete(key);
  history.replaceState({},'',url);
}
function readSaved(){try{const values=JSON.parse(localStorage.getItem(storageKey)||'[]');saved=Array.isArray(values)?values.filter(id=>typeof id==='string'):[];}catch{storageAvailable=false;}}
function toggleSave(id){
  saved=saved.includes(id)?saved.filter(value=>value!==id):[...saved,id];
  try{localStorage.setItem(storageKey,JSON.stringify(saved));}catch{storageAvailable=false;}
  render();list.querySelector(`[data-save="${CSS.escape(id)}"]`)?.focus();
}
function saveButton(p){const b=button('', 'paper-save',()=>toggleSave(p.id));b.dataset.save=p.id;b.append(icon('star'));b.setAttribute('aria-label',tr('收藏论文：','Save paper: ')+p.title);b.setAttribute('aria-pressed',String(saved.includes(p.id)));return b;}
function filters(){return {query:fields.q.value,searchField:searchField.value,disciplines:selected,matchMode,primaryOnly:primary.checked,subfield:fields.subfield.value,venue:fields.venue.value,year:fields.year.value,savedOnly:savedOnly.checked,saved,arxiv,github,sessions,rooms};}
function refresh(){page=1;syncUrl();render();}
function populateFilters(){
  const subset=filterPapers(papers,{disciplines:selected,matchMode,primaryOnly:primary.checked});
  for(const key of ['subfield','venue','year']){
    const el=fields[key],current=el.value,values=[...new Set((key==='subfield'?subset:papers).map(p=>String(p[key]||'')).filter(Boolean))].sort();
    if(key==='year')values.reverse();if(current&&!values.includes(current))values.push(current);
    el.replaceChildren();const all=node('option',tr('全部','All'));all.value='';el.append(all);
    for(const value of values){const option=node('option',value);option.value=value;el.append(option);}el.value=current;
  }
}
function renderSidebar(){
  const categories=$('paper-disciplines');categories.replaceChildren();
  const pool=filterPapers(papers,{...filters(),tag:selectedTag,disciplines:[]});
  const all=button('', 'discipline-button discipline-all',()=>{selected=[];fields.subfield.value='';refresh();categories.querySelector('.discipline-all')?.focus();});all.append(node('span',tr('全部学科','All disciplines')),node('span',String(pool.length),'discipline-count'));all.setAttribute('aria-pressed',String(!selected.length));categories.append(all);
  const countFor=(entries,id)=>entries.filter(p=>id==='unclassified'?!p.disciplines?.length:primary.checked?p.disciplines?.[0]===id:p.disciplines?.includes(id)).length;
  const counts=Object.keys(DISCIPLINES).map(id=>[id,countFor(pool,id)]);
  const maximum=Math.max(1,...counts.map(([,count])=>count));
  for(const [id,count] of counts){
    const b=button('', 'discipline-button '+colorClass({disciplines:[id]}),()=>{selected=selected.includes(id)?selected.filter(v=>v!==id):[...selected,id];fields.subfield.value='';refresh();categories.querySelector(`[data-discipline="${id}"]`)?.focus();});
    b.dataset.discipline=id;b.setAttribute('aria-pressed',String(selected.includes(id)));
    const fill=node('span',undefined,'discipline-fill');fill.style.width=Math.max(18,count/maximum*100)+'%';
    const dot=node('span',undefined,'discipline-dot'),copy=node('span',undefined,'discipline-copy');copy.append(node('span',disciplineLabel(id,'zh-CN')),node('small',disciplineLabel(id,'en')));
    b.append(fill,dot,copy,node('span',String(count),'discipline-count'));categories.append(b);
  }
  for(const b of $('match-mode').children)b.setAttribute('aria-pressed',String(b.dataset.match===matchMode));
  const tags=$('tag-filters');tags.replaceChildren();
  for(const [tag,count] of [['',filterPapers(papers,filters()).length],...tagCounts(filterPapers(papers,filters()))]){
    const b=button((tag?tagLabel(tag,root.lang,translations,englishLabels):tr('全部标签','All tags'))+' · '+count,'',()=>{selectedTag=tag;refresh();[...tags.children].find(el=>el.dataset.tag===tag)?.focus();});b.dataset.tag=tag;b.setAttribute('aria-pressed',String(selectedTag===tag));tags.append(b);
  }
  if(selectedTag&&![...tags.children].some(b=>b.dataset.tag===selectedTag)){const b=button(tagLabel(selectedTag,root.lang,translations,englishLabels)+' · 0','',()=>{selectedTag='';refresh();});b.setAttribute('aria-pressed','true');tags.append(b);}
  renderResourceFacets();
  $('storage-note').textContent=storageAvailable?tr('收藏仅保存在当前浏览器','Bookmarks stay in this browser'):tr('存储不可用，收藏仅本次有效','Storage unavailable; bookmarks last for this visit');
}
function renderResourceFacets(){
  const current={...filters(),tag:selectedTag};
  for(const [group,options,value] of [['arxiv',arxivOptions,arxiv],['github',githubOptions,github]]){
    const host=$(group+'-facet'),counts=new Map(facetCounts(papers,current,group,options.map(([id])=>id)));host.replaceChildren();
    for(const [id,zh,en] of options){
      const label=node('label',undefined,'facet-row'),input=node('input');input.type='radio';input.name=group;input.value=id;input.checked=id===value;
      input.addEventListener('change',()=>{if(group==='arxiv')arxiv=id;else github=id;refresh();host.querySelector(`input[value="${id}"]`)?.focus({preventScroll:true});});
      label.append(input,node('span',tr(zh,en),'facet-label'),node('span',String(counts.get(id)),'facet-count'));host.append(label);
    }
  }
  for(const [group,key,hostId,selection,labelFor] of [['sessions','session','session-facet',sessions,sessionLabel],['rooms','room','room-facet',rooms,roomLabel]]){
    const host=$(hostId),values=facetValues(key),counts=new Map(facetCounts(papers,current,group,values));host.replaceChildren();
    for(const value of values){
      const label=node('label',undefined,'facet-row'),input=node('input');input.type='checkbox';input.value=value;input.checked=selection.includes(value);
      input.addEventListener('change',()=>{const updated=selection.includes(value)?selection.filter(v=>v!==value):[...selection,value];if(group==='sessions')sessions=updated;else rooms=updated;refresh();[...host.querySelectorAll('input')].find(el=>el.value===value)?.focus({preventScroll:true});});
      const copy=node('span',undefined,'facet-label');copy.append(node('span',labelFor(value)));
      if(group==='sessions'&&value!==missing){const times=[...new Set(papers.filter(p=>p.session===value).map(p=>p.sessionTime).filter(Boolean))];if(times.length)copy.append(node('small',times.join(' · ')));}
      label.append(input,copy,node('span',String(counts.get(value)),'facet-count'));host.append(label);
    }
    if(!values.length)host.append(node('p',tr('暂无收录信息','No information available'),'facet-note'));
  }
}
function renderLabels(p){
  const box=node('div',undefined,'card-labels');
  for(const id of p.disciplines||[]){const b=button(disciplineLabel(id),'discipline-chip '+colorClass({disciplines:[id]}),()=>{selected=[id];refresh();});if(DISCIPLINES[id])b.dataset.discipline=id;box.append(b);}
  for(const tag of paperTags(p)){const b=button(tagLabel(tag,root.lang,translations,englishLabels),'topic-chip',()=>{selectedTag=tag;refresh();});box.append(b);}return box;
}
function resourceLinks(p){
  const box=node('div',undefined,'card-resources');
  const arxiv=arxivLink(p);
  const resources=[[tr('论文页面','Paper page'),p.paperUrl||p.forumUrl,'external'],['PDF',p.pdfUrl,'file'],[githubLink(p)?'GitHub':tr('代码','Code'),p.codeUrl,'code']];
  if(arxiv){if(resources[0][1]===arxiv)resources[0]=['arXiv',arxiv,'external'];else resources.unshift(['arXiv',arxiv,'external']);}
  for(const [label,url,name] of resources){const a=resource(label,url,name);if(a)box.append(a);}
  if(arxiv&&p.arxivStatus==='verified')box.append(node('span',tr('arXiv 已验证','arXiv verified'),'resource-badge'));
  else if(['probable','needs-review'].includes(p.arxivStatus))box.append(node('span',tr('arXiv 待核对','arXiv needs review'),'resource-badge resource-review'));
  if(p.sample)box.append(node('span',tr('测试样例','Test entry'),'sample-badge'));if(p.imported)box.append(node('span',tr('元数据导入','Imported metadata'),'sample-badge'));if(p.classificationStatus==='needs-review')box.append(node('span',tr('分类待复核','Classification pending review'),'sample-badge'));return box;
}
function card(p,index){
  const article=node('article',undefined,'catalog-paper '+colorClass(p));article.dataset.paperId=p.id;
  if(DISCIPLINES[p.disciplines?.[0]])article.dataset.discipline=p.disciplines[0];
  const heading=node('div',undefined,'card-heading'),title=node('h2'),link=paperLink(p.id,p.title);title.append(link);
  heading.append(node('span','#'+(papers.indexOf(p)+1),'card-number'),title,saveButton(p));article.append(heading);
  const authors=node('p',(p.authors||[]).join(', '),'card-authors');article.append(authors,renderLabels(p));
  const meta=node('div',undefined,'card-meta');meta.append(icon('calendar'),node('span',[p.venue,p.year,p.subfield].filter(Boolean).join(' · ')),node('span',p.published?tr('发表 ','Published ')+p.published:p.imported&&p.dateRaw?tr('来源日期 ','Source date ')+p.dateRaw:tr('发表日期待补充','Publication date unavailable')));article.append(meta,resourceLinks(p));
  if(p.session||p.room){const schedule=node('div',undefined,'card-meta card-schedule');schedule.append(node('span',[p.session?sessionLabel(p.session):'',p.sessionTime,p.room,p.poster].filter(Boolean).join(' · ')));meta.after(schedule);}
  const text=p.abstract||p.abstractZh||'',abstract=node('p',text||tr('摘要待补充','Abstract not available'),'card-abstract');
  const open=expanded.has(p.id);abstract.id='abstract-'+index;abstract.classList.toggle('is-expanded',open);article.append(abstract);
  const footer=node('div',undefined,'card-footer');
  if(text){const b=button(tr(open?'收起摘要':'展开摘要',open?'Collapse abstract':'Expand abstract'),'abstract-toggle',()=>{if(expanded.has(p.id))expanded.delete(p.id);else expanded.add(p.id);const isOpen=expanded.has(p.id);abstract.classList.toggle('is-expanded',isOpen);b.replaceChildren(document.createTextNode(tr(isOpen?'收起摘要':'展开摘要',isOpen?'Collapse abstract':'Expand abstract')),icon('chevron'));b.setAttribute('aria-expanded',String(isOpen));});b.append(icon('chevron'));b.setAttribute('aria-expanded',String(open));b.setAttribute('aria-controls',abstract.id);footer.append(b);}
  const read=paperLink(p.id,tr('查看解读','Read summary'));footer.append(read);article.append(footer);
  return article;
}
function renderTable(entries){
  const table=node('table',undefined,'catalog-table'),caption=node('caption',tr('论文检索结果','Paper search results'),'sr-only'),head=node('thead'),row=node('tr');
  for(const text of ['#',tr('论文','Paper'),tr('作者','Authors'),tr('研究方向','Research area'),tr('来源 / 日期','Source / Date'),tr('资源','Resources'),tr('收藏','Save')]){const th=node('th',text);th.scope='col';row.append(th);}head.append(row);const body=node('tbody');
  for(const p of entries){const r=node('tr');r.append(node('td',String(papers.indexOf(p)+1)));const title=node('td'),a=paperLink(p.id,p.title);title.append(a);r.append(title,node('td',(p.authors||[]).join(', ')));const labels=node('td');labels.append(renderLabels(p));r.append(labels,node('td',[p.venue,p.year,p.published].filter(Boolean).join(' · ')));const links=node('td');links.append(resourceLinks(p));r.append(links);const save=node('td');save.append(saveButton(p));r.append(save);body.append(r);}table.append(caption,head,body);list.append(table);
}
function renderPagination(pagination,total){
  const host=$('catalog-pagination');host.replaceChildren();host.hidden=pagination.pages<=1;
  if(host.hidden)return;
  const go=target=>{page=target;syncUrl();render();list.scrollIntoView({block:'start'});host.querySelector('[aria-current="page"]')?.focus({preventScroll:true});};
  const previous=button(tr('上一页','Previous'),'',()=>go(page-1));previous.disabled=page===1;host.append(previous);
  for(let n=Math.max(1,page-2);n<=Math.min(pagination.pages,page+2);n++){const b=button(String(n),'',()=>go(n));if(n===page)b.setAttribute('aria-current','page');host.append(b);}
  const next=button(tr('下一页','Next'),'',()=>go(page+1));next.disabled=page===pagination.pages;host.append(next,node('span',tr(`第 ${page} / ${pagination.pages} 页 · 共 ${total} 篇`,`Page ${page} of ${pagination.pages} · ${total} papers`)));
}
function render(){
  if(!loaded)return;populateFilters();renderSidebar();
  const matches=filterPapers(papers,{...filters(),tag:selectedTag}),ids=new Set(matches.map(p=>p.id));
  const entries=sortPapers(papers.filter(p=>ids.has(p.id)),sort.value);
  $('paper-count').replaceChildren(node('strong',String(entries.length)),document.createTextNode(tr(' 篇论文',' papers')));
  const chips=$('active-filters');chips.replaceChildren();
  for(const id of selected)chips.append(button(disciplineLabel(id)+' ×','',()=>{selected=selected.filter(v=>v!==id);refresh();}));
  if(selectedTag)chips.append(button(tagLabel(selectedTag,root.lang,translations,englishLabels)+' ×','',()=>{selectedTag='';refresh();}));
  if(arxiv!=='all'){const option=arxivOptions.find(([id])=>id===arxiv);chips.append(button('arXiv: '+tr(option[1],option[2])+' ×','',()=>{arxiv='all';refresh();}));}
  if(github!=='all'){const option=githubOptions.find(([id])=>id===github);chips.append(button('GitHub: '+tr(option[1],option[2])+' ×','',()=>{github='all';refresh();}));}
  for(const value of sessions)chips.append(button(sessionLabel(value)+' ×','',()=>{sessions=sessions.filter(v=>v!==value);refresh();}));
  for(const value of rooms)chips.append(button(roomLabel(value)+' ×','',()=>{rooms=rooms.filter(v=>v!==value);refresh();}));
  message.hidden=!!entries.length;message.textContent=tr('没有匹配的论文。试试重置筛选或更换关键词。','No matching papers. Reset filters or try another keyword.');
  const pagination=paginatePapers(entries,page);page=pagination.page;syncUrl();
  list.dataset.view=view;list.replaceChildren();if(view==='table')renderTable(pagination.items);else pagination.items.forEach((p,index)=>list.append(card(p,index)));
  renderPagination(pagination,entries.length);
  for(const b of $('view-mode').children)b.setAttribute('aria-pressed',String(b.dataset.view===view));
  const en=root.lang==='en';fields.q.placeholder=tr('搜索标题、作者、摘要、论文 ID… 支持 "精确短语"，按 / 聚焦','Search title, author, abstract, paper ID… Use "exact phrases", press / to focus');
  const fieldLabels=en?['All fields','Title','Authors','Abstract','Paper ID']:['全部字段','标题','作者','摘要','论文 ID'];[...searchField.options].forEach((o,i)=>o.textContent=fieldLabels[i]);
  const sortLabels=en?['Default (catalog order)','Published: newest first','Published: oldest first','Title A–Z']:['默认（收录顺序）','发表日期：最新优先','发表日期：最早优先','标题 A–Z'];[...sort.options].forEach((o,i)=>o.textContent=sortLabels[i]);
  $('collection-scope').textContent=papers.some(p=>p.classificationStatus==='source-provided')?tr('研究方向沿用来源分类，未映射至现有类别的论文仍保留；来源日期不等同于发表日期。','Research areas follow source classifications; papers without a matching category are retained. Source dates are not necessarily publication dates.'):papers.some(p=>p.imported)?tr('批量导入数据的研究方向为规则初分，尚未逐篇人工复核；来源日期不等同于发表日期。','Imported research areas are rule-based and not individually reviewed; source dates are not necessarily publication dates.'):papers.some(p=>p.sample)?tr('包含测试样例；收录数仅代表本站文献库。','Includes test entries; counts reflect this collection only.'):tr('收录数仅代表本站文献库。','Counts reflect this collection only.');
}
for(const [key,el] of Object.entries(fields))el.addEventListener(key==='q'?'input':'change',refresh);
for(const el of [savedOnly,primary,searchField,sort])el.addEventListener('change',refresh);
for(const b of $('match-mode').children)b.addEventListener('click',()=>{matchMode=b.dataset.match;refresh();});
for(const b of $('view-mode').children)b.addEventListener('click',()=>{view=b.dataset.view;refresh();});
$('clear-filters').addEventListener('click',()=>{for(const el of Object.values(fields))el.value='';selected=[];selectedTag='';savedOnly.checked=false;primary.checked=false;matchMode='any';arxiv='all';github='all';sessions=[];rooms=[];searchField.value='all';refresh();fields.q.focus();});
document.addEventListener('keydown',e=>{if(e.key==='/'&&!e.ctrlKey&&!e.metaKey&&!e.altKey&&!e.target.closest('input,select,textarea,[contenteditable="true"]')){e.preventDefault();fields.q.focus();}});
new MutationObserver(render).observe(root,{attributes:true,attributeFilter:['lang','data-theme']});
window.addEventListener('popstate',()=>{readUrl();render();});window.addEventListener('pageshow',()=>{readSaved();render();});
window.addEventListener('storage',e=>{if(e.key===storageKey){readSaved();render();}});
const narrow=matchMedia('(max-width: 760px)');function adaptSidebar(){document.querySelector('.sidebar-disclosure').open=!narrow.matches;}narrow.addEventListener('change',adaptSidebar);adaptSidebar();
async function load(){
  message.hidden=false;message.textContent=tr('正在加载论文…','Loading papers…');
  try{
    const response=await fetch('data/papers-index.json',{cache:'no-cache'});if(!response.ok)throw new Error('Load failed');const data=await response.json();
    if(!Array.isArray(data.papers)||data.papers.some(p=>!p.id||!p.title||!Array.isArray(p.authors)||(p.disciplines&&!Array.isArray(p.disciplines)))||new Set(data.papers.map(p=>p.id)).size!==data.papers.length)throw new Error('Invalid catalog');
    papers=data.papers;translations=data.tagTranslations||{};englishLabels=data.tagLabelsEn||{};vocabulary=data.tagVocabulary||[];loaded=true;populateFilters();const id=readUrl();syncUrl();$('data-updated').textContent=data.updated||'—';if(data.updated)$('data-updated').dateTime=data.updated;render();if(id&&papers.some(p=>p.id===id))location.replace(readingUrl(id,location.search));
  }catch{message.replaceChildren(node('p',tr('论文数据暂时无法加载，请重试。','Could not load papers. Please retry.')),button(tr('重试','Retry'),'',load));}
}
readSaved();load();
