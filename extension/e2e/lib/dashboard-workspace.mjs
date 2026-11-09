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
 const r=document.createElement('div');r.id='independent-fixture';r.append(document.querySelector('#view-soltui').cloneNode(true));document.body.append(r);window.r=r;window.calls=[];window.preview=0;window.fixtureDoc='  original\\n';
 window.liveClock=Date.now()-2000;window.liveDirection='UP';window.liveAccuracy=80;window.liveSamples=40;window.liveVoting={min_accuracy:60,min_resolved:20};window.liveHeld=null;window.liveHoldAsset=null;
 const spec=[
 {name:'prices.status',describe:'Prices',params:[],read_only:true},
 {name:'forwardtest.predictions',describe:'Predictions',params:[{name:'asset',type:'string'}],read_only:true},
 {name:'demo.rows',describe:'Rows',params:[],read_only:true},
 {name:'docs.read',describe:'Read',params:[{name:'path',type:'string',required:true}],read_only:true},
 {name:'docs.write',describe:'Write',params:[{name:'path',type:'string',required:true},{name:'text',type:'string',required:true}],read_only:false},
 {name:'jupiter.order_preview',describe:'Preview',params:[],read_only:false},
 {name:'jupiter.order_submit',describe:'Submit',params:[{name:'preview_id',type:'string',required:true}],read_only:false,requires_confirm:true},
 {name:'settings.save',describe:'Settings',params:[{name:'base_address',type:'string'},{name:'forwardtest_autostart',type:'bool'}],read_only:false}];
 const en=(command,result)=>({ok:true,command,result,error:null});
 const tx=async m=>{calls.push(m);if(m.type==='soltuiSession')return {ok:true,result:{available:true,connected:true,generation:1}};if(m.type==='soltuiCommands')return {ok:true,result:en('list',spec)};
 if(m.command==='prices.status')return {ok:true,result:en(m.command,{live:true,prices:{'SOL-USD':{mid:100,bid:99,ask:101,spread_bps:20,quote_ts:liveClock/1000,quote_age_s:(Date.now()-liveClock)/1000}}})};
 if(m.command==='forwardtest.predictions'){const response={ok:true,result:en(m.command,{asset:m.params.asset,voting:liveVoting,rows:[{label:'fixture strategy',accuracy:liveAccuracy,resolved:40,pred_1m:liveDirection,acc_1m:liveAccuracy,resolved_1m:liveSamples,issued_1m:Date.now()/1000-60,expires_1m:Date.now()/1000+300}]})};if(m.params.asset===liveHoldAsset)return new Promise((resolve,reject)=>{liveHeld={resolve:()=>resolve(response),reject:()=>reject(new Error('old coin failed'))}});return response;}
 if(m.command==='settings.save' && m.params.live_vote_min_accuracy!==undefined){liveVoting={min_accuracy:m.params.live_vote_min_accuracy,min_resolved:m.params.live_vote_min_resolved};return {ok:true,result:en(m.command,{settings:liveVoting})};}
 if(m.command==='jupiter.order_preview')return {ok:true,result:en(m.command,{preview_id:'preview-'+(++preview),status:'REVIEW'})};
 if(m.command==='jupiter.order_submit')return {ok:true,result:en(m.command,{preview_id:m.params.preview_id,status:'FILLED',rows:[{preview_id:'row-choice'}]})};
 if(m.command==='docs.read')return {ok:true,result:en(m.command,{path:m.params.path,text:fixtureDoc,editable:true})};
 if(m.command==='docs.write'){fixtureDoc=m.params.text;return {ok:true,result:en(m.command,{path:m.params.path,bytes:fixtureDoc.length})}};
 return {ok:true,result:en(m.command,{rows:[{name:'apple',value:2},{name:'pear',value:1}]})};};
 await (await import(chrome.runtime.getURL('src/ui/soltui-panel.js'))).mountSoltuiPanel(r,tx);
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

await ev(`window.dispatchEvent(new PageTransitionEvent('pagehide'))`);

}
