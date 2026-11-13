"""Client safety checks; a VM DOM does not replace installed browser acceptance."""

from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

WEB = Path(__file__).parents[1] / "web"


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.labels = []
        self.remote_scripts = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.append(attributes["id"])
        if tag == "label" and attributes.get("for"):
            self.labels.append(attributes["for"])
        if tag == "script" and attributes.get("src", "").startswith(
            ("http:", "https:")
        ):
            self.remote_scripts.append(attributes["src"])


HARNESS = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {randomUUID} = require('node:crypto');
const source = fs.readFileSync(process.argv[1], 'utf8');
async function fixture(preferences = null) {
  const elements = new Map(); let document;
  class Element {
    constructor(tag = 'div') { this.tagName = tag.toUpperCase(); this.children = []; this.dataset = {}; this.attributes = {}; this.value = ''; this.textContent = ''; this.checked = false; this.disabled = false; this.hidden = false; this.isConnected = true; }
    append(...items) { for (const item of items) { if (item?.tagName === '#FRAGMENT') this.children.push(...item.children); else if (item !== undefined) this.children.push(typeof item === 'string' ? {textContent:item,children:[]} : item); } }
    replaceChildren(...items) { this.children = []; this.append(...items); }
    setAttribute(name, value) { this.attributes[name] = String(value); }
    removeAttribute(name) { delete this.attributes[name]; }
    addEventListener(name, callback) { (this.events ||= {})[name] ||= []; this.events[name].push(callback); }
    dispatch(name) { for (const callback of this.events?.[name] || []) callback({target:this}); }
    querySelectorAll(selector) { const all = []; const visit = (item) => { for (const child of item.children || []) { all.push(child); visit(child); } }; visit(this); return selector.includes('input') ? all.filter(item => item.tagName === 'INPUT' && (!selector.includes(':checked') || item.checked)) : selector === '[data-control-key]' ? all.filter(item => item.dataset?.controlKey) : []; }
    closest(selector) { return this.id === 'aggregate-meter' && selector === '.aggregate-reading' ? element('aggregate-reading') : null; }
    matches() { return false; }
    focus() { document.activeElement = this; }
    get childNodes() { return this.children; }
    get lastChild() { return this.children.at(-1); }
    get rows() { return this.children.filter(item => item.tagName === 'TR'); }
  }
  const element = (id) => { if (!elements.has(id)) { const item = new Element(); item.id = id; elements.set(id,item); } return elements.get(id); };
  document = {activeElement:null, getElementById:element, createElement:tag=>new Element(tag), createDocumentFragment:()=>new Element('#fragment'), createTextNode:text=>({tagName:'#TEXT',textContent:text,children:[]}), querySelectorAll:()=>[]};
  const context = vm.createContext({document, location:{hash:'',origin:'http://127.0.0.1:8768'}, window:{addEventListener(){}}, localStorage:{getItem(){return preferences ? JSON.stringify(preferences) : null;},setItem(){}}, console, URL, AbortController, crypto:{randomUUID}, fetch:async()=>{throw new Error('offline');}, setTimeout:()=>1, clearTimeout(){}, setInterval(){}, queueMicrotask(){}});
  vm.runInContext(source, context);
  await new Promise(setImmediate); await new Promise(setImmediate);
  return {context,element};
}
const read = (context, code) => vm.runInContext(code, context);
const tree = (element) => [element, ...(element.children || []).flatMap(tree)];

function seedResearch(context, selected = true) {
  const now = Date.now()/1000;
  const bot = {bot_id:'research-a',source:'f5_batch',owner:'soltui.f5_batch',batch_id:'batch-a',asset:'SOL',strategy_id:'rsi',interval:'1d',preset_horizon:'medium',quote_currency:'USD',mode:'paper',lifecycle:'forward',observed_state:'forecast_recorded',observed_at:now,registration_observation_stale:false,forward:{calls:1,resolved:0,last_target:now+86400,trial_id:'trial-a'}};
  const forward = {status:'unavailable',calls:1,recorded:1,resolved:0,pending:1,excluded:0,missing_economics:0,expired:0,quote_currency:'USD',paper_capital_usd:10000,capital_semantics:'frozen_independent_virtual_trial_basis_not_shared_allocated_cash',trial_id:'trial-a',profit_assessment:'unknown_no_resolved_economics'};
  const analytics = {status:'available',as_of:now,batch_id:'batch-a',source:{status:'available'},coins:[{bot_id:bot.bot_id,asset:'SOL',strategy_id:'rsi',interval:'1d',horizon:'medium',forward}]};
  context.researchSample={bot,analytics,status:{batch_id:'batch-a',supervisor_running:true,heartbeat_at:now,batch:{run_id:'batch-a',running:true,counts:{partial:1},total:1}},registrations:{status:'available',total:1,next_after:null,bots:[bot]}};
  read(context,`state.activeRun='run-a';state.status=researchSample.status;state.registrations=researchSample.registrations;state.selected=${selected ? 'researchSample.bot.bot_id' : 'null'};state.selectedRecord=${selected ? 'researchSample.bot' : 'null'};state.analytics=${selected ? 'researchSample.analytics' : 'null'}`);
  read(context,"$('status-filter').value='all'");
  return context.researchSample;
}
(async()=>{
  {
    const {context,element} = await fixture();
    read(context,"state.swap={config:{default_referral_fee_bps:50},url:'http://127.0.0.1:9000',scope:'manual_wallet_swap'};renderSwapState()");
    assert(tree(element('swap-facts')).some(item=>item.textContent==='0.50% (50 bps) configured default'));
    assert.equal(element('swap-load').disabled,false);
    assert.equal(element('swap-container').children.length,0);
  }
  {
    const {context,element} = await fixture();
    element('launch-referral-bps').value='50';
    read(context,"state.status={config:{cost_model:{referral_fee_bps:10,fee_bps:6}}};renderLaunchCatalog()");
    assert.equal(element('launch-referral-bps').value,'50');
    assert.equal(element('launch-fee-bps').value,6);
    assert.equal(read(context,'state.status.config.cost_model.referral_fee_bps'),10);
    element('launch-referral-bps').value='75';read(context,'renderLaunchCatalog()');
    assert.equal(element('launch-referral-bps').value,'75');
  }
  {
    const {context,element} = await fixture(); const now = Date.now()/1000;
    context.sample = {instrument:'SOL/USD',status:'available',signal:'Strong Buy',as_of:now,horizon_seconds:60,market:{status:'available',observation:{observed_at:now,received_at:now,source:'fixture',kind:'reference'},limitations:[]},aggregate:{balance_percent:75,expires_at:now-1,included:[],excluded:[]},selection:{instrument:'SOL/USD',revision:2,selected_ids:['rsi']},catalog:[{strategy_id:'rsi'}],strategies:[]};
    read(context,'state.oracle=sample; renderSelectedAggregate()');
    assert.equal(element('aggregate-signal').textContent,'Unavailable');
    assert.equal(element('aggregate-meter').hidden,true);
    context.sample.aggregate.expires_at=now+60; context.sample.instrument='BTC/USD';
    read(context,'renderSelectedAggregate()');
    assert.equal(element('aggregate-signal').textContent,'Unavailable');
    context.sample.instrument='SOL/USD'; read(context,'renderSelectedAggregate()');
    assert.equal(element('aggregate-signal').textContent,'Strong Buy');
    assert.equal(element('aggregate-meter').value,75);
    read(context,"state.voterDrafts.set(voterKey(),{ids:['rsi'],revision:1,dirty:true});renderSelectedAggregate()");
    assert.equal(element('voters-save').disabled,true);
    assert.match(element('voters-status').textContent,/changed while you edited/);
    read(context,"state.activeRun='separate-run'");
    assert.equal(read(context,'currentVoterDraft().dirty'),false);
  }
  {
    const prefs = {instrument:'ZEC/USDT',interval:'1h',strategy:'candidate1'};
    const {context,element} = await fixture(prefs);
    assert.equal(read(context,'state.oracleInstrument'),'ZEC/USDT');
    assert.equal(read(context,'state.oracleInterval'),'1h');
    assert.equal(read(context,'state.oracleStrategy'),'candidate1');
    const saved = []; context.localStorage.setItem=(key,value)=>saved.push([key,JSON.parse(value)]);
    context.window.OracleChart={render:async graph=>{context.lastGraph=graph;}};
    read(context,"state.polling=true;state.oracle={signal:'Long'};setInstrument('SOL/USD')");
    assert.equal(read(context,'state.oracle'),null); assert.equal(context.lastGraph,undefined);
    element('oracle-frequency').value='1m';element('oracle-frequency').dispatch('change');
    element('oracle-strategy').value='rsi';element('oracle-strategy').dispatch('change');
    assert.equal(saved.at(-1)[0],'solmargintrader.oracle.display.v1');
    assert.equal(saved.at(-1)[1].instrument,'SOL/USD');assert.equal(saved.at(-1)[1].interval,'1m');assert.equal(saved.at(-1)[1].strategy,'rsi');
    assert.match(read(context,'oracleDisplayPath()'),/interval=1m&strategy=rsi/);
    read(context,"state.oracle={instrument:'SOL/USD',status:'unavailable',display:{publication_instrument:'ZEC/USDT',available_intervals:['1m'],strategies:[]}};renderSelectedAggregate()");
    assert(tree(element('oracle-instrument-detail')).some(item=>item.value==='ZEC/USDT'));
  }
  for (const changed of ["state.oracleInterval='1h'", "state.oracleStrategy='rsi'", "state.oracleInstrument='BTC/USD'"]) {
    const {context} = await fixture(); let release;
    context.fetch=async path=>{if(path.startsWith('/api/oracle?')) return new Promise(resolve=>{release=()=>resolve({ok:true,json:async()=>({schema_version:1,ok:true,data:{instrument:'SOL/USD',signal:'OLD'}})});});throw new Error('offline');};
    const pending=read(context,'refresh()');await new Promise(setImmediate);
    read(context,changed+';changeOracleDisplay()');release();await pending;
    assert.equal(read(context,'state.oracle'),null);
  }
  {
    const {context,element} = await fixture();
    read(context,"state.control={servers:[{id:'manager',actions:[{action:'manager.service',label:'Install',enabled:true,params:{action:'install'}},{action:'manager.service',label:'Uninstall',enabled:true,params:{action:'uninstall'}}]}],catalog:{}};renderControl()");
    const before=element('server-actions').querySelectorAll('[data-control-key]')[1]; before.focus();
    read(context,'renderControl()');
    const after=element('server-actions').querySelectorAll('[data-control-key]')[1];
    assert.notEqual(before,after); assert.equal(context.document.activeElement,after);
  }
  {
    const {context,element} = await fixture(); let posts=0; let posted;
    context.fetch=async(url,options)=>{if(options?.method==='POST'){posts+=1;posted=JSON.parse(options.body);return {ok:true,status:202,json:async()=>({schema_version:1,ok:true,data:{id:posted.request_id,action:posted.action,state:'queued'}})}}throw new Error('offline');};
    read(context,"state.activeRun='legacy-v1';state.session={csrf_nonce:'fixture'};state.control={read_only_source:true,mutation_allowed:false,servers:[{id:'pipeline',actions:[{action:'pipeline.stop',enabled:true}]}],recording:{enabled:true,revision:1},catalog:{strategies:[{id:'rsi'}],manager_schema:{strategies:{trend:{}}}}};renderControl()");
    assert.equal(element('source-policy').hidden,false);
    assert.match(element('source-policy-detail').textContent,/read-only/);
    assert.equal(element('server-actions').querySelectorAll('[data-control-key]')[0].disabled,true);
    assert.equal(element('recording-save').disabled,false);
    assert.equal(element('launch-submit').disabled,false);
    assert.equal(read(context,"actionBlocked('oracle.voters.set',{})"),false);
    for(const action of ['pipeline.start','backtest.stop','oracle.restart','recorder.start']) await read(context,`submitAction('${action}',{})`);
    assert.equal(posts,0);
    assert.equal(read(context,"actionBlocked('pipeline.start',{run_id:'separate-run'})"),false);
    await read(context,"submitAction('manager.prepare-input',{identity:'native',mode:'prospective'})");
    assert.equal(posts,1);assert.equal(posted.params.run_id,undefined);assert.equal(posted.params.mode,'prospective');
  }
  {
    const {context,element} = await fixture(); let posted;
    context.fetch=async(url,options)=>{if(options?.method==='POST'){posted=JSON.parse(options.body);return {ok:true,status:202,json:async()=>({schema_version:1,ok:true,data:{id:posted.request_id,action:posted.action,state:'queued'}})}}throw new Error('offline');};
    read(context,"state.session={csrf_nonce:'fixture'};state.control={configs:[{bot_id:'native',display_name:'Native',strategy_id:'trend',source:'manager',config_revision:1}],statuses:{bots:[{bot_id:'native',action_capabilities:{}}]},catalog:{manager_schema:{strategies:{trend:{}}}}};renderManagerConfigs()");
    const mode=tree(element('manager-configs')).find(item=>item.id==='manager-input-mode-native');
    assert.equal(mode.value,'prospective');mode.value='historical';mode.dispatch('change');
    const controls=tree(element('manager-configs'));
    assert(controls.some(item=>item.textContent==='Register prepared input'));
    assert(controls.some(item=>item.textContent==='Check registered data'));
    assert(controls.some(item=>item.textContent==='Check cycle evidence'));
    controls.find(item=>item.tagName==='BUTTON'&&item.textContent==='Prepare reference input').dispatch('click');
    await new Promise(setImmediate);
    assert.equal(posted.action,'manager.prepare-input');assert.equal(posted.params.identity,'native');assert.equal(posted.params.mode,'historical');assert.equal(posted.params.source,undefined);
  }
  {
    const {context} = await fixture();
    const rendered=read(context,"renderMarkdown('# <img src=x onerror=bad()>\\n\\n[bad](javascript:alert(1))\\n\\n<script>bad()</script>')");
    const nodes=tree(rendered);
    assert.equal(nodes.some(node=>['SCRIPT','IMG','IFRAME'].includes(node.tagName)),false);
    assert.equal(nodes.some(node=>node.tagName==='A' && String(node.href).startsWith('javascript:')),false);
    assert.equal(nodes.some(node=>String(node.textContent).includes('<script>')),true);
  }
  {
    const {context,element} = await fixture(); let unlock; let posts=0; let posted;
    context.fetch=async(url,options)=>{
      if(url==='/api/session') return await new Promise(resolve=>{unlock=()=>resolve({ok:true,status:200,json:async()=>({schema_version:1,ok:true,data:{csrf_nonce:'fixture-memory-nonce'}})});});
      if(options?.method==='POST') {posts+=1;posted=JSON.parse(options.body);assert.equal(options.headers['X-Sol-CSRF'],'fixture-memory-nonce');return {ok:true,status:202,json:async()=>({schema_version:1,ok:true,data:{id:posted.request_id,action:posted.action,state:'queued'}})};}
      throw new Error('offline');
    };
    read(context,"state.activeRun='run-a';state.session=null");
    const action=read(context,"submitAction('pipeline.stop',{})");
    await Promise.resolve(); read(context,"state.activeRun='run-b'"); unlock(); await action;
    assert.equal(posted.params.run_id,'run-a'); assert.equal(posts,1);
    assert.equal(element('action-feedback').textContent.includes('fixture-memory-nonce'),false);
    await new Promise(setImmediate);
  }
  {
    const {context} = await fixture(); let posts=0;
    read(context,"state.session={csrf_nonce:'fixture-memory-nonce'}");
    context.fetch=async(url,options)=>{if(options?.method==='POST')posts+=1;throw new Error('connection lost');};
    await read(context,"submitAction('pipeline.start',{})");
    assert.equal(posts,1);
    assert.equal(read(context,"Array.from(state.localActions.values()).at(-1).state"),'unknown');
  }

  {
    const {context,element}=await fixture();const sample=seedResearch(context,false);let requests=0;
    context.fetch=async(path,options)=>{assert.equal(options?.method,undefined);assert.match(path,/bot_id=research-a&run_id=run-a/);requests++;return {ok:true,json:async()=>({schema_version:1,ok:true,data:sample.analytics})};};
    await read(context,'selectSoleResearchBot()');
    assert.equal(read(context,'state.selected'),'research-a');assert.equal(requests,1);
    assert.equal(element('paper-capital-title').textContent,'Selected trial capital');
    assert.equal(element('paper-capital').textContent,'$10,000.00');
    assert.match(element('capital-note').textContent,/Independent virtual trial/);
    assert.equal(element('paper-pnl').textContent,'Awaiting first settlement');
    assert.match(element('pnl-note').textContent,/1 pending call/);
    assert.match(element('pnl-note').textContent,/not a guaranteed settlement time/);
    assert.equal(element('selected-name').textContent,'SOL · rsi');
    assert(tree(element('overview-fields')).some(item=>item.textContent==='Running · research batch owner'));
    assert.equal(element('equity-message').textContent,'Awaiting first settlement');
    assert(tree(element('bot-rows')).some(item=>item.textContent==='Awaiting first settlement'));
    assert.equal(sample.analytics.coins[0].forward.realized_pnl_usd,undefined);
  }

  {
    const {context,element}=await fixture();const sample=seedResearch(context,false);let analytics=0;
    const response=data=>({ok:true,json:async()=>({schema_version:1,ok:true,data})});
    context.fetch=async(path,options)=>{
      assert.equal(options?.method,undefined);
      if(path.startsWith('/api/status'))return response(sample.status);
      if(path.startsWith('/api/registrations'))return response(sample.registrations);
      if(path.startsWith('/api/telemetry'))return response({next_after:0,events:[],has_more:false});
      if(path.startsWith('/api/control'))return response({});
      if(path.startsWith('/api/analytics')){analytics++;return response(sample.analytics);}
      throw new Error('fixture endpoint unavailable');
    };
    await read(context,'refresh()');await new Promise(setImmediate);
    assert.equal(read(context,'state.selected'),'research-a');assert.equal(analytics,1);
    assert.equal(element('paper-capital').textContent,'$10,000.00');
  }
  for (const change of ["state.registrations.total=2", "state.page=1", "state.registrations.next_after='more'", "state.selected='explicit-manager';state.selectedRecord={bot_id:'explicit-manager',source:'manager'}"]) {
    const {context}=await fixture();seedResearch(context,false);let requests=0;
    context.fetch=async()=>{requests++;throw new Error('must not fetch');};read(context,change);
    await read(context,'selectSoleResearchBot()');assert.equal(requests,0);
    assert.equal(read(context,'state.selected'),change.includes('explicit-manager')?'explicit-manager':null);
  }
  {
    const {context,element}=await fixture();const sample=seedResearch(context);
    sample.analytics.coins[0].forward.realized_pnl_usd=0;
    read(context,'renderSummary();renderInspector();renderAnalytics()');
    assert.equal(element('paper-pnl').textContent,'Awaiting first settlement');
    for (const [field,expected] of [['missing_economics','Missing economics'],['excluded','Recording gaps'],['expired','Expired outcomes']]) {
      sample.analytics.coins[0].forward[field]=1;read(context,'renderSummary();renderAnalytics()');
      assert.equal(element('paper-pnl').textContent,expected);assert.equal(element('equity-message').textContent,expected);
      sample.analytics.coins[0].forward[field]=0;
    }
    sample.analytics.coins[0].forward.status='available';sample.analytics.coins[0].forward.resolved=1;sample.analytics.coins[0].forward.pending=0;sample.analytics.coins[0].forward.realized_pnl_usd=125;
    read(context,'renderSummary();renderInspector()');assert.equal(element('paper-pnl').textContent,'$125.00');
    assert(tree(element('overview-fields')).some(item=>item.textContent==='$125.00'));
    sample.status.heartbeat_at-=31;read(context,'renderInspector()');
    assert(!tree(element('overview-fields')).some(item=>item.textContent==='Running · research batch owner'));
    sample.status.heartbeat_at=Date.now()/1000;sample.status.batch.run_id='other-batch';read(context,'renderInspector()');
    assert(!tree(element('overview-fields')).some(item=>item.textContent==='Running · research batch owner'));
  }
  for(const change of ["state.analytics.as_of-=31", "state.analytics.as_of+=60", "state.analytics.source.status='unavailable'", "state.analytics.batch_id='other-batch'", "state.status.batch_id='other-batch'", "state.analytics.coins[0].forward.trial_id='other-trial'", "state.registrations.bots[0].registration_observation_stale=true"]) {
    const {context,element}=await fixture();seedResearch(context);read(context,change+';renderSummary();renderInspector();renderAnalytics()');
    assert.equal(element('paper-capital').textContent,'Unavailable');assert.equal(element('paper-pnl').textContent,'Evidence unavailable');
    assert(!tree(element('overview-fields')).some(item=>item.textContent==='$10,000.00'));
    assert.equal(element('coin-rows').children.length,0);
  }
  {
    const {context,element}=await fixture();seedResearch(context);
    read(context,"state.selected='manager-a';state.selectedRecord={bot_id:'manager-a',source:'manager'};state.telemetry={manager:{status:'available',bots:[{bot_id:'manager-a',mode:'paper',configured_virtual_capital:{value:500},financials:{realized_net_pnl_usd:{value:2},unrealized_net_pnl_usd:{value:3}}}]}};renderSummary()");
    assert.equal(element('paper-capital-title').textContent,'Manager virtual capital');assert.equal(element('paper-capital').textContent,'$500.00');
    assert.equal(element('paper-pnl').textContent,'$5.00');assert.equal(element('paper-pnl-title').textContent,'Manager paper P&L');
  }
  {
    const {context,element}=await fixture();const sample=seedResearch(context);let releaseOld;
    const other={...sample.bot,bot_id:'research-b',asset:'BTC',forward:{...sample.bot.forward,trial_id:'trial-b'}};
    sample.registrations.bots.push(other);sample.registrations.total=2;
    const newer={...sample.analytics,coins:[{...sample.analytics.coins[0],bot_id:other.bot_id,asset:'BTC',forward:{...sample.analytics.coins[0].forward,paper_capital_usd:20000,trial_id:'trial-b'}}]};
    context.otherBot=other;
    const response=data=>({ok:true,json:async()=>({schema_version:1,ok:true,data})});
    context.fetch=async path=>{
      if(path.startsWith('/api/analytics?bot_id=research-a'))return new Promise(resolve=>{releaseOld=()=>resolve(response(sample.analytics));});
      if(path.startsWith('/api/analytics?bot_id=research-b'))return response(newer);
      if(path.startsWith('/api/status'))return response(sample.status);
      if(path.startsWith('/api/registrations'))return response(sample.registrations);
      if(path.startsWith('/api/telemetry'))return response({next_after:0,has_more:false,events:[]});
      if(path.startsWith('/api/control'))return response({});
      throw new Error('fixture endpoint unavailable');
    };
    const pending=read(context,'refresh()');await new Promise(setImmediate);await read(context,'selectBot(otherBot)');
    assert.equal(element('paper-capital').textContent,'$20,000.00');releaseOld();await pending;
    assert.equal(read(context,'state.analytics.coins[0].bot_id'),'research-b');assert.equal(element('paper-capital').textContent,'$20,000.00');
  }

  {
    const {context,element}=await fixture();const sample=seedResearch(context);
    sample.analytics.coins[0].forward.calls=0;sample.analytics.coins[0].forward.recorded=0;sample.analytics.coins[0].forward.pending=0;
    read(context,'renderSummary()');assert.equal(element('paper-pnl').textContent,'Awaiting first call');
    context.fetch=async()=>{throw new Error('fixture failed');};await read(context,'selectBot(researchSample.bot)');
    assert.equal(element('paper-pnl').textContent,'Evidence unavailable');assert.equal(element('pnl-note').textContent,'Research owner unavailable');
  }
  {
    const {context}=await fixture();const sample=seedResearch(context);let oldRelease;let calls=0;
    const latest={...sample.analytics,coins:[{...sample.analytics.coins[0],forward:{...sample.analytics.coins[0].forward,paper_capital_usd:25000}}]};
    context.fetch=async()=>{
      calls++;if(calls===1)return new Promise(resolve=>{oldRelease=()=>resolve({ok:true,json:async()=>({schema_version:1,ok:true,data:sample.analytics})});});
      return {ok:true,json:async()=>({schema_version:1,ok:true,data:latest})};
    };
    const older=read(context,'selectBot(researchSample.bot)');await new Promise(setImmediate);
    await read(context,'selectBot(researchSample.bot)');oldRelease();await older;
    assert.equal(read(context,'state.analytics.coins[0].forward.paper_capital_usd'),25000);
  }
  {
    const {context}=await fixture();const sample=seedResearch(context);let release;
    context.fetch=async()=>new Promise(resolve=>{release=()=>resolve({ok:true,json:async()=>({schema_version:1,ok:true,data:sample.analytics})});});
    const pending=read(context,'selectBot(researchSample.bot)');await new Promise(setImmediate);
    read(context,"state.activeRun='run-b';state.analytics=null");release();await pending;assert.equal(read(context,'state.analytics'),null);
  }
  {
    const {context,element}=await fixture();const now=Date.now()/1000;
    context.qualifyingSample={instrument:'SOL/USD',status:'unavailable',as_of:now,horizon_seconds:60,market:{status:'available',observation:{instrument:'SOL/USD',observed_at:now,received_at:now,source:'fixture',kind:'reference'}},selection:{instrument:'SOL/USD',selected_ids:['bb_reversion','rsi','macd']},aggregate:{reason:'insufficient_current_voting_evidence',included:[],excluded:[{strategy_id:'bb_reversion',reason:'accuracy_at_or_below_threshold'},{strategy_id:'rsi',reason:'insufficient_evidence'},{strategy_id:'macd',reason:'warmup_required'}]},catalog:[{strategy_id:'bb_reversion',version:'v1'},{strategy_id:'rsi'},{strategy_id:'macd'}],strategies:[{strategy_id:'bb_reversion',version:'v1',instrument:'SOL/USD',source:'fixture',kind:'reference',issued_at:now-1,expires_at:now+30,horizon_seconds:60,direction:1,hits:8,resolved:29,confidence_percent:100*8/29,selected:true}]};
    read(context,'state.oracle=qualifyingSample;renderSelectedAggregate()');
    assert.equal(element('aggregate-signal').textContent,'Unavailable');assert.equal(element('aggregate-meter').hidden,true);
    assert.match(element('aggregate-reason').textContent,/0 of 3 selected strategies qualify/);
    assert.match(element('aggregate-reason').textContent,/1 warming up/);
    assert.match(element('oracle-shadow-leader').textContent,/bb reversion · UP/);
    assert.match(element('oracle-shadow-leader').textContent,/8\/29/);
    assert.match(element('oracle-shadow-leader').textContent,/Unqualified shadow/);
    const row=context.qualifyingSample.strategies[0];
    for(const [key,value] of [['expires_at',now-1],['instrument','BTC/USD'],['source','other'],['version','old'],['resolved',0]]) {
      const previous=row[key];row[key]=value;read(context,'renderSelectedAggregate()');
      assert.equal(element('oracle-shadow-leader').hidden,true);row[key]=previous;
    }
    context.qualifyingSample.market.observation.observed_at=now-16;read(context,'renderSelectedAggregate()');
    assert.equal(element('oracle-shadow-leader').hidden,true);
  }
  console.log('UI behavior: stale/pair gates, voter isolation, legacy guards, native input routing, hostile Markdown, run capture and no automatic mutation retry passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
"""


class UiContractTests(unittest.TestCase):
    def test_static_dom_targets_labels_and_sdk_isolation(self):
        document = Document()
        document.feed((WEB / "index.html").read_text())
        self.assertFalse(
            [key for key, count in Counter(document.ids).items() if count > 1]
        )
        self.assertFalse(set(document.labels) - set(document.ids))
        source = (WEB / "app.js").read_text()
        targets = set(re.findall(r'\$\("([A-Za-z0-9-]+)"\)', source))
        self.assertFalse(targets - set(document.ids))
        self.assertFalse(document.remote_scripts)
        for sink in (
            "innerHTML",
            "outerHTML",
            "insertAdjacentHTML",
            "sessionStorage",
        ):
            self.assertNotIn(sink, source)
        self.assertEqual(source.count("localStorage."), 2)
        self.assertEqual(source.count('"solmargintrader.oracle.display.v1"'), 2)
        self.assertNotIn("localStorage.clear", source)

    @unittest.skipUnless(
        shutil.which("node"), "Node is needed for the client behavior checks"
    )
    def test_client_behavior_contract(self):
        completed = subprocess.run(
            [shutil.which("node"), "-e", HARNESS, str(WEB / "app.js")],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
