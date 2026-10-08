import {mountMindMap} from './mind-map.mjs';
import {formatTime,findMatches,activeSegment,sortCourses} from './replay-core.mjs';
const $=id=>document.getElementById(id), video=$('video');
let course, courses=[], rows=[], matches=[], matchIndex=-1, current=-1, panel='chapters', objectUrl, loadId=0, scale=1, lastSaved=0;
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function empty(parent,text='该项分析暂未生成。'){parent.replaceChildren(el('p',text,'empty'));}
function notice(text){$('notice').textContent=text;}
function safeUrl(value){if(!value)return '';try{const u=new URL(value,location.href);return ['http:','https:','blob:'].includes(u.protocol)?u.href:'';}catch{return '';}}
function seek(ms){if(!Number.isFinite(ms))return;if(!video.currentSrc||video.readyState===0){notice('视频尚未就绪，请先加载课程视频。');return;}video.currentTime=Math.min(ms/1000,Number.isFinite(video.duration)?video.duration:ms/1000);update();}
function timeButton(ms){const b=el('button',formatTime(ms),'time');b.disabled=!Number.isFinite(ms);b.addEventListener('click',()=>seek(ms));return b;}
function save(){if(!course||!Number.isFinite(video.currentTime)||!video.readyState)return;try{localStorage.setItem('ai4s-replay:'+course.id,JSON.stringify({time:video.currentTime}));}catch{}}
function update(){const ms=video.currentTime*1000;$('position').textContent=formatTime(ms);const next=video.readyState > 0 ? activeSegment(rows,ms) : -1;if(next!==current){$('transcript').children[current]?.classList.remove('active');current=next;const node=$('transcript').children[current];node?.classList.add('active');if(node&&$('follow').checked){$('transcript').scrollTo({top:node.offsetTop-50,behavior:'smooth'});}}if(Date.now()-lastSaved>5000){save();lastSaved=Date.now();}}
function renderTranscript(){const box=$('transcript');box.replaceChildren();if(!rows.length){empty(box,'课堂原文待生成。视频可以先行观看，接入听悟后将显示带时间戳的转写。');return;}
  rows.forEach((r,i)=>{const b=el('button',undefined,'utterance');b.append(el('small',`${r.speaker||'发言人'}  ·  ${formatTime(r.start)}`));const p=el('span');let from=0;for(const hit of matches.filter(h=>h.index===i)){p.append(document.createTextNode(r.text.slice(from,hit.start)),el('mark',r.text.slice(hit.start,hit.end)));from=hit.end;}p.append(document.createTextNode(r.text.slice(from)));b.append(p);b.addEventListener('click',()=>seek(r.start));box.append(b);});current=-1;update();}
function search(){matches=findMatches(rows,$('search').value);matchIndex=matches.length?0:-1;renderTranscript();showMatch(false);}
function selectTranscript() {
  const polished = $('transcript-mode').value === 'polished' && course?.transcriptPolished?.length;
  rows = (polished ? course.transcriptPolished : course?.transcript) || [];
  $('transcript-note').textContent = polished
    ? 'AI 整理稿 · 按段落定位；未整理的片段保留原文。可切换原始转写核对。'
    : '原始语音转写 · 可能存在识别错误。';
  search();
}
function showMatch(jump=true){$('count').textContent=`${matchIndex+1}/${matches.length}`;$('previous').disabled=$('next').disabled=!matches.length;document.querySelectorAll('.utterance.hit').forEach(n=>n.classList.remove('hit'));document.querySelectorAll('mark.current-match').forEach(n=>n.classList.remove('current-match'));if(matchIndex<0)return;const hit=matches[matchIndex],node=$('transcript').children[hit.index];node.classList.add('hit');$('transcript').querySelectorAll('mark')[matchIndex]?.classList.add('current-match');$('transcript').scrollTo({top:node.offsetTop-30,behavior:'smooth'});if(jump)seek(rows[hit.index].start);}
function renderPanel(){const box=$('panel');box.replaceChildren();const values=course?.[panel]||[];if(!values.length){empty(box);return;}values.forEach((r,i)=>{const card=el('article',undefined,'card');if(panel==='chapters'){card.append(timeButton(r.start),el('h3',r.title),el('p',r.summary));}if(panel==='speakers'){card.append(el('h3',r.speaker),el('p',r.summary));}if(panel==='questions'){card.append(el('h3',r.question),el('p',r.answer));if(Number.isFinite(r.start))card.append(timeButton(r.start));}if(panel==='slides'){const url=safeUrl(r.image);if(url){const img=el('img');img.src=url;img.alt=`课件画面 ${i+1}`;img.loading='lazy';img.className='slide-image';img.addEventListener('error',()=>img.replaceWith(el('p','图片加载失败')));const open=el('button',undefined,'slide-open');open.setAttribute('aria-label',`预览课件画面 ${i+1}`);open.append(img);open.onclick=()=>{$('preview').querySelector('img').src=url;$('preview').showModal();};card.append(open);}card.append(timeButton(r.start),el('p',r.summary||'暂无该画面的讲解摘要'));}box.append(card);});}
let disposeMind;
function renderMind() {
  disposeMind?.();
  const tree = $('mind-tree');
  tree.replaceChildren();
  if (!course.mindMap?.length) empty(tree, '脑图待生成');
  else disposeMind = mountMindMap(tree, course.mindMap);
  scale = 1;
  zoom(0);
  $('mind-viewport').scrollTo(0, 0);
}
function zoom(delta){scale=Math.min(1.8,Math.max(.5,scale+delta));$('mind-tree').style.zoom=scale;$('zoom-reset').textContent=Math.round(scale*100)+'%';}
async function read(url){const res=await fetch(url);if(!res.ok)throw new Error('课程数据加载失败');return res.json();}
async function load(id) {
  save();
  const token = ++loadId;
  video.pause();
  video.removeAttribute('src');
  video.load();
  if (objectUrl) { URL.revokeObjectURL(objectUrl); objectUrl = null; }
  const entry = courses.find(c => c.id === id);
  course = null;
  $('transcript-mode').disabled = true;
  $('transcript-note').textContent = '';
  rows = [];
  matches = [];
  matchIndex = -1;
  current = -1;
  $('title').textContent = entry?.title || '课程';
  $('meta').textContent = '';
  $('summary').textContent = '正在加载课程概要…';
  $('keywords').replaceChildren();
  $('search').value = '';
  $('position').textContent = '0:00';
  $('video-empty').hidden = false;
  $('local-video').disabled = true;
  $('local-video').value = '';
  disposeMind?.();
  empty($('mind-tree'), '正在加载脑图…');
  empty($('transcript'), '正在加载…');
  empty($('panel'), '正在加载…');
  showMatch(false);
  notice('正在加载课程…');
  try {
    const data = await read(entry.data);
    if (token !== loadId) return;
    course = data;
    const hasPolished = Boolean(course.transcriptPolished?.length);
    $('transcript-mode').querySelector('[value="polished"]').disabled = !hasPolished;
    $('transcript-mode').value = hasPolished ? 'polished' : 'original';
    $('transcript-mode').disabled = false;
    selectTranscript();
    $('title').textContent = course.title;
    $('meta').textContent = `${course.date || ''} · 北京邮电大学`;
    $('course').value = id;
    document.querySelectorAll('#course-list button').forEach(button => {
      const selected = button.dataset.course === id;
      button.classList.toggle('selected', selected);
      if (selected) button.setAttribute('aria-current', 'true');
      else button.removeAttribute('aria-current');
    });
    history.replaceState(null, '', `?course=${encodeURIComponent(id)}`);
    renderTranscript();
    $('summary').textContent = course.summary || '分析待生成。接入听悟后，将在这里呈现课程概要。';
    for (const word of course.keywords || []) {
      const button = el('button', word);
      button.onclick = () => { $('search').value = word; search(); showMatch(); };
      $('keywords').append(button);
    }
    renderPanel();
    renderMind();
    let url = safeUrl(course.videoUrl);
    if (['localhost', '127.0.0.1'].includes(location.hostname)) {
      try {
        const local = await read(`data/${id}.local.json`);
        if (token !== loadId) return;
        url = safeUrl(local.videoUrl) || url;
      } catch { /* Local media configuration is optional. */ }
    }
    if (token !== loadId) return;
    $('local-video').disabled = false;
    $('video-empty').hidden = Boolean(url);
    if (url) video.src = url;
    notice(rows.length
      ? 'AI 分析和整理仅供学习参考，请以课堂视频为准。播放进度保存在当前浏览器。'
      : '课程已建档，课堂分析待生成。当前不展示模拟转写或摘要。');
  } catch {
    if (token !== loadId) return;
    notice('课程数据加载失败，请刷新重试。');
    $('summary').textContent = '无法加载课程概要';
    empty($('mind-tree'), '无法加载脑图');
    empty($('transcript'), '无法加载课堂原文');
    empty($('panel'), '无法加载课程分析');
  }
}
video.addEventListener('timeupdate',update);video.addEventListener('pause',save);window.addEventListener('pagehide',save);video.addEventListener('loadedmetadata',()=>{try{const saved=JSON.parse(localStorage.getItem('ai4s-replay:'+course.id));if(saved?.time>0&&saved.time<video.duration-3)video.currentTime=saved.time;}catch{}video.playbackRate=Number($('speed').value);});video.addEventListener('error',()=>notice('视频加载失败，请检查视频地址，或选择本地视频观看。'));
$('speed').onchange=()=>{video.playbackRate=Number($('speed').value);};$('local-video').onchange=e=>{const file=e.target.files[0];if(!file)return;save();if(objectUrl)URL.revokeObjectURL(objectUrl);objectUrl=URL.createObjectURL(file);video.src=objectUrl;$('video-empty').hidden=true;notice('正在播放所选本地视频，文件不会上传。请确保它与当前课时一致。');};
$('transcript-mode').onchange=selectTranscript;
$('search').addEventListener('input',search);$('search').addEventListener('keydown',e=>{if(e.key==='Enter'&&matches.length){matchIndex=(matchIndex+1)%matches.length;showMatch();}});$('next').onclick=()=>{matchIndex=(matchIndex+1)%matches.length;showMatch();};$('previous').onclick=()=>{matchIndex=(matchIndex-1+matches.length)%matches.length;showMatch();};$('course').onchange=e=>load(e.target.value);
document.querySelectorAll('[data-panel]').forEach(b=>b.onclick=()=>{panel=b.dataset.panel;document.querySelectorAll('[data-panel]').forEach(n=>{n.classList.toggle('selected',n===b);n.setAttribute('aria-pressed',String(n===b));});renderPanel();});
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-view]').forEach(n=>{n.classList.toggle('selected',n===b);n.setAttribute('aria-pressed',String(n===b));});$('guide').hidden=b.dataset.view!=='guide';$('mind').hidden=b.dataset.view!=='mind';});
$('zoom-in').onclick=()=>zoom(.1);$('zoom-out').onclick=()=>zoom(-.1);$('zoom-reset').onclick=()=>{scale=1;zoom(0);};$('close-preview').onclick=()=>$('preview').close();
const viewport=$('mind-viewport');let drag;viewport.addEventListener('pointerdown',e=>{if(e.pointerType==='touch'||e.target.closest('button'))return;drag={x:e.clientX,y:e.clientY,left:viewport.scrollLeft,top:viewport.scrollTop};viewport.setPointerCapture(e.pointerId);});viewport.addEventListener('pointermove',e=>{if(drag){viewport.scrollLeft=drag.left+drag.x-e.clientX;viewport.scrollTop=drag.top+drag.y-e.clientY;}});viewport.addEventListener('pointerup',()=>drag=null);viewport.addEventListener('pointercancel',()=>drag=null);
try{courses=sortCourses(await read('data/courses.json'));if(!courses.length)throw new Error();for(const c of courses){const option=el('option',c.title);option.value=c.id;$('course').append(option);const b=el('button');b.dataset.course=c.id;const copy=el('span',c.title,'course-copy');b.title=c.title;b.append(copy);b.onclick=()=>load(c.id);$('course-list').append(b);}const id=new URLSearchParams(location.search).get('course');await load(courses.some(c=>c.id===id)?id:courses[0].id);}catch{notice('课程目录加载失败，请通过本地预览服务或网站访问。');$('title').textContent='课程暂不可用';}

function expandMind(expanded) {
  $('mind').classList.toggle('expanded', expanded);
  document.body.classList.toggle('mind-expanded', expanded);
  $('mind-expand').textContent = expanded ? '收起画布' : '展开画布';
  $('mind-expand').setAttribute('aria-expanded', String(expanded));
}
$('mind-expand').onclick = () => expandMind(!$('mind').classList.contains('expanded'));
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && $('mind').classList.contains('expanded')) {
    expandMind(false);
    $('mind-expand').focus();
  }
});
