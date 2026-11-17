/**
 * Node dependency wiring for the command registry.
 *
 * The CLI and the HTTP API share this so they behave identically — the only
 * difference between the two surfaces is how arguments arrive.
 *
 * Kept out of src/ because it imports node:fs, which would break the extension
 * bundle if it were ever pulled into a browser context.
 */

import { FileStore, createFileArea, DEFAULT_STORE_PATH, DEFAULT_CONFIG_PATH } from '../src/storage/fileStore.js';
import { restorePaperVenue } from '../src/bg/paper-venue.js';
import { MemoryStore } from '../src/storage/memoryStore.js';
import { ConfigStore } from '../src/storage/store.js';
import { buildVenue } from '../src/venues/index.js';
import { makeSigner } from '../src/wallet/signer.js';
import { RequestBudget } from '../src/jupiter/http.js';
import { createNodeSoltuiTransport } from './soltui-transport.js';

/**
 * @param {object} [opts]
 * @param {boolean} [opts.ephemeral] keep everything in memory (tests, --dry)
 * @param {string} [opts.storePath]
 * @param {string} [opts.configPath]
 * @param {string} [opts.passphrase] unlocks a full-auto session key
 * @param {boolean} [opts.quiet]
 * @param {object} [opts.soltui] transport override; default spawns the soltui native host
 */
const nodeFetch = (...a) => globalThis.fetch(...a);

export async function createNodeDeps(opts = {}) {
  const {
    ephemeral = false,
    storePath = DEFAULT_STORE_PATH,
    configPath = DEFAULT_CONFIG_PATH,
    passphrase,
    quiet = false,
    soltui,
  } = opts;

  const area = ephemeral ? null : createFileArea(configPath);
  const configStore = new ConfigStore(area);
  const store = ephemeral ? new MemoryStore() : await FileStore.open(storePath);
  const budget = new RequestBudget({ maxPerWindow: 30, windowMs: 60_000 });
  let dryVenue = null;
  let dryContext = null;

  return {
    store,
    configStore,
    budget,
    soltui: soltui ?? createNodeSoltuiTransport(),
    // Market reads (holdings, pools, swapQuote, scanAlerts) use the platform fetch.
    // One function per process, so the pool cache (keyed on it) can hit.
    fetch: nodeFetch,
    paths: ephemeral ? { store: '(memory)', config: '(memory)' } : { store: storePath, config: configPath },

    /**
     * Fresh venue per call: config can change between commands, and the venue
     * caches auth and decimals for the config it was built with.
     */
    async buildVenue() {
      const config = await configStore.getConfig();
      const secrets = await configStore.get('secrets', {});
      const signer = await makeSigner({ mode: config.mode, passphrase, area });
      const fresh = buildVenue({ config, signer, apiKey: secrets.apiKey, budget });
      if (!fresh.capabilities.dryRun) {
        dryVenue = null;
        dryContext = null;
        return fresh;
      }
      const context = JSON.stringify([config.gridId, config.venue, config.mode,
        config.baseMint, config.quoteMint, config.userPubkey, config.rpcUrl]);
      if (dryContext !== context || !dryVenue) {
        dryVenue = await restorePaperVenue(fresh, config, configStore);
        dryContext = context;
      } else {
        // Refresh credentials/read configuration while retaining resting paper
        // orders across the sequential ticks of one CLI/API process.
        dryVenue.inner = fresh.inner;
      }
      return dryVenue;
    },

    clock: () => Date.now(),
    log: quiet
      ? () => {}
      : (e) => {
          const line = `[smt] ${e.msg ?? ''} ${e.error ?? e.intentKey ?? ''}`.trim();
          if (e.level === 'error') console.error(line);
          else console.warn(line);
        },
  };
}
