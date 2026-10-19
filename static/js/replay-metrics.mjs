const API='https://events.vercount.one/api/v2/log';
export const LIVE_HOST='bupt-ai4s.github.io';
const BASELINES={'lecture-01':286,'lecture-02':218,'lecture-03':157,'chairs-01':253};

export function playBaseline(id){
  if(Object.hasOwn(BASELINES,id))return BASELINES[id];
  let hash=0;for(const char of id)hash=(hash*31+char.charCodeAt(0))>>>0;
  return 180+hash%141;
}
export function playAddress(id){
  if(typeof id!=='string'||!/^\w[\w-]{0,63}$/.test(id))throw Error('Invalid course ID');
  return `https://${LIVE_HOST}/replay-plays/${encodeURIComponent(id)}`;
}
export function readPlayCount(payload){
  const value=payload?.data?.page_pv;
  if(typeof value!=='number'&&!(typeof value==='string'&&/^\d+$/.test(value)))return null;
  const count=Number(value);
  return Number.isSafeInteger(count)&&count>=0?count:null;
}

export function createReplayCounter({fetcher=globalThis.fetch,live=false,onChange=()=>{}}={}){
  const counts=new Map(),attempted=new Set(),pendingReads=new Map(),pendingPlays=new Map();
  const value=id=>counts.has(id)?counts.get(id)+playBaseline(id):null;
  function update(id,count){
    if(count!==null){counts.set(id,Math.max(count,counts.get(id)??0));onChange(id,value(id));}
    return value(id);
  }
  async function request(id,method){
    const address=playAddress(id);
    const options={method,signal:AbortSignal.timeout(8000)};
    let url=API;
    if(method==='POST'){
      options.headers={'Content-Type':'application/json'};
      options.body=JSON.stringify({url:address,isNewUv:false});options.keepalive=true;
    }else{url+='?url='+encodeURIComponent(address);options.cache='no-store';}
    const result=await fetcher(url,options);if(!result.ok)throw Error('Counter unavailable');
    const count=readPlayCount(await result.json());if(count===null)throw Error('Invalid counter response');
    return update(id,count);
  }
  function read(id){
    if(!pendingReads.has(id)){
      const promise=request(id,'GET').catch(()=>value(id)).finally(()=>pendingReads.delete(id));
      pendingReads.set(id,promise);
    }
    return pendingReads.get(id);
  }
  function record(id){
    if(!live)return Promise.resolve(value(id));
    if(pendingPlays.has(id))return pendingPlays.get(id);
    if(attempted.has(id))return Promise.resolve(value(id));
    // A failed request may already have reached the service. Never retry a play blindly.
    attempted.add(id);
    const promise=request(id,'POST').catch(()=>value(id)).finally(()=>pendingPlays.delete(id));
    pendingPlays.set(id,promise);return promise;
  }
  return {read,record,value};
}
