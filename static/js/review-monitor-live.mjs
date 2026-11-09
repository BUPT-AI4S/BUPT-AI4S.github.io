const LIVE_URL = 'https://raw.githubusercontent.com/BUPT-AI4S/ai4s-crawler/main/reviews/monitor-data.json';

async function readSnapshot(fetcher, url) {
  const controller = typeof AbortController === 'function' ? new AbortController() : null;
  const timer = controller ? setTimeout(() => controller.abort(), 8000) : null;
  try {
    const init = controller ? {cache:'no-store', signal: controller.signal} : {cache:'no-store'};
    const response = await fetcher(url, init);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (!Array.isArray(data.years) || !data.years.length) throw new Error('没有可用的年度数据');
    return data;
  } finally {
    if (timer) clearTimeout(timer);
  }
}

export async function loadMonitorSnapshot(fetcher, now = Date.now()) {
  try { return {data:await readSnapshot(fetcher, `${LIVE_URL}?v=${now}`), live:true}; }
  catch { return {data:await readSnapshot(fetcher, 'data/review-monitor.json'), live:false}; }
}
