// 把 index.html 里的外链脚本内联进来，jsdom 按顺序执行 —— 行为等同真实浏览器
const { JSDOM } = require('jsdom');
const fs = require('fs');
const path = require('path');
const APP = '/Users/diting/考研英二/app';
let html = fs.readFileSync(path.join(APP, 'index.html'), 'utf8');

let order = [];
html = html.replace(/<script src="([^"]+)"><\/script>/g, (m, f) => {
  order.push(f.split('/').pop());
  let code = fs.readFileSync(path.join(APP, f), 'utf8');
  if (code.includes('</script>')) throw new Error(f + ' 里有 </script>，会截断内联');
  return `<script>${code}</script>`;
});
console.log('执行顺序:', order.join(' → '));

const dom = new JSDOM(html, {
  url: 'file://' + APP + '/index.html',
  runScripts: 'dangerously',
  pretendToBeVisual: true,
  beforeParse(window) {
    // 模拟 file:// 下 fetch 被拦 + localStorage 报错
    window.fetch = async () => { throw new Error('file:// 下 fetch 被拦'); };
    window.Audio = class { constructor(s){this.src=s;} play(){return Promise.resolve();} pause(){} };
    window.speechSynthesis = { speak(){}, cancel(){} };
    window.SpeechSynthesisUtterance = class {};
    window.HTMLElement.prototype.scrollIntoView = function () {};
    window.addEventListener('error', (e) => console.log('❌ 脚本错误:', e.message));
  },
});

setTimeout(() => {
  const d = dom.window.document;
  console.log('卡片数量:', d.querySelectorAll('#wordList .card').length);
  console.log('页条:', d.querySelectorAll('.page-chip').length, ' 天条:', d.querySelectorAll('.day-chip').length,
    ' 类别:', d.querySelectorAll('.cat-chip').length);
  console.log('标题:', d.querySelector('#dayTitle').textContent, '|', d.querySelector('#subLine').textContent);
  console.log('统计:', d.querySelector('.stats').textContent.replace(/\s+/g, ' ').trim());
  const c = d.querySelector('#wordList .card');
  console.log('第一张卡:', c ? c.textContent.replace(/\s+/g, ' ').trim().slice(0, 50) : '无');
}, 900);
