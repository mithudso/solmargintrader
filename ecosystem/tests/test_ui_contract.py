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
        shutil.which("node"), "Node is needed for chart lifecycle checks"
    )
    def test_oracle_chart_refresh_preserves_hidden_overlay_and_single_instance(self):
        program = r"""
const vm=require('node:vm'), fs=require('node:fs'), assert=require('node:assert/strict');
const nodes=new Map();
class Element {
 constructor(tag='div'){this.tagName=tag;this.children=[];this.events={};this.dataset={};this.classList={add(){}};}
 append(...items){for(const item of items)this.children.push(...(item.tagName==='#fragment'?item.children:[item]));}
 replaceChildren(...items){this.children=[];this.append(...items);}
 addEventListener(name,listener){this.events[name]=listener;}
}
const element=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
let created=0, markerRows=[];
const library={LineSeries:{},createChart(){created++;return{addSeries:()=>({setData(){}}),timeScale:()=>({getVisibleLogicalRange:()=>null,fitContent(){}})};},createSeriesMarkers:()=>({setMarkers(rows){markerRows=rows;}})};
const context={document:{getElementById:element,createElement:tag=>new Element(tag),createDocumentFragment:()=>new Element('#fragment')},window:{},fakeLibrary:library};
// Replace only the module transport with a local fake, leaving render and DOM code intact.
const source=fs.readFileSync(process.argv[1],'utf8');
assert.equal(source.split('import("/lightweight-charts.mjs")').length,2);
vm.runInNewContext(source.replace('import("/lightweight-charts.mjs")','Promise.resolve(fakeLibrary)'),context);
const graph={status:'available',instrument:'SOL/USD',count:1,ticks:[{tick_id:'one',time:1000,price:10,strategies:[{strategy_id:'rsi',direction:1}],aggregate:null}]};
(async()=>{
 await Promise.all([context.window.OracleChart.render(graph),context.window.OracleChart.render(graph)]);
 assert.equal(created,1,'overlapping renders created multiple chart instances');
 const toggle=element('oracle-chart-legend').children[0].children[0];
 assert.equal(toggle.checked,true);toggle.checked=false;toggle.events.change();
 assert.equal(markerRows.length,0);
 await context.window.OracleChart.render(graph);
 assert.equal(element('oracle-chart-legend').children[0].children[0].checked,false,'polling reset the hidden overlay');
 assert.equal(markerRows.length,0);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
        result = subprocess.run(
            [shutil.which("node"), "-e", program, str(WEB / "oracle-chart.js")],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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
