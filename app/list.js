/* 点听列表渲染 —— 卡片、分页、筛选 */
/* ---------------- 点听 ---------------- */
function filtered() {
  const q = state.search.trim().toLowerCase();
  return dayWords(state.day).filter((w) => {
    if (state.filter === 'todo' && state.mastered.has(w.w)) return false;
    if (state.filter === 'done' && !state.mastered.has(w.w)) return false;
    if (!q) return true;
    return w.w.toLowerCase().includes(q) || w.m.toLowerCase().includes(q);
  });
}

function cardNode(w) {
  const el = document.createElement('article');
  const masked = state.coverWord;
  el.className = 'card' + (state.mastered.has(w.w) ? ' done' : '') + (masked ? ' masked' : '');
  el.innerHTML =
    '<div class="spk">🔊</div>' +
    '<div class="body"><div class="wline"><span class="w"></span>' +
    '<span class="ipa"></span><span class="list-tag"></span></div>' +
    '<div class="m"></div></div>' +
    '<button class="chk" aria-label="标记掌握">✓</button>';
  const wEl = el.querySelector('.w');
  const mEl = el.querySelector('.m');
  wEl.textContent = masked ? '• • •' : w.w;
  el.querySelector('.ipa').textContent = '/' + (state.accent === 'uk' ? w.uk : w.us) + '/';
  el.querySelector('.list-tag').textContent = (w.list || '').replace('Word List ', 'L');
  mEl.textContent = w.m;
  // 「释义」勾选框控制显示，取消勾选就整列藏起来
  mEl.hidden = state.hideMeaning;

  el.addEventListener('click', (e) => {
    if (e.target.closest('.chk')) return;
    document.querySelectorAll('.card.playing').forEach((c) => c.classList.remove('playing'));
    el.classList.add('playing');
    // 听音猜词：整遍播完才把单词显出来
    playWord(w, () => {
      el.classList.remove('playing');
      if (masked) {
        wEl.textContent = w.w;
        el.classList.remove('masked');
      }
    });
  });
  el.querySelector('.chk').addEventListener('click', (e) => {
    e.stopPropagation();
    if (state.mastered.has(w.w)) state.mastered.delete(w.w);
    else state.mastered.add(w.w);
    el.classList.toggle('done', state.mastered.has(w.w));
    save(); updateHeader(); renderDayBar(); renderPageBar();
  });
  return el;
}

function appendChunk() {
  const box = $('#wordList');
  const old = $('#more');
  if (old) old.remove();
  const frag = document.createDocumentFragment();
  const end = Math.min(rendered + PAGE, currentItems.length);
  for (let i = rendered; i < end; i++) frag.appendChild(cardNode(currentItems[i]));
  rendered = end;
  box.appendChild(frag);
  if (rendered < currentItems.length) {
    const more = document.createElement('button');
    more.id = 'more';
    more.className = 'ghost wide';
    more.textContent = `加载更多（还有 ${currentItems.length - rendered} 词）`;
    more.addEventListener('click', appendChunk);
    box.appendChild(more);
  }
}

function renderList() {
  const box = $('#wordList');
  currentItems = filtered();
  rendered = 0;
  box.innerHTML = '';
  if (!currentItems.length) {
    box.innerHTML = '<p class="empty">这里还没有词</p>';
    return;
  }
  appendChunk();
}

function updateHeader() {
  const ws = dayWords();
  const done = ws.filter((w) => state.mastered.has(w.w)).length;
  $('#dayTitle').textContent = state.cat + ' · ' + titleOf(state.page, state.day);
  const cat = curCat();
  const gday = (currentDays().find((d) => d.day === state.day) || {}).gday;
  const plan = !cat ? ''
    : (gday ? `第 ${gday}/${cat.dayCount} 天` : `全类 ${cat.dayCount} 天`);
  $('#subLine').textContent = `点一下单词就朗读 · 共 ${ws.length} 词` + (plan ? ' · ' + plan : '');
  $('#doneNum').textContent = done;
  $('#totalNum').textContent = ws.length;
  const total = catWords();
  const doneAll = total.filter((w) => state.mastered.has(w.w)).length;
  const bar = $('#progBar');
  if (bar) bar.style.width = (total.length ? (doneAll / total.length) * 100 : 0) + '%';
  const badge = $('#wrongBadge');
  const n = Object.keys(state.wrong).length;
  badge.textContent = n;
  badge.hidden = n === 0;
}
