import test from 'node:test';
import assert from 'node:assert/strict';
import {loadMonitorSnapshot} from '../static/js/review-monitor-live.mjs';

test('uses current crawler summary before the deployed snapshot', async () => {
  const calls=[]; const fetcher=async url=>{calls.push(url);return {ok:true,json:async()=>({years:[{year:2025}],commit:'live'})}};
  const result=await loadMonitorSnapshot(fetcher,123);
  assert.equal(result.data.commit,'live'); assert.equal(result.live,true);
  assert.match(calls[0],/raw\.githubusercontent\.com/); assert.equal(calls.length,1);
});

test('falls back to the deployed snapshot when the crawler summary cannot load', async () => {
  const calls=[]; const fetcher=async url=>{calls.push(url); if(calls.length===1) throw new Error('offline'); return {ok:true,json:async()=>({years:[{year:2024}],commit:'published'})}};
  const result=await loadMonitorSnapshot(fetcher,123);
  assert.equal(result.data.commit,'published'); assert.equal(result.live,false);
  assert.equal(calls[1],'data/review-monitor.json');
});

async function renderMonitor(t, sources) {
  const elements = new Map();
  const element = () => ({value:'', innerHTML:'', textContent:'', style:{}, hidden:false, listeners:{}, addEventListener(name, handler) { this.listeners[name] = handler; }});
  const document = {
    querySelector(selector) {
      if (!elements.has(selector)) elements.set(selector, element());
      return elements.get(selector);
    },
    createElement() { return {click() {}}; },
  };
  document.querySelector('#status').value = 'all';
  let downloaded;
  t.mock.method(URL, 'createObjectURL', blob => { downloaded = blob; return 'blob:test'; });
  t.mock.method(URL, 'revokeObjectURL', () => {});
  const snapshot = {generated_at:'2026-11-09T14:00:00Z', commit:'test', repository:'https://example.org/', years:[{year:2024, captured_at:'2026-11-05', sources}]};
  const originals = new Map(['document','fetch','setInterval'].map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  t.after(() => {
    for (const [key, descriptor] of originals) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else delete globalThis[key];
    }
  });
  globalThis.document = document;
  globalThis.fetch = async () => ({ok:true, json:async () => snapshot});
  globalThis.setInterval = () => 0;
  await import(`../static/js/review-monitor.mjs?render-test=${encodeURIComponent(t.name)}`);
  assert.equal(document.querySelector('#error').textContent, '');
  return {get: selector => document.querySelector(selector), download: async () => {
    document.querySelector('#download').listeners.click();
    return downloaded.text();
  }};
}

const source = overrides => ({code:'envsoft', title:'Environmental Modelling & Software', owner:'南耀笛', papers:260, candidates:9, snapshot_candidates:9, missing_abstract:9, official_total:260, state:'已采集', issues:[], actions:[], files:[], evidence_urls:[], ...overrides});

test('renders verified backfills and remaining count in the actual page and download', async t => {
  const page = await renderMonitor(t, [source({backfilled_abstract:9, remaining_missing_abstract:0, issues:['其他元信息仍待核查']})]);
  const counts = /原始缺摘要 9 篇 · 已核补齐 9 篇 · 仍缺 0 篇/;
  assert.match(page.get('#list').innerHTML, counts);
  assert.match(page.get('#metrics').innerHTML, /<strong>0<\/strong><span>候选仍缺摘要<\/span>/);
  assert.match(page.get('#list').innerHTML, /其他元信息仍待核查/);
  assert.match(await page.download(), counts);
});

test('renders old cached data as unknown instead of inventing zero backfills', async t => {
  const page = await renderMonitor(t, [source({})]);
  const counts = /原始缺摘要 9 篇 · 已核补齐 未知 篇 · 仍缺 未知 篇（补齐统计待更新）/;
  assert.match(page.get('#list').innerHTML, counts);
  assert.match(page.get('#metrics').innerHTML, /<strong>未知<\/strong><span>候选仍缺摘要（补齐统计待更新）<\/span>/);
  assert.match(await page.download(), counts);
});

test('does not hide unavailable counts behind a known zero in the overview', async t => {
  const page = await renderMonitor(t, [source({backfilled_abstract:9, remaining_missing_abstract:0}), source({code:'unavailable', missing_abstract:null, backfilled_abstract:null, remaining_missing_abstract:null})]);
  assert.match(page.get('#metrics').innerHTML, /<strong>未知<\/strong><span>候选仍缺摘要（补齐统计待更新）<\/span>/);
  assert.match(page.get('#list').innerHTML, /原始缺摘要 未知 篇 · 已核补齐 未知 篇 · 仍缺 未知 篇/);
});
