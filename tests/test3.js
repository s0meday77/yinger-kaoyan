const { JSDOM } = require('jsdom');
const fs = require('fs');
const path = require('path');

const APP = path.join(__dirname, '..', 'app');
const html = fs.readFileSync(path.join(APP, 'index.html'), 'utf8');
const data = JSON.parse(fs.readFileSync(path.join(APP, 'data/words.json'), 'utf8'));

const dom = new JSDOM(html, { url: 'http://localhost:8766/', runScripts: 'outside-only', pretendToBeVisual: true });
const { window } = dom;

window.fetch = async (url) => {
  const u = String(url);
  if (u.includes('words.json')) return { json: async () => data };
  // 播放时改成 fetch 取整段音频再播（绕开 iOS 的分段请求问题），这里给个假 blob
  if (u.includes('/audio/')) return { ok: true, blob: async () => ({ size: 5000 }) };
  throw new Error('unexpected fetch ' + u);
};
window.URL.createObjectURL = () => 'blob:test';
window.URL.revokeObjectURL = () => {};
const played = [];
window.Audio = class {
  constructor(src) { this.src = src; this.playbackRate = 1; played.push(src); }
  play() { setTimeout(() => this.onended && this.onended(), 0); return Promise.resolve(); }
  pause() {}
};
window.speechSynthesis = { speak() {}, cancel() {} };
window.SpeechSynthesisUtterance = class {};
window.navigator.serviceWorker = { register: async () => {} };
window.HTMLElement.prototype.scrollIntoView = function () {};

window.eval(
  ['ui.js', 'audio.js', 'offline.js', 'app.js', 'list.js', 'practice.js']
    .map((f) => fs.readFileSync(path.join(APP, f), 'utf8'))
    .join('\n') + '\nwindow.__s = state;'
);

const $ = (s) => window.document.querySelector(s);
const $$ = (s) => window.document.querySelectorAll(s);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const out = [];
const check = (n, c, e = '') => out.push(`${c ? '✅' : '❌'} ${n}${e ? ' — ' + e : ''}`);

(async () => {
  await sleep(400);

  const cats = $$('.cat-chip');
  check('六个类别都在', cats.length === 6, [...cats].map((c) => c.textContent).join(' / '));
  check('高频词是选中态', cats[0].classList.contains('active'), cats[0].textContent);
  // 中频词已上线，剩低频/偶考/基础/补充四类还没导入
  check('中频词已导入', !cats[1].classList.contains('empty'), cats[1].textContent);
  check('其余四类标待导入', [...cats].slice(2).every((c) => c.classList.contains('empty')), '');

  const pg = data.categories[0].pages;
  const pages = $$('.page-chip');
  check('页条 = 全部 + 12 页', pages.length === pg.length + 1, `${pages.length} 个`);
  check('页序与教材一致', pg.map((p) => p.name).join(',') === Array.from({ length: 12 }, (_, i) => `Word List ${i + 1}`).join(','), '');
  check('默认停在第 1 页', window.__s.page === 1, String(window.__s.page));

  check('整页汇总 83 词', $$('#wordList .card').length === 83, `${$$('#wordList .card').length} 张`);
  check('标题是 Word List 1 · 整页', $('#dayTitle').textContent.includes('Word List 1 · 整页'), $('#dayTitle').textContent);

  const dchips = $$('.day-chip');
  check('天条 = 整页 + 4 天', dchips.length === 5, [...dchips].map((c) => c.textContent).join(' / '));

  dchips[1].click();
  await sleep(60);
  const day1 = data.words.filter((w) => w.cat === '高频词' && w.page === 1 && w.day === 1).length;
  check('第 1 天切分正确', $$('#wordList .card').length === day1, `${$$('#wordList .card').length} 词（应为 ${day1}）`);
  check('标题带页和天', /Word List 1 · 第 1 天/.test($('#dayTitle').textContent), $('#dayTitle').textContent);

  played.length = 0;
  $$('#wordList .card')[0].click();
  await sleep(30);
  check('点词播真人录音', played.length > 0 && String(played[0]).startsWith('blob:'), played[0] || '无');

  // 听写只覆盖当前页当前天
  window.document.querySelector('.tab[data-tab="dict"]').click();
  await sleep(120);
  const q = window.__s.queue;
  check('听写队列 = 当天词数', q.length === day1, `${q.length} / ${day1}`);
  check('队列都属于第 1 页第 1 天', q.every((w) => w.page === 1 && w.day === 1), '');

  const target = q[0].w;
  $('#dictInput').value = target;
  $('#dictSubmit').click();
  await sleep(50);
  check('答对判定', $('#feedback').textContent.includes('正确'), '');

  await sleep(700);
  $('#dictInput').value = 'zzzzzz';
  $('#dictSubmit').click();
  await sleep(50);
  check('答错判定', $('#feedback').textContent.includes('拼错了'), '');
  check('错词入库', Object.keys(window.__s.wrong).length === 1, '');

  // 翻到 Word List 8（只有 33 词）
  $$('.page-chip')[8].click();
  await sleep(80);
  check('第 8 页 33 词', $$('#wordList .card').length === 33, `${$$('#wordList .card').length} 张`);
  check('第 8 页天条 4 天', $$('.day-chip').length === 5, [...$$('.day-chip')].map((c) => c.textContent).join(' / '));

  // 全部页
  $$('.page-chip')[0].click();
  await sleep(80);
  check('全部页 = 971 词', $('#subLine').textContent.includes('971'), $('#subLine').textContent);
  check('全部页时天条隐藏', $('#dayBar').hidden === true, '');

  // 皮肤
  window.document.querySelector('#settingsBtn').click();
  await sleep(30);
  const dots = [...$$('#themePick .theme-item')];
  check('皮肤有 6 套', dots.length === 6, [...dots].map((d) => d.textContent).join(' / '));
  check('默认跟随系统', window.__s.theme === 'auto', window.__s.theme);
  dots.find((d) => d.textContent.includes('米黄')).click();
  await sleep(30);
  check('切米黄生效', window.document.documentElement.dataset.theme === 'sepia',
    window.document.documentElement.dataset.theme);
  check('状态栏颜色同步', window.document.querySelector('meta[name=theme-color]').content === '#f3ecdd',
    window.document.querySelector('meta[name=theme-color]').content);
  check('选中态标记', $$('#themePick .theme-item.active')[0].textContent.includes('米黄'), '');
  window.document.querySelector('#closeSheet').click();

  // 进度线
  const w0 = $('#progBar').style.width;
  check('进度线已计算', w0 !== '' && w0 !== '0%', w0);

  // ---- 记忆开关 ----
  await sleep(1200);              // 等上一题的「答错重播」播完，避免串到后面的计数
  window.document.querySelector('.tab[data-tab="listen"]').click();
  $$('.page-chip')[1].click();
  await sleep(60);

  const card0 = $$('#wordList .card')[0];
  check('释义默认显示', card0.querySelector('.m').hidden === false && card0.querySelector('.m').textContent.length > 1,
    card0.querySelector('.m').textContent);
  const meanBox = $('#optMean');
  meanBox.checked = false;
  meanBox.dispatchEvent(new window.Event('change'));
  await sleep(40);
  check('取消「释义」就藏起来', $$('#wordList .card')[0].querySelector('.m').hidden === true, '');
  meanBox.checked = true;
  meanBox.dispatchEvent(new window.Event('change'));
  await sleep(40);
  check('勾上「释义」又显示', $$('#wordList .card')[0].querySelector('.m').hidden === false, '');
  check('头部已掌握统计', /^\d+$/.test($('#doneNum').textContent) && /^\d+$/.test($('#totalNum').textContent),
    `${$('#doneNum').textContent} / ${$('#totalNum').textContent}`);

  // 每词朗读遍数
  played.length = 0;
  card0.click();
  await sleep(900);
  check('默认每词朗读 2 遍', played.length === 2, `播放 ${played.length} 次`);
  window.document.querySelector('#settingsBtn').click();
  await sleep(20);
  $('#optRepeats').value = '3';
  $('#optRepeats').dispatchEvent(new window.Event('change'));
  window.document.querySelector('#closeSheet').click();
  played.length = 0;
  card0.click();
  await sleep(1500);
  check('切到 3 遍生效', played.length === 3, `播放 ${played.length} 次`);
  window.document.querySelector('#settingsBtn').click();
  $('#optRepeats').value = '2';
  $('#optRepeats').dispatchEvent(new window.Event('change'));
  window.document.querySelector('#closeSheet').click();

  // 听音猜词
  window.document.querySelector('#settingsBtn').click();
  $('#optCoverWord').checked = true;
  $('#optCoverWord').dispatchEvent(new window.Event('change'));
  window.document.querySelector('#closeSheet').click();
  await sleep(40);
  const maskCard = $$('#wordList .card')[0];
  check('听音猜词：词被遮住', maskCard.classList.contains('masked') && maskCard.querySelector('.w').textContent.trim() === '• • •',
    maskCard.querySelector('.w').textContent);
  maskCard.click();
  await sleep(900);
  check('播完自动揭示单词', maskCard.querySelector('.w').textContent === window.__s.words[0].w || !maskCard.classList.contains('masked'),
    maskCard.querySelector('.w').textContent);

  // 乱序
  const pageNo = window.__s.page;
  // ⚠️ 必须连类别一起筛：高频和中频的页号都从 1 开始，只按 page 会串类
  const inCat = (w) => w.cat === window.__s.cat;
  const textbook = window.__s.words.filter((w) => inCat(w) && w.page === pageNo).map((w) => w.w).join(',');
  window.document.querySelector('#settingsBtn').click();
  const shuf = $('#optShuffle');
  shuf.checked = true;
  shuf.dispatchEvent(new window.Event('change'));
  window.document.querySelector('#closeSheet').click();
  await sleep(60);
  const mixed = window.__s.queue.map((w) => w.w).join(',');
  check('乱序打散了教材顺序', mixed !== textbook, `首位 ${mixed.split(',')[0]}（教材首位 ${textbook.split(',')[0]}）`);
  window.document.querySelector('#settingsBtn').click();
  shuf.checked = false;
  shuf.dispatchEvent(new window.Event('change'));
  window.document.querySelector('#closeSheet').click();
  await sleep(60);
  check('关掉乱序恢复教材顺序', window.__s.queue.map((w) => w.w).join(',') === textbook, '');

  // 工具条按钮
  const shufBtn = $('#btnShuffle');
  shufBtn.click();
  await sleep(60);
  check('🔀乱序按钮点亮', shufBtn.classList.contains('on') && window.__s.shuffle === true, shufBtn.className);
  shufBtn.click();
  await sleep(60);
  check('再点一次关掉', !shufBtn.classList.contains('on') && window.__s.shuffle === false, '');

  const undone = $('#optUndone');
  undone.checked = true;
  undone.dispatchEvent(new window.Event('change'));
  await sleep(40);
  const shown = $$('#wordList .card').length;
  const allInPage = window.__s.words.filter((w) => inCat(w) && w.page === window.__s.page).length;
  check('只练未掌握：列表变短', shown < allInPage, `${shown} / ${allInPage}`);
  undone.checked = false;
  undone.dispatchEvent(new window.Event('change'));
  await sleep(40);
  check('取消后恢复全部', $$('#wordList .card').length === allInPage, `${$$('#wordList .card').length}`);

  // 连听
  await sleep(1200);
  window.document.querySelector('.tab[data-tab="listen"]').click();
  await sleep(40);
  played.length = 0;
  $('#chainBtn').click();
  await sleep(100);
  check('连听开起来了', window.__s.chain === true && $('#chainBtn').textContent.includes('停止'), $('#chainBtn').textContent);
  await sleep(1500);
  check('连听会自动往下播', played.length >= 2, `已播 ${played.length} 次`);
  $('#chainBtn').click();
  await sleep(60);
  check('连听能停下', window.__s.chain === false, '');

  // 必须重打
  window.document.querySelector('#settingsBtn').click();
  $('#optMustRetype').checked = true;
  $('#optMustRetype').dispatchEvent(new window.Event('change'));
  window.document.querySelector('#closeSheet').click();
  window.document.querySelector('.tab[data-tab="dict"]').click();
  await sleep(120);
  const input = $('#dictInput');
  input.value = 'zzzzzz';
  $('#dictSubmit').click();
  await sleep(50);
  check('答错必须重打：不清空不锁', input.disabled === false && input.value === '', `disabled=${input.disabled}`);
  check('重打提示', $('#feedback').textContent.includes('再打一遍'), $('#feedback').textContent);
  const right = window.__s.queue[window.__s.qi].w;
  input.value = right;
  $('#dictSubmit').click();
  await sleep(50);
  check('重打对了就通过', $('#feedback').textContent.includes('正确'), '');

  // 数据完整性
  check('每天词数连续无空洞', (() => {
    for (const c of data.categories) {
      for (const p of c.pages) {
        const ws = data.words.filter((w) => w.cat === c.name && w.page === p.index);
        if (ws.length !== p.count) return false;
        const days = [...new Set(ws.map((w) => w.day))].sort((a, b) => a - b);
        if (days.join(',') !== days.map((_, i) => i + 1).join(',')) return false;
      }
    }
    return true;
  })(), '');
  // 每个类别的全局天数各自从 1 连续排下来（高频 48 天、中频 36 天）
  check('每类全局天数连续', data.categories.every((c) => {
    const g = [...new Set(data.words.filter((w) => w.cat === c.name).map((w) => w.gday))].sort((a, b) => a - b);
    return g.length === c.dayCount && g[0] === 1 && g[g.length - 1] === c.dayCount;
  }), data.categories.map((c) => `${c.name} ${c.dayCount} 天`).join(' / '));

  const bad = data.words.filter((w) => !w.us || !w.uk || !w.us_audio || !w.uk_audio);
  check('所有词都有英美音标和录音', bad.length === 0, bad.length ? bad.slice(0, 5).map((w) => w.w).join(',') : '');

  console.log(out.join('\n'));
  const failed = out.filter((l) => l.startsWith('❌')).length;
  console.log(`\n通过 ${out.length - failed}/${out.length}`);
  process.exit(failed ? 1 : 0);
})();
