/** Fail a fixture request wait in bounded time without retaining its timer. */
export async function waitForFixture(promise, label, milliseconds = 10_000) {
  let timer;
  try {
    return await Promise.race([
      promise,
      new Promise((_, reject) => { timer = setTimeout(() => reject(new Error(`fixture request timed out: ${label}`)), milliseconds); }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}
