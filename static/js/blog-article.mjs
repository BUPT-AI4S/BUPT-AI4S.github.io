import {collectionName,readCollection,safeLink} from './blog-core.mjs';
import {setupTheme,setupLanguage,getLanguage,tr,node,link} from './blog-shared.mjs';
setupTheme();
const $=id=>document.getElementById(id),params=new URLSearchParams(location.search);
let entry,article,loadError=null;
function renderChrome(){
  if(article&&!loadError){
    const title=getLanguage()==='en'?entry.titleEn||article.title:article.title;
    document.title=title+tr(' · 科学智能博客',' · AI4S Blog');$('article-title').textContent=title;
    $('article-subtitle').textContent=article.subtitle||'';
    $('article-meta').textContent=article.byline||'BUPT Reasoning';
    $('article-tags').replaceChildren(node('span',collectionName(entry.collection,getLanguage())));
    $('article-links').replaceChildren(...(article.links||entry.links||[]).map(resource=>link((resource.label==='原始论文'?tr('原始论文','Original paper'):resource.label)+' ↗',resource.url,true)));
    if($('continue-title'))$('continue-title').textContent=tr('继续阅读','Continue reading');
    if($('continue-link'))$('continue-link').textContent=tr('返回文章列表 →','Back to articles →');
  }else if(loadError){
    $('article-title').textContent=loadError==='missing'?tr('文章未找到','Article not found'):tr('文章暂时无法加载','Article could not be loaded');
    $('article-status').replaceChildren(link(tr('返回博客列表 →','Back to articles →'),'blog.html'));
  }else $('article-title').textContent=tr('正在加载文章…','Loading article…');
}
setupLanguage(renderChrome);
function appendText(parent,text){
  // Keep supplied wording; make explicit web addresses clickable without injecting HTML.
  const parts=text.split(/(https?:\/\/[^\s<>，。；）\u3400-\u9fff]+)/g);
  for(const part of parts)parent.append(/^https?:\/\//.test(part)?link(part,part,true):document.createTextNode(part));
}
async function load(){
  try{
    const response=await fetch('data/blog-index.json');if(!response.ok)throw Error();const catalog=await response.json();
    entry=catalog.articles.find(item=>item.articleId===params.get('id'));
    if(!entry)throw Error('missing');
    const result=await fetch(entry.dataUrl);if(!result.ok)throw Error();article=await result.json();
    const collection=readCollection(location.search);
    const returnUrl='blog.html'+(collection==='all'?'':'?category='+encodeURIComponent(collection))+'#'+encodeURIComponent(entry.articleId);
    $('back-link').href=returnUrl;
    const body=$('article-body'),toc=$('article-toc');body.replaceChildren();toc.replaceChildren();
    let headingIndex=0;
    for(const block of article.blocks){
      if(block.type==='heading'){
        const heading=node(block.level===3?'h3':'h2',block.text);heading.id='part-'+(++headingIndex);body.append(heading);
        if(block.level!==3)toc.append(link(block.text,'#'+heading.id));
      }else if(block.type==='image'){
        const figure=node('figure'),image=node('img');const src=safeLink(block.src);if(!src)continue;
        image.src=src;image.alt=block.caption||tr('文章配图','Article figure');image.loading='lazy';
        image.onerror=()=>image.replaceWith(node('p',tr('配图加载失败，请刷新后重试。','The figure could not be loaded. Please refresh to try again.')));
        figure.append(image);if(block.caption)figure.append(node('figcaption',block.caption));body.append(figure);
      }else if(block.type==='table'){
        const wrap=node('div',undefined,'table-scroll'),table=node('table');
        block.rows.forEach((cells,index)=>{const row=node('tr');cells.forEach(text=>{const cell=node(index?'td':'th',text);if(!index)cell.scope='col';row.append(cell);});table.append(row);});wrap.append(table);body.append(wrap);
      }else if(block.type==='paragraph'){
        const p=node('p',undefined,block.text.startsWith('图源：')?'source-note':undefined);appendText(p,block.text);body.append(p);
      }
    }
    const end=node('section',undefined,'article-end'),endTitle=node('h2'),endLink=link('',returnUrl);
    endTitle.id='continue-title';endLink.id='continue-link';end.append(endTitle,endLink);
    body.append(end);$('article-status').replaceChildren();renderChrome();
  }catch(error){loadError=error.message||'failed';renderChrome();}
}
load();
