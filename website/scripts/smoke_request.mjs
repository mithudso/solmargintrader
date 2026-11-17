export function requester(base, { fetchImpl = fetch, timeoutMs = 10000 } = {}) {
  return async (path, init = {}) => {
    const controller = new AbortController();
    let timer;
    const deadline = new Promise((resolve, reject) => {
      timer = setTimeout(() => { controller.abort(); reject(new Error('Smoke request deadline exceeded')); }, timeoutMs);
    });
    try {
      return await Promise.race([deadline, (async () => {
        const response = await fetchImpl(`${base}${path}`, {
          ...init, signal: controller.signal, redirect: 'manual',
          headers: { Origin: base, 'Content-Type': 'application/json', ...init.headers }
        });
        const text = await response.text();
        return { status: response.status, headers: response.headers, json: async () => JSON.parse(text) };
      })()]);
    } finally { clearTimeout(timer); }
  };
}
