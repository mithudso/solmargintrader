import { soltui } from './ui-kit.js';
import { mountLivePanel } from './live-panel.js';
import { mountFloatingOwner } from './floating-owner.js';

const requested = new URL(location.href).searchParams.get('asset');
const asset = /^[A-Z0-9]{1,20}$/.test(requested ?? '') ? requested : 'SOL';
const panel = mountLivePanel(document.getElementById('liveWindowPanel'), { read: soltui, asset,
  dashboardURL: chrome.runtime.getURL('src/ui/dashboard.html') });
const owner = mountFloatingOwner({ read: soltui, asset: () => panel.asset, onState(pinned) {
  document.getElementById('pinStatus').textContent = pinned ? 'Pinned. Keep this window open; closing it ends its floating view.' : 'Floating view closed. Pin again to reopen.';
} });
document.getElementById('openWorkspace').href = chrome.runtime.getURL('src/ui/dashboard.html#soltui/signal');
document.getElementById('openWorkspace').target = '_blank';
document.getElementById('pinLive').onclick = () => {
  try { owner.pin().catch(error => { document.getElementById('pinStatus').textContent = error.message; }); }
  catch (error) { document.getElementById('pinStatus').textContent = error.message; }
};
window.addEventListener('pagehide', () => { owner.dispose(); panel.dispose(); }, { once: true });
