/* 皮肤 · 连听 —— 外观与播放控制 */
/* ---------------- 皮肤 ---------------- */
// dot 的两个色是预览用的「底色 + 主色」，和 style.css 里的皮肤保持一致
const THEMES = [
  { id: 'auto', name: '跟随系统', bg: 'linear-gradient(135deg,#f4f5f9 50%,#0f1117 50%)', dot: '#5b5bd6' },
  { id: 'light', name: '纯白', bg: '#f4f5f9', dot: '#5b5bd6' },
  { id: 'sepia', name: '米黄', bg: '#f3ecdd', dot: '#b0763a' },
  { id: 'green', name: '雾绿', bg: '#e9f0ea', dot: '#4f8464' },
  { id: 'dark', name: '深色', bg: '#0f1117', dot: '#8b8bf0' },
  { id: 'midnight', name: '墨蓝', bg: '#0b1220', dot: '#4d8fd6' }
];
const BAR_COLOR = { light: '#f4f5f9', sepia: '#f3ecdd', green: '#e9f0ea', dark: '#0f1117', midnight: '#0b1220' };

function applyTheme(id) {
  const dark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  const real = id === 'auto' ? (dark ? 'dark' : 'light') : id;
  document.documentElement.dataset.theme = real;
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute('content', BAR_COLOR[real] || '#f4f5f9');
}
function renderThemes() {
  const box = $('#themePick');
  if (!box) return;
  box.innerHTML = '';
  THEMES.forEach((t) => {
    const b = document.createElement('button');
    b.className = 'theme-item' + (state.theme === t.id ? ' active' : '');
    b.type = 'button';
    const d = document.createElement('span');
    d.className = 'theme-dot';
    d.style.background = t.bg;
    const i = document.createElement('i');
    i.style.background = t.dot;
    d.appendChild(i);
    const s = document.createElement('small');
    s.textContent = t.name;
    b.append(d, s);
    b.addEventListener('click', () => {
      state.theme = t.id;
      applyTheme(t.id);
      renderThemes();
      save();
    });
    box.appendChild(b);
  });
}

/* ---------------- 连听：一口气播完整课 ---------------- */
let chainTimer = null;
let chainIdx = 0;

function stopChain(msg) {
  if (chainTimer) { clearTimeout(chainTimer); chainTimer = null; }
  if (!state.chain) return;
  state.chain = false;
  const b = $('#chainBtn');
  b.classList.remove('on');
  b.textContent = '▶ 连听';
  document.querySelectorAll('.card.playing').forEach((c) => c.classList.remove('playing'));
  if (msg) toast(msg);
}

function stepChain() {
  if (!state.chain) return;
  if (chainIdx >= currentItems.length) { stopChain('这一课听完了 🎉'); return; }
  const w = currentItems[chainIdx];
  const el = document.querySelectorAll('#wordList .card')[chainIdx];
  chainIdx += 1;
  document.querySelectorAll('.card.playing').forEach((c) => c.classList.remove('playing'));
  if (el) {
    el.classList.add('playing');
    if (el.scrollIntoView) el.scrollIntoView({ block: 'nearest' });
  }
  playWord(w, () => {
    if (el) el.classList.remove('playing');
    if (state.chain) chainTimer = setTimeout(stepChain, 600);
  });
}

function startChain() {
  if (state.chain) { stopAudio(); stopChain('已停止连听'); return; }
  if (!currentItems.length) { toast('这一课没有单词'); return; }
  state.chain = true;
  chainIdx = 0;
  const b = $('#chainBtn');
  b.classList.add('on');
  b.textContent = '⏸ 停止';
  stepChain();
}
