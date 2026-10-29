/* 离线缓存：外壳常驻，音频按需缓存 + 一键全量打包 */
const VER = 'v10';
// './' 也要缓存：从主屏幕图标启动时请求的是目录根，不是 index.html
const SHELL = ['./', 'index.html', 'style.css', 'app.js', 'list.js', 'ui.js', 'practice.js',
               'manifest.webmanifest', 'data/words.js', 'data/words.json',
               'icons/icon-192.png', 'icons/icon-512.png'];

self.addEventListener('install', (e) => {
  e.waitUntil((async () => {
    const c = await caches.open(VER);
    // 逐个加，某个文件失败不影响整体
    await Promise.all(SHELL.map((u) => c.add(u).catch(() => {})));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== VER).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  // 音频：缓存优先，听过就离线可用
  if (url.pathname.includes('/audio/')) {
    e.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(VER).then((c) => c.put(req, copy));
        return res;
      }))
    );
    return;
  }

  // 外壳：网络优先（保证拿到新版），失败回落缓存
  e.respondWith(
    fetch(req).then((res) => {
      const copy = res.clone();
      caches.open(VER).then((c) => c.put(req, copy));
      return res;
    }).catch(async () => {
      const hit = await caches.match(req);
      if (hit) return hit;
      // 离线时不管是 /kaoyan-yinger/ 还是 /kaoyan-yinger/index.html？xx
      // 一律回落到首页，交给前端路由处理
      if (req.mode === 'navigate') {
        return (await caches.match('index.html')) || (await caches.match('./')) || Response.error();
      }
      return Response.error();
    })
  );
});

/* ---------------- 一键打包：把全部音频灌进缓存 ---------------- */
async function cacheAll(urls, port) {
  const cache = await caches.open(VER);
  const total = urls.length;
  let done = 0;
  let fail = 0;
  let next = 0;
  const CONC = 6;                       // 6 个并发，快又不至于把网络打爆

  async function worker() {
    while (next < urls.length) {
      const u = urls[next++];
      try {
        if (!(await cache.match(u))) {
          const r = await fetch(u, { cache: 'no-cache' });
          if (r && r.ok) await cache.put(u, r.clone());
          else fail += 1;
        }
      } catch (err) {
        fail += 1;
      }
      done += 1;
      if (done % 10 === 0 || done === total) {
        port && port.postMessage({ type: 'offline-progress', done, total, fail });
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(CONC, total || 1) }, worker));
  port && port.postMessage({ type: 'offline-done', done, total, fail });
}

async function reportStatus(urls, port) {
  const cache = await caches.open(VER);
  let have = 0;
  for (const u of urls) if (await cache.match(u)) have += 1;
  port && port.postMessage({ type: 'offline-status', have, total: urls.length });
}

self.addEventListener('message', (e) => {
  const d = e.data || {};
  if (d.type === 'cache-audio' && Array.isArray(d.urls)) {
    e.waitUntil(cacheAll(d.urls, e.source));
  } else if (d.type === 'cache-status' && Array.isArray(d.urls)) {
    e.waitUntil(reportStatus(d.urls, e.source));
  }
});
