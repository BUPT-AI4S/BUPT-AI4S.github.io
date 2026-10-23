import {latestNews,articleUrl} from './news-core.mjs?v=20261023-home-news';
import {getLanguage} from './blog-shared.mjs';

const banner=document.getElementById('home-news');
let current,pending=false;

function render(){
 if(!current){banner.hidden=true;return;}
 const english=getLanguage()==='en',title=document.getElementById('home-news-title'),details=document.getElementById('home-news-details');
 title.textContent=english?current.titleEn||current.title:current.title;
 title.href=details.href=articleUrl(current.id);
 document.getElementById('home-news-summary').textContent=english?current.summaryEn||current.summary:current.summary;
 const date=document.getElementById('home-news-date');date.textContent=current.date;date.dateTime=current.date;
 banner.hidden=false;
}

async function refresh(){
 if(pending)return;
 pending=true;
 try{
  const response=await fetch('data/news-index.json',{cache:'no-cache',signal:AbortSignal.timeout(10000)});
  if(!response.ok)throw Error('News unavailable');
  const catalog=await response.json();
  if(catalog.schemaVersion!==1||!Array.isArray(catalog.articles))throw Error('Invalid news catalog');
  current=latestNews(catalog.articles);render();
 }catch{/* Retain the last successful teaser during a temporary connection failure. */}
 finally{pending=false;}
}

document.addEventListener('ai4s-language-change',render);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
setInterval(()=>{if(!document.hidden)refresh();},60000);
refresh();
