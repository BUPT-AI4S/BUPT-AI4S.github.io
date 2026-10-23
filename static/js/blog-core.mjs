const categories={data:'科学数据',knowledge:'科学知识模型',foundation:'科学基础模型',agents:'科学智能体',evaluation:'科学评测',labs:'自主实验室','math-physics':'数理科学',life:'生命科学',matter:'物质科学',earth:'地球宇宙科学',information:'信息科学',social:'社会科学'};
const categoriesEn={data:'Scientific data',knowledge:'Scientific knowledge models',foundation:'Scientific foundation models',agents:'Scientific agents',evaluation:'Scientific evaluation',labs:'Autonomous laboratories','math-physics':'Mathematics & physics',life:'Life sciences',matter:'Chemical & materials sciences',earth:'Earth & space sciences',information:'Information sciences',social:'Social sciences'};
export const categoryName=(id,lang='zh')=>(lang==='en'?categoriesEn:categories)[id]||id;
export const COLLECTIONS=[
  {id:'reviews',zh:'综述',en:'Reviews',hintZh:'从全景建立认识',hintEn:'Start with the big picture'},
  {id:'agents',zh:'科学智能体',en:'Scientific agents',hintZh:'从行动走向发现',hintEn:'From action to discovery'},
  {id:'foundation',zh:'科学基础模型',en:'Foundation models',hintZh:'探索模型与表征',hintEn:'Explore models and representations'},
  {id:'knowledge',zh:'科学知识建模',en:'Knowledge modeling',hintZh:'连接知识与推理',hintEn:'Connect knowledge and reasoning'},
  {id:'data',zh:'科学数据',en:'Scientific data'},
  {id:'evaluation',zh:'评测',en:'Evaluation'},
  {id:'labs',zh:'自主实验室',en:'Autonomous labs'},
  {id:'math-physics',zh:'AI4数理科学',en:'AI4 Mathematics & Physics'},
  {id:'life',zh:'AI4生命科学',en:'AI4 Life sciences'},
  {id:'matter',zh:'AI4物质科学',en:'AI4 Matter sciences'},
  {id:'earth',zh:'AI4地球宇宙科学',en:'AI4 Earth & Space sciences'},
  {id:'information',zh:'AI4信息科学',en:'AI4 Information sciences'},
  {id:'social',zh:'AI4社会科学',en:'AI4 Social sciences'}
];
export const collectionName=(id,lang='zh')=>COLLECTIONS.find(group=>group.id===id)?.[lang==='en'?'en':'zh']||(lang==='en'?'All articles':'全部文章');
export function readCollection(search){
  const id=new URLSearchParams(search).get('category');
  return COLLECTIONS.some(group=>group.id===id)?id:'all';
}
export const filterCollection=(entries,id)=>COLLECTIONS.some(group=>group.id===id)?entries.filter(entry=>entry.collection===id):[...entries];
export function seriesLabel(entry,lang='zh'){
  if(![1,2,3,4].includes(entry.seriesPart))return '';
  return lang==='en'?'Part '+['I','II','III','IV'][entry.seriesPart-1]:'精读（'+['一','二','三','四'][entry.seriesPart-1]+'）';
}
export const readingLink=(id,collection)=>'blog-article.html?id='+encodeURIComponent(id)+(COLLECTIONS.some(group=>group.id===collection)?'&category='+encodeURIComponent(collection):'');
export function safeLink(value){
  if(typeof value!=='string'||!value.trim()||/[\u0000-\u0020\\]/.test(value)||value.startsWith('//'))return null;
  if(/^https?:\/\//i.test(value)){try{return new URL(value).href;}catch{return null;}}
  if(/^[a-z][a-z\d+.-]*:/i.test(value)||value.startsWith('/'))return null;
  return value;
}

// Preserve the former heading IDs so links into older articles still resolve.
export function splitChapters(blocks){
  const chapters=[];let chapter,headingIndex=0;
  for(const source of blocks){
    const block={...source};
    if(block.type==='heading')block.headingId='part-'+(++headingIndex);
    if(block.type==='heading'&&block.level!==3){
      chapter={id:block.headingId,title:block.text,blocks:[]};chapters.push(chapter);
    }else if(!chapter){
      chapter={id:'intro',title:null,blocks:[]};chapters.push(chapter);
    }
    chapter.blocks.push(block);
  }
  return chapters;
}
export function chapterFromHash(chapters,hash){
  let id;try{id=decodeURIComponent(hash.replace(/^#/,''));}catch{return 0;}
  const index=chapters.findIndex(chapter=>chapter.id===id||chapter.blocks.some(block=>block.headingId===id));
  return index<0?0:index;
}
