import { OracleStore } from './oracle-store.js';
import { ORACLE, oracleIdentity, oracleInput, transitionOracle, oracleMetrics, oracleMode, validateOracleState } from './oracle-model.js';
import { TIMEFRAMES } from './timeframes.js';

const safeError = error => ['oracle_partition_capacity', 'invalid_oracle_state', 'oracle_source_unavailable'].includes(error?.message)
  ? error.message : ['invalid_oracle_features', 'indicator arithmetic is not finite'].includes(error?.message)
    ? 'oracle_features_unavailable' : 'oracle_storage_unavailable';

/** One shared input, six independent models. Selection changes only the displayed
 * detail; transaction reducers and late displays always consult the latest input. */
export class OracleController {
  #store;
  #clock;
  #change;
  #latest;
  #queued = false;
  #running = false;
  #disposed = false;
  #generation = 0;
  #nextAt = 0;
  #key = null;
  #eligible = false;
  #suspended = false;
  #pauseReason = null;
  #selected = ORACLE.horizon;
  #models = new Map();
  #errors = new Map();
  constructor({ store = new OracleStore(), clock = Date.now, onChange = () => {} } = {}) {
    this.#store = store; this.#clock = clock; this.#change = onChange;
  }
  selectHorizon(horizon) {
    if (!TIMEFRAMES.some(t => t.seconds === horizon)) throw new Error('invalid_oracle_horizon');
    this.#selected = horizon;
    if (!this.#disposed) this.#publish();
  }
  observe(snapshot) {
    if (this.#disposed) return;
    let key = null, eligible = false;
    try { key = oracleIdentity(snapshot).key; eligible = oracleInput(snapshot, this.#clock()).eligible; } catch { /* Invalid input cannot reactivate a saved forecast. */ }
    const identityChanged = key !== this.#key, readinessChanged = eligible !== this.#eligible;
    this.#suspended = false; this.#pauseReason = null;
    this.#latest = snapshot; this.#eligible = eligible;
    if (identityChanged) {
      this.#generation++; this.#key = key; this.#nextAt = 0;
      this.#models.clear(); this.#errors.clear(); this.#store.cancelPending?.();
    }
    // Do not wait behind an in-flight commit or the one-second read throttle to
    // invalidate a same-source live display. Keep verified historical evidence.
    if (identityChanged || readinessChanged || !eligible) this.#publish();
    this.#queued = true;
    if (!this.#running && this.#clock() >= this.#nextAt) void this.#drain();
  }
  #publish() {
    let input, error;
    try { input = oracleInput(this.#latest, this.#clock()); }
    catch { if (this.#latest?.status !== 'connecting' && this.#latest) error = 'oracle_source_unavailable'; }
    const bound = input?.key === this.#key || (this.#suspended && this.#key !== null), horizons = {};
    for (const { label, seconds } of TIMEFRAMES) {
      const saved = bound ? this.#models.get(seconds) : undefined;
      const failure = this.#errors.get(seconds)?.error || error
        || (input?.reason === 'oracle_features_unavailable' ? input.reason : undefined);
      horizons[seconds] = { ...saved, horizon: seconds, label,
        sourceKey: saved?.state.key, inputReady: Boolean(saved && input?.eligible && !failure),
        reason: this.#pauseReason || input?.reason || 'awaiting_catalog_identity', ...(failure ? { error: failure } : {}) };
    }
    this.#change({ ...horizons[this.#selected], selectedHorizon: this.#selected, horizons, suspended: this.#suspended, reason: this.#pauseReason || input?.reason || 'awaiting_catalog_identity' });
  }
  async #drain() {
    this.#running = true; this.#queued = false;
    const generation = this.#generation, key = this.#key;
    this.#nextAt = this.#clock() + 1000;
    try {
      if (!key) { this.#publish(); return; }
      await Promise.all(TIMEFRAMES.map(async ({ seconds }) => {
        if (this.#clock() < (this.#errors.get(seconds)?.retryAt || 0)) return;
        let partition;
        try {
          const initial = oracleIdentity(this.#latest, seconds);
          partition = initial.key;
          const result = await this.#store.update(initial.key, state => {
            if (this.#disposed || generation !== this.#generation || key !== this.#key) throw new Error('oracle_obsolete_session');
            const current = oracleInput(this.#latest, this.#clock(), seconds);
            if (current.key !== initial.key) throw new Error('oracle_obsolete_session');
            return transitionOracle(state, current);
          });
          if (!this.#disposed && generation === this.#generation && key === this.#key) {
            this.#models.set(seconds, { state: result.state, metrics: oracleMetrics(result.state),
              mode: oracleMode(result.state), feedback: result.feedback });
            this.#errors.delete(seconds);
          }
        } catch (error) {
          if (!this.#disposed && generation === this.#generation) {
            this.#errors.set(seconds, { error: safeError(error), retryAt: this.#clock() + 5000 });
            // A failed write must not hide a readable, verified old partition
            // on cold reload. Keep it historical and retain the write error.
            if (partition && !this.#models.has(seconds) && this.#store.load) {
              try {
                const saved = await this.#store.load(partition);
                if (saved) {
                  validateOracleState(saved, partition);
                  if (!this.#disposed && generation === this.#generation && key === this.#key)
                    this.#models.set(seconds, { state: saved, metrics: oracleMetrics(saved), mode: oracleMode(saved) });
                }
              } catch { /* Preserve the original refusal; never create empty evidence. */ }
            }
          }
        }
      }));
      if (!this.#disposed && generation === this.#generation) this.#publish();
    } finally {
      this.#running = false;
      if (!this.#disposed && this.#queued && this.#clock() >= this.#nextAt) void this.#drain();
    }
  }
  suspend(reason = 'feed_paused') {
    this.#generation++; this.#latest = null; this.#queued = false; this.#nextAt = 0; this.#eligible = false;
    this.#suspended = true; this.#pauseReason = reason; this.#store.cancelPending?.();
    // Keep the already verified source's history, while every forecast remains
    // inactive. A genuinely different/unknown source still clears it in observe.
    this.#publish();
  }
  stop() { this.#disposed = true; this.#generation++; this.#queued = false; this.#store.close(); }
}
