import {filterNews,articleUrl,findArticle} from './news-core.mjs?v=20261023-news';
import {node,link,getLanguage,tr} from './blog-shared.mjs';

const $=id=>document.getElementById(id),listing=!!$('news-list');
let entries=[],article,entry,query=new URLSearchParams(location.search).get('q')||'',failed=false;
const images=[],galleries=[];let currentImage=0,originButton;
const asset=path=>{if(typeof path!=='string'||!/^data\/news\/assets\/[a-z0-9-]+\/[A-Za-z0-9_.-]+\.(png|jpe?g|webp)$/.test(path))throw Error('Invalid news image');return path;};
async function json(path){const result=await fetch(path,{cache:'no-cache'});if(!result.ok)throw Error('Content unavailable');return result.json();}
const headline=item=>getLanguage()==='en'?item.titleEn||item.title:item.title;
function backUrl(){const params=new URLSearchParams();if(query)params.set('q',query);return 'news.html'+(params.size?'?'+params:'');}

function renderList(){
 $('news-query').placeholder=tr('搜索标题、关键词','Search titles and keywords');
 if(failed){showError();return;}
 const found=filterNews(entries,query);$('news-list').replaceChildren(...found.map(item=>{
  const card=node('article',undefined,'news-item'),thumbnail=link('',articleUrl(item.id,query),'');thumbnail.className='news-thumbnail';thumbnail.tabIndex=-1;thumbnail.setAttribute('aria-hidden','true');
  const image=node('img');image.src=asset(item.cover);image.alt='';image.width=600;image.height=375;thumbnail.append(image);
  const content=node('div',undefined,'news-item-content'),heading=node('h3');heading.append(link(headline(item),articleUrl(item.id,query)));
  const meta=node('div',undefined,'news-item-meta'),date=node('time',item.date);date.dateTime=item.date;
  const arrow=node('span','↗','news-item-arrow');arrow.setAttribute('aria-hidden','true');meta.append(node('span',getLanguage()==='en'?item.sourceEn||item.source:item.source),date,arrow);
  content.append(heading,node('p',getLanguage()==='en'?item.summaryEn||item.summary:item.summary,'news-item-summary'),meta);card.append(thumbnail,content);return card;
 }));
 $('news-status').hidden=true;$('news-empty').hidden=found.length>0;
 $('news-result-count').textContent=tr('共 '+found.length+' 条动态',found.length+' '+(found.length===1?'story':'stories'));
}

function search(value,push=true){
 query=value.trim().slice(0,150);$('news-query').value=query;
 const url=new URL(location.href);if(query)url.searchParams.set('q',query);else url.searchParams.delete('q');
 if(push)history.pushState(null,'',url);renderList();
}

function appendText(parent,text){
 for(const part of text.split(/(https?:\/\/[^\s<>，。；）\u3400-\u9fff]+)/g))parent.append(/^https?:\/\//.test(part)?link(part,part,true):document.createTextNode(part));
}

function imageButton(item){
 const button=node('button',undefined,'news-image-button');button.type='button';
 const image=node('img');image.src=asset(item.src);image.alt=item.caption||tr('课程配图','Course image');image.loading='lazy';
 const index=images.length;images.push({...item,button});button.dataset.imageIndex=String(index);button.append(image);
 button.onclick=()=>{originButton=button;showImage(index);$('news-image-viewer').showModal();document.body.classList.add('news-image-open');};
 return button;
}

function showImage(index){
 currentImage=index;const item=images[index];$('viewer-image').src=asset(item.src);$('viewer-image').alt=item.caption||tr('课程配图','Course image');
 $('viewer-caption').textContent=item.caption||tr('课程讲堂海报','Course lecture poster');
 $('image-position').textContent=(index+1)+' / '+images.length;
 $('image-previous').disabled=index===0;$('image-next').disabled=index===images.length-1;
}

function renderArticle(){
 if(!article)return;
 $('news-title').textContent=headline(entry);document.documentElement.dataset.titleZh=article.title+' · 课程动态';document.documentElement.dataset.titleEn=(entry.titleEn||entry.title)+' · Course news';
 document.title=(getLanguage()==='en'?document.documentElement.dataset.titleEn:document.documentElement.dataset.titleZh);
 $('news-subtitle').textContent=article.subtitle;$('news-source').textContent=getLanguage()==='en'?entry.sourceEn||article.source:article.source;
 $('news-date').textContent=article.date;$('news-date').dateTime=article.date;
 $('news-back').href=backUrl();document.querySelectorAll('.news-return').forEach(a=>a.href=backUrl());
 $('news-toc').replaceChildren(...article.blocks.filter(block=>block.type==='heading'&&block.level!==3).map(block=>{
  const a=link((block.number?block.number+' ':'')+block.text,'#'+block.id);a.onclick=()=>{if(matchMedia('(max-width:800px)').matches)$('news-contents').open=false;};return a;
 }));
 for(const [index,item] of images.entries())item.button.setAttribute('aria-label',tr('查看原图：','Enlarge image: ')+(item.caption||tr('讲堂海报','Lecture poster')+' '+(index+1)));
 for(const gallery of galleries){gallery.title.textContent=tr('讲堂海报','Lecture posters');gallery.hint.textContent=tr('左右浏览 · 点击海报查看原图','Browse sideways · Select a poster to enlarge');gallery.previous.setAttribute('aria-label',tr('上一张海报','Previous poster'));gallery.next.setAttribute('aria-label',tr('下一张海报','Next poster'));}
 $('news-image-viewer').setAttribute('aria-label',tr('查看原图','View original image'));
 for(const [id,zh,en] of [['image-previous','上一张图片','Previous image'],['image-next','下一张图片','Next image'],['image-close','关闭图片','Close image']])$(id).setAttribute('aria-label',tr(zh,en));
 if($('news-image-viewer').open)showImage(currentImage);
}

function buildBody(){
 const body=$('news-body');
 for(const block of article.blocks){
  if(block.type==='paragraph'){const p=node('p');appendText(p,block.text);body.append(p);}
  else if(block.type==='heading'){const h=node(block.level===3?'h3':'h2');h.id=block.id;if(block.number)h.append(node('span',block.number,'news-section-number'));h.append(document.createTextNode(block.text));body.append(h);}
  else if(block.type==='image'){const figure=node('figure',undefined,block.compact?'news-figure-compact':'');figure.append(imageButton(block));if(block.caption)figure.append(node('figcaption',block.caption));body.append(figure);}
  else if(block.type==='video'){
   const url=new URL(block.src);if(url.protocol!=='https:')throw Error('News video requires HTTPS');
   const figure=node('figure',undefined,'news-video'),video=node('video');video.controls=true;video.playsInline=true;video.preload='metadata';
   if(block.poster)video.poster=asset(block.poster);video.setAttribute('aria-label',block.caption||'报告回看');
   const source=node('source');source.src=url.href;source.type='video/mp4';video.append(source,link('打开报告视频 ↗',url.href,true));figure.append(video);
   if(block.caption)figure.append(node('figcaption',block.caption));body.append(figure);
  }
  else if(block.type==='gallery'){
   const section=node('section',undefined,'news-gallery'),heading=node('div',undefined,'news-gallery-heading'),title=node('p'),controls=node('div',undefined,'news-gallery-controls');
   const previous=node('button','←'),next=node('button','→'),counter=node('span','1 / '+block.images.length);previous.type=next.type='button';previous.disabled=true;
   controls.append(previous,counter,next);heading.append(title,controls);const track=node('div',undefined,'news-gallery-track');track.setAttribute('role','group');track.setAttribute('aria-label',tr('讲堂海报','Lecture posters'));
   track.append(...block.images.map(imageButton));const hint=node('p',undefined,'news-gallery-hint');section.append(heading,track,hint);body.append(section);
   let current=0;
   const sync=()=>{const children=[...track.children];current=children.reduce((best,child,index)=>Math.abs(child.offsetLeft-track.firstElementChild.offsetLeft-track.scrollLeft)<Math.abs(children[best].offsetLeft-track.firstElementChild.offsetLeft-track.scrollLeft)?index:best,0);counter.textContent=(current+1)+' / '+children.length;previous.disabled=track.scrollLeft<2;next.disabled=track.scrollLeft+track.clientWidth>=track.scrollWidth-2;};
   const move=step=>{const target=Math.max(0,Math.min(block.images.length-1,current+step)),child=track.children[target];track.scrollTo({left:child.offsetLeft-track.firstElementChild.offsetLeft,behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'instant':'smooth'});};
   previous.onclick=()=>move(-1);next.onclick=()=>move(1);track.addEventListener('scroll',sync,{passive:true});new ResizeObserver(sync).observe(track);galleries.push({title,hint,previous,next});
  }else throw Error('Unsupported news content');
 }
}

function showError(){
 $('news-status').hidden=false;
 const message=failed==='missing'?tr('未找到这条动态。','This news item was not found.'):tr('内容暂时无法加载。','This content could not be loaded.');
 $('news-status').replaceChildren(node('span',message),link(tr(' 返回动态列表 →',' Back to news →'),backUrl()));
}

document.addEventListener('ai4s-language-change',()=>listing?renderList():failed?showError():renderArticle());
if(listing){
 $('news-query').value=query;$('news-search').onsubmit=event=>{event.preventDefault();search($('news-query').value);};$('news-clear').onclick=()=>{search('');$('news-query').focus();};
 window.addEventListener('popstate',()=>{query=new URLSearchParams(location.search).get('q')||'';$('news-query').value=query;renderList();});
}else{
 $('news-contents').open=!matchMedia('(max-width:800px)').matches;
 $('image-previous').onclick=()=>{if(currentImage>0)showImage(currentImage-1);};$('image-next').onclick=()=>{if(currentImage<images.length-1)showImage(currentImage+1);};$('image-close').onclick=()=>$('news-image-viewer').close();
 const viewer=$('news-image-viewer');viewer.addEventListener('close',()=>{document.body.classList.remove('news-image-open');originButton?.focus({preventScroll:true});});
 viewer.addEventListener('keydown',event=>{if(event.key==='ArrowLeft'&&currentImage>0){event.preventDefault();showImage(currentImage-1);}else if(event.key==='ArrowRight'&&currentImage<images.length-1){event.preventDefault();showImage(currentImage+1);}});
 viewer.addEventListener('click',event=>{if(event.target===viewer){const rect=viewer.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)viewer.close();}});
}
try{
 const catalog=await json('data/news-index.json');if(catalog.schemaVersion!==1||!Array.isArray(catalog.articles))throw Error('Invalid news catalog');entries=catalog.articles;
 if(listing)renderList();
 else{
  entry=findArticle(entries,new URLSearchParams(location.search).get('id'));
  if(!entry){failed='missing';showError();}
  else{article=await json('data/news/articles/'+entry.id+'.json');if(article.id!==entry.id||!Array.isArray(article.blocks))throw Error('Invalid news article');buildBody();renderArticle();$('news-status').hidden=true;$('news-detail-content').hidden=false;
   if(location.hash){let anchor;try{anchor=decodeURIComponent(location.hash.slice(1));}catch{}if(anchor)requestAnimationFrame(()=>document.getElementById(anchor)?.scrollIntoView());}}
 }
}catch(error){console.error(error);failed=true;showError();}
