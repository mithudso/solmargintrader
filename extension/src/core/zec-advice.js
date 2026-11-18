export const ZEC_REMOTE_COMMANDS = Object.freeze(['zecSnapshot', 'zecAdvisories', 'zecAdvice']);
export const ZEC_ADVICE_TTL_MS = 120_000;

export const ZEC_ADVICE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['snapshotId', 'decision', 'rationale', 'invalidation'],
  properties: {
    snapshotId: { type: 'string', format: 'uuid' },
    decision: { enum: ['WAIT', 'OBSERVE', 'PAPER_ONLY'] },
    rationale: { type: 'string', minLength: 1, maxLength: 800 },
    invalidation: { type: 'string', minLength: 1, maxLength: 500 },
  },
};

export function validZecAdvice(value) {
  const schema = ZEC_ADVICE_SCHEMA;
  if (!value || typeof value !== 'object' || Array.isArray(value)
      || Object.keys(value).length !== schema.required.length
      || !schema.required.every(key => Object.hasOwn(value, key))) return false;
  const plain = (text, limit) => typeof text === 'string' && text === text.trim()
    && text.length > 0 && text.length <= limit && !/[\p{C}\p{Zl}\p{Zp}]/u.test(text);
  return typeof value.snapshotId === 'string'
    && /^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(value.snapshotId)
    && schema.properties.decision.enum.includes(value.decision)
    && plain(value.rationale, schema.properties.rationale.maxLength)
    && plain(value.invalidation, schema.properties.invalidation.maxLength);
}
