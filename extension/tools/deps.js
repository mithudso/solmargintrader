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
import { MemoryStore } from '../src/storage/memoryStore.js';
import { ConfigStore } from '../src/storage/store.js';
import { buildVenue } from '../src/venues/index.js';
import { makeSigner } from '../src/wallet/signer.js';
import { RequestBudget } from '../src/jupiter/http.js';

/**
 * @param {object} [opts]
 * @param {boolean} [opts.ephemeral] keep everything in memory (tests, --dry)
 * @param {string} [opts.storePath]
 * @param {string} [opts.configPath]
 * @param {string} [opts.passphrase] unlocks a full-auto session key
 * @param {boolean} [opts.quiet]
 */
export async function createNodeDeps(opts = {}) {
  const {
    ephemeral = false,
    storePath = DEFAULT_STORE_PATH,
    configPath = DEFAULT_CONFIG_PATH,
    passphrase,
    quiet = false,
  } = opts;

  const area = ephemeral ? null : createFileArea(configPath);
  const configStore = new ConfigStore(area);
  const store = ephemeral ? new MemoryStore() : await FileStore.open(storePath);
  const budget = new RequestBudget({ maxPerWindow: 30, windowMs: 60_000 });

  return {
    store,
    configStore,
    budget,
    paths: ephemeral ? { store: '(memory)', config: '(memory)' } : { store: storePath, config: configPath },

    /**
     * Fresh venue per call: config can change between commands, and the venue
     * caches auth and decimals for the config it was built with.
     */
    async buildVenue() {
      const config = await configStore.getConfig();
      const secrets = await configStore.get('secrets', {});
      const signer = await makeSigner({ mode: config.mode, passphrase, area });
      return buildVenue({ config, signer, apiKey: secrets.apiKey, budget });
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
