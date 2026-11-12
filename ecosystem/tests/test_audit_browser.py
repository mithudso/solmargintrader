"""Offline deferred-response and marker regressions, with explicit completion."""

from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

WEB = Path(__file__).parents[1] / "web"


@unittest.skipUnless(shutil.which("node"), "Node required for browser contracts")
class BrowserMaintenanceTests(unittest.TestCase):
    def run_js(self, code, file):
        result = subprocess.run(
            [shutil.which("node"), "-e", code, str(WEB / file)],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("COMPLETE", result.stdout)

    def test_latest_swap_selection_owns_configuration(self):
        self.run_js(
            r"""
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const elements=new Map(),requests=[];
const element=id=>{if(!elements.has(id))elements.set(id,{value:'50',textContent:'',disabled:false,events:{},addEventListener(k,f){this.events[k]=f;}});return elements.get(id)};
const context={document:{getElementById:element},window:{},location:{search:'?asset=SOL'},URLSearchParams,AbortController,setTimeout:()=>1,clearTimeout(){},fetch:url=>new Promise(resolve=>requests.push({url,resolve}))};vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);
const timer=setTimeout(()=>process.exit(2),5000);
(async()=>{element('swap-asset').value='USDC';const pending=element('swap-asset').events.change();
const reply=asset=>({ok:true,json:async()=>({schema_version:1,ok:true,data:{provider:'jupiter',plugin_src:'https://plugin.jup.ag/plugin-v1.js',asset,asset_mapping_status:'available',default_referral_fee_bps:50,minimum_referral_fee_bps:50,maximum_referral_fee_bps:255,selected_referral_account:'fixture'}})});
requests[1].resolve(reply('USDC'));await pending;requests[0].resolve(reply('SOL'));await new Promise(setImmediate);
assert.equal(element('swap-asset').value,'USDC');assert.equal(vm.runInContext('settings.asset',context),'USDC');console.log('COMPLETE');})().catch(e=>{console.error(e);process.exitCode=1}).finally(()=>clearTimeout(timer));
""",
            "swap.js",
        )

    def test_long_flat_and_existing_buy_sell_aggregate_markers(self):
        self.run_js(
            r"""
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
class Element{constructor(){this.children=[];this.dataset={};this.classList={add(){}};}append(...x){this.children.push(...x)}replaceChildren(...x){this.children=x}addEventListener(){}}
const nodes=new Map(),element=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id)};let markers=[];
const library={createChart:()=>({addSeries:()=>({setData(){}}),timeScale:()=>({getVisibleLogicalRange:()=>null,fitContent(){}})}),createSeriesMarkers:()=>({setMarkers:x=>markers=x}),LineSeries:{}};
const context={window:{},document:{getElementById:element,createElement:()=>new Element(),createDocumentFragment:()=>new Element()},library};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8').replace('import("/lightweight-charts.mjs")','Promise.resolve(library)'),context);
const timer=setTimeout(()=>process.exit(2),5000);
(async()=>{for(const [i,signal] of ['Long','Flat','Strong Buy','Strong Sell'].entries()){await context.window.OracleChart.render({status:'available',instrument:'SOL/USD',count:1,ticks:[{time:i+1,tick_id:i+1,price:10,strategies:[],aggregate:{signal}}]});assert.equal(markers.length,1);assert.equal(markers[0].text,i===0||i===2?'ALL ↑':i===3?'ALL ↓':'ALL ·');}console.log('COMPLETE');})().catch(e=>{console.error(e);process.exitCode=1}).finally(()=>clearTimeout(timer));
""",
            "oracle-chart.js",
        )
