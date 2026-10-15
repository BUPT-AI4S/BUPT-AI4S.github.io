import { DISCIPLINES, detailReturnUrl, paperTags, tagLabel, cardAbstract, readingUrl, relatedPapers } from './papers-core.mjs?v=20261015-import1';

const root = document.documentElement, $ = id => document.getElementById(id);
const tr = (zh, en) => root.lang === 'en' ? en : zh;
let paper, catalog=[];
let currentView = 'summary';
let summaryScroll = 0;
const readerTabs = [$('summary-tab'), $('original-tab')];
let tocItems=[],tocFrame=0,activeTocLink=null;
function highlightToc(link) {
  if(link===activeTocLink)return;
  activeTocLink?.removeAttribute('aria-current');
  activeTocLink=link;
  activeTocLink?.setAttribute('aria-current','location');
}
function updateToc() {
  tocFrame=0;
  if(currentView!=='summary'||!tocItems.length)return;
  const threshold=document.querySelector('.reading-switchbar').getBoundingClientRect().bottom+32;
  let current=tocItems[0];
  for(const item of tocItems){if(item.heading.getBoundingClientRect().top<=threshold)current=item;else break;}
  if(window.scrollY>0&&document.documentElement.scrollHeight-window.scrollY-window.innerHeight<=2)current=tocItems[tocItems.length-1];
  highlightToc(current.link);
}
function scheduleToc(){if(!tocFrame)tocFrame=requestAnimationFrame(updateToc);}
function bindToc() {
  activeTocLink=null;
  tocItems=[...$('reading-toc').querySelectorAll('a')].map(link=>({link,heading:document.getElementById(decodeURIComponent(link.hash.slice(1)))})).filter(item=>item.heading);
  scheduleToc();
}
window.addEventListener('scroll',scheduleToc,{passive:true});
window.addEventListener('resize',scheduleToc);
$('reading-body').addEventListener('load',scheduleToc,true);
$('reading-toc').addEventListener('click',event=>{const link=event.target.closest('a');if(link)highlightToc(link);});
function setView(view, focus = false) {
  const entering=view==='original'&&currentView!=='original',leaving=view==='summary'&&currentView==='original';
  if(entering)summaryScroll=window.scrollY;
  currentView = view;
  root.classList.toggle('reader-active',view==='original');
  $('reader-tools').hidden=view!=='original';
  $('summary-view').hidden = view !== 'summary';
  $('original-view').hidden = view !== 'original';
  readerTabs.forEach((tab,index)=>{const active=(index===0)===(view==='summary');tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;});
  if(view==='original') renderReader();
  if(leaving){if(document.fullscreenElement)document.exitFullscreen().catch(()=>{});window.scrollTo(0,summaryScroll);}
  if(focus) readerTabs[view==='summary'?0:1].focus({preventScroll:true});
  if(view==='summary')scheduleToc();
}
function syncFullscreen(){const active=!!document.fullscreenElement,b=$('reader-fullscreen');b.hidden=!root.requestFullscreen;b.textContent=tr(active?'退出全屏':'全屏阅读',active?'Exit fullscreen':'Fullscreen');b.setAttribute('aria-pressed',String(active));}
$('reader-fullscreen').addEventListener('click',async()=>{
  try {if(document.fullscreenElement)await document.exitFullscreen();else await root.requestFullscreen();}
  catch {$('reader-status').classList.remove('sr-only');$('reader-status').textContent=tr('浏览器暂不支持全屏，已保持铺满窗口。','Fullscreen is unavailable; the reader still fills the window.');}
  syncFullscreen();
});
document.addEventListener('fullscreenchange',syncFullscreen);
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&currentView==='original'&&!document.fullscreenElement){event.preventDefault();setView('summary',true);}});
window.addEventListener('message',event=>{if(event.origin===location.origin&&event.source===$('paper-reader').querySelector('iframe')?.contentWindow&&event.data?.type==='ai4s-pdf-exit'&&currentView==='original'){if(document.fullscreenElement)document.exitFullscreen().catch(()=>{});else setView('summary',true);}});
readerTabs.forEach((tab,index)=>{
  tab.addEventListener('click',()=>setView(index===0?'summary':'original'));
  tab.addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();setView(event.key==='Home'?'summary':event.key==='End'?'original':currentView==='summary'?'original':'summary',true);}});
});
$('view-original').addEventListener('click',()=>setView('original',true));
function safeResource(label,url) {
  try {const target=new URL(url);if(target.protocol!=='https:')return null;const a=node('a',label);a.href=target.href;a.target='_blank';a.rel='noopener noreferrer';return a;} catch {return null;}
}
function renderReader() {
  if(!paper)return;
  const host=$('paper-reader');
  const existing=host.querySelector('iframe'),language=root.lang==='en'?'en':'zh';
  if(existing) {existing.title=tr('论文原文阅读器','Original paper reader');if(new URL(existing.src).searchParams.get('lang')!==language)existing.src='pdf-reader.html?'+new URLSearchParams({id:paper.id,lang:language});return;}
  host.replaceChildren();
  const pdf=safeResource('',paper.pdfUrl);
  if(pdf) {const frame=node('iframe');const params=new URLSearchParams({id:paper.id,lang:root.lang==='en'?'en':'zh'});frame.src='pdf-reader.html?'+params;frame.title=tr('论文原文阅读器','Original paper reader');frame.referrerPolicy='no-referrer';host.append(frame);}
  else host.append(node('p',tr('暂无可嵌入的 PDF，请通过上方论文页面阅读原文。','No PDF available. Read the original on the paper page above.'),'papers-message'));
}
function renderActions() {
  const box=$('reading-actions');box.replaceChildren();
  for(const [key,zh,en] of [['ai4s-saved-papers',['收藏','已收藏'],['Save','Saved']],['ai4s-liked-papers',['点赞','已点赞'],['Like','Liked']]]) {
    let values=[];try {const value=JSON.parse(localStorage.getItem(key)||'[]');if(Array.isArray(value))values=value;}catch{}
    const selected=values.includes(paper.id),button=node('button',tr(zh[Number(selected)],en[Number(selected)]));button.type='button';button.setAttribute('aria-pressed',String(selected));
    button.addEventListener('click',()=>{values=selected?values.filter(id=>id!==paper.id):[...values,paper.id];try {localStorage.setItem(key,JSON.stringify(values));renderActions();box.children[key==='ai4s-saved-papers'?0:1].focus();}catch {button.textContent=tr('浏览器存储不可用','Browser storage unavailable');}});box.append(button);
  }
}
let tagTranslations = {};
let tagLabelsEn = {};
function node(tag, text, cls) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (cls) element.className = cls;
  return element;
}
function renderBack() {
  $('back-to-papers').href = detailReturnUrl(location.search);
}
let relatedLimit=6;
function renderRelated() {
  const box=$('related-papers');box.replaceChildren();
  const related=relatedPapers(paper,catalog);
  const list=node('div',undefined,'related-list');
  for(const entry of related.slice(0,relatedLimit)) {
    const link=node('a',undefined,'related-entry');link.href=readingUrl(entry.id,new URL($('back-to-papers').href).search);
    link.append(node('h3',tr(entry.titleZh||entry.title,entry.title)),node('p',[entry.venue,entry.year,...paperTags(entry).filter(tag=>paperTags(paper).includes(tag)).map(tag=>tagLabel(tag,root.lang,tagTranslations,tagLabelsEn))].filter(Boolean).join(' · ')));
    list.append(link);
  }
  if(related.length)box.append(list);
  if(related.length>relatedLimit){const more=node('button',tr('查看更多相关论文','Show more related papers'),'related-more');more.type='button';more.addEventListener('click',()=>{const old=relatedLimit;relatedLimit+=6;renderRelated();box.querySelectorAll('.related-entry')[old]?.focus();});box.append(more);}
  if(!related.length)box.append(node('p',tr('暂未收录同标签的其他论文。','No other papers share these tags yet.')));
}
function render() {
  renderBack();
  if (!paper) return;
  const p = paper, notes = p.notes || [];
  const hasNotes = p.content ? Object.values(p.content).some(c=>c.html?.trim()) : notes.length;
  document.querySelector('.reading-toc').hidden=!hasNotes;
  $('reading-title').textContent = tr(p.titleZh || p.title, p.title);
  document.title = $('reading-title').textContent + ' · AI4S';
  $('reading-english-title').textContent = root.lang === 'en' ? '' : p.title;
  $('reading-authors').textContent = (p.authors.length?p.authors.join(' · '):tr('作者待补充','Authors not available')) + (p.affiliations?.length ? '\n'+tr('单位：','Affiliations: ')+p.affiliations.join(' · ') : '');
  const disciplines = (p.disciplines || []).map(id => DISCIPLINES[id] ? tr(...DISCIPLINES[id]) : id);
  $('reading-meta').textContent = [...disciplines, p.subfield, p.venue, p.year].filter(Boolean).join(' · ');
  if(p.published) $('reading-meta').textContent+=' · '+p.published;
  else if(p.imported&&p.dateRaw)$('reading-meta').textContent+=' · '+tr('来源日期：','Source date: ')+p.dateRaw;
  renderActions();
  const abstract=cardAbstract(p,root.lang);
  $('reading-abstract').textContent=abstract.text||tr('原文摘要待补充。','Abstract not available.');
  const attribution=$('abstract-attribution');attribution.replaceChildren();
  if(root.lang!=='en'&&p.abstractZh)attribution.append(document.createTextNode('中文译文 · '));
  else if(root.lang!=='en'&&abstract.text)attribution.append(document.createTextNode('暂无中文译文，显示英文原摘要。 '));
  else if(root.lang==='en'&&!p.abstract&&abstract.text)attribution.append(document.createTextNode('English abstract unavailable; showing Chinese translation. '));
  const source=safeResource(tr('摘要来源','Abstract source'),p.abstractSource);if(source)attribution.append(source);

  const keywords=$('reading-keywords');keywords.replaceChildren(node('span',tr('关键词','Keywords'),'tag-label'));
  for(const word of p.keywords||[])keywords.append(node('span',word));
  $('original-title').textContent=tr(p.titleZh||p.title,p.title);
  const originalResources=$('original-resources');originalResources.replaceChildren();
  for(const [label,url] of [[tr('打开 PDF','Open PDF'),p.pdfUrl],[tr('论文页面','Paper page'),p.paperUrl||p.forumUrl]]) {const link=safeResource(label,url);if(link){if(url===p.pdfUrl)link.href='pdf-reader.html?'+new URLSearchParams({id:p.id,lang:root.lang==='en'?'en':'zh'});originalResources.append(link);}}
  syncFullscreen();
  renderRelated();
  const resources = $('reading-resources'); resources.replaceChildren();
  for (const [label, url] of [[tr('论文页面', 'Paper page'), p.paperUrl || p.forumUrl], ['PDF', p.pdfUrl], [p.codeUrl?.startsWith('https://github.com/')?'GitHub':tr('代码', 'Code'), p.codeUrl]]) {
    try {
      const target = new URL(url);
      if (target.protocol !== 'https:') continue;
      const link = node('a', label + ' ↗'); link.href = label==='PDF'?'pdf-reader.html?'+new URLSearchParams({id:p.id,lang:root.lang==='en'?'en':'zh'}):target.href; link.target = '_blank'; link.rel = 'noopener noreferrer'; resources.append(link);
    } catch {}
  }
  const provenance = p.notesMeta;
  $('reading-provenance').textContent = p.imported&&!hasNotes ? tr('批量导入的论文元数据；AI 解读尚未生成。研究方向为规则初分，尚未人工复核。','Imported paper metadata; AI notes have not been generated. Research areas are rule-based and have not been reviewed.') : !hasNotes ? tr('AI 解读待补充。下方提供论文简介与原文入口。', 'AI summary pending. Read the introduction or original paper below.') : provenance ?
    tr(`大模型生成 · ${provenance.reviewed ? '已人工审核' : '未人工审核'} · ${provenance.generated}。依据：${provenance.basisZh}`, `AI generated · ${provenance.reviewed ? 'Human reviewed' : 'Not human reviewed'} · ${provenance.generated}. Source: ${provenance.basisEn}`) :
    tr('解读来源与审核状态待补充。', 'Summary provenance and review status pending.');
  const body = $('reading-body'), toc = $('reading-toc'); body.replaceChildren(); toc.replaceChildren();
  const sections = hasNotes?[
    {headingZh:'领域与关键词',headingEn:'Field & Keywords',textZh:[p.subfield,'关键词：'+(p.keywords||[]).join(' · '),'标签：'+paperTags(p).map(tag=>tagLabel(tag,'zh',tagTranslations,tagLabelsEn)).join(' · ')].filter(Boolean).join('\n'),textEn:[p.subfield,'Keywords: '+(p.keywords||[]).join(' · '),'Tags: '+paperTags(p).map(tag=>tagLabel(tag,'en',tagTranslations,tagLabelsEn)).join(' · ')].filter(Boolean).join('\n')},
    ...notes.filter(n=>n.id==='summary'||n.headingZh==='一句话总结'),
    ...notes.filter(n=>n.id!=='summary'&&n.headingZh!=='一句话总结')
  ]:[];
  sections.forEach((section, index) => {
    const title = tr(section.headingZh, section.headingEn || section.headingZh);
    const block = node('section', undefined, 'reading-section'); block.id = 'section-' + (section.id || index);
    block.append(node('h2', title), node('p', tr(section.textZh, section.textEn || section.textZh) || tr('内容待补充', 'Content pending')));
    body.append(block); const link = node('a', title); link.href = '#' + block.id; toc.append(link);
  });
  if(p.content) {
    const selected=p.content[root.lang==='en'?'en':'zh'];
    const content=selected?.html?.trim()?selected:(p.content.zh?.html?.trim()?p.content.zh:p.content.en);
    if(content?.html) {
      const block=node('section',undefined,'reading-markdown');
      // HTML is generated at build time from Markdown with raw HTML disabled.
      block.innerHTML=content.html;
      body.append(block);
      for(const heading of content.toc||[]) {
        const link=node('a',heading.title);link.href='#'+heading.id;toc.append(link);
      }
      for(const image of block.querySelectorAll('img')) image.addEventListener('error',()=>{
        image.replaceWith(node('p',tr('图片暂时无法加载','Image unavailable')));
      },{once:true});
    }
  }
  if(p.figures?.length) {
    const gallery=node('section',undefined,'reading-section');gallery.id='paper-figures';gallery.append(node('h2',tr('论文配图','Figures')));
    for(const figure of p.figures) {
      let url;
      try {url=new URL(figure.src,location.href);if(url.protocol!=='https:' && !(url.origin===location.origin && ['http:','https:'].includes(url.protocol))) continue;}catch {continue;}
      const box=node('figure'),image=node('img');image.src=url.href;image.alt=tr(figure.altZh||figure.captionZh||'',figure.altEn||figure.captionEn||'');image.loading='lazy';
      image.addEventListener('error',()=>{image.hidden=true;box.prepend(node('p',tr('图片暂时无法加载','Image unavailable')));},{once:true});
      box.append(image,node('figcaption',tr(figure.captionZh||'',figure.captionEn||figure.captionZh||'')));
      if(figure.sourceUrl) {try {const source=new URL(figure.sourceUrl);if(source.protocol==='https:'){const a=node('a',tr('图片来源 ↗','Figure source ↗'));a.href=source.href;a.target='_blank';a.rel='noopener noreferrer';box.append(a);}}catch {}}
      gallery.append(box);
    }
    body.append(gallery);const link=node('a',tr('论文配图','Figures'));link.href='#paper-figures';toc.append(link);
  }
  $('reading-message').hidden = true; $('reading-article').hidden = false;
  setView(currentView);
  bindToc();
}
async function load() {
  const message = $('reading-message'); message.hidden = false;
  message.textContent = tr('正在加载论文解读…', 'Loading paper summary…');
  renderBack();
  try {
    const response = await fetch('data/papers-index.json', {cache:'no-cache'});
    if (!response.ok) throw new Error('Load failed');
    const data = await response.json();
    tagTranslations = data.tagTranslations || {};
    tagLabelsEn = data.tagLabelsEn || {};
    if (!Array.isArray(data.papers)) throw new Error('Invalid data');
    catalog=data.papers;
    const id = new URLSearchParams(location.search).get('id');
    const entry = data.papers.find(p => p.id === id);
    if (!entry) { message.textContent = tr('未找到这篇论文，请返回文献列表选择。', 'Paper not found. Return to the list to choose a paper.'); return; }
    if (!/^data\/(papers|papers-built)\/[A-Za-z0-9][A-Za-z0-9._-]*\.json$/.test(entry.dataUrl)) throw new Error('Invalid paper path');
    const detail = await fetch(entry.dataUrl, {cache:'no-cache'});
    if (!detail.ok) throw new Error('Paper load failed');
    paper = await detail.json();
    if (paper.id !== id || !paper.title || !Array.isArray(paper.authors)) {paper=null;throw new Error('Invalid paper data');}
    render();
  } catch {
    message.replaceChildren(node('p', tr('论文解读暂时无法加载，请重试。', 'Could not load this paper. Please retry.')));
    const retry = node('button', tr('重试', 'Retry')); retry.type = 'button'; retry.addEventListener('click', load); message.append(retry);
  }
}
new MutationObserver(() => { if (paper) render(); else load(); }).observe(root, { attributes: true, attributeFilter: ['lang', 'data-theme'] });
load();
