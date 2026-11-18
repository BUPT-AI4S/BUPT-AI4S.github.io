import test from 'node:test';
import assert from 'node:assert/strict';
import {loadMonitorSnapshot} from '../static/js/review-monitor-live.mjs';

test('renders official-no-abstract records as not requiring supplementation', async () => {
  const ids = ['year','owner','search','status','owner-actions','view-title','scope','metrics','count','empty','list','download','error','provenance','content'];
  const elements = Object.fromEntries(ids.map(id => [id, {value:id==='year'?'2025':id==='status'?'all':'',style:{},addEventListener(){}}]));
  const globals = {document:globalThis.document,fetch:globalThis.fetch,setInterval:globalThis.setInterval};
  globalThis.document = {querySelector:selector=>elements[selector.slice(1)]};
  globalThis.setInterval = ()=>0;
  globalThis.fetch = async ()=>({ok:true,json:async()=>({generated_at:'now',commit:'test',repository:'https://example.org/',years:[{year:2025,sources:[{
    code:'nm',title:'Nature Medicine',owner:'A',issues:[],actions:[],files:[],evidence_urls:[],candidates:38,
    missing_abstract:1,abstract_not_required:1,abstract_supplement_required:0
  }]}]})});
  try {
    await import('../static/js/review-monitor.mjs');
    assert.match(elements.list.innerHTML,/候选待补摘要 0 篇/);
    assert.match(elements.list.innerHTML,/无需补摘要 1 篇（原始缺摘要 1 篇）/);
    assert.match(elements.list.innerHTML,/暂无自动提示/);
    assert.doesNotMatch(elements.list.innerHTML,/项待关注/);
    assert.match(elements.metrics.innerHTML,/<strong>0<\/strong><span>候选待补摘要/);
  } finally {
    Object.assign(globalThis,globals);
  }
});

test('shows reviewed inclusions missing from the candidate file and their abstract gaps', async () => {
  const ids = ['year','owner','search','status','owner-actions','view-title','scope','metrics','count','empty','list','download','error','provenance','content'];
  const elements = Object.fromEntries(ids.map(id => [id, {value:id==='year'?'2025':id==='status'?'all':'',style:{},addEventListener(){}}]));
  const globals = {document:globalThis.document,fetch:globalThis.fetch,setInterval:globalThis.setInterval};
  globalThis.document = {querySelector:selector=>elements[selector.slice(1)]};
  globalThis.setInterval = ()=>0;
  globalThis.fetch = async ()=>({ok:true,json:async()=>({generated_at:'now',commit:'test',repository:'https://example.org/',years:[{year:2025,sources:[{
    code:'v',title:'Venue',owner:'A',issues:['存在待同步论文'],actions:[],files:[],evidence_urls:[],candidates:2,
    missing_abstract:0,abstract_supplement_required:0,unsynced_included:3,unsynced_missing_abstract:2
  }]}]})});
  try {
    await import('../static/js/review-monitor.mjs?test=unsynced');
    assert.match(elements.metrics.innerHTML,/<strong>3<\/strong><span>已纳入待同步/);
    assert.match(elements.metrics.innerHTML,/<strong>2<\/strong><span>待同步缺摘要/);
    assert.match(elements.list.innerHTML,/已纳入待同步 3 篇，其中缺摘要 2 篇/);
  } finally {
    Object.assign(globalThis,globals);
  }
});

test('shows full catalogue and final inclusion counts in summary and source detail', async () => {
  const ids=['year','owner','search','status','owner-actions','view-title','scope','metrics','count','empty','list','download','error','provenance','content'];
  const elements=Object.fromEntries(ids.map(id=>[id,{value:id==='year'?'2025':id==='status'?'all':'',style:{},addEventListener(){}}]));
  const globals={document:globalThis.document,fetch:globalThis.fetch,setInterval:globalThis.setInterval};
  globalThis.document={querySelector:selector=>elements[selector.slice(1)]}; globalThis.setInterval=()=>0;
  globalThis.fetch=async()=>({ok:true,json:async()=>({generated_at:'now',commit:'test',repository:'https://example.org/',years:[{year:2025,sources:[{
    code:'v',title:'Venue',owner:'A',issues:[],actions:[],files:[],evidence_urls:[],papers:10,papers_missing_abstract:3,
    candidates:5,final_included:2,final_missing_abstract:1,decisions:{include:2,exclude:3,pending:0,unreviewed:0}
  }]}]})});
  try {
    await import('../static/js/review-monitor.mjs?test=final-counts');
    assert.match(elements.metrics.innerHTML,/<strong>3<\/strong><span>全量缺摘要/);
    assert.match(elements.metrics.innerHTML,/<strong>2<\/strong><span>精筛纳入/);
    assert.match(elements.metrics.innerHTML,/<strong>1<\/strong><span>纳入缺摘要/);
    assert.match(elements.list.innerHTML,/全量采集 10 篇，缺摘要 3 篇/);
    assert.match(elements.list.innerHTML,/精筛纳入 2 篇，缺摘要 1 篇/);
    assert.match(elements.metrics.innerHTML,/<strong>20\.0%<\/strong><span>AI4S占比/);
    assert.match(elements.list.innerHTML,/采集 <strong>10/);
    assert.match(elements.list.innerHTML,/纳入 <strong>2/);
    assert.match(elements.list.innerHTML,/占比 <strong>20\.0%/);
  } finally {Object.assign(globalThis,globals);}
});

test('shows consistent 2024 metrics with zero abstract gaps for an old cached summary', async () => {
  const ids=['year','owner','search','status','owner-actions','view-title','scope','metrics','count','empty','list','download','error','provenance','content'];
  const elements=Object.fromEntries(ids.map(id=>[id,{value:id==='year'?'2024':id==='status'?'all':'',style:{},addEventListener(){}}]));
  const globals={document:globalThis.document,fetch:globalThis.fetch,setInterval:globalThis.setInterval};
  globalThis.document={querySelector:s=>elements[s.slice(1)]}; globalThis.setInterval=()=>0;
  globalThis.fetch=async()=>({ok:true,json:async()=>({generated_at:'now',commit:'test',repository:'https://example.org/',years:[{year:2024,sources:[{
    code:'v',title:'Venue',owner:'A',issues:[],actions:[],files:[],evidence_urls:[],papers:10,papers_missing_abstract:7,candidates:1,missing_abstract:3,abstract_supplement_required:3,final_included:3,final_missing_abstract:7,unsynced_included:2,unsynced_missing_abstract:1
  }]}]})});
  try {
    await import('../static/js/review-monitor.mjs?test=2024-closed');
    assert.match(elements.metrics.innerHTML,/<strong>2<\/strong><span>已纳入待同步/);
    assert.match(elements.metrics.innerHTML,/<strong>0<\/strong><span>待同步缺摘要/);
    assert.match(elements.metrics.innerHTML,/<strong>0<\/strong><span>全量缺摘要/);
    assert.match(elements.metrics.innerHTML,/<strong>0<\/strong><span>纳入缺摘要/);
    assert.match(elements.metrics.innerHTML,/<strong>0<\/strong><span>候选待补摘要/);
    assert.match(elements.list.innerHTML,/全量采集 10 篇，缺摘要 0 篇/);
    assert.match(elements.list.innerHTML,/精筛纳入 3 篇，缺摘要 0 篇/);
  } finally {Object.assign(globalThis,globals);}
});

test('weights overall share and sorts known sources while keeping unknowns last', async () => {
  const ids=['year','owner','search','status','sort','owner-actions','view-title','scope','metrics','count','empty','list','download','error','provenance','content'];
  const elements=Object.fromEntries(ids.map(id=>[id,{value:id==='year'?'2025':id==='status'?'all':id==='sort'?'default':'',style:{},addEventListener(type,fn){this.onchange=fn;}}]));
  const globals={document:globalThis.document,fetch:globalThis.fetch,setInterval:globalThis.setInterval};
  globalThis.document={querySelector:s=>elements[s.slice(1)]};globalThis.setInterval=()=>0;
  const source=(code,papers,final_included)=>({code,title:code,owner:'A',issues:[],actions:[],files:[],evidence_urls:[],candidates:0,papers,final_included});
  globalThis.fetch=async()=>({ok:true,json:async()=>({generated_at:'now',commit:'test',repository:'https://example.org/',years:[{year:2025,sources:[source('Alpha',10,2),source('Beta',90,45),source('Unknown',10,null),source('NoTotal',null,1)]}]})});
  try {
    await import('../static/js/review-monitor.mjs?test=sorting');
    assert.match(elements.metrics.innerHTML,/<strong>47\.0%<\/strong><span>AI4S占比（部分来源）/);
    assert.match(elements.list.innerHTML,/占比 <strong>未知/);
    elements.sort.value='included';elements.sort.onchange();
    assert.ok(elements.list.innerHTML.indexOf('Beta') < elements.list.innerHTML.indexOf('Alpha'));
    assert.ok(elements.list.innerHTML.indexOf('NoTotal') < elements.list.innerHTML.indexOf('Unknown'));
    elements.sort.value='ratio';elements.sort.onchange();
    assert.ok(elements.list.innerHTML.indexOf('Beta') < elements.list.innerHTML.indexOf('Alpha'));
    assert.ok(elements.list.innerHTML.indexOf('Alpha') < elements.list.innerHTML.indexOf('Unknown'));
  } finally {Object.assign(globalThis,globals);}
});

test('uses current crawler summary before the deployed snapshot', async () => {
  const calls=[]; const fetcher=async url=>{calls.push(url);return {ok:true,json:async()=>({years:[{year:2025}],commit:'live'})}};
  const result=await loadMonitorSnapshot(fetcher,123);
  assert.equal(result.data.commit,'live'); assert.equal(result.live,true);
  assert.match(calls[0],/raw\.githubusercontent\.com/); assert.equal(calls.length,2);
});

test('falls back to the deployed snapshot when the crawler summary cannot load', async () => {
  const calls=[]; const fetcher=async url=>{calls.push(url); if(calls.length===1) throw new Error('offline'); return {ok:true,json:async()=>({years:[{year:2024}],commit:'published'})}};
  const result=await loadMonitorSnapshot(fetcher,123);
  assert.equal(result.data.commit,'published'); assert.equal(result.live,false);
  assert.match(calls[1],/^data\/review-monitor\.json\?v=123$/);
});


test('prefers the newer published snapshot over stale live cache', async () => {
  const fetcher=async url=>({ok:true,json:async()=>url.startsWith('https:')
    ? {years:[{year:2024}],commit:'stale',generated_at:'2026-11-16T15:11:35Z'}
    : {years:[{year:2024}],commit:'current',generated_at:'2026-11-16T15:16:07Z'}});
  const result=await loadMonitorSnapshot(fetcher,123);
  assert.equal(result.data.commit,'current');
  assert.equal(result.live,false);
  assert.equal(result.staleLive,true);
});

test('prefers live when newer and survives a failed published request', async () => {
  for (const failPublished of [false,true]) {
    const fetcher=async url=>{
      if (failPublished && !url.startsWith('https:')) throw new Error('published offline');
      return {ok:true,json:async()=>url.startsWith('https:')
        ? {years:[{year:2024}],commit:'current',generated_at:'2026-11-16T15:16:07Z'}
        : {years:[{year:2024}],commit:'old',generated_at:'2026-11-16T15:11:35Z'}};
    };
    const result=await loadMonitorSnapshot(fetcher,123);
    assert.equal(result.data.commit,'current');
    assert.equal(result.live,true);
  }
});

test('fails visibly if neither snapshot can be read', async () => {
  await assert.rejects(loadMonitorSnapshot(async()=>{throw new Error('both offline');},123),/both offline/);
});
