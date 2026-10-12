import { DISCIPLINES, listReturnUrl, paperTags, tagLabel } from './papers-core.mjs?v=20261012-files';

const root = document.documentElement, $ = id => document.getElementById(id);
const tr = (zh, en) => root.lang === 'en' ? en : zh;
let paper;
let tagTranslations = {};
const narrow = matchMedia('(max-width: 900px)');
const directory = document.querySelector('.reading-toc details');
function sizeDirectory() { directory.open = !narrow.matches; }
sizeDirectory();
narrow.addEventListener('change', sizeDirectory);
function node(tag, text, cls) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (cls) element.className = cls;
  return element;
}
function renderBack() {
  const params = new URLSearchParams(location.search);
  const back = new URL(listReturnUrl(params.get('from') || ''), location.href);
  const current = new URLSearchParams(location.search);
  for (const key of ['lang', 'theme']) {
    if (current.get(key)) back.searchParams.set(key, current.get(key));
    else back.searchParams.delete(key);
  }
  $('back-to-papers').href = back.pathname + back.search;
}
function render() {
  renderBack();
  if (!paper) return;
  const p = paper, notes = p.notes || [];
  const hasNotes = p.content ? Object.values(p.content).some(c=>c.html?.trim()) : notes.length;
  $('reading-title').textContent = tr(p.titleZh || p.title, p.title);
  document.title = $('reading-title').textContent + ' · AI4S';
  $('reading-english-title').textContent = root.lang === 'en' ? '' : p.title;
  $('reading-authors').textContent = p.authors.join(' · ') + (p.affiliations?.length ? '\n'+tr('单位：','Affiliations: ')+p.affiliations.join(' · ') : '');
  const disciplines = (p.disciplines || []).map(id => DISCIPLINES[id] ? (id === 'general' ? '' : 'AI for ') + tr(...DISCIPLINES[id]) : id);
  $('reading-meta').textContent = [...disciplines, p.subfield, p.venue, p.year].filter(Boolean).join(' · ');
  const resources = $('reading-resources'); resources.replaceChildren();
  for (const [label, url] of [[tr('论文页面', 'Paper page'), p.paperUrl || p.forumUrl], ['PDF', p.pdfUrl], [p.codeUrl?.startsWith('https://github.com/')?'GitHub':tr('代码', 'Code'), p.codeUrl]]) {
    try {
      const target = new URL(url);
      if (target.protocol !== 'https:') continue;
      const link = node('a', label + ' ↗'); link.href = target.href; link.target = '_blank'; link.rel = 'noopener noreferrer'; resources.append(link);
    } catch {}
  }
  const provenance = p.notesMeta;
  $('reading-provenance').textContent = !hasNotes ? tr('AI 解读待补充。下方提供论文简介与原文入口。', 'AI summary pending. Read the introduction or original paper below.') : provenance ?
    tr(`大模型生成 · ${provenance.reviewed ? '已人工审核' : '未人工审核'} · ${provenance.generated}。依据：${provenance.basisZh}`, `AI generated · ${provenance.reviewed ? 'Human reviewed' : 'Not human reviewed'} · ${provenance.generated}. Source: ${provenance.basisEn}`) :
    tr('解读来源与审核状态待补充。', 'Summary provenance and review status pending.');
  const body = $('reading-body'), toc = $('reading-toc'); body.replaceChildren(); toc.replaceChildren();
  const sections = [
    {headingZh:'领域与关键词',headingEn:'Field & Keywords',textZh:[p.subfield,'关键词：'+(p.keywords||[]).join(' · '),'标签：'+paperTags(p).map(tag=>tagLabel(tag,'zh',tagTranslations)).join(' · ')].filter(Boolean).join('\n'),textEn:[p.subfield,'Keywords: '+(p.keywords||[]).join(' · '),'Tags: '+paperTags(p).join(' · ')].filter(Boolean).join('\n')},
    ...notes.filter(n=>n.id==='summary'||n.headingZh==='一句话总结'),
    { headingZh: p.abstractZh?'中文摘要':'中文概述', headingEn: p.abstract?'Abstract':'Summary', textZh: p.abstractZh || p.summaryZh || p.abstract || p.summaryEn, textEn: p.abstract || p.summaryEn || p.abstractZh || p.summaryZh },
    ...notes.filter(n=>n.id!=='summary'&&n.headingZh!=='一句话总结')
  ];
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
    if (!Array.isArray(data.papers)) throw new Error('Invalid data');
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
