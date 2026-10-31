/* 听写 · 错词 · 提示 —— 从 app.js 拆出，保持单文件易读 */
/* ---------------- 听写 ---------------- */
function buildQueue(onlyWrong, autoPlay = true) {
  let pool = onlyWrong ? state.words.filter((w) => state.wrong[w.w]) : dayWords();
  if (!pool.length) {
    toast(onlyWrong ? '错词本是空的' : '这一课没有单词');
    return false;
  }
  // 乱序开着就完全打散；关着就照教材顺序来，方便对着书学
  // 只有「复习错词」模式始终按错得多到少排
  if (state.shuffle) pool = pool.slice().sort(() => Math.random() - 0.5);
  else if (onlyWrong) {
    pool = pool.slice().sort((a, b) => (state.wrong[b.w] || 0) - (state.wrong[a.w] || 0) || Math.random() - 0.5);
  } else pool = pool.slice();
  state.queue = pool;
  state.qi = 0;
  state.answered = 0;
  state.correct = 0;
  state.reviewMode = onlyWrong;
  $('#dictHint').textContent = onlyWrong ? '复习模式 · 只练错词'
    : titleOf(state.page, state.day) + ' · 听发音拼单词';
  nextDict(autoPlay);
  return true;
}

function nextDict(autoPlay = true) {
  const w = state.queue[state.qi];
  const input = $('#dictInput');
  $('#feedback').innerHTML = '';
  input.value = '';
  input.className = '';
  input.disabled = false;
  state.tries = 0;
  const ipa = w ? (state.accent === 'uk' ? w.uk : w.us) : '';
  $('#ipaReveal').textContent = state.showIpa && ipa ? '/' + ipa + '/' : '';
  $('#dictCounter').textContent = `${Math.min(state.qi + 1, state.queue.length)} / ${state.queue.length}`;
  $('#dictAcc').textContent = state.answered
    ? `正确率 ${Math.round((state.correct / state.answered) * 100)}%` : '正确率 —';
  if (!w) {
    $('#dictHint').textContent = '这一课完成啦 🎉';
    $('#playBig').disabled = true;
    return;
  }
  $('#playBig').disabled = false;
  if (autoPlay) setTimeout(playCurrentDict, 260);
}

function playCurrentDict() {
  const w = state.queue[state.qi];
  if (!w) return;
  const btn = $('#playBig');
  btn.classList.remove('hit');
  void btn.offsetWidth;
  btn.classList.add('hit');
  playWord(w);
}

function checkAnswer() {
  const w = state.queue[state.qi];
  if (!w) return;
  const input = $('#dictInput');
  const val = input.value.trim().toLowerCase();
  if (!val) return;
  const firstTry = state.tries === 0;   // 同一题重打不算新题，正确率只统计第一次
  if (val === w.w.toLowerCase()) {
    if (firstTry) { state.answered += 1; state.correct += 1; }
    state.tries = 0;
    input.classList.add('ok');
    $('#feedback').innerHTML = '<span class="good">✓ 正确</span>';
    if (state.wrong[w.w]) {
      state.wrong[w.w] -= 1;
      if (state.wrong[w.w] <= 0) delete state.wrong[w.w];
    }
    state.mastered.add(w.w);
    save(); updateHeader(); renderDayBar(); renderPageBar();
    if (state.autoNext) setTimeout(() => { state.qi += 1; nextDict(); }, 600);
    else input.disabled = true;
  } else {
    if (firstTry) state.answered += 1;
    state.tries += 1;
    if (firstTry) {
      state.wrong[w.w] = (state.wrong[w.w] || 0) + 1;
      save(); updateHeader();
    }
    input.classList.add('bad');
    if (state.replayWrong) playWord(w);
    if (state.mustRetype) {
      // 必须重打：不给答案，清空输入让他再拼一遍
      $('#feedback').innerHTML =
        `<span class="bad">✗ 再打一遍</span><br><span class="hint">听清楚再拼，这个要记牢</span>`;
      input.value = '';
      input.classList.remove('bad');
      setTimeout(() => input.classList.add('bad'), 20);
      input.focus();
    } else {
      $('#feedback').innerHTML =
        `<span class="bad">✗ 拼错了</span><br>正确答案：<span class="right">${w.w}</span>` +
        `<br><span class="hint">${w.m}</span>`;
      input.disabled = true;
    }
  }
  $('#dictAcc').textContent = state.answered
    ? `正确率 ${Math.round((state.correct / state.answered) * 100)}%` : '正确率 —';
}

function revealAnswer() {
  const w = state.queue[state.qi];
  if (!w) return;
  state.answered += 1;
  state.wrong[w.w] = (state.wrong[w.w] || 0) + 1;
  save(); updateHeader();
  $('#dictInput').disabled = true;
  $('#feedback').innerHTML = `答案：<span class="right">${w.w}</span><br><span class="hint">${w.m}</span>`;
  const ipa = state.accent === 'uk' ? w.uk : w.us;
  $('#ipaReveal').textContent = ipa ? '/' + ipa + '/' : '';
}

/* ---------------- 错词 ---------------- */
function renderWrong() {
  const box = $('#wrongList');
  const items = state.words.filter((w) => state.wrong[w.w])
    .sort((a, b) => state.wrong[b.w] - state.wrong[a.w]);
  box.innerHTML = '';
  $('#wrongSub').textContent = items.length ? `${items.length} 个词待巩固` : '答错的词会攒在这里';
  if (!items.length) {
    box.innerHTML = '<p class="empty">还没有错词，继续保持 👏</p>';
    return;
  }
  items.forEach((w) => {
    const el = document.createElement('article');
    el.className = 'card';
    el.innerHTML =
      '<div class="spk">🔊</div>' +
      '<div class="body"><div class="wline"><span class="w"></span><span class="ipa"></span></div>' +
      '<div class="m"></div></div>' +
      `<span class="pill">错 ${state.wrong[w.w]} 次</span>`;
    el.querySelector('.w').textContent = w.w;
    const ipa = state.accent === 'uk' ? w.uk : w.us;
    el.querySelector('.ipa').textContent = ipa ? '/' + ipa + '/' : '';
    el.querySelector('.m').textContent = w.m;
    el.addEventListener('click', () => playWord(w));
    box.appendChild(el);
  });
}

/* ---------------- 工具 ---------------- */
function toast(msg) {
  const t = $('#toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.remove('show'), 1900);
}
