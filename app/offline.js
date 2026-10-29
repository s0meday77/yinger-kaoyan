/* 离线：把全部录音灌进手机缓存 + 「添加到主屏幕」引导 */

/* ---------------- 离线打包 ---------------- */
function offlineSetup() {
  const btn = $('#offlineBtn');
  const bar = $('#offlineBar');
  const wrap = $('#offlineBarWrap');
  const st = $('#offlineStatus');
  if (!btn || !st) return;

  // 双击本地文件打开时没有 Service Worker，打包功能用不了
  if (!('serviceWorker' in navigator) || location.protocol === 'file:') {
    st.textContent = '用网址打开时才能打包（双击文件不支持）';
    btn.disabled = true;
    return;
  }

  const urls = audioUrls();

  navigator.serviceWorker.addEventListener('message', (ev) => {
    const d = ev.data || {};
    if (d.type === 'version') {
      // 版本号由 Service Worker 报上来，能直接看出手机是不是跑着最新版
      const v = $('#verLine');
      if (v) v.textContent = d.ver;
    } else if (d.type === 'offline-progress') {
      wrap.hidden = false;
      bar.style.width = ((d.done / Math.max(1, d.total)) * 100).toFixed(1) + '%';
      st.textContent = '打包中 ' + d.done + ' / ' + d.total + '，别切走、别锁屏';
    } else if (d.type === 'offline-done') {
      wrap.hidden = false;
      bar.style.width = '100%';
      btn.disabled = false;
      if (d.fail) {
        st.textContent = '打包完成，' + d.fail + ' 个没下成功，可再点一次补齐';
        btn.textContent = '📥 补齐剩余';
      } else {
        st.textContent = '✅ 已全部打包，以后不联网也能用';
        btn.textContent = '✅ 已打包';
      }
    } else if (d.type === 'offline-status') {
      if (d.have >= d.total) {
        st.textContent = '✅ 已全部打包，以后不联网也能用';
        btn.textContent = '✅ 已打包';
        wrap.hidden = false;
        bar.style.width = '100%';
      } else {
        // 0 也要显示出来——以前不显示，用户根本不知道打包到底成没成
        st.textContent = '已缓存 ' + d.have + ' / ' + d.total + ' 个发音';
      }
    }
  });

  btn.addEventListener('click', async () => {
    a2hsClose();                       // 会用打包功能了，安装提示就不用再挡着了
    btn.disabled = true;
    st.textContent = '准备中…';
    try {
      const reg = await navigator.serviceWorker.ready;
      const sw = reg.active || navigator.serviceWorker.controller;
      if (!sw) throw new Error('离线服务还没启动，刷新一下再试');
      sw.postMessage({ type: 'cache-audio', urls });
    } catch (e) {
      st.textContent = '打包失败：' + (e.message || e);
      btn.disabled = false;
    }
  });

  // 启动时问一下版本号和已经存了多少
  navigator.serviceWorker.ready.then((reg) => {
    const sw = reg.active || navigator.serviceWorker.controller;
    if (!sw) return;
    sw.postMessage({ type: 'version' });
    sw.postMessage({ type: 'cache-status', urls });
  }).catch(() => {});
}

/* ---------------- 添加到主屏幕提示 ---------------- */
/** 关掉「添加到主屏幕」提示，并且以后再也不出现 */
function a2hsClose() {
  const el = $('#a2hs');
  if (el) el.hidden = true;
  try { localStorage.setItem('kaoyan_a2hs', '1'); } catch (e) { /* 存不住也不影响关闭 */ }
}

function a2hsSetup() {
  const el = $('#a2hs');
  if (!el) return;
  let seen = false;
  try { seen = localStorage.getItem('kaoyan_a2hs') === '1'; } catch (e) { /* 忽略 */ }
  const mq = (q) => !!(window.matchMedia && window.matchMedia(q).matches);
  // 已经是从桌面图标打开的独立 App，就不该再提示
  const standalone = window.navigator.standalone === true
    || mq('(display-mode: standalone)')
    || mq('(display-mode: fullscreen)')
    || mq('(display-mode: minimal-ui)');
  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  if (standalone || seen || !isIOS) { el.hidden = true; return; }
  el.hidden = false;
  // 8 秒后自己收起来，绝不一直挡着单词（收起不记标记，下次打开还会提示一下）
  const timer = setTimeout(() => { el.hidden = true; }, 8000);
  // 点条上任何一个地方都能关，并且以后不再出现
  el.addEventListener('click', () => { clearTimeout(timer); a2hsClose(); });
  const btn = $('#a2hsClose');
  if (btn) btn.addEventListener('click', (e) => { e.stopPropagation(); clearTimeout(timer); a2hsClose(); });
}

