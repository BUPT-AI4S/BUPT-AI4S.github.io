import {collectionName,readCollection,safeLink,splitChapters,chapterFromHash} from './blog-core.mjs';
import {setupTheme,setupLanguage,getLanguage,tr,node,link} from './blog-shared.mjs';
setupTheme();
const $=id=>document.getElementById(id),params=new URLSearchParams(location.search);
let entry,article,chapters=[],current=0,loadError=null;
const chapterTitle=chapter=>chapter.title||tr('引言','Introduction');

function renderChrome(){
  if(article&&!loadError){
    const title=getLanguage()==='en'?entry.titleEn||article.title:article.title;
    document.title=title+tr(' · 科学智能博客',' · AI4S Blog');$('article-title').textContent=title;
    $('article-subtitle').textContent=article.subtitle||'';
    $('article-meta').textContent=article.byline||'BUPT Reasoning';
    $('article-tags').replaceChildren(node('span',collectionName(entry.collection,getLanguage())));
    $('article-links').replaceChildren(...(article.links||entry.links||[]).map(resource=>link((resource.label==='原始论文'?tr('原始论文','Original paper'):resource.label)+' ↗',resource.url,true)));
    renderContents();renderChapter();
  }else if(loadError){
    $('article-title').textContent=loadError==='missing'?tr('文章未找到','Article not found'):tr('文章暂时无法加载','Article could not be loaded');
    $('article-status').classList.remove('sr-only');
    $('article-status').replaceChildren(link(tr('返回博客列表 →','Back to articles →'),'blog.html'));
  }else $('article-title').textContent=tr('正在加载文章…','Loading article…');
}
setupLanguage(renderChrome);
function appendText(parent,text){
  const parts=text.split(/(https?:\/\/[^\s<>，。；）\u3400-\u9fff]+)/g);
  for(const part of parts)parent.append(/^https?:\/\//.test(part)?link(part,part,true):document.createTextNode(part));
}
function renderBlock(block){
  if(block.type==='heading'){
    const heading=node(block.level===3?'h3':'h2',block.text);heading.id=block.headingId;return heading;
  }
  if(block.type==='image'){
    const src=safeLink(block.src);if(!src)return null;
    const figure=node('figure'),image=node('img');image.src=src;image.alt=block.caption||tr('文章配图','Article figure');image.loading='lazy';
    image.onerror=()=>image.replaceWith(node('p',tr('配图加载失败，请刷新后重试。','The figure could not be loaded. Please refresh to try again.')));
    figure.append(image);if(block.caption)figure.append(node('figcaption',block.caption));return figure;
  }
  if(block.type==='table'){
    const wrap=node('div',undefined,'table-scroll'),table=node('table');
    block.rows.forEach((cells,index)=>{const row=node('tr');cells.forEach(text=>{const cell=node(index?'td':'th',text);if(!index)cell.scope='col';row.append(cell);});table.append(row);});wrap.append(table);return wrap;
  }
  if(block.type==='paragraph'){
    const p=node('p',undefined,block.text.startsWith('图源：')?'source-note':undefined);appendText(p,block.text);return p;
  }
  return null;
}
function renderContents(){
  $('article-toc').replaceChildren(...chapters.map((chapter,index)=>{
    const a=link(chapterTitle(chapter),'#'+chapter.id);a.dataset.chapter=index;
    a.onclick=event=>{event.preventDefault();navigate(index);if(matchMedia('(max-width:800px)').matches)$('chapter-directory').open=false;};
    return a;
  }));
}
function renderChapter(){
  const chapter=chapters[current];if(!chapter)return;
  const body=$('article-body');body.replaceChildren();
  if(chapter.id==='intro'){const h=node('h2',chapterTitle(chapter));h.id='intro';body.append(h);}
  for(const block of chapter.blocks){const element=renderBlock(block);if(element)body.append(element);}
  const firstHeading=body.querySelector('h2,h3');if(firstHeading)firstHeading.tabIndex=-1;
  $('chapter-progress').textContent=tr(`第 ${current+1} / ${chapters.length} 章`,`Chapter ${current+1} of ${chapters.length}`);
  $('chapter-label').textContent=chapterTitle(chapter);
  $('chapter-previous').disabled=current===0;$('chapter-next').disabled=current===chapters.length-1;
  $('chapter-previous').textContent=tr('← 上一章','← Previous chapter');$('chapter-next').textContent=tr('下一章 →','Next chapter →');
  $('chapter-navigation').hidden=false;
  $('article-toc').querySelectorAll('a').forEach((a,index)=>{if(index===current)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');});
  $('article-status').textContent=tr(`正在阅读：${chapterTitle(chapter)}`,`Reading: ${chapterTitle(chapter)}`);
}
function scrollToChapter(){
  let id;try{id=decodeURIComponent(location.hash.slice(1));}catch{}
  const target=(id&&$(id))||$('article-body').querySelector('h2,h3')||$('article-body');
  target.scrollIntoView({behavior:'instant',block:'start'});target.focus({preventScroll:true});
}
function navigate(index){
  if(index<0||index>=chapters.length)return;
  current=index;history.pushState(null,'','#'+chapters[current].id);renderChapter();scrollToChapter();
}
$('chapter-previous').onclick=()=>navigate(current-1);$('chapter-next').onclick=()=>navigate(current+1);
window.addEventListener('hashchange',()=>{if(!chapters.length||['#article-title','#article-body'].includes(location.hash))return;current=chapterFromHash(chapters,location.hash);renderChapter();scrollToChapter();});
$('chapter-directory').open=!matchMedia('(max-width:800px)').matches;
async function load(){
  try{
    const response=await fetch('data/blog-index.json');if(!response.ok)throw Error();const catalog=await response.json();
    entry=catalog.articles.find(item=>item.articleId===params.get('id'));if(!entry)throw Error('missing');
    const result=await fetch(entry.dataUrl);if(!result.ok)throw Error();article=await result.json();
    const collection=readCollection(location.search);
    const returnUrl='blog.html'+(collection==='all'?'':'?category='+encodeURIComponent(collection))+'#'+encodeURIComponent(entry.articleId);
    for(const id of ['back-link','back-catalog','reader-return'])$(id).href=returnUrl;
    chapters=splitChapters(article.blocks);current=chapterFromHash(chapters,location.hash);renderChrome();
    if(location.hash)requestAnimationFrame(scrollToChapter);
  }catch(error){loadError=error.message||'failed';renderChrome();}
}
load();
