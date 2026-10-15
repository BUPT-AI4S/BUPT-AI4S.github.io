import {COLLECTIONS,collectionName,filterCollection,readCollection,seriesLabel,readingLink} from './blog-core.mjs';
import {setupTheme,setupLanguage,getLanguage,tr,node,link} from './blog-shared.mjs';
setupTheme();
const list=document.getElementById('article-list'),status=document.getElementById('load-status');
let entries=null,failed=false;
let collection=readCollection(location.search);
function selectCollection(id){
  collection=id;
  const url=new URL(location.href);if(id==='all')url.searchParams.delete('category');else url.searchParams.set('category',id);
  url.hash='';history.replaceState(null,'',url);render();
  document.getElementById('article-scroll').scrollTop=0;
  if(!matchMedia('(prefers-reduced-motion: reduce)').matches)list.animate([{opacity:.4,transform:'translateY(6px)'},{opacity:1,transform:'none'}],{duration:230,easing:'ease-out'});
  document.getElementById(id==='all'?'all-articles':'pocket-'+id)?.focus({preventScroll:true});
}
function renderPockets(){
  const buttons=COLLECTIONS.map(group=>{
    const button=node('button',undefined,'pocket-tab');button.type='button';button.id='pocket-'+group.id;button.dataset.collection=group.id;
    button.setAttribute('aria-pressed',String(collection===group.id));button.setAttribute('aria-controls','article-panel');
    if(entries&&!entries.some(entry=>entry.collection===group.id))button.classList.add('pocket-empty');
    for(const cls of ['pocket-back','pocket-paper paper-one','pocket-paper paper-two']){
      const decoration=node('span',undefined,cls);decoration.setAttribute('aria-hidden','true');button.append(decoration);
    }
    const front=node('span',undefined,'pocket-front');
    front.append(node('span',collectionName(group.id,getLanguage()),'pocket-title'));button.append(front);
    button.onclick=()=>selectCollection(group.id);return button;
  });
  document.getElementById('pocket-tabs').replaceChildren(...buttons);
  document.getElementById('all-articles').setAttribute('aria-pressed',String(collection==='all'));
  document.getElementById('article-panel').dataset.collection=collection;
  document.getElementById('collection-title').textContent=collectionName(collection,getLanguage());
  const series=document.getElementById('series-description');series.hidden=collection!=='reviews';
  series.textContent=tr('《科学大语言模型：从数据基础到智能体前沿》精读系列','A Survey of Scientific Large Language Models: From Data Foundations to Agent Frontiers — A Close Reading');
}
function render(){
  renderPockets();
  if(entries){
    const visible=filterCollection(entries,collection);
    list.replaceChildren(...visible.map(renderCard));status.replaceChildren();
    document.getElementById('empty-collection').hidden=visible.length>0;
    document.getElementById('collection-status').textContent=tr('当前显示：','Showing: ')+collectionName(collection,getLanguage());
  }
  else if(failed){
    status.replaceChildren(node('span',tr('文章暂时加载失败。','Articles could not be loaded.')));
    const retry=node('button',tr('重新加载','Try again'));retry.onclick=load;status.append(retry);
  }else status.textContent=tr('正在加载文章…','Loading articles…');
}
document.getElementById('all-articles').onclick=()=>selectCollection('all');
window.addEventListener('popstate',()=>{collection=readCollection(location.search);render();});
setupLanguage(render);

function renderCard(entry,index){
  const card=node('article',undefined,'article-card');card.id=entry.articleId;card.dataset.collection=entry.collection;
  const top=node('div',undefined,'card-top');
  top.append(node('span',String((entry.order??index)+1).padStart(2,'0'),'card-number'));
  if(entry.seriesPart)top.append(node('span',seriesLabel(entry,getLanguage()),'series-part'));
  const english=getLanguage()==='en';
  const heading=node('h3');heading.append(link(english?entry.titleEn||entry.title:entry.title,readingLink(entry.articleId,collection)));
  const tags=node('div',undefined,'tags');
  tags.append(node('span',collectionName(entry.collection,getLanguage())));
  const actions=node('div',undefined,'card-actions');
  const read=link(tr('阅读全文','Read article'),readingLink(entry.articleId,collection));read.className='card-read';
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
      const scroll=document.getElementById('article-scroll'),card=document.getElementById(target.articleId);
      scroll.scrollTop+=card.getBoundingClientRect().top-scroll.getBoundingClientRect().top-4;
    }
  }catch{
    failed=true;render();
  }
}
load();
