import {COLLECTIONS,collectionName,filterCollection,filterBlogArticles,readCollection,seriesLabel,readingLink} from './blog-core.mjs?v=20261104-search';
import {setupTheme,setupLanguage,getLanguage,tr,node,link} from './blog-shared.mjs?v=20261104-navigation';
setupTheme();
const list=document.getElementById('article-list'),status=document.getElementById('load-status');
let entries=null,failed=false;
let collection=readCollection(location.search);
let query=new URLSearchParams(location.search).get('q')||'';
const searchInput=document.getElementById('blog-search'),searchClear=document.getElementById('search-clear');
const drawer=document.getElementById('category-drawer'),categoryToggle=document.getElementById('category-toggle');
categoryToggle.onclick=()=>{drawer.showModal();categoryToggle.setAttribute('aria-expanded','true');};
document.getElementById('category-close').onclick=()=>drawer.close();
drawer.addEventListener('close',()=>categoryToggle.setAttribute('aria-expanded','false'));
drawer.addEventListener('click',event=>{if(event.target===drawer){const r=drawer.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)drawer.close();}});
function selectCollection(id){
  collection=id;
  const url=new URL(location.href);if(id==='all')url.searchParams.delete('category');else url.searchParams.set('category',id);
  url.hash='';history.replaceState(null,'',url);render();
  if(drawer.open)drawer.close();
  if(!matchMedia('(prefers-reduced-motion: reduce)').matches)list.animate([{opacity:.4,transform:'translateY(6px)'},{opacity:1,transform:'none'}],{duration:230,easing:'ease-out'});
  document.getElementById(id==='all'?'all-articles':'pocket-'+id)?.focus({preventScroll:true});
  window.scrollTo({top:0,left:0,behavior:'instant'});
}
function renderPockets(){
  const buttons=[...COLLECTIONS,{id:'all'}].map(group=>{
    const button=node('button',undefined,'pocket-tab');button.type='button';button.id=group.id==='all'?'all-articles':'pocket-'+group.id;button.dataset.collection=group.id;
    button.setAttribute('aria-pressed',String(collection===group.id));button.setAttribute('aria-controls','article-panel');
    if(entries&&group.id!=='all'&&!entries.some(entry=>entry.collection===group.id))button.classList.add('pocket-empty');
    for(const cls of ['pocket-back','pocket-paper paper-one','pocket-paper paper-two']){
      const decoration=node('span',undefined,cls);decoration.setAttribute('aria-hidden','true');button.append(decoration);
    }
    const front=node('span',undefined,'pocket-front');
    front.append(node('span',collectionName(group.id,getLanguage()),'pocket-title'));button.append(front);
    button.onclick=()=>selectCollection(group.id);return button;
  });
  document.getElementById('pocket-tabs').replaceChildren(...buttons);
  document.getElementById('category-options').replaceChildren(...[{id:'all'},...COLLECTIONS].map(group=>{
    const button=node('button',undefined,'category-option');button.type='button';button.dataset.collection=group.id;
    button.setAttribute('aria-pressed',String(collection===group.id));
    button.append(node('span',collectionName(group.id,getLanguage())),node('span',entries?String(filterCollection(entries,group.id).length):'…','category-count'));
    button.onclick=()=>selectCollection(group.id);return button;
  }));
  document.getElementById('article-panel').dataset.collection=collection;
  document.getElementById('collection-title').textContent=collectionName(collection,getLanguage());
  const series=document.getElementById('series-description');series.hidden=collection!=='reviews';
  series.textContent=tr('《科学大语言模型：从数据基础到智能体前沿》精读系列','A Survey of Scientific Large Language Models: From Data Foundations to Agent Frontiers — A Close Reading');
}
function render(){
  renderPockets();
  if(searchInput.value!==query)searchInput.value=query;
  searchInput.placeholder=tr('搜索标题、摘要或关键词','Search titles, summaries or keywords');
  searchClear.hidden=!query;
  if(entries){
    const visible=filterBlogArticles(entries,collection,query);
    list.replaceChildren(...visible.map(renderCard));status.replaceChildren();
    const empty=document.getElementById('empty-collection');empty.hidden=visible.length>0;
    const searching=Boolean(query.trim())&&filterCollection(entries,collection).length>0;
    empty.querySelector('h3').textContent=searching?tr('没有找到匹配文章','No matching articles'):tr('新内容，正在路上','More to explore, soon');
    empty.querySelector('p').textContent=searching?tr('试试其他关键词，或清除搜索后查看当前分类的全部文章。','Try different keywords, or clear the search to see all articles in this topic.'):tr('该分类暂未收录文章，后续会陆续补充。','Articles for this topic will be added here.');
    document.getElementById('search-status').textContent=query.trim()?tr(`找到 ${visible.length} 篇匹配文章`,`${visible.length} matching articles`):tr(`共 ${visible.length} 篇文章`,`${visible.length} articles`);
    document.getElementById('collection-status').textContent=tr('当前显示：','Showing: ')+collectionName(collection,getLanguage());
  }
  else if(failed){
    status.replaceChildren(node('span',tr('文章暂时加载失败。','Articles could not be loaded.')));
    const retry=node('button',tr('重新加载','Try again'));retry.onclick=load;status.append(retry);
  }else status.textContent=tr('正在加载文章…','Loading articles…');
}
function updateSearch(value){
  query=value;
  const url=new URL(location.href);if(query.trim())url.searchParams.set('q',query.trim());else url.searchParams.delete('q');
  url.hash='';history.replaceState(null,'',url);render();
}
searchInput.oninput=()=>updateSearch(searchInput.value);
searchClear.onclick=()=>{updateSearch('');searchInput.focus({preventScroll:true});};
document.getElementById('blog-search-form').onsubmit=event=>{event.preventDefault();updateSearch(searchInput.value);};
window.addEventListener('popstate',()=>{collection=readCollection(location.search);query=new URLSearchParams(location.search).get('q')||'';render();});
setupLanguage(render);

function renderCard(entry,index){
  const card=node('article',undefined,'article-card');card.id=entry.articleId;card.dataset.collection=entry.collection;
  const top=node('div',undefined,'card-top');
  top.append(node('span',String((entry.order??index)+1).padStart(2,'0'),'card-number'));
  if(entry.seriesPart)top.append(node('span',seriesLabel(entry,getLanguage()),'series-part'));
  const english=getLanguage()==='en';
  const heading=node('h3');heading.append(link(english?entry.titleEn||entry.title:entry.title,readingLink(entry.articleId,collection,query),true));
  const tags=node('div',undefined,'tags');
  tags.append(node('span',collectionName(entry.collection,getLanguage())));
  const actions=node('div',undefined,'card-actions');
  const read=link(tr('阅读全文','Read article'),readingLink(entry.articleId,collection,query),true);read.className='card-read';
  const arrow=node('span','↗');arrow.setAttribute('aria-hidden','true');read.append(arrow);actions.append(read);
  for(const resource of entry.links||[]){const a=link((resource.label==='原始论文'?tr('原始论文','Original paper'):resource.label)+' ↗',resource.url,true);a.className='paper-link';actions.append(a);}
  card.append(top,heading,node('p',english?entry.summaryEn||entry.summary:entry.summary,'card-summary'),tags,node('p',(entry.authors||['BUPT Reasoning']).join(' · '),'card-author'),actions);
  return card;
}

async function load(){
  failed=false;render();
  try{
    const response=await fetch('data/blog-index.json',{cache:'no-cache'});if(!response.ok)throw Error();
    const catalog=await response.json();if(!Array.isArray(catalog.articles)||!catalog.articles.length)throw Error();
    entries=[...catalog.articles].sort((a,b)=>(a.order??0)-(b.order??0));
    const target=entries.find(entry=>location.hash==='#'+encodeURIComponent(entry.articleId));
    if(target&&collection!=='all'&&target.collection!==collection)collection=target.collection;
    render();
    if(target){
      document.getElementById(target.articleId)?.scrollIntoView({behavior:'instant',block:'start'});
    }
  }catch{
    failed=true;render();
  }
}
load();
