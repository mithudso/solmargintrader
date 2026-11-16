import { OracleStore } from './oracle-store.js';
import { oracleInput, transitionOracle, oracleMetrics, oracleMode } from './oracle-model.js';

/** Coalesce existing feed snapshots; create no stream, recorder or background
 * owner. Stop/suspend fences callbacks from an obsolete window/feed generation. */
export class OracleController {
  #store;
  #clock;
  #change;
  #queued;
  #running = false;
  #disposed = false;
  #generation = 0;
  #nextAt = 0;
  #key = null;
  constructor({ store = new OracleStore(), clock = Date.now, onChange = () => {} } = {}) {
    this.#store = store; this.#clock = clock; this.#change = onChange;
  }
  observe(snapshot) {
    if (this.#disposed) return;
    let key = null;
    try { key = oracleInput(snapshot, this.#clock()).key; } catch { /* Unverified identity cannot retain a prior partition's display. */ }
    if (key !== this.#key) {
      this.#generation++; this.#key = key; this.#nextAt = 0;
      this.#store.cancelPending?.();
      this.#change({ inputReady: false, reason: key ? 'source_state_loading' : 'awaiting_catalog_identity' });
    }
    this.#queued = snapshot;
    if (!this.#running && this.#clock() >= this.#nextAt) void this.#drain();
  }
  async #drain() {
    this.#running = true;
    const snapshot = this.#queued, generation = this.#generation;
    this.#queued = null; this.#nextAt = this.#clock() + 1000;
    try {
      if (!snapshot?.sourceIdentity && snapshot?.status === 'connecting') {
        this.#change({ inputReady: false, reason: 'awaiting_catalog_identity' });
        return;
      }
      const initial = oracleInput(snapshot, this.#clock());
      const result = await this.#store.update(initial.key, state => {
        if (this.#disposed || generation !== this.#generation || initial.key !== this.#key) throw new Error('oracle_obsolete_session');
        const current = oracleInput(snapshot, this.#clock());
        if (current.key !== initial.key) throw new Error('oracle_obsolete_session');
        return transitionOracle(state, current);
      });
      if (!this.#disposed && generation === this.#generation) {
        const current = oracleInput(snapshot, this.#clock());
        this.#change({ state: result.state, sourceKey: current.key, metrics: oracleMetrics(result.state), mode: oracleMode(result.state),
          feedback: result.feedback, inputReady: current.eligible, reason: current.reason });
      }
    } catch (error) {
      if (!this.#disposed && generation === this.#generation) {
        this.#change({ inputReady: false,
          error: ['oracle_partition_capacity', 'invalid_oracle_state', 'oracle_source_unavailable'].includes(error?.message) ? error.message : 'oracle_storage_unavailable' });
        this.#nextAt = this.#clock() + 5000;
      }
    } finally {
      this.#running = false;
      if (!this.#disposed && this.#queued && this.#clock() >= this.#nextAt) void this.#drain();
    }
  }
  suspend(reason = 'feed_paused') {
    this.#generation++; this.#key = null; this.#queued = null; this.#nextAt = 0;
    this.#store.cancelPending?.();
    this.#change({ inputReady: false, suspended: true, reason });
  }
  stop() { this.#disposed = true; this.#generation++; this.#queued = null; this.#store.close(); }
}
