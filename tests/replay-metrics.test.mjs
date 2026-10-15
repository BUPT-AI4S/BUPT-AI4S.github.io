import test from 'node:test';
import assert from 'node:assert/strict';
import {createReplayCounter,playAddress,playBaseline,readPlayCount} from '../static/js/replay-metrics.mjs';

const response=count=>({ok:true,json:async()=>({status:'success',data:{page_pv:count}})});
function harness(live=true){
  const calls=[],values=new Map();
  const counter=createReplayCounter({live,fetcher:async(url,options={})=>{
    calls.push({url,options});
    const key=options.method==='POST'?JSON.parse(options.body).url:new URL(url).searchParams.get('url');
    if(options.method==='POST')values.set(key,(values.get(key)||0)+1);
    return response(values.get(key)||0);
  }});
  return {counter,calls,values};
}

test('every course has a stable baseline and a distinct counter key',()=>{
  assert.equal(playBaseline('lecture-01'),286);
  assert.equal(playBaseline('lecture-02'),218);
  assert.equal(playBaseline('chairs-01'),253);
  assert.equal(playBaseline('lecture-03'),playBaseline('lecture-03'));
  assert.notEqual(playAddress('lecture-01'),playAddress('lecture-02'));
  assert.equal(new URL(playAddress('lecture-01')).search,'');
  assert.throws(()=>playAddress('../lecture-01'));
});

test('reading does not count a play; resumes and course switches count once per page',async()=>{
  const {counter,calls}=harness();
  assert.equal(await counter.read('lecture-01'),286);
  assert.equal(calls.filter(c=>c.options.method==='POST').length,0);
  await Promise.all([counter.record('lecture-01'),counter.record('lecture-01')]);
  await counter.record('lecture-02');
  await counter.record('lecture-01');
  assert.equal(calls.filter(c=>c.options.method==='POST').length,2);
  assert.equal(counter.value('lecture-01'),287);
  assert.equal(counter.value('lecture-02'),219);
  assert.equal(JSON.parse(calls.find(c=>c.options.method==='POST').options.body).isNewUv,false);
});

test('local previews read shared totals but never submit plays',async()=>{
  const {counter,calls}=harness(false);
  await counter.read('chairs-01');
  await counter.record('chairs-01');
  assert.equal(counter.value('chairs-01'),253);
  assert.ok(calls.every(c=>c.options.method!=='POST'));
});

test('a late read cannot overwrite a newer successful play',async()=>{
  let resolveRead;
  const counter=createReplayCounter({live:true,fetcher:async(url,options)=>
    options.method==='POST'?response(1):new Promise(resolve=>resolveRead=resolve)});
  const reading=counter.read('lecture-01');
  await counter.record('lecture-01');
  resolveRead(response(0));await reading;
  assert.equal(counter.value('lecture-01'),287);
});

test('malformed totals and failures do not become fabricated successful plays',async()=>{
  for(const count of [null,undefined,'',false,-1,1.5,'NaN','1x'])assert.equal(readPlayCount({data:{page_pv:count}}),null);
  assert.equal(readPlayCount({data:{page_pv:'0'}}),0);
  let posts=0;
  const counter=createReplayCounter({live:true,fetcher:async(url,options)=>{
    if(options.method==='POST'){posts++;throw Error('uncertain delivery');}
    return response(4);
  }});
  await counter.read('lecture-01');await counter.record('lecture-01');await counter.record('lecture-01');
  assert.equal(counter.value('lecture-01'),290);
  assert.equal(posts,1);
  const offline=createReplayCounter({live:true,fetcher:async()=>{throw Error('offline');}});
  assert.equal(await offline.read('lecture-02'),null);
  assert.equal(offline.value('lecture-02'),null);
});
