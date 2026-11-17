// Keep one unresolved calculation per account in this tab. No credentials are stored.
export function createBacktestRecovery({ storage = () => sessionStorage, uuid = () => crypto.randomUUID() } = {}) {
  const key = account => `oraclebot.backtest.pending.v1:${encodeURIComponent(account)}`;
  const failure = () => new Error('Browser storage could not save calculation recovery. Check Recent calculations before trying again.');
  function pending(account) {
    try {
      const raw = storage().getItem(key(account));
      if (!raw) return null;
      const value = JSON.parse(raw);
      if (value.version !== 1 || typeof value.idempotencyKey !== 'string' || !/^[A-Za-z0-9_-]{16,128}$/.test(value.idempotencyKey) ||
          !value.request || typeof value.request !== 'object' || Array.isArray(value.request) ||
          !['coin', 'interval', 'strategy'].every(field => typeof value.request[field] === 'string') ||
          !['capital', 'leverage'].every(field => Number.isFinite(value.request[field])) ||
          (value.jobId !== undefined && typeof value.jobId !== 'string')) throw failure();
      return value;
    } catch { throw failure(); }
  }
  function save(account, value) {
    try {
      const raw = JSON.stringify(value);
      storage().setItem(key(account), raw);
      if (storage().getItem(key(account)) !== raw) throw failure();
    } catch { throw failure(); }
  }
  function clear(account, idempotencyKey) {
    if (pending(account)?.idempotencyKey !== idempotencyKey) return;
    try { storage().removeItem(key(account)); } catch { throw failure(); }
  }
  return {
    pending,
    begin(account, request) {
      const saved = pending(account);
      if (saved) return { record: saved, fresh: false };
      const record = { version: 1, idempotencyKey: uuid(), request: structuredClone(request) };
      save(account, record); // Persist before sending the request that can reserve quota.
      return { record, fresh: true };
    },
    observe(account, job, idempotencyKey) {
      const saved = pending(account);
      if (!saved || (saved.jobId ? saved.jobId !== job.id : saved.idempotencyKey !== idempotencyKey)) return;
      if (job.status === 'complete' || job.status === 'failed') clear(account, saved.idempotencyKey);
      else if (typeof job.id === 'string') save(account, { ...saved, jobId: job.id });
    },
    rejected(account, submission, error) {
      // A first definite refusal has no accepted job. Retried/ambiguous writes keep their identity.
      if (submission?.fresh && [400, 402, 413, 422, 429].includes(error?.status)) clear(account, submission.record.idempotencyKey);
    },
  };
}
