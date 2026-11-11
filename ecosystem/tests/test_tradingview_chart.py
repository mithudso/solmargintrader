"""The external chart must not gain the local control room's origin or session."""

from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

WEB = Path(__file__).parents[1] / "web"
HARNESS = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const elements = new Map();
class Element {
  constructor() { this.children=[];this.attributes={};this.events={};this.hidden=false;this.disabled=false; }
  addEventListener(name, listener) { this.events[name]=listener; }
  setAttribute(key,value) { this.attributes[key]=value; }
  replaceChildren(...children) { this.children=children; }
  focus() { this.focused=true; }
}
const element = id => { if(!elements.has(id))elements.set(id,new Element());return elements.get(id); };
const context = {URL,document:{getElementById:element,createElement:()=>new Element()}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),context);
const load=element('tradingview-load'),close=element('tradingview-close'),container=element('tradingview-chart-container');
assert.equal(container.children.length,0); // No remote document until requested.
load.events.click();
assert.equal(container.children.length,1);
const frame=container.children[0];
const url=new URL(frame.src);
assert.equal(url.origin,'https://www.tradingview-widget.com');
assert.equal(url.pathname,'/embed-widget/advanced-chart/');
const config=JSON.parse(decodeURIComponent(url.hash.slice(1)));
assert.equal(config.symbol,'CRYPTO:ZECUSD');
assert.equal(config.interval,'1');
assert.equal(config.allow_symbol_change,false);
assert.equal(Object.keys(config).some(key=>/secret|owner|wallet|account|token|session/i.test(key)),false);
assert.equal(frame.attributes.sandbox,'allow-scripts allow-same-origin');
assert.equal(frame.referrerPolicy,'no-referrer');
assert.match(frame.title,/ZECUSD/);
assert.equal(load.disabled,true);
load.events.click();
assert.equal(container.children[0],frame); // Repeated clicks cannot open duplicate feeds.
close.events.click();
assert.equal(container.children.length,0);
assert.equal(container.hidden,true);
assert.equal(load.disabled,false);
assert.equal(load.focused,true);
load.events.click();
assert.equal(container.children.length,1);
assert.notEqual(container.children[0],frame);
"""


class TradingViewChartTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is needed for chart isolation checks")
    def test_external_chart_load_close_and_isolation(self):
        result = subprocess.run(
            [shutil.which("node"), "-e", HARNESS, str(WEB / "tradingview-chart.js")],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
