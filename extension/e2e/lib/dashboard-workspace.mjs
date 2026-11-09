/** Real DOM regression checks. All mutations use an injected, memory-only transport. */
import assert from 'node:assert/strict';

export async function verifyDashboardWorkflows(page, browser) {
  const ev = page.ev;
  const wait = async (expr) => {
    const value = await browser.waitFor(() => ev(expr), 15000);
    assert.ok(value, expr);
    return value;
  };
await ev(`(async()=>{
 const r=document.createElement('div');r.id='independent-fixture';r.append(document.querySelector('#view-soltui').cloneNode(true));for(const id of ['deskStartAll','workspacePinLive','workspaceWorkflowStatus','workspaceLiveRail'])r.append(document.getElementById(id).cloneNode(false));document.body.append(r);window.r=r;window.calls=[];window.preview=0;window.fixtureDoc='  original\\n';window.workflowHeld=null;
 window.interleaveDocWrite=false;window.fixtureDocs=null;window.holdDocRead=false;window.holdDocWrite=false;window.docHeldRead=null;window.docHeldWrite=null;window.previewAvailable=true;
 window.liveClock=Date.now()-2000;window.liveDirection='UP';window.liveAccuracy=80;window.liveSamples=40;window.liveVoting={min_accuracy:60,min_resolved:20};window.liveHeld=null;window.liveHoldAsset=null;window.liveFailNext=false;

 const spec=[
 {name:'signals.check',describe:'Current check',params:[],read_only:true,long_running:true},
 {name:'prices.quote',describe:'Jupiter price',params:[],read_only:true,long_running:true},
 {name:'batch.run_all',describe:'All tests',params:[],read_only:false,long_running:true},
 {name:'batch.status',describe:'Batch status',params:[],read_only:true,long_running:true},
 {name:'prices.status',describe:'Prices',params:[],read_only:true},
 {name:'forwardtest.predictions',describe:'Predictions',params:[{name:'asset',type:'string'}],read_only:true},
 {name:'demo.rows',describe:'Rows',params:[],read_only:true},
 {name:'docs.read',describe:'Read',params:[{name:'path',type:'string',required:true}],read_only:true},
 {name:'docs.write',describe:'Write',params:[{name:'path',type:'string',required:true},{name:'text',type:'string',required:true},{name:'expected_revision',type:'string',required:true}],read_only:false},
 {name:'jupiter.order_preview',describe:'Preview',params:[],read_only:false},
 {name:'jupiter.order_submit',describe:'Submit',params:[{name:'preview_id',type:'string',required:true}],read_only:false,requires_confirm:true},
 {name:'settings.save',describe:'Settings',params:[{name:'base_address',type:'string'},{name:'forwardtest_autostart',type:'bool'}],read_only:false}];
 const revision=async text=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))).map(x=>x.toString(16).padStart(2,'0')).join('');
 const en=(command,result)=>({ok:true,command,result,error:null});
 const tx=async m=>{calls.push(m);if(m.type==='soltuiSession')return {ok:true,result:{available:true,connected:true,generation:1}};if(m.type==='soltuiCommands')return {ok:true,result:en('list',spec)};
 if(m.command==='signals.check')return {ok:true,result:en(m.command,{score:100,checked_at:Date.now()/1000,strategies:1,rows:[{strategy:'fresh fixture',prediction:'UP',error:''}]})};
 if(m.command==='prices.quote')return {ok:true,result:en(m.command,{price:87.25,source:'jupiter',block_id:123,fetched_at:Date.now()/1000})};
 if(m.command==='live.rail_refresh')return {ok:true,result:en(m.command,{running:true})};
 if(m.command==='live.rail')return {ok:true,result:en(m.command,{observed_at:Date.now()/1000,age_seconds:0,stale:false,voting:{},activity:{items:[],wallet_items:[]},workflow:{}})};
 if(m.command==='paper.workflow_ensure')return new Promise(resolve=>{workflowHeld=()=>resolve({ok:true,result:en(m.command,{state:'running',running:true,stages:{}})})});
 if(m.command==='batch.run_all')return {ok:true,result:en(m.command,{run_id:'fixture-batch',running:true,message:'Backtesting then forward'})};
 if(m.command==='batch.status')return {ok:true,result:en(m.command,{run_id:'fixture-batch',running:true,phase:'backtesting',assets:['SOL'],intervals:['1m','5m'],counts:{pending:2}})};
 if(m.command==='prices.status')return {ok:true,result:en(m.command,{live:true,prices:{'SOL-USD':{mid:100,bid:99,ask:101,spread_bps:20,quote_ts:liveClock/1000,quote_age_s:(Date.now()-liveClock)/1000}}})};
 if(m.command==='forwardtest.predictions'){if(liveFailNext){liveFailNext=false;throw new Error('temporary prediction read failure')};const response={ok:true,result:en(m.command,{asset:m.params.asset,voting:liveVoting,rows:[{label:'fixture strategy',accuracy:liveAccuracy,resolved:40,pred_1m:liveDirection,acc_1m:liveAccuracy,resolved_1m:liveSamples,issued_1m:Date.now()/1000-60,expires_1m:Date.now()/1000+300}]})};if(m.params.asset===liveHoldAsset)return new Promise((resolve,reject)=>{liveHeld={resolve:()=>resolve(response),reject:()=>reject(new Error('old coin failed'))}});return response;}
 if(m.command==='settings.save' && m.params.live_vote_min_accuracy!==undefined){liveVoting={min_accuracy:m.params.live_vote_min_accuracy,min_resolved:m.params.live_vote_min_resolved};return {ok:true,result:en(m.command,{settings:liveVoting})};}
 if(m.command==='jupiter.order_preview')return {ok:true,result:en(m.command,{preview_id:'preview-'+(++preview),status:'REVIEW',submission_available:previewAvailable,notice:previewAvailable?'Review preview':'Jupiter submission is unavailable.'})};
 if(m.command==='jupiter.order_submit')return {ok:true,result:en(m.command,{preview_id:m.params.preview_id,status:'FILLED',rows:[{preview_id:'row-choice'}]})};
 if(m.command==='docs.read'){const answer={ok:true,result:en(m.command,{path:m.params.path,text:fixtureDocs?fixtureDocs[m.params.path]:fixtureDoc,revision:await revision(fixtureDocs?fixtureDocs[m.params.path]:fixtureDoc),editable:true})};if(holdDocRead){holdDocRead=false;return new Promise(resolve=>{docHeldRead=()=>resolve(answer)})}return answer;}
 if(m.command==='docs.write'){if(interleaveDocWrite){interleaveDocWrite=false;fixtureDocs[m.params.path]='concurrent writer';}const current=fixtureDocs?fixtureDocs[m.params.path]:fixtureDoc;if(m.params.expected_revision!==await revision(current))return {ok:true,result:{ok:false,error:{message:'Document changed since it was read.'}}};if(fixtureDocs)fixtureDocs[m.params.path]=m.params.text;else fixtureDoc=m.params.text;const answer={ok:true,result:en(m.command,{path:m.params.path,bytes:m.params.text.length,revision:await revision(m.params.text)})};if(holdDocWrite){holdDocWrite=false;return new Promise(resolve=>{docHeldWrite=()=>resolve(answer)})}return answer;};
 return {ok:true,result:en(m.command,{rows:[{name:'apple',value:2},{name:'pear',value:1}]})};};
 const intervals=[],nativeSetInterval=window.setInterval;
 window.setInterval=(fn,delay,...args)=>{const id=nativeSetInterval(fn,delay,...args);intervals.push({fn,delay,id});return id};
 try {await (await import(chrome.runtime.getURL('src/ui/soltui-panel.js'))).mountSoltuiPanel(r,tx);(await import(chrome.runtime.getURL('src/ui/live-workspace.js'))).mountLiveWorkspace(r,async(command,params)=>{const response=await tx({type:'soltuiCall',command,params});return response.result.result;})}
 finally {window.setInterval=nativeSetInterval;for(const interval of intervals)clearInterval(interval.id)}
 const predictionTimer=intervals.find(x=>x.fn.name==='pollLivePredictions');
 window.liveTimerTick=predictionTimer?.fn;window.liveTimerDelay=predictionTimer?.delay;
 window.livePriceTick=intervals.find(x=>x.delay===5000)?.fn;
 window.pick=name=>{const s=r.querySelector('#soltuiCommand');s.value=name;s.dispatchEvent(new Event('change'))};
 })()`);
await ev(`pick('jupiter.order_preview');r.querySelector('#soltuiForm').requestSubmit()`);
await wait(`r.querySelector('#soltuiNext button')!==null`);
await ev(`r.querySelector('#soltuiNext button').click()`);
await ev(`(()=>{const c=r.querySelector('#soltuiForm input[type=checkbox]');c.checked=true;c.dispatchEvent(new Event('change'));const p=r.querySelector('[name=preview_id]');p.value='changed';p.dispatchEvent(new Event('input',{bubbles:true}));})()`);
assert.deepEqual(await ev(`({checked:r.querySelector('#soltuiForm input[type=checkbox]').checked,disabled:r.querySelector('#soltuiForm button').disabled})`),{checked:false,disabled:true});
console.log('PASS parameter edit revokes confirmation');
await ev(`(()=>{const p=r.querySelector('[name=preview_id]');p.value='preview-1';p.dispatchEvent(new Event('input',{bubbles:true}));const c=r.querySelector('#soltuiForm input[type=checkbox]');c.checked=true;c.dispatchEvent(new Event('change'));r.querySelector('#soltuiForm').requestSubmit()})()`);
await wait(`calls.some(x=>x.command==='jupiter.order_submit')`);
assert.deepEqual(await ev(`({checked:r.querySelector('#soltuiForm input[type=checkbox]').checked,disabled:r.querySelector('#soltuiForm button').disabled})`),{checked:false,disabled:true});
await ev(`(()=>{const c=r.querySelector('#soltuiForm input[type=checkbox]');c.checked=true;c.dispatchEvent(new Event('change'));[...r.querySelectorAll('#soltuiTables button')].find(x=>x.textContent==='Inspect / use row').click()})()`);
assert.deepEqual(await ev(`({value:r.querySelector('[name=preview_id]').value,checked:r.querySelector('#soltuiForm input[type=checkbox]').checked,disabled:r.querySelector('#soltuiForm button').disabled})`),{value:'row-choice',checked:false,disabled:true});
console.log('PASS row selection and completed attempt revoke confirmation');
await ev(`pick('jupiter.order_preview');r.querySelector('#soltuiForm').requestSubmit()`);
await wait(`preview===2 && r.querySelector('#soltuiNext button')!==null`);
await ev(`r.querySelector('#soltuiNext button').click()`);
assert.equal(await ev(`r.querySelector('[name=preview_id]').value`),'preview-2');
console.log('PASS cached submit result does not overwrite fresh preview handoff');
await ev(`(()=>{pick('settings.save');const c=r.querySelector('[aria-label="Clear base_address"]');c.checked=true;c.dispatchEvent(new Event('change',{bubbles:true}));r.querySelector('[name=forwardtest_autostart]').value='false';r.querySelector('#soltuiForm').requestSubmit()})()`);
await wait(`calls.some(x=>x.command==='settings.save')`);
assert.deepEqual(await ev(`calls.find(x=>x.command==='settings.save').params`),{base_address:'',forwardtest_autostart:false});
console.log('PASS explicit string clear and false boolean reach mock backend');
await ev(`(()=>{pick('docs.read');r.querySelector('[name=path]').value='fixture.md';r.querySelector('#soltuiForm').requestSubmit()})()`);
await wait(`r.querySelector('#soltuiEditor').value===fixtureDoc`);
await ev(`r.querySelector('#soltuiEditor').value='  saved\\n\\n';r.querySelector('#soltuiSave').click()`);
await wait(`r.querySelector('#soltuiEditorStatus').textContent==='Saved to disk.'`);
assert.equal(await ev('fixtureDoc'),'  saved\n\n');
await ev(`r.querySelector('#soltuiEditor').value='my draft';fixtureDoc='external change';r.querySelector('#soltuiSave').click()`);
await wait(`r.querySelector('#soltuiEditorStatus').textContent.startsWith('Save refused:')`);
assert.equal(await ev(`calls.filter(x=>x.command==='docs.write').length`),1);
console.log('PASS editor preserves whitespace and refuses external-edit overwrite');
await ev(`fixtureDocs={'A.md':'base','B.md':'base'};r.querySelector('#soltuiEditor').value='  saved\\n\\n';pick('docs.read');r.querySelector('[name=path]').value='A.md';r.querySelector('#soltuiForm').requestSubmit()`);
await wait(`r.querySelector('#soltuiEditorPath').textContent.startsWith('A.md')`);
await ev(`r.querySelector('#soltuiEditor').value='draft A';holdDocRead=true;r.querySelector('#soltuiSave').click()`);
await wait(`docHeldRead!==null`);
await ev(`r.querySelector('#soltuiEditor').value='base';r.querySelector('[name=path]').value='B.md';r.querySelector('#soltuiForm').requestSubmit()`);
await wait(`r.querySelector('#soltuiEditorPath').textContent.startsWith('B.md')`);
await ev(`r.querySelector('#soltuiEditor').value='draft B';r.querySelector('#soltuiEditorStatus').textContent='Editing B';docHeldRead();docHeldRead=null;new Promise(resolve=>setTimeout(resolve,0))`);
assert.equal(await ev(`calls.filter(x=>x.command==='docs.write' && x.params.path==='B.md').length`),0,'a safety read for A must never authorize a write to B');
assert.equal(await ev(`r.querySelector('#soltuiEditor').value`),'draft B');
await ev(`r.querySelector('#soltuiEditor').value='base';r.querySelector('[name=path]').value='A.md';r.querySelector('#soltuiForm').requestSubmit()`);
await wait(`r.querySelector('#soltuiEditorPath').textContent.startsWith('A.md')`);
await ev(`r.querySelector('#soltuiEditor').value='draft A';holdDocWrite=true;r.querySelector('#soltuiSave').click()`);
await wait(`docHeldWrite!==null`);
await ev(`r.querySelector('#soltuiEditor').value='base';r.querySelector('[name=path]').value='B.md';r.querySelector('#soltuiForm').requestSubmit()`);
await wait(`r.querySelector('#soltuiEditorPath').textContent.startsWith('B.md')`);
await ev(`r.querySelector('#soltuiEditor').value='draft B';r.querySelector('#soltuiEditorStatus').textContent='Editing B';docHeldWrite();docHeldWrite=null;new Promise(resolve=>setTimeout(resolve,0))`);
assert.equal(await ev(`r.querySelector('#soltuiEditorStatus').textContent`),'Editing B','a late acknowledgement cannot mark a new document saved');
assert.equal(await ev(`r.querySelector('#soltuiEditor').value`),'draft B');
console.log('PASS editor binds saves and acknowledgements to the original document');
await ev(`r.querySelector('#soltuiEditor').value='base';r.querySelector('[name=path]').value='A.md';r.querySelector('#soltuiForm').requestSubmit()`);
await wait(`r.querySelector('#soltuiEditorPath').textContent.startsWith('A.md')`);
await ev(`r.querySelector('#soltuiEditor').value='CAS draft';interleaveDocWrite=true;r.querySelector('#soltuiSave').click()`);
await wait(`r.querySelector('#soltuiEditorStatus').textContent.startsWith('Save refused:')`);
assert.equal(await ev(`fixtureDocs['A.md']`),'concurrent writer');
assert.equal(await ev(`r.querySelector('#soltuiEditor').value`),'CAS draft');
assert.match(await ev(`calls.filter(x=>x.command==='docs.write').at(-1).params.expected_revision`),/^[a-f0-9]{64}$/);
console.log('PASS atomic revision conflict preserves concurrent text and editor draft');

await ev(`previewAvailable=false;pick('jupiter.order_preview');r.querySelector('#soltuiForm').requestSubmit()`);
await wait(`preview===3`);
assert.equal(await ev(`r.querySelector('#soltuiNext button')`),null);
assert.ok(await ev(`r.querySelector('#soltuiNext').textContent.includes('unavailable')`));
console.log('PASS unavailable unsigned Jupiter previews offer no submission handoff');
await ev(`r.querySelector('#soltuiLiveRefresh').click()`);
await wait(`r.querySelector('#soltuiLiveScore').textContent.includes('Strong Buy') && r.querySelectorAll('#soltuiLiveChart g[data-tick-time]').length===1`);
assert.ok(await ev(`r.querySelector('#soltuiLiveScore').classList.contains('signal-score-green')`));
const firstTick = await ev(`({time:r.querySelector('#soltuiLiveChart g').dataset.tickTime,x:Number(r.querySelector('#soltuiLiveChart .score-tick').getAttribute('x'))})`);
await ev(`liveClock+=1000;liveDirection='DOWN';r.querySelector('#soltuiLiveRefresh').click()`);
await wait(`r.querySelector('#soltuiPredictionsScore').textContent.includes('Strong Sell') && r.querySelectorAll('#soltuiLiveChart g[data-tick-time]').length===2`);
assert.ok(await ev(`r.querySelector('#soltuiPredictionsScore').classList.contains('signal-score-red')`));
const previousTick = await ev(`({score:r.querySelector('#soltuiLiveChart g').dataset.score,x:Number(r.querySelector('#soltuiLiveChart .score-tick').getAttribute('x'))})`);
assert.equal(previousTick.score, '100');
assert.equal(firstTick.x - previousTick.x, 56);
await ev(`(()=>{const field=r.querySelector('#soltuiVoteMinScore');field.value='90';field.dispatchEvent(new Event('change'))})()`);
await wait(`r.querySelector('#soltuiLiveScore').textContent.includes('No qualifying')`);
assert.ok(await ev(`r.querySelector('#soltuiLiveScore').classList.contains('signal-score-gray')`));
assert.ok(await ev(`calls.some(x=>x.command==='settings.save' && x.params.live_vote_min_accuracy===90)`));
assert.equal(await ev(`r.querySelector('#soltuiLiveChart g').dataset.score`), '100');
console.log('PASS gated live score, colored labels and immutable chart scores scrolling left');
await ev(`liveVoting={min_accuracy:60,min_resolved:20};liveDirection='UP';liveHoldAsset='ETH';r.querySelector('#soltuiLiveAsset').value='ETH';r.querySelector('#soltuiLiveAsset').dispatchEvent(new Event('change'))`);
await wait(`liveHeld!==null`);
assert.ok(await ev(`r.querySelector('#soltuiLiveScore').textContent.includes('No qualifying') && r.querySelector('#soltuiLiveChart').children.length===0`));
await ev(`r.querySelector('#soltuiLiveStream').checked=true;r.querySelector('#soltuiLiveAsset').value='SOL';r.querySelector('#soltuiLiveAsset').dispatchEvent(new Event('change'));liveHoldAsset=null;liveHeld.reject();liveHeld=null`);
await wait(`r.querySelector('#soltuiLiveScore').textContent.includes('Strong Buy') && r.querySelector('#soltuiLiveStatus').textContent.startsWith('SOL-USD')`);
assert.equal(await ev(`r.querySelector('#soltuiLiveStream').checked`),true,'obsolete coin failures cannot stop the current stream');
console.log('PASS coin switch clears old scores and ignores obsolete failures');

// Drive the registered timer with a clock; no manual refresh may perform the
// second read, and Follow stream stays off throughout the cadence checks.
assert.equal(await ev(`typeof liveTimerTick`), 'function');
assert.equal(await ev(`liveTimerDelay`), 10000, 'predictions have a dedicated ten-second timer');
await ev(`window.realNow=Date.now;window.testNow=realNow();Date.now=()=>testNow;liveClock=testNow-1000;r.querySelector('#soltuiLiveStream').checked=false;liveDirection='UP';r.querySelector('#soltuiLiveRefresh').click()`);
await wait(`r.querySelector('#soltuiLivePredictionStatus').textContent.startsWith('Updated') && r.querySelector('#soltuiLiveScore').textContent.includes('Strong Buy')`);
const reads = () => ev(`calls.filter(x=>x.command==='forwardtest.predictions').length`);
const baseline = await reads();
await ev(`liveDirection='DOWN';testNow+=9999;livePriceTick()`);
assert.equal(await reads(), baseline, 'no read before the ten-second deadline');
await ev(`testNow+=1;liveTimerTick()`);
await wait(`r.querySelector('#soltuiLiveScore').textContent.includes('Strong Sell')`);
assert.equal(await reads(), baseline + 1);
assert.ok(await ev(`r.querySelector('#soltuiLivePredictions').textContent.includes('DOWN')`));
assert.ok(await ev(`r.querySelector('#soltuiLivePredictionStatus').textContent.includes('10s')`));
await ev(`liveFailNext=true;testNow+=10000;liveTimerTick()`);
await wait(`r.querySelector('#soltuiLivePredictionStatus').textContent.includes('temporary prediction read failure')`);
assert.equal(await reads(), baseline + 2);
await ev(`liveDirection='UP';testNow+=9999;livePriceTick()`);
assert.equal(await reads(), baseline + 2, 'failures retry at ten seconds, not every price tick');
await ev(`testNow+=1;liveTimerTick()`);
await wait(`r.querySelector('#soltuiLiveScore').textContent.includes('Strong Buy') && r.querySelector('#soltuiLivePredictionStatus').textContent.startsWith('Updated')`);
assert.equal(await reads(), baseline + 3);
await ev(`liveHoldAsset='SOL';testNow+=10000;liveTimerTick()`);
await wait(`liveHeld!==null`);
await ev(`testNow+=10000;liveTimerTick()`);
assert.equal(await reads(), baseline + 4, 'an in-flight request cannot overlap another read');
await ev(`liveHoldAsset=null;liveHeld.resolve();liveHeld=null`);
await wait(`r.querySelector('#soltuiLivePredictionStatus').textContent.startsWith('Updated')`);
await ev(`r.querySelector('#soltuiLive').hidden=true;testNow+=10000;liveTimerTick()`);
assert.equal(await reads(), baseline + 4, 'hidden views do not poll');
await ev(`r.querySelector('#soltuiLive').hidden=false;liveTimerTick()`);
await wait(`calls.filter(x=>x.command==='forwardtest.predictions').length===${baseline + 5}`);
await wait(`r.querySelector('#soltuiLivePredictionStatus').textContent.startsWith('Updated')`);
await ev(`Date.now=realNow`);
console.log('PASS automatic ten-second prediction refresh with Follow off, changed rows, retry, single request and hidden-view guards');

// Direct controls must call the backend, not just select a second form.
await ev(`liveAccuracy=0;r.querySelector('#soltuiLiveRefresh').click()`);
await wait(`r.querySelector('#soltuiLiveScore').textContent.includes('No qualifying')`);
await ev(`r.querySelector('#soltuiManualCheck').click()`);
await wait(`r.querySelector('#manualSignalResult').textContent.includes('fresh fixture')`);
assert.ok(await ev(`r.querySelector('#manualSignalResult').textContent.includes('UP')`));
await ev(`r.querySelector('#soltuiPriceSource').value='jupiter';r.querySelector('#soltuiPriceSource').dispatchEvent(new Event('change'))`);
await wait(`r.querySelector('#soltuiLiveStatus').textContent.startsWith('Jupiter SOL/USD')`);
assert.ok(await ev(`calls.some(x=>x.command==='prices.quote'&&x.params.source==='jupiter')`));
await ev(`r.querySelector('#deskStartAll').click()`);
await wait(`calls.some(x=>x.command==='paper.workflow_ensure') && r.querySelector('#deskStartAll').disabled`);
assert.deepEqual(await ev(`calls.find(x=>x.command==='paper.workflow_ensure').params`),{asset:'SOL',scope:'all'});
await ev(`r.querySelector('#deskStartAll').click()`);
assert.equal(await ev(`calls.filter(x=>x.command==='paper.workflow_ensure').length`),1,'pending workflow cannot duplicate');
await ev(`workflowHeld();workflowHeld=null`);
await wait(`!r.querySelector('#deskStartAll').disabled`);
await ev(`r.querySelector('#soltuiWorkspace').value='all';r.querySelector('#soltuiWorkspace').dispatchEvent(new Event('change'));[...r.querySelectorAll('.tool-card')].find(b=>b.textContent.includes('demo › rows')).click()`);
await wait(`r.querySelector('#soltuiResultCard').classList.contains('expanded-output') && r.querySelector('#soltuiResultLabel').textContent.startsWith('demo.rows')`);
assert.ok(await ev(`calls.some(x=>x.command==='demo.rows')`));
assert.ok(await ev(`r.querySelector('#tradingViewChart iframe').src.includes('tradingview-widget.com/embed-widget/advanced-chart/')`));
console.log('PASS direct actions, expanded results, manual fresh assessment, Jupiter source and one-button paper workflow');

await ev(`window.dispatchEvent(new PageTransitionEvent('pagehide'))`);

}
