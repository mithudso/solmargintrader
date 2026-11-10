"""Explicit assumptions and manual SDK contracts; no wallet or provider call."""

from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

from ecosystem.swaps import (
    SWAP_TRIGGER_REFERRAL_ACCOUNT,
    ULTRA_REFERRAL_ACCOUNT,
    config,
    validate_cost_model,
)


class SwapTests(unittest.TestCase):
    def model(self, **changes):
        return {
            "source": "configured_scenario",
            "fee_bps": 6.0,
            "slippage_bps": 2.0,
            "borrow_long_bps_hour": 0.8,
            "borrow_short_bps_hour": 0.15,
            **changes,
        }

    def test_default_preserves_recorded_referral_and_known_fee_mismatch(self):
        value = config()
        self.assertEqual(value["selected_referral_account"], ULTRA_REFERRAL_ACCOUNT)
        self.assertEqual(
            value["referral_accounts"]["swap_trigger"], SWAP_TRIGGER_REFERRAL_ACCOUNT
        )
        self.assertEqual(value["default_referral_fee_bps"], 10)
        self.assertEqual(value["minimum_referral_fee_bps"], 50)
        self.assertFalse(value["default_fee_supported"])
        self.assertFalse(value["live_ready"])
        self.assertFalse(value["server_can_sign_or_submit"])
        self.assertIsNone(value["actual_quote_fees"])
        self.assertFalse(value["auto_connect"])

    def test_only_verified_mints_are_prefilled(self):
        sol, usdc = config("SOL"), config("usdc")
        self.assertEqual(sol["initial_input_mint"], usdc["initial_output_mint"])
        self.assertEqual(sol["initial_output_mint"], usdc["initial_input_mint"])
        unknown = config("BTC")
        self.assertEqual(unknown["asset_mapping_status"], "unavailable")
        self.assertIsNone(unknown["initial_input_mint"])
        for asset in ("../SOL", "SOL/USDC", None, "SOL\0"):
            with self.subTest(asset=asset), self.assertRaises(ValueError):
                config(asset)

    def test_cost_model_is_explicit_and_idempotent_without_double_counting(self):
        value = validate_cost_model(self.model())
        self.assertEqual(value["fee_bps"], 6.0)
        self.assertEqual(value["referral_fee_bps"], 10.0)
        self.assertEqual(value["total_fee_bps"], 16.0)
        self.assertEqual(validate_cost_model(value), value)
        self.assertEqual(
            validate_cost_model(self.model(referral_fee_bps=0))["total_fee_bps"], 6.0
        )

    def test_cost_model_rejects_fake_provenance_and_unknown_or_invalid_fields(self):
        values = [
            self.model(source="jupiter_quote"),
            self.model(provider="jupiter"),
            self.model(total_fee_bps=6),
            self.model(fee_bps=True),
            self.model(fee_bps=float("nan")),
            self.model(fee_bps=float("inf")),
            self.model(fee_bps=10**1000),
            self.model(total_fee_bps=10**1000),
            self.model(slippage_bps=-1),
            self.model(fee_bps=9999, referral_fee_bps=10),
            {},
        ]
        for value in values:
            with self.subTest(value=list(value)), self.assertRaises(ValueError):
                validate_cost_model(value)

    def test_browser_contract_blocks_unsupported_fee_then_requires_a_manual_sdk_click(
        self,
    ):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node is required for the isolated browser-contract test")
        script = Path(__file__).parents[1] / "web/swap.js"
        program = r"""
const vm=require('node:vm'), fs=require('node:fs');
const cfg=JSON.parse(fs.readFileSync(0,'utf8')), nodes=new Map(), scripts=[];
function element(id){if(!nodes.has(id))nodes.set(id,{value:id==='referral-fee'?'10':'SOL',disabled:false,textContent:'',events:{},addEventListener(k,f){this.events[k]=f;},replaceChildren(){}});return nodes.get(id);}
let timer=0;const timers=new Map();
const context={Number,Error,URLSearchParams,AbortController,location:{search:'?asset=SOL'},window:{},setTimeout(f){timers.set(++timer,f);return timer;},clearTimeout(t){timers.delete(t);},fetch:async(url)=>({ok:true,json:async()=>({schema_version:1,ok:true,data:cfg})}),document:{getElementById:element,createElement(){return {remove(){this.removed=true;}};},head:{append(script){scripts.push(script);}}}};
vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);
(async()=>{
 await new Promise(setImmediate);
 const initial=element('load-jupiter').disabled;
 await element('load-jupiter').events.click();
 const blocked=scripts.length;
 element('referral-fee').value='50';element('referral-fee').events.input();
 const before=scripts.length, pending=element('load-jupiter').events.click();
 const requested=scripts.length;scripts[0].onerror();await pending;
 const error=element('swap-state').textContent;
 let options=null;context.window.Jupiter={init(value){options=value;}};
 await element('load-jupiter').events.click();
 console.log(JSON.stringify({initial,blocked,before,requested,error,options,src:scripts[0].src}));
})().catch(()=>process.exit(1));
"""
        result = subprocess.run(
            [node, "-e", program, str(script)],
            input=json.dumps(config()),
            text=True,
            capture_output=True,
            check=True,
            timeout=10,
        )
        observed = json.loads(result.stdout)
        self.assertTrue(observed["initial"])
        self.assertEqual(observed["blocked"], 0)
        self.assertEqual(observed["before"], 0)
        self.assertEqual(observed["requested"], 1)
        self.assertIn("Unavailable", observed["error"])
        self.assertFalse(observed["options"]["autoConnect"])
        self.assertFalse(observed["options"]["enableWalletPassthrough"])
        self.assertEqual(
            observed["options"]["formProps"]["referralAccount"], ULTRA_REFERRAL_ACCOUNT
        )
        self.assertEqual(observed["options"]["formProps"]["referralFee"], 50)


if __name__ == "__main__":
    unittest.main()
