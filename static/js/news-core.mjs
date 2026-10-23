export function filterNews(entries,query=''){
 const terms=query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
 return entries.filter(entry=>{const text=[entry.title,entry.titleEn,entry.summary,entry.summaryEn,entry.source,entry.date].filter(Boolean).join(' ').toLocaleLowerCase();return terms.every(term=>text.includes(term));});
}
export function articleUrl(id,query=''){
 const params=new URLSearchParams({id});if(query.trim())params.set('q',query.trim());return 'news-article.html?'+params;
}
export function findArticle(entries,id){return typeof id==='string'&&/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id)?entries.find(entry=>entry.id===id):undefined;}
