/** Metadata accompanies the learner in the same IndexedDB transaction. */
const uuid = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;
export const validLearningId = value => typeof value === 'string' && uuid.test(value);
/** These bytes are a storage protocol: object insertion order must not change
 * the digest of one committed revision after a multi-store reconstruction. */
export function checkpointText(state) {
  const ordered = value => Array.isArray(value) ? value.map(ordered)
    : value !== null && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(key => [key, ordered(value[key])])) : value;
  return JSON.stringify(ordered(state));
}
export function checkpointMeta(record) {
  if (!record?.lineage && record?.revision === undefined) return { lineage: null, revision: 0 };
  if (!validLearningId(record?.lineage) || !Number.isSafeInteger(record.revision) || record.revision < 1) throw new Error('oracle_checkpoint_metadata_invalid');
  return { lineage: record.lineage, revision: record.revision };
}
export function nextCheckpoint(record) {
  const previous = checkpointMeta(record);
  if (previous.revision >= Number.MAX_SAFE_INTEGER) throw new Error('oracle_checkpoint_revision_exhausted');
  return { lineage: previous.lineage || crypto.randomUUID(), revision: previous.revision + 1 };
}
export function restoreCheckpoint(key, checkpoint, validate) {
  const metadata = checkpointMeta(checkpoint);
  if (!metadata.lineage || checkpoint?.state?.key !== key) throw new Error('oracle_checkpoint_identity_mismatch');
  validate(checkpoint.state, key);
  return { key, state: structuredClone(checkpoint.state), ...metadata };
}
