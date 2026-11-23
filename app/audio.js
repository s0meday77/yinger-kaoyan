/* 发音：拿手机里的缓存录音播放，拿不到就用系统语音兜底。
 *
 * 为什么不用 new Audio('data/audio/xx.mp3') 直接播：
 * iOS 播放媒体时会发 Range（分段）请求，Service Worker 手上只有一份完整的
 * 缓存响应，回给它就对不上，结果就是——离线时除了碰巧播过的词，其余全哑。
 * 所以统一改成 fetch 取整段 → blob → 本地 URL → 播放，完全绕开分段请求。
 */

let audioEl = null;

/** 这个词该用哪份录音：新录的三套音色优先，没有就退回有道的旧录音 */
function audioPath(w) {
  const v = w.v;
  if (v) {
    if (v[state.voice]) return v[state.voice];
    // 选中的那一套缺了，随便挑一套有的，总比没声强
    const anyKey = Object.keys(v)[0];
    if (anyKey) return v[anyKey];
  }
  return state.accent === 'uk' ? w.uk_audio : w.us_audio;
}

/** 文件名规则：和 tools/tts_voices.py 的 safe_name 必须一模一样 */
function safeName(s) {
  return String(s).toLowerCase().replace(/ /g, '_').replace(/\//g, '_');
}

const VOICE_KEYS = ['m', 'f', 'c'];

/** 词组录音的路径：audio/ph/<音色>/<单词>_<第几条>.mp3 */
function phrasePath(w, idx, voice) {
  return 'audio/ph/' + (voice || state.voice) + '/' + safeName(w.w) + '_' + idx + '.mp3';
}

/** 全部发音文件的路径（单词 + 词组，三个音色），打包时一次性灌进手机缓存 */
function audioUrls() {
  const out = [];
  state.words.forEach((w) => {
    if (w.v) {
      Object.keys(w.v).forEach((k) => out.push('data/' + w.v[k]));
    } else {
      if (w.us_audio) out.push('data/' + w.us_audio);
      if (w.uk_audio) out.push('data/' + w.uk_audio);
    }
    let i = 0;
    (w.sb || []).forEach((b) => {
      if (b.k !== '例') return;
      if (b.p) VOICE_KEYS.forEach((k) => out.push('data/' + phrasePath(w, i, k)));
      i += 1;
    });
  });
  return out;
}

/** 播一条词组；录音不在就用系统语音兜底 */
async function playPhrase(w, idx, text, done) {
  stopAudio();
  const file = 'data/' + phrasePath(w, idx);
  if (location.protocol === 'file:') { playSrc(file, Math.max(1, state.repeats | 0), done); return; }
  let url = null;
  try {
    const res = await fetch(file, { cache: 'force-cache' });
    if (!res || !res.ok) throw new Error('没缓存');
    const blob = await res.blob();
    if (blob.size < 500) throw new Error('音频不完整');
    url = URL.createObjectURL(blob);
  } catch (e) {
    // 还没录到这个音色，先用系统语音顶着；`place/put …` 读 or 别读 slash
    speakTTS(text.replace(/\s*\/\s*/g, ' or '), done);
    return;
  }
  playSrc(url, Math.max(1, state.repeats | 0), done, () => URL.revokeObjectURL(url));
}

/** 播放单词；repeats 遍数由设置决定，最后一遍播完回调 done */
async function playWord(w, done) {
  stopAudio();
  const rel = audioPath(w);
  if (!rel) { speakTTS(w.w, done); return; }
  const file = 'data/' + rel;
  const total = Math.max(1, state.repeats | 0);

  // 双击本地文件打开时 fetch 会被拦，只能拿路径直接播
  if (location.protocol === 'file:') { playSrc(file, total, done); return; }

  let url = null;
  try {
    // force-cache：优先用手机里存的那份，飞行模式下也能取到
    const res = await fetch(file, { cache: 'force-cache' });
    if (!res || !res.ok) throw new Error('没缓存');
    const blob = await res.blob();
    if (blob.size < 500) throw new Error('音频不完整');
    url = URL.createObjectURL(blob);
  } catch (e) {
    // 录音不在手机里（没打包 / 被系统清理），退回系统语音，至少还有声
    if (window.__AUDIO_MISS__ !== w.w) {
      window.__AUDIO_MISS__ = w.w;
      if (typeof toast === 'function') toast('这段录音不在手机里，先用系统语音代替');
    }
    speakTTS(w.w, done);
    return;
  }
  playSrc(url, total, done, () => URL.revokeObjectURL(url));
}

/** 真正播放：重复 total 遍，结束时清理 blob */
function playSrc(src, total, done, cleanup) {
  let left = total;
  const finish = () => {
    if (cleanup) cleanup();
    if (done) done();
  };
  const once = () => {
    audioEl = new Audio(src);
    audioEl.playbackRate = state.rate;
    audioEl.onended = () => {
      left -= 1;
      if (left > 0) setTimeout(once, 380);
      else finish();
    };
    audioEl.play().catch(() => { left = 0; finish(); });
  };
  once();
}

function speakTTS(text, done) {
  const synth = window.speechSynthesis;
  if (!synth) { if (done) done(); return; }
  let left = Math.max(1, state.repeats | 0);
  const say = () => {
    const u = new SpeechSynthesisUtterance(text);
    u.lang = state.accent === 'uk' ? 'en-GB' : 'en-US';
    u.rate = state.rate;
    u.onend = () => {
      left -= 1;
      if (left > 0) setTimeout(say, 380);
      else if (done) done();
    };
    u.onerror = () => { left = 0; if (done) done(); };
    synth.speak(u);
  };
  synth.cancel();
  say();
}

function stopAudio() {
  if (audioEl) { audioEl.pause(); audioEl = null; }
  if (window.speechSynthesis) window.speechSynthesis.cancel();
}
