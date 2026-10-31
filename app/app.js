/* 高频词 · 每天一课 —— 纯前端 PWA */
const $ = (s) => document.querySelector(s);
const KEY = 'gaopin_daily_v1';

const state = {
  words: [],
  wordSet: new Set(),
  days: [],
  cats: [],
  cat: '',
  page: 1,              // 0 = 本类全部页
  day: 0,               // 0 = 整页汇总
  theme: 'auto',
  accent: 'us',
  rate: 1,
  repeats: 2,           // 每词朗读遍数
  hideMeaning: true,    // 释义点开才看
  coverWord: false,     // 听音猜词
  shuffle: false,       // 打乱顺序
  showIpa: false,
  autoNext: true,
  replayWrong: true,    // 答错自动重播
  mustRetype: false,    // 答错必须重打
  tries: 0,             // 当前听写题已错几次
  mastered: new Set(),
  wrong: {},
  search: '',
  filter: 'all',
  reviewMode: false,
  queue: [],
  chain: false,
  qi: 0,
  answered: 0,
  correct: 0
};

const PAGE = 100;
let rendered = 0;
let currentItems = [];

/* ---------------- 存储 ---------------- */
// 用 file:// 打开时有些浏览器会禁掉 localStorage，必须全部兜住，
// 否则一次异常就会把整个启动流程打断（表现就是：有工具栏但没单词）
function readStore() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '{}') || {};
  } catch (e) {
    return {};
  }
}
function save() {
  try {
    localStorage.setItem(KEY, JSON.stringify({
      accent: state.accent, rate: state.rate, repeats: state.repeats,
      hideMeaning: state.hideMeaning, coverWord: state.coverWord, shuffle: state.shuffle,
      showIpa: state.showIpa, autoNext: state.autoNext,
      replayWrong: state.replayWrong, mustRetype: state.mustRetype,
      day: state.day, page: state.page, cat: state.cat, theme: state.theme,
      mastered: [...state.mastered], wrong: state.wrong
    }));
  } catch (e) { /* 存不了就存不了，不影响使用 */ }
}
function load() {
  try {
    const d = readStore();
    state.accent = d.accent || 'us';
    state.rate = d.rate || 1;
    state.repeats = d.repeats || 2;
    state.hideMeaning = d.hideMeaning === true;
    state.coverWord = !!d.coverWord;
    state.shuffle = !!d.shuffle;
    state.showIpa = !!d.showIpa;
    state.autoNext = d.autoNext !== false;
    state.replayWrong = d.replayWrong !== false;
    state.mustRetype = !!d.mustRetype;
    state.theme = d.theme || 'auto';
    state.mastered = new Set(d.mastered || []);
    state.wrong = d.wrong || {};
  } catch (e) { /* 忽略损坏数据 */ }
}

/* ---------------- 页 → 天 ---------------- */
function curCat() {
  return state.cats.find((x) => x.name === state.cat);
}
function curPages() {
  const c = curCat();
  return c ? (c.pages || []) : [];
}
function curPage() {
  return curPages().find((p) => p.index === state.page) || null;
}
function catWords() {
  return state.words.filter((w) => w.cat === state.cat);
}
/** 当前页的全部词；page = 0 表示整类 */
function pageWords(page) {
  const pool = catWords();
  const p = page === undefined ? state.page : page;
  return p === 0 ? pool : pool.filter((w) => w.page === p);
}
/** 整页汇总（day = 0）或页内某一天 */
function dayWords(day) {
  const pool = pageWords();
  const d = day === undefined ? state.day : day;
  return d === 0 ? pool : pool.filter((w) => w.day === d);
}
function currentDays() {
  const p = curPage();
  return p ? p.days : [];
}
function dayMastered(day) {
  return dayWords(day).filter((w) => state.mastered.has(w.w)).length;
}
function pageMastered(p) {
  return pageWords(p.index).filter((w) => state.mastered.has(w.w)).length;
}
/** 「Word List 3 · 第 2 天」这样的标题 */
function titleOf(page, day) {
  if (page === 0) return '全部页';
  const p = curPages().find((x) => x.index === page);
  if (!p) return '全部页';
  return p.name + (day ? ' · 第 ' + day + ' 天' : ' · 整页');
}

function renderPageBar() {
  const bar = $('#pageBar');
  bar.innerHTML = '';
  const pages = curPages();
  bar.hidden = pages.length <= 1 && !pages.length;
  const mk = (val, label, sub) => {
    const b = document.createElement('button');
    const full = val !== 0 && pageMastered({ index: val }) === (pageWords(val).length || 1);
    b.className = 'page-chip' + (state.page === val ? ' active' : '') + (full ? ' full' : '');
    b.appendChild(document.createTextNode(label));
    const s = document.createElement('small');
    s.textContent = sub;
    b.appendChild(s);
    b.addEventListener('click', () => {
      state.page = val;
      state.day = 0;
      state.search = '';
      $('#search').value = '';
      stopAudio(); stopChain();
      save(); renderPageBar(); renderDayBar(); renderList(); updateHeader();
      buildQueue(false, false);
    });
    bar.appendChild(b);
  };
  const all = catWords();
  const allDone = all.filter((w) => state.mastered.has(w.w)).length;
  mk(0, '全部', allDone ? `${allDone}/${all.length}` : all.length + '词');
  pages.forEach((p) => {
    const done = pageMastered(p);
    // ComfyUI 这类自建章节带 short 中文名，教学类词库仍显示页码
    mk(p.index, p.short || String(p.index), done ? `${done}/${p.count}` : `${p.count}词`);
  });
  const active = bar.querySelector('.page-chip.active');
  if (active) active.scrollIntoView({ block: 'nearest', inline: 'center' });
}

function renderDayBar() {
  const bar = $('#dayBar');
  bar.innerHTML = '';
  const days = currentDays();
  // 选了「全部页」就不显示天，避免两套编号混在一起
  if (state.page === 0 || !days.length) {
    bar.hidden = true;
    return;
  }
  bar.hidden = false;
  const mk = (val, label, extra) => {
    const b = document.createElement('button');
    b.className = 'day-chip' + (state.day === val ? ' active' : '') + (extra || '');
    b.textContent = label;
    b.addEventListener('click', () => {
      state.day = val;
      state.search = '';
      $('#search').value = '';
      stopAudio(); stopChain();
      save(); renderDayBar(); renderList(); updateHeader();
      buildQueue(false, false);
    });
    bar.appendChild(b);
  };
  mk(0, `整页 ${pageWords().length}`, pageMastered({ index: state.page }) === pageWords().length ? ' full' : '');
  days.forEach((d) => {
    const done = dayMastered(d.day);
    mk(d.day, `第${d.day}天 ${d.count}`, done === d.count ? ' full' : '');
  });
  const active = bar.querySelector('.day-chip.active');
  if (active) active.scrollIntoView({ block: 'nearest', inline: 'center' });
}

function renderCatBar() {
  const bar = $('#catBar');
  bar.innerHTML = '';
  state.cats.forEach((c) => {
    const b = document.createElement('button');
    b.className = 'cat-chip' + (state.cat === c.name ? ' active' : '') + (c.count ? '' : ' empty');
    b.innerHTML = '';
    b.appendChild(document.createTextNode(c.name));
    const small = document.createElement('small');
    small.textContent = c.count ? c.count + ' 词' : '待导入';
    b.appendChild(small);
    bar.appendChild(b);
    if (!c.count) return;
    b.addEventListener('click', () => {
      state.cat = c.name;
      state.page = 1;
      state.day = 0;
      state.search = '';
      $('#search').value = '';
      stopAudio(); stopChain();
      save(); renderCatBar(); renderPageBar(); renderDayBar(); renderList(); updateHeader();
      buildQueue(false, false);
    });
  });
}

/* ---------------- 回到顶部 ---------------- */
// 单词页往下翻过一屏就浮出箭头，一点平滑滑回顶上（跟购物 App 一个手感）
function setupToTop() {
  const btn = $('#toTop');
  if (!btn) return;
  const sync = () => {
    const onList = $('#tab-listen').classList.contains('active');
    btn.classList.toggle('show', onList && window.scrollY > 360);
  };
  btn.addEventListener('click', () => {
    const before = window.scrollY;
    try {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (e) {
      window.scrollTo(0, 0);
    }
    // 老内核不认 smooth：平滑没动起来就直接跳顶
    setTimeout(() => {
      if (window.scrollY >= before - 2) window.scrollTo(0, 0);
    }, 350);
  });
  window.addEventListener('scroll', sync, { passive: true });
  window.__toTopSync = sync;   // 切标签 / 换页后手动刷新一次
  sync();
}

/* ---------------- 事件 ---------------- */
function bind() {
  setupToTop();

  document.querySelectorAll('.tab').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach((b) => b.classList.toggle('active', b === btn));
      document.querySelectorAll('.tab-pane').forEach((p) => p.classList.remove('active'));
      $('#tab-' + btn.dataset.tab).classList.add('active');
      stopAudio(); stopChain();
      if (btn.dataset.tab === 'wrong') renderWrong();
      if (window.__toTopSync) window.__toTopSync();
    });
  });

  $('#search').addEventListener('input', (e) => { state.search = e.target.value; renderList(); });

  /* ---- 工具条 ---- */
  $('#btnShuffle').addEventListener('click', () => {
    state.shuffle = !state.shuffle;
    $('#btnShuffle').classList.toggle('on', state.shuffle);
    save(); renderList(); buildQueue(false, false);
    toast(state.shuffle ? '已打乱顺序' : '已恢复教材顺序');
  });
  $('#btnReset').addEventListener('click', () => {
    if (state.page === 0) { toast('先在页条上选一页，再重置'); return; }
    const ws = dayWords();
    if (!ws.length) return;
    ws.forEach((w) => state.mastered.delete(w.w));
    save(); updateHeader(); renderDayBar(); renderPageBar(); renderList();
    toast(state.day ? '这一天已重置' : '这一页已重置');
  });
  $('#optMean').addEventListener('change', (e) => {
    state.hideMeaning = !e.target.checked; save(); renderList();
  });
  $('#optTwice').addEventListener('change', (e) => {
    state.repeats = e.target.checked ? Math.max(2, state.repeats) : 1;
    $('#optRepeats').value = String(state.repeats);
    save();
  });
  $('#optUndone').addEventListener('change', (e) => {
    state.filter = e.target.checked ? 'todo' : 'all'; save(); renderList();
  });
  $('#rate').addEventListener('input', (e) => {
    state.rate = Number(e.target.value);
    $('#rateVal').textContent = state.rate.toFixed(2);
    $('#optRate').value = state.rate;
    $('#optRateVal').textContent = state.rate.toFixed(2) + '×';
    save();
  });
  $('#accentSel').addEventListener('change', (e) => {
    state.accent = e.target.value;
    $('#optAccent').value = state.accent;
    save(); updateHeader(); renderList(); renderWrong();
    toast(state.accent === 'us' ? '已切换美音' : '已切换英音');
  });

  $('#chainBtn').addEventListener('click', startChain);
  $('#playBig').addEventListener('click', playCurrentDict);
  $('#dictSubmit').addEventListener('click', checkAnswer);
  $('#dictInput').addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return;
    if ($('#dictInput').disabled) { state.qi += 1; nextDict(); return; }
    checkAnswer();
  });
  $('#btnReveal').addEventListener('click', revealAnswer);
  $('#btnSkip').addEventListener('click', () => { state.qi += 1; nextDict(); });
  $('#reviewBtn').addEventListener('click', () => {
    if (buildQueue(true)) document.querySelector('.tab[data-tab="dict"]').click();
  });
  $('#clearWrong').addEventListener('click', () => {
    state.wrong = {}; save(); updateHeader(); renderWrong(); toast('错词本已清空');
  });

  const sheet = $('#sheet');
  $('#settingsBtn').addEventListener('click', () => { renderThemes(); sheet.hidden = false; });
  $('#closeSheet').addEventListener('click', () => { sheet.hidden = true; });
  sheet.addEventListener('click', (e) => { if (e.target === sheet) sheet.hidden = true; });
  $('#optAccent').addEventListener('change', (e) => {
    state.accent = e.target.value;
    $('#accentSel').value = state.accent;
    save(); updateHeader(); renderList(); renderWrong();
  });
  $('#optRate').addEventListener('input', (e) => {
    state.rate = Number(e.target.value);
    $('#optRateVal').textContent = state.rate.toFixed(2) + '×';
    $('#rate').value = state.rate;
    $('#rateVal').textContent = state.rate.toFixed(2);
    save();
  });
  $('#optRepeats').addEventListener('change', (e) => {
    state.repeats = Math.max(1, Number(e.target.value) || 1);
    $('#optTwice').checked = state.repeats >= 2;
    save(); toast(`每词朗读 ${state.repeats} 遍`);
  });
  $('#optShowIpa').addEventListener('change', (e) => {
    state.showIpa = e.target.checked; save();
    const w = state.queue[state.qi];
    $('#ipaReveal').textContent = state.showIpa && w ? '/' + (state.accent === 'uk' ? w.uk : w.us) + '/' : '';
  });
  $('#optAutoNext').addEventListener('change', (e) => { state.autoNext = e.target.checked; save(); });
  $('#optReplayWrong').addEventListener('change', (e) => { state.replayWrong = e.target.checked; save(); });
  $('#optMustRetype').addEventListener('change', (e) => { state.mustRetype = e.target.checked; save(); });
  $('#optHideMeaning').addEventListener('change', (e) => {
    state.hideMeaning = e.target.checked;
    $('#optMean').checked = !state.hideMeaning;
    save(); renderList();
  });
  $('#optCoverWord').addEventListener('change', (e) => {
    state.coverWord = e.target.checked; save(); renderList();
  });
  $('#optShuffle').addEventListener('change', (e) => {
    state.shuffle = e.target.checked;
    $('#btnShuffle').classList.toggle('on', state.shuffle);
    save(); buildQueue(false, false);
  });
  $('#resetProgress').addEventListener('click', () => {
    state.mastered.clear(); state.wrong = {};
    save(); updateHeader(); renderDayBar(); renderList(); renderWrong();
    toast('进度已清空');
  });
}

/* ---------------- 启动 ---------------- */
async function boot() {
  load();
  applyTheme(state.theme);
  if (window.matchMedia) {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => { if (state.theme === 'auto') applyTheme('auto'); };
    if (mq.addEventListener) mq.addEventListener('change', onChange);
    else if (mq.addListener) mq.addListener(onChange);
  }
  try {
    // data/words.js 已经在 index.html 里用 script 标签载入；没有才走网络
    const data = window.__WORDS__ || await (await fetch('data/words.json', { cache: 'no-cache' })).json();
    state.words = data.words;
    state.wordSet = new Set(state.words.map((w) => w.w));
    // 六个类别固定显示，没导入的标"待导入"
    const ORDER = ['高频词', '中频词', '低频词', '偶考词', '基础词', '补充词'];
    const found = data.categories || [];
    state.cats = ORDER.map((name) => found.find((c) => c.name === name)
      || { name, count: 0, pageCount: 0, dayCount: 0, days: [], pages: [] });
    found.forEach((c) => { if (!ORDER.includes(c.name)) state.cats.push(c); });
    const first = state.cats.find((c) => c.count > 0) || state.cats[0];
    state.cat = first ? first.name : '';
  } catch (e) {
    document.body.innerHTML = '<p style="padding:40px;text-align:center">词库加载失败：' + e.message + '</p>';
    return;
  }
  bind();
  $('#optAccent').value = state.accent;
  $('#optRate').value = state.rate;
  $('#optRateVal').textContent = state.rate.toFixed(2) + '×';
  $('#optRepeats').value = state.repeats;
  // 工具条初始状态
  $('#accentSel').value = state.accent;
  $('#rate').value = state.rate;
  $('#rateVal').textContent = state.rate.toFixed(2);
  $('#btnShuffle').classList.toggle('on', state.shuffle);
  $('#optMean').checked = !state.hideMeaning;
  $('#optTwice').checked = state.repeats >= 2;
  $('#optUndone').checked = state.filter === 'todo';
  $('#optShowIpa').checked = state.showIpa;
  $('#optAutoNext').checked = state.autoNext;
  $('#optReplayWrong').checked = state.replayWrong;
  $('#optMustRetype').checked = state.mustRetype;
  $('#optHideMeaning').checked = state.hideMeaning;
  $('#optCoverWord').checked = state.coverWord;
  $('#optShuffle').checked = state.shuffle;

  // 回到上次翻到的那一页；没记录就停在第一个没学完的页
  const saved = readStore();
  if (saved.cat && state.cats.some((c) => c.name === saved.cat && c.count > 0)) state.cat = saved.cat;
  const pages = curPages();
  const savedPage = pages.find((p) => p.index === saved.page);
  if (savedPage) {
    state.page = savedPage.index;
    state.day = saved.day !== undefined && saved.day <= savedPage.days.length ? saved.day : 0;
  } else {
    const todo = pages.find((p) => pageMastered(p) < p.count) || pages[0];
    state.page = todo ? todo.index : 0;
    state.day = 0;
  }

  renderCatBar();
  renderPageBar();
  renderDayBar();
  renderList();
  updateHeader();
  buildQueue(false, false);

  // file:// 下有的浏览器会直接抛 DOMException，包一层别让它中断启动
  try {
    if ('serviceWorker' in navigator) {
      // 有新版本接管时自动刷新一次，省得用户关两次才看到更新
      const hadController = !!navigator.serviceWorker.controller;
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        if (hadController && performance.now() < 8000) location.reload();
      });
      // updateViaCache:'none' —— 每次启动都必须去服务器核对 sw.js，
      // 不能被浏览器那 10 分钟的 HTTP 缓存糊弄过去
      navigator.serviceWorker.register('sw.js', { updateViaCache: 'none' }).catch(() => {});
    }
  } catch (e) { /* 本地文件打开时离线缓存本来也用不上 */ }

  offlineSetup();
}

// 一定要等所有 <script> 都执行完再启动：
// boot() 会立刻调 bind()，而 bind() 用到了 practice.js 里的函数。
// 词库走 words.js 时没有 await 让出执行栈，提前跑就会 ReferenceError。
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => { boot().catch((e) => console.error(e)); });
} else {
  boot().catch((e) => console.error(e));
}

