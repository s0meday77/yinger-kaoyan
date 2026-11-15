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

/** 书上的释义 + 词组，做成可折叠的一块——想只背单词就收起来 */
function bookNode(w) {
  const wrap = document.createElement('div');
  wrap.className = 'book';

  const btn = document.createElement('button');
  btn.className = 'fold';
  btn.type = 'button';
  const phrs = w.sp || [];
  const defs = w.sm || [];
  const parts = [];
  if (defs.length) parts.push('释义');
  if (phrs.length) parts.push('词组 ' + phrs.length);
  btn.innerHTML = '<i class="arw">▸</i><span>' + parts.join(' · ') + '</span>';

  const box = document.createElement('div');
  box.className = 'extra';
  box.hidden = true;

  defs.forEach((d) => {
    const p = document.createElement('p');
    p.className = 'def';
    p.textContent = d;
    box.appendChild(p);
  });

  if (phrs.length) {
    const list = document.createElement('div');
    list.className = 'phrs';
    phrs.forEach((item) => {
      const row = document.createElement('div');
      row.className = 'phr';
      const en = document.createElement('span');
      en.className = 'pen';
      en.textContent = item.p;
      const zh = document.createElement('span');
      zh.className = 'pzh';
      zh.textContent = item.t;
      row.append(en, zh);
      // 点词组单独朗读它，只读一遍，不跟着「每词朗读」跑三遍
      row.addEventListener('click', (e) => {
        e.stopPropagation();
        stopAudio();
        const keep = state.repeats;
        state.repeats = 1;
        speakTTS(item.p);
        state.repeats = keep;
      });
      list.appendChild(row);
    });
    box.appendChild(list);
  }

  // 设了「释义点开才看」就默认收起，否则一进来就摊开
  const open = () => {
    box.hidden = !box.hidden;
    btn.classList.toggle('open', !box.hidden);
    btn.querySelector('.arw').textContent = box.hidden ? '▸' : '▾';
  };
  btn.addEventListener('click', (e) => { e.stopPropagation(); open(); });
  wrap.append(btn, box);
  if (!state.hideMeaning) open();
  return wrap;
}

function cardNode(w) {
  const el = document.createElement('article');
  const masked = state.coverWord;
  const hasBook = (w.sm && w.sm.length) || (w.sp && w.sp.length);
  el.className = 'card' + (state.mastered.has(w.w) ? ' done' : '') + (masked ? ' masked' : '');
  el.innerHTML =
    '<div class="spk">🔊</div>' +
    '<div class="body"><div class="wline"><span class="w"></span>' +
    '<span class="ipa"></span><span class="list-tag"></span></div>' +
    (hasBook ? '' : '<div class="m"></div>') + '</div>' +
    '<button class="chk" aria-label="标记掌握">✓</button>';
  const wEl = el.querySelector('.w');
  const mEl = el.querySelector('.m');
  wEl.textContent = masked ? '• • •' : w.w;
  const ipa = state.accent === 'uk' ? w.uk : w.us;
  // 专业词（如 EasyNegative、DPM++ 2M）查不到音标，留空别显示成 //
  el.querySelector('.ipa').textContent = ipa ? '/' + ipa + '/' : '';
  el.querySelector('.list-tag').textContent = (w.list || '').replace('Word List ', 'L');
  // 有书上内容的词，释义和词组都收进折叠区，主行不再重复有道释义
  if (hasBook) {
    const book = bookNode(w);
    // 听音猜词时先藏着，词组里写着单词本身，一露馅就没得猜了
    if (masked) book.hidden = true;
    el.querySelector('.body').appendChild(book);
  } else {
    mEl.textContent = w.m;
    // 「释义」勾选框控制显示，取消勾选就整列藏起来
    mEl.hidden = state.hideMeaning;
  }

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
        const book = el.querySelector('.book');
        if (book) book.hidden = false;
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
