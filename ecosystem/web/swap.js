"use strict";

// This origin contains public settings only. Never reach into the parent page.
const SDK_SRC = "https://plugin.jup.ag/plugin-v1.js";
const $ = (id) => document.getElementById(id);
let settings = null;
let busy = false;
let loaded = false;
let feeEdited = false;
let configGeneration = 0;

function state(message) { $("swap-state").textContent = message; }
function selectedFee() { return Number($("referral-fee").value); }
function validFee() {
  const fee = selectedFee();
  return settings && Number.isInteger(fee) && fee >= settings.minimum_referral_fee_bps && fee <= settings.maximum_referral_fee_bps;
}
function updateFee(announce = true) {
  const fee = selectedFee();
  const display = Number.isFinite(fee) ? `${(fee / 100).toFixed(2)}% (${fee} bps)` : "Unavailable";
  $("selected-fee").textContent = `Explicitly selected referral: ${display}`;
  $("fee-summary").textContent = `${display}; actual application requires provider quote evidence`;
  $("load-jupiter").disabled = busy || loaded || !validFee() || settings?.asset_mapping_status !== "available";
  if (announce && !busy && !loaded) {
    state(validFee() ? "Ready to load the external interface on your click. Wallet connection and transactions still need your approval." : "Unavailable: choose a referral fee within the published range explicitly. Your selected fee has not been changed.");
  }
}
async function readConfig(asset) {
  const generation = ++configGeneration;
  settings = null;
  $("load-jupiter").disabled = true;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5000);
  try {
    const response = await fetch(`/config?asset=${encodeURIComponent(asset)}`, { cache: "no-store", credentials: "omit", signal: controller.signal });
    const envelope = await response.json();
    if (generation !== configGeneration) return;
    if (!response.ok || !envelope.ok || envelope.schema_version !== 1 || envelope.data?.provider !== "jupiter" || envelope.data.plugin_src !== SDK_SRC) throw new Error("public_config_unavailable");
    settings = envelope.data;
    if (!feeEdited) $("referral-fee").value = String(settings.default_referral_fee_bps);
    $("referral-account").textContent = settings.selected_referral_account;
    $("swap-asset").value = settings.asset_mapping_status === "available" ? settings.asset : "";
    $("asset-note").textContent = settings.asset_mapping_status === "available" ? `Verified initial pair: ${settings.asset === "USDC" ? "USDC / SOL" : "SOL / USDC"}. You can inspect other tokens inside Jupiter after loading.` : `The requested symbol ${settings.asset} has no verified mint mapping here. Choose a verified initial pair explicitly; this page will not invent a wrapped-token address.`;
    updateFee();
    if (settings.asset_mapping_status !== "available") state("Unavailable: initial token mapping requires an explicit selection.");
  } catch {
    if (generation !== configGeneration) return;
    state("Unavailable: public swap configuration could not be read. No SDK or wallet request was started.");
  } finally { clearTimeout(timer); }
}
function loadSdk() {
  return new Promise((resolve, reject) => {
    if (typeof window.Jupiter?.init === "function") { resolve(); return; }
    const script = document.createElement("script");
    const timer = setTimeout(() => { script.remove(); reject(new Error("sdk_unavailable")); }, 15000);
    script.src = SDK_SRC;
    script.async = true;
    script.referrerPolicy = "no-referrer";
    script.onload = () => { clearTimeout(timer); if (typeof window.Jupiter?.init === "function") resolve(); else { script.remove(); reject(new Error("sdk_contract_unavailable")); } };
    script.onerror = () => { clearTimeout(timer); script.remove(); reject(new Error("sdk_unavailable")); };
    document.head.append(script);
  });
}
async function loadManually() {
  if (busy || loaded || !validFee() || settings?.asset_mapping_status !== "available") return;
  const fee = selectedFee();
  busy = true;
  $("referral-fee").disabled = true;
  $("swap-asset").disabled = true;
  updateFee();
  state("Loading the official Jupiter interface. No server order or signing operation is available.");
  try {
    await loadSdk();
    $("jupiter-plugin").replaceChildren();
    window.Jupiter.init({
      displayMode: "integrated",
      integratedTargetId: "jupiter-plugin",
      autoConnect: false,
      enableWalletPassthrough: false,
      containerStyles: { height: "580px" },
      formProps: {
        initialInputMint: settings.initial_input_mint,
        initialOutputMint: settings.initial_output_mint,
        referralAccount: settings.selected_referral_account,
        referralFee: fee,
      },
      onSuccess: () => state("Jupiter reported a swap result. Review the provider's transaction link for independent chain confirmation."),
      onSwapError: () => state("Unavailable: Jupiter could not complete the requested swap. Inspect the provider and wallet. No referral fee was raised automatically."),
    });
    loaded = true;
    $("load-jupiter").textContent = "Jupiter interface loaded";
    state("Jupiter interface loaded. Connect your wallet manually, inspect the actual quote and every fee, then approve each wallet action yourself. Funded trading has not been verified by this server.");
  } catch {
    state("Unavailable: Jupiter's SDK could not load or initialize. No fee was changed and this server submitted no order. A retry requires another click.");
    $("load-jupiter").textContent = "Retry Jupiter manually";
  } finally {
    busy = false;
    $("referral-fee").disabled = loaded;
    $("swap-asset").disabled = loaded;
    updateFee(false);
  }
}
$("referral-fee").addEventListener("input", () => { feeEdited = true; updateFee(); });
$("swap-asset").addEventListener("change", () => readConfig($("swap-asset").value));
$("load-jupiter").addEventListener("click", loadManually);
readConfig(new URLSearchParams(location.search).get("asset") || "SOL");
