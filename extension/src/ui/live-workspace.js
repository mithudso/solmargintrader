import { soltui } from './ui-kit.js';
import { mountLivePanel, workflowText } from './live-panel.js';
import { mountFloatingOwner } from './floating-owner.js';
import { voteHint } from './vote-tools.js';

export function mountLiveWorkspace(root = document, read = soltui) {
  const byId = id => root.querySelector(`#${id}`);
  const host = byId('workspaceLiveRail');
  if (!host) return;
  const input = byId('soltuiLiveAsset'), primary = byId('deskStartAll');
  const asset = () => /^[A-Z0-9]{1,20}$/.test(input?.value.trim().toUpperCase() ?? '') ? input.value.trim().toUpperCase() : 'SOL';
  let disposed = false, starting = false;
  const hints = new Set();
  const panel = mountLivePanel(host, { read, asset: asset(), onSnapshot(snapshot) {
    for (const old of hints) if (!old.button.isConnected) { old.dispose(); hints.delete(old); }
    if (!starting) primary.textContent = snapshot.workflow?.running || snapshot.workflow?.batch?.running ? 'Paper workflow running' : 'Start / resume paper bots';
    primary.title = workflowText(snapshot.workflow);
  }, onAsset(coin) { if (input && input.value !== coin) { input.value = coin; input.dispatchEvent(new Event('change')); } }, voteButton(row, coin) {
    const hint = voteHint({ row, asset: coin, read }); hints.add(hint);
    return hint.button;
  } });
  const owner = mountFloatingOwner({ read, asset: () => panel.asset });
  const change = () => panel.setAsset(asset());
  input?.addEventListener('change', change);
  // Storage restore happens after mount and does not emit a DOM change.
  const timer = window.setInterval(() => { if (!disposed && asset() !== panel.asset) change(); }, 1000);
  primary.onclick = async () => {
    if (starting) return;
    starting = true; primary.disabled = true; primary.textContent = 'Preparing paper workflow…';
    try {
      const result = await read('paper.workflow_ensure', { asset: asset(), scope: 'all' });
      byId('workspaceWorkflowStatus').textContent = workflowText(result);
      await panel.refresh();
    } catch (error) { byId('workspaceWorkflowStatus').textContent = error.message; }
    finally { starting = false; primary.disabled = false; if (!disposed) panel.refresh(); }
  };
  byId('workspacePinLive').onclick = () => {
    try { owner.pin(panel.asset).catch(error => { byId('workspaceWorkflowStatus').textContent = error.message; }); }
    catch (error) { byId('workspaceWorkflowStatus').textContent = error.message; }
  };
  const dispose = () => { disposed = true; clearInterval(timer); panel.dispose(); owner.dispose(); input?.removeEventListener('change', change); for (const h of hints) h.dispose(); };
  window.addEventListener('pagehide', dispose, { once: true });
  return { panel, dispose };
}
