import {safeLink} from './blog-core.mjs';
export function node(tag,text,cls){const element=document.createElement(tag);if(text!==undefined)element.textContent=text;if(cls)element.className=cls;return element;}
export function link(text,url,external=false){const valid=safeLink(url);if(!valid)return node('span',text);const a=node('a',text);a.href=valid;if(external){a.target='_blank';a.rel='noopener noreferrer';}return a;}
export const getLanguage=()=>document.documentElement.lang==='en'?'en':'zh';
export const tr=(zh,en)=>getLanguage()==='en'?en:zh;
export function setupLanguage(onChange=()=>{}){
  const button=document.getElementById('lang-toggle');
  function apply(lang){
    const root=document.documentElement;root.lang=lang==='en'?'en':'zh-CN';root.dataset.lang=lang;
    document.querySelectorAll('[data-zh][data-en]').forEach(el=>el.textContent=el.dataset[lang]);
    document.querySelectorAll('[data-label-zh][data-label-en]').forEach(el=>el.setAttribute('aria-label',lang==='en'?el.dataset.labelEn:el.dataset.labelZh));
    button.textContent=lang==='en'?'中文':'EN';button.setAttribute('aria-label',lang==='en'?'切换到中文':'Switch to English');
    try{localStorage.setItem('ai4s-lang',lang);}catch{}
    const url=new URL(location.href);if(url.searchParams.has('lang')){url.searchParams.set('lang',lang);history.replaceState(null,'',url);}
    document.dispatchEvent(new Event('ai4s-language-change'));onChange();
  }
  let preferred=new URLSearchParams(location.search).get('lang');
  if(!['zh','en'].includes(preferred)){try{preferred=localStorage.getItem('ai4s-lang');}catch{}}
  button.onclick=()=>apply(getLanguage()==='en'?'zh':'en');apply(preferred==='en'?'en':'zh');
}
export function setupTheme(){
  const root=document.documentElement,button=document.getElementById('theme-toggle');
  function update(){const dark=root.dataset.theme==='dark';button.textContent=dark?tr('☀ 浅色','☀ Light'):tr('☾ 深色','☾ Dark');button.setAttribute('aria-label',dark?tr('切换浅色主题','Switch to light theme'):tr('切换深色主题','Switch to dark theme'));}
  button.onclick=()=>{const theme=root.dataset.theme==='dark'?'light':'dark';root.dataset.theme=theme;try{localStorage.setItem('ai4s-theme',theme);}catch{}update();};update();
  document.addEventListener('ai4s-language-change',update);
}
