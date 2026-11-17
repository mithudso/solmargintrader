import test from 'node:test';
import assert from 'node:assert/strict';
import { importSource } from './helpers/import-source.js';
import { MemoryStore } from '../src/storage/memoryStore.js';
import { ConfigStore } from '../src/storage/store.js';
async function worker() {
  const listeners={}, alarms=new Map(), data=new Map(), events=[], logs=[];
  const store = new MemoryStore();
  globalThis.chrome={runtime:{onInstalled:{addListener:fn=>listeners.installed=fn},onStartup:{addListener:fn=>listeners.startup=fn},onMessage:{addListener:fn=>listeners.message=fn}},
    storage:{local:{get:async key=>({[key]:data.get(key)}),set:async values=>{for(const [k,v] of Object.entries(values))data.set(k,v);}}},
    alarms:{get:async name=>alarms.get(name),create:async(name,options)=>alarms.set(name,options),clear:async name=>alarms.delete(name),onAlarm:{addListener:fn=>listeners.alarm=fn}},
    action:{setBadgeText:async()=>{},setBadgeBackgroundColor:async()=>{}}};
  globalThis.__workerFixture={store};
  const module=await importSource('src/bg/service-worker.js',{replace:[["import { Store, ConfigStore } from '../storage/store.js';", "import { ConfigStore } from '../storage/store.js'; const Store={open:async()=>globalThis.__workerFixture.store};"]],append:'// fixture '+crypto.randomUUID()});
  for(let i=0;i<40;i++) await Promise.resolve();
  return {module,listeners,alarms,data,store,events,logs};
}
test('CDO-536effe7ed worker activation restores all five missing recurring alarms',async()=>{
  const f=await worker(); assert.deepEqual([...f.alarms.keys()].sort(),['solmargintrader-tick','solmargintrader-manager','solmargintrader-control-room','solmargintrader-soltui-build','solmargintrader-alerts'].sort());
});
test('CDO-d17cfbe924 monitor commits one transition when two read passes overlap',async()=>{
  const {module}=await worker(); const configStore=new ConfigStore(null), store=new MemoryStore(); let state='up',release,entered;
  const barrier=new Promise(resolve=>entered=resolve), gate=new Promise(resolve=>release=resolve); let block=false;
  const deps={configStore,store,clock:()=>1000,soltui:{request:async()=>{
    if(block){entered();await gate;}
    return {ok:true,command:'suite',error:null,result:{schema_version:1,capability:'control-room-v1',status:{state:'running',ui_url:'http://127.0.0.1:57927'},health:{schema_version:1,overall:state,ready:state==='up',components:{manager:{state}}}}};
  }}};
  const notices=[]; await module.runControlRoomMonitor({deps,notify:async a=>notices.push(a)}); state='down'; block=true;
  const first=module.runControlRoomMonitor({deps,notify:async a=>notices.push(a)}); await barrier;
  const second=module.runControlRoomMonitor({deps,notify:async a=>notices.push(a)}); release(); await Promise.all([first,second]);
  assert.equal(notices.length,1,'overlap must not duplicate transition notifications');
});
test('CDO-9ca6f8975f alarm failures emit fixed safe diagnostics and a durable code',async()=>{
  const f=await worker(), errors=[], original=console.error;
  chrome.storage.local.get=async()=>{throw new Error('synthetic-secret-must-not-leak');}; console.error=(...args)=>errors.push(args);
  try{await f.listeners.alarm({name:'solmargintrader-manager'});for(let i=0;i<40;i++)await Promise.resolve();}
  finally{console.error=original;}
  assert.ok(errors.length);assert.ok(!JSON.stringify(errors).includes('synthetic-secret'));
  assert.ok((await f.store.recentEvents()).some(e=>e.type==='background-failure'&&e.operation==='manager-poll'));
});
test('CDO-7947b7c6b5 actual installed listener forwards update details and preserves owner KILL',async()=>{
  const f=await worker(); f.data.set('runtime',{armed:true,killSwitch:true});f.data.set('config',{mode:'full-auto'});
  await f.listeners.installed({reason:'update',previousVersion:'fixture-old'}); for(let i=0;i<50;i++)await Promise.resolve();
  assert.equal(f.data.get('runtime').armed,false);assert.equal(f.data.get('runtime').killSwitch,true);assert.equal(f.data.get('config').mode,'full-auto');
  assert.ok((await f.store.recentEvents()).some(e=>e.type==='updated'&&e.previousVersion==='fixture-old'));
});
