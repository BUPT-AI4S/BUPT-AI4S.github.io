import test from 'node:test';
import assert from 'node:assert/strict';
import {loadMonitorSnapshot} from '../static/js/review-monitor-live.mjs';

test('renders official-no-abstract records as not requiring supplementation', async () => {
  const ids = ['year','owner','search','status','owner-actions','view-title','scope','metrics','count','empty','list','download','error','provenance','content'];
  const elements = Object.fromEntries(ids.map(id => [id, {value:id==='year'?'2024':id==='status'?'all':'',style:{},addEventListener(){}}]));
  const globals = {document:globalThis.document,fetch:globalThis.fetch,setInterval:globalThis.setInterval};
  globalThis.document = {querySelector:selector=>elements[selector.slice(1)]};
  globalThis.setInterval = ()=>0;
  globalThis.fetch = async ()=>({ok:true,json:async()=>({generated_at:'now',commit:'test',repository:'https://example.org/',years:[{year:2024,sources:[{
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
