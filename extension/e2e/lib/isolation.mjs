/** Install before loading the extension: every new target starts paused. */
export async function isolateTargets(browser, { onEvent = () => {}, preparePage } = {}) {
  let failure = null;
  const sessions = new Map();
  const settings = { autoAttach: true, waitForDebuggerOnStart: true, flatten: true };
  const off = browser.on(message => {
    if (message.method !== 'Target.attachedToTarget') { onEvent(message, browser); return; }
    const { sessionId, targetInfo } = message.params;
    const task = (async () => {
      await browser.call('Network.enable', {}, sessionId);
      await browser.call('Network.setBlockedURLs', { urls: ['ws://*', 'wss://*'] }, sessionId);
      await browser.call('Fetch.enable', { patterns: [{ urlPattern: 'http://*' }, { urlPattern: 'https://*' }] }, sessionId);
      await browser.call('Runtime.enable', {}, sessionId);
      if (['page', 'iframe'].includes(targetInfo.type)) {
        await browser.call('Target.setAutoAttach', settings, sessionId);
        if (preparePage) await preparePage(sessionId, browser);
      }
      await browser.call('Runtime.runIfWaitingForDebugger', {}, sessionId);
    })().catch(async () => { failure = new Error('Target isolation setup failed'); await browser.close(); });
    sessions.set(sessionId, task);
  });
  await browser.call('Target.setAutoAttach', settings);
  return { off, sessions, assertHealthy() { if (failure) throw failure; } };
}
