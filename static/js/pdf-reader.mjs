import * as pdfjs from '../vendor/pdfjs/pdf.mjs';
import {EventBus,PDFViewer,PDFLinkService} from '../vendor/pdfjs/pdf_viewer.mjs';
import {pdfSourceLinks,nativePdfSource} from './pdf-reader-core.mjs';
const $=id=>document.getElementById(id),params=new URLSearchParams(location.search),en=params.get('lang')==='en';
const tr=(zh,english)=>en?english:zh;document.documentElement.lang=en?'en':'zh-CN';
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&window.parent!==window){event.preventDefault();window.parent.postMessage({type:'ai4s-pdf-exit'},location.origin);}});
pdfjs.GlobalWorkerOptions.workerSrc=new URL('../vendor/pdfjs/pdf.worker.mjs',import.meta.url).href;
const assets=new URL('../vendor/pdfjs/',import.meta.url).href;
const eventBus=new EventBus(),linkService=new PDFLinkService({eventBus,externalLinkTarget:2,externalLinkRel:'noopener noreferrer'});
const viewer=new PDFViewer({container:$('viewer-container'),viewer:$('pdf-viewer'),eventBus,linkService,textLayerMode:1,annotationMode:1,imageResourcesPath:assets+'images/'});linkService.setViewer(viewer);
let task,documentPdf,loadVersion=0;
function controls(ready){for(const id of ['previous','next','zoom-in','zoom-out','fit-width','page-number'])$(id).disabled=!ready;}
for(const [id,zh,english] of [['previous','上一页','Previous'],['next','下一页','Next'],['fit-width','适合宽度','Fit width'],['pdf-download','原站 PDF','Original PDF'],['pdf-paper-page','论文页面','Paper page'],['reader-mode','浏览器阅读 · 如未显示，请打开原站 PDF','Browser reader · If blank, open Original PDF'],['retry-pdf','重试','Retry'],['page-label','页码','Page']])$(id).textContent=tr(zh,english);
$('native-pdf').title=tr('浏览器 PDF 阅读器','Browser PDF reader');
function message(text,retry=false){$('pdf-message-text').textContent=text;$('pdf-message').hidden=!text;$('retry-pdf').hidden=!retry;}
function update(){const page=viewer.currentPageNumber||1;$('page-number').value=page;$('previous').disabled=page<=1;$('next').disabled=page>=(documentPdf?.numPages||1);$('zoom-level').textContent=Math.round(viewer.currentScale*100)+'%';}
eventBus.on('pagesinit',()=>{viewer.currentScaleValue='page-width';update();});
eventBus.on('pagechanging',update);eventBus.on('scalechanging',update);
eventBus.on('pagerendered',event=>{if(!documentPdf)return;if(event.error)message(tr('该页渲染失败，请重试。','Could not render this page. Please retry.'),true);else message('');});
$('previous').addEventListener('click',()=>{viewer.currentPageNumber=Math.max(1,viewer.currentPageNumber-1);});
$('next').addEventListener('click',()=>{viewer.currentPageNumber=Math.min(documentPdf?.numPages||1,viewer.currentPageNumber+1);});
$('page-number').addEventListener('change',()=>{viewer.currentPageNumber=Math.max(1,Math.min(documentPdf?.numPages||1,parseInt($('page-number').value,10)||1));update();});
$('zoom-in').addEventListener('click',()=>{viewer.currentScale=Math.min(4,viewer.currentScale*1.2);});
$('zoom-out').addEventListener('click',()=>{viewer.currentScale=Math.max(.25,viewer.currentScale/1.2);});
$('fit-width').addEventListener('click',()=>{viewer.currentScaleValue='page-width';});
new ResizeObserver(()=>{if(documentPdf&&viewer.currentScaleValue==='page-width')viewer.currentScaleValue='page-width';}).observe($('viewer-container'));
new ResizeObserver(entries=>{document.documentElement.style.setProperty('--pdf-toolbar-height',entries[0].target.getBoundingClientRect().height+'px');}).observe(document.querySelector('.pdf-toolbar'));
function useBrowserReader(url) {
  documentPdf=null;viewer.setDocument(null);controls(false);
  $('pdf-controls').hidden=true;$('viewer-container').hidden=true;
  $('native-reader').hidden=false;$('reader-mode').hidden=false;
  $('native-pdf').src=nativePdfSource(url);message('');
}
async function load(){
  const version=++loadVersion;let sources={pdf:'',paper:''};
  controls(false);message(tr('正在加载 PDF…','Loading PDF…'));documentPdf=null;viewer.setDocument(null);
  $('native-reader').hidden=true;$('native-pdf').removeAttribute('src');$('reader-mode').hidden=true;
  $('pdf-controls').hidden=false;$('viewer-container').hidden=false;
  for(const id of ['pdf-download','pdf-paper-page']){$(id).hidden=true;$(id).removeAttribute('href');}
  try{
    await task?.destroy();if(version!==loadVersion)return;
    const response=await fetch('data/papers-index.json',{cache:'no-cache'});if(!response.ok)throw new Error('catalog');const data=await response.json();
    if(version!==loadVersion)return;
    const paper=data.papers.find(p=>p.id===params.get('id'));sources=pdfSourceLinks(paper);
    for(const [id,url] of [['pdf-download',sources.pdf],['pdf-paper-page',sources.paper]]){if(url){$(id).href=url;$(id).hidden=false;}}
    if(!sources.pdf)throw new Error('No valid PDF URL');
    document.title=paper.title+' · PDF';
    task=pdfjs.getDocument({url:sources.pdf,cMapUrl:assets+'cmaps/',cMapPacked:true,standardFontDataUrl:assets+'standard_fonts/',wasmUrl:assets+'wasm/',isEvalSupported:false});
    task.onProgress=({loaded,total})=>{if(version===loadVersion)message(total?tr(`正在加载 PDF… ${Math.min(100,Math.round(loaded/total*100))}%`,`Loading PDF… ${Math.min(100,Math.round(loaded/total*100))}%`):tr('正在加载 PDF…','Loading PDF…'));};
    const pdf=await task.promise;if(version!==loadVersion)return;
    documentPdf=pdf;$('page-count').textContent='/ '+documentPdf.numPages;$('page-number').max=documentPdf.numPages;viewer.setDocument(documentPdf);linkService.setDocument(documentPdf);controls(true);update();
  }catch(error){if(version!==loadVersion)return;console.error('PDF loading failed',error);if(sources.pdf)useBrowserReader(sources.pdf);else message(tr('PDF 暂不可用，请重试或通过论文页面阅读。','PDF unavailable. Retry or read on the paper page.'),true);}
}
$('retry-pdf').addEventListener('click',load);load();
