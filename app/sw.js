/* 离线缓存：外壳常驻，音频按需缓存 + 一键全量打包 */
const VER = 'v17';
// 音频单独放一个固定名字的缓存，不跟版本号走：
// 这样以后每次发新版，用户辛苦打包的 1942 个录音不会被清掉重来
const AUDIO = 'audio-v1';
// './' 也要缓存：从主屏幕图标启动时请求的是目录根，不是 index.html
const SHELL = ['./', 'index.html', 'style.css', 'app.js', 'list.js', 'ui.js', 'practice.js',
               'audio.js', 'offline.js',
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
  e.waitUntil((async () => {
    const keys = await caches.keys();
    // AUDIO 那个缓存留着——录音跟代码版本无关，删了用户就得重下 46MB
    // 老版本（音频和外壳混在一起）里的录音先搬过来，别让用户白打一次包
    for (const k of keys) {
      if (k === VER || k === AUDIO) continue;
      const old = await caches.open(k);
      const audioReqs = (await old.keys()).filter((r) => r.url.includes('/audio/'));
      if (audioReqs.length) {
        const dst = await caches.open(AUDIO);
        for (const r of audioReqs) {
          try {
            const resp = await old.match(r);
            if (resp) await dst.put(r, resp);
          } catch (err) { /* 搬不动就算了，打包时会重新下 */ }
        }
      }
    }
    await Promise.all(keys.filter((k) => k !== VER && k !== AUDIO).map((k) => caches.delete(k)));
    await self.clients.claim();
    // 装上新版本后直接把打开的页面重载一遍：
    // 否则页面还停在旧 JS 上，用户会觉得「怎么改都没变」
    const clients = await self.clients.matchAll({ type: 'window' });
    clients.forEach((c) => { try { c.navigate(c.url); } catch (err) { /* 忽略 */ } });
  })());
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  // 音频：缓存优先，听过就离线可用。
  // 媒体元素会发 Range（bytes=a-b）请求，缓存里只有整段，得手动切出 206 回给它，
  // 否则 iOS 上离线播放会一声不吭地失败。
  if (url.pathname.includes('/audio/')) {
    e.respondWith((async () => {
      let hit = null;
      try { hit = await caches.match(req, { ignoreVary: true, ignoreSearch: true }); } catch (err) { hit = null; }
      if (!hit) {
        try {
          const res = await fetch(req);
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(AUDIO).then((c) => c.put(req, copy)).catch(() => {});
          }
          return res;
        } catch (err) {
          return Response.error();
        }
      }
      const range = req.headers.get('range');
      if (!range) return hit;
      const buf = await hit.arrayBuffer();
      const m = /bytes=(\d*)-(\d*)/.exec(range);
      const start = m && m[1] ? parseInt(m[1], 10) : 0;
      const end = m && m[2] ? parseInt(m[2], 10) : buf.byteLength - 1;
      const chunk = buf.slice(start, Math.min(end, buf.byteLength - 1) + 1);
      return new Response(chunk, {
        status: 206,
        statusText: 'Partial Content',
        headers: {
          'Content-Type': hit.headers.get('Content-Type') || 'audio/mpeg',
          'Content-Range': 'bytes ' + start + '-' + (start + chunk.byteLength - 1) + '/' + buf.byteLength,
          'Content-Length': String(chunk.byteLength),
          'Accept-Ranges': 'bytes',
        },
      });
    })());
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
  const cache = await caches.open(AUDIO);
  const total = urls.length;
  let done = 0;
  let fail = 0;
  let next = 0;
  const CONC = 8;                       // 8 个并发，快又不至于把网络打爆

  // 取回整段再写缓存：能顺手校验大小，避免把 404 的 HTML 当成录音存进去
  async function grab(u) {
    const r = await fetch(u, { cache: 'no-cache' });
    if (!r || !r.ok) throw new Error('下载失败');
    const buf = await r.arrayBuffer();
    if (buf.byteLength < 500) throw new Error('文件不完整');
    await cache.put(u, new Response(buf, { headers: { 'Content-Type': 'audio/mpeg' } }));
  }

  async function worker() {
    while (next < urls.length) {
      const u = urls[next++];
      if (!(await cache.match(u))) {
        let ok = false;
        // 网络抖一下就重试一次，别让一个词把整包卡住
        for (let t = 0; t < 2 && !ok; t++) {
          try { await grab(u); ok = true; } catch (err) { /* 下一轮重试 */ }
        }
        if (!ok) fail += 1;
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
  const cache = await caches.open(AUDIO);
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
  } else if (d.type === 'version') {
    // 设置面板里显示版本号，用户一眼就能确认手机是不是跑着最新版
    if (e.source) e.source.postMessage({ type: 'version', ver: VER });
  }
});
