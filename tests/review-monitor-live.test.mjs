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
