/* Học N1 — ứng dụng học & luyện thi JLPT N1. Dữ liệu tiến độ đồng bộ với GitHub. */
'use strict';
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const main = $('#main');
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const DAY = 864e5;
const todayKey = (d = new Date()) => { const z = new Date(d.getTime() - d.getTimezoneOffset() * 6e4); return z.toISOString().slice(0, 10); };
const startOfDay = (t = Date.now()) => { const d = new Date(t); d.setHours(0, 0, 0, 0); return d.getTime(); };
const shuffle = a => { a = [...a]; for (let i = a.length - 1; i > 0; i--) { const j = Math.random() * (i + 1) | 0; [a[i], a[j]] = [a[j], a[i]]; } return a; };
const pick = (a, n) => shuffle(a).slice(0, n);
const ICON = {
  speak: '<svg viewBox="0 0 24 24"><path d="M4 9v6h4l5 4V5L8 9zM16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12"/></svg>',
};

/* ---------------- state (lưu localStorage + GitHub) ---------------- */
const LS_STATE = 'n1.state.v1', LS_CFG = 'n1.github.v1';
const emptyState = () => ({ v: 1, updated: 0, srs: {}, active: {}, log: {}, exams: [], kana: {}, custom: [], settings: { newPerDay: 20, theme: 'auto' } });
let S = (() => { try { return Object.assign(emptyState(), JSON.parse(localStorage.getItem(LS_STATE)) || {}); } catch { return emptyState(); } })();
let CFG = (() => { try { return JSON.parse(localStorage.getItem(LS_CFG)) || {}; } catch { return {}; } })();
function save(dirty = true) {
  if (dirty) { S.updated = Date.now(); scheduleSync(); }
  try { localStorage.setItem(LS_STATE, JSON.stringify(S)); } catch { }
}
function logDay(field, n = 1) { const k = todayKey(); const d = S.log[k] ||= { rev: 0, neu: 0, ok: 0 }; d[field] = (d[field] || 0) + n; }
function applyTheme() { const t = S.settings.theme; if (t === 'auto') document.documentElement.removeAttribute('data-theme'); else document.documentElement.dataset.theme = t; }
applyTheme();

/* ---------------- data ---------------- */
const DATA = {};
async function load(name) {
  if (DATA[name]) return DATA[name];
  const r = await fetch(`data/${name}.json`);
  if (!r.ok) throw new Error('Không tải được dữ liệu ' + name);
  return (DATA[name] = await r.json());
}
async function allVocab() { const v = await load('vocab'); return v.flatMap(d => d.items.map(i => ({ ...i, deck: d.id }))).concat(S.custom.map(c => ({ ...c, deck: 'custom' }))); }
function customDeck() { return { id: 'custom', group: 'Của tôi', name: 'Từ tôi tự thêm', items: S.custom }; }
async function decks() { const v = await load('vocab'); return S.custom.length ? [...v, customDeck()] : v; }

/* ---------------- SRS (SM-2 rút gọn) ---------------- */
const cid = (type, id) => `${type}:${id}`;
function schedule(card, g) {
  const c = card || { ivl: 0, ease: 2.5, reps: 0, lapses: 0 };
  const now = Date.now();
  if (g === 1) { c.lapses++; c.reps = 0; c.ivl = 0; c.ease = Math.max(1.3, c.ease - 0.2); c.due = now + 10 * 6e4; }
  else {
    if (c.reps === 0) c.ivl = g === 2 ? 1 : g === 3 ? 1 : 4;
    else if (c.reps === 1) c.ivl = g === 2 ? 2 : g === 3 ? 3 : 6;
    else c.ivl = Math.max(c.ivl + 1, Math.round(c.ivl * (g === 2 ? 1.2 : g === 3 ? c.ease : c.ease * 1.3)));
    c.ease = Math.max(1.3, c.ease + (g === 2 ? -0.15 : g === 4 ? 0.15 : 0));
    c.reps++; c.due = startOfDay(now) + c.ivl * DAY + 4 * 36e5;
  }
  c.last = now; return c;
}
function nextLabel(card, g) {
  const c = schedule(card ? { ...card } : null, g);
  if (g === 1) return '10 phút';
  return c.ivl >= 30 ? Math.round(c.ivl / 30) + ' tháng' : c.ivl + ' ngày';
}
const isMastered = c => c && c.ivl >= 21;

let VIDX = null;
async function buildItem(key) {
  const [type, id] = [key.slice(0, key.indexOf(':')), key.slice(key.indexOf(':') + 1)];
  if (type === 'v') { if (!VIDX) VIDX = new Map((await allVocab()).map(x => [x.id, x])); const it = VIDX.get(id); return it && { key, type, it }; }
  if (type === 'k') { const it = (await load('kanji')).find(x => x.id === id); return it && { key, type, it }; }
  if (type === 'g') { const it = (await load('grammar')).find(x => x.id === id); return it && { key, type, it }; }
}
async function activeNewKeys() {
  const keys = [];
  const ds = await decks(), K = await load('kanji'), G = await load('grammar');
  for (const d of ds) if (S.active['v:' + d.id]) for (const i of d.items) keys.push(cid('v', i.id));
  const chs = Object.keys(S.active).filter(k => k.startsWith('k:')).map(k => +k.slice(2));
  for (const k of K) if (chs.includes(k.ch)) keys.push(cid('k', k.id));
  for (const g of G) if (S.active['g:' + g.set]) keys.push(cid('g', g.id));
  return keys.filter(k => !S.srs[k]);
}
async function queueToday() {
  const now = Date.now();
  const due = Object.entries(S.srs).filter(([, c]) => c.due <= now + 0).sort((a, b) => a[1].due - b[1].due).map(([k]) => k);
  const doneNew = (S.log[todayKey()] || {}).neu || 0;
  const room = Math.max(0, (S.settings.newPerDay | 0) - doneNew);
  const fresh = (await activeNewKeys()).slice(0, room);
  return { due, fresh };
}

/* ---------------- TTS ---------------- */
let jaVoice = null;
function initVoice() { const vs = speechSynthesis.getVoices(); jaVoice = vs.find(v => /ja[-_]JP/i.test(v.lang)) || vs.find(v => /^ja/i.test(v.lang)) || null; }
if ('speechSynthesis' in window) { initVoice(); speechSynthesis.onvoiceschanged = initVoice; }
function speak(t) {
  if (!('speechSynthesis' in window)) return toast('Trình duyệt không hỗ trợ đọc');
  speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(String(t).replace(/[／/].*$/, '')); u.lang = 'ja-JP'; if (jaVoice) u.voice = jaVoice; u.rate = .9; speechSynthesis.speak(u);
}
document.addEventListener('click', e => { const b = e.target.closest('[data-say]'); if (b) { e.preventDefault(); e.stopPropagation(); speak(b.dataset.say); } });
const sayBtn = t => `<button class="icon-btn" data-say="${esc(t)}" aria-label="Nghe phát âm">${ICON.speak}</button>`;

let toastT;
function toast(m) { const t = $('#toast'); t.textContent = m; t.classList.add('show'); clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove('show'), 2600); }

/* ---------------- GitHub sync ---------------- */
const GH = {
  ok() { return CFG.token && CFG.owner && CFG.repo; },
  api(path, opt = {}) {
    return fetch(`https://api.github.com/repos/${CFG.owner}/${CFG.repo}${path}`, {
      ...opt, headers: { Authorization: `Bearer ${CFG.token}`, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', ...(opt.body ? { 'Content-Type': 'application/json' } : {}) }
    });
  },
  b64e(s) { const b = new TextEncoder().encode(s); let r = ''; for (let i = 0; i < b.length; i += 0x8000) r += String.fromCharCode(...b.subarray(i, i + 0x8000)); return btoa(r); },
  b64d(s) { const bin = atob(s.replace(/\n/g, '')); return new TextDecoder().decode(Uint8Array.from(bin, c => c.charCodeAt(0))); },
  path() { return CFG.path || 'progress.json'; }, branch() { return CFG.branch || 'userdata'; },
  async get() {
    const r = await this.api(`/contents/${this.path()}?ref=${encodeURIComponent(this.branch())}`);
    if (r.status === 404) return { data: null, sha: null };
    if (!r.ok) throw new Error(await errText(r));
    const j = await r.json();
    let text;
    if (j.content) text = this.b64d(j.content);
    else { const b = await this.api(`/git/blobs/${j.sha}`); text = this.b64d((await b.json()).content); }
    return { data: JSON.parse(text), sha: j.sha };
  },
  async ensureBranch() {
    const br = this.branch();
    const r = await this.api(`/branches/${encodeURIComponent(br)}`);
    if (r.ok) return;
    const repo = await (await this.api('')).json();
    const base = await this.api(`/git/ref/heads/${repo.default_branch}`);
    if (!base.ok) throw new Error('Repo chưa có commit nào — hãy tạo ít nhất 1 file (ví dụ README) rồi thử lại.');
    const sha = (await base.json()).object.sha;
    const c = await this.api('/git/refs', { method: 'POST', body: JSON.stringify({ ref: `refs/heads/${br}`, sha }) });
    if (!c.ok) throw new Error(await errText(c));
  },
  async put(data, sha) {
    const body = { message: `Cập nhật tiến độ ${todayKey()}`, content: this.b64e(JSON.stringify(data)), branch: this.branch() };
    if (sha) body.sha = sha;
    const r = await this.api(`/contents/${this.path()}`, { method: 'PUT', body: JSON.stringify(body) });
    if (!r.ok) { const e = new Error(await errText(r)); e.status = r.status; throw e; }
    return (await r.json()).content.sha;
  }
};
async function errText(r) { let m = ''; try { m = (await r.json()).message; } catch { } const map = { 401: 'Token không hợp lệ hoặc đã hết hạn', 403: 'Token không có quyền ghi vào repo này', 404: 'Không tìm thấy repo (kiểm tra tên & quyền của token)', 409: 'Xung đột phiên bản', 422: 'Dữ liệu bị từ chối' }; return `${map[r.status] || 'Lỗi GitHub ' + r.status}${m ? ' — ' + m : ''}`; }
function merge(a, b) { // gộp 2 trạng thái, giữ bản mới hơn cho từng mục
  const out = emptyState();
  out.srs = { ...a.srs };
  for (const [k, c] of Object.entries(b.srs || {})) if (!out.srs[k] || (c.last || 0) > (out.srs[k].last || 0)) out.srs[k] = c;
  out.log = { ...a.log };
  for (const [d, v] of Object.entries(b.log || {})) { const o = out.log[d] || {}; out.log[d] = { rev: Math.max(o.rev || 0, v.rev || 0), neu: Math.max(o.neu || 0, v.neu || 0), ok: Math.max(o.ok || 0, v.ok || 0) }; }
  const ex = new Map(); for (const e of [...(a.exams || []), ...(b.exams || [])]) ex.set(e.id, e); out.exams = [...ex.values()].sort((x, y) => x.at - y.at);
  const newer = (b.updated || 0) > (a.updated || 0) ? b : a;
  out.active = { ...(newer.active || {}) }; out.settings = { ...a.settings, ...(newer.settings || {}) };
  out.kana = { ...a.kana }; for (const [k, v] of Object.entries(b.kana || {})) { const o = out.kana[k]; if (!o || v.n > o.n) out.kana[k] = v; }
  const cu = new Map(); for (const c of [...(a.custom || []), ...(b.custom || [])]) cu.set(c.id, c); out.custom = [...cu.values()];
  out.updated = Math.max(a.updated || 0, b.updated || 0);
  return out;
}
let syncTimer = null, syncing = false, lastSync = null, syncErr = null, remoteSha = null;
function scheduleSync() { if (!GH.ok()) return; clearTimeout(syncTimer); syncTimer = setTimeout(() => sync(), 15000); setPill(); }
async function sync(manual = false) {
  if (!GH.ok() || syncing) return; syncing = true; setPill('Đang đồng bộ…');
  try {
    await GH.ensureBranch();
    const { data, sha } = await GH.get();
    if (data) S = merge(S, data);
    S.updated = Date.now();
    remoteSha = await GH.put(S, sha);
    save(false); lastSync = Date.now(); syncErr = null;
    if (manual) toast('Đã đồng bộ với GitHub');
  } catch (e) { syncErr = e.message; if (manual) toast(e.message); }
  syncing = false; setPill(); if (manual || location.hash.startsWith('#/settings')) route();
}
function setPill(t) {
  const p = $('#syncPill'); p.className = 'sync-pill';
  if (t) { p.textContent = t; return; }
  if (!GH.ok()) { p.textContent = 'Chưa kết nối GitHub'; return; }
  if (syncErr) { p.classList.add('err'); p.textContent = 'Lỗi đồng bộ'; return; }
  p.classList.add('ok'); p.textContent = lastSync ? 'Đã lưu lên GitHub ' + new Date(lastSync).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }) : 'Đã kết nối GitHub';
}
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden' && syncTimer) { clearTimeout(syncTimer); syncTimer = null; sync(); } });

/* ---------------- router ---------------- */
const routes = [];
const on = (re, fn) => routes.push([re, fn]);
let cleanup = null;
async function route() {
  if (cleanup) { cleanup(); cleanup = null; }
  const h = location.hash.slice(1) || '/today';
  const [path, qs] = h.split('?');
  const q = Object.fromEntries(new URLSearchParams(qs || ''));
  const top = path.split('/')[1];
  $$('#nav a[data-nav]').forEach(a => a.classList.toggle('on', a.dataset.nav === ({ vocab: 'learn', kanji: 'learn', grammar: 'learn', kana: 'learn', review: 'today', read: 'exam', mock: 'exam' }[top] || top)));
  for (const [re, fn] of routes) { const m = path.match(re); if (m) { try { await fn(...m.slice(1).map(decodeURIComponent), q); } catch (e) { main.innerHTML = `<div class="status err">${esc(e.message)}</div>`; console.error(e); } main.focus({ preventScroll: true }); return; } }
  location.hash = '#/today';
}
window.addEventListener('hashchange', () => { route(); window.scrollTo(0, 0); });

/* ---------------- Hôm nay ---------------- */
function streak() {
  let n = 0, d = new Date();
  if (!(S.log[todayKey(d)]?.rev > 0)) d = new Date(d.getTime() - DAY);
  while (S.log[todayKey(d)]?.rev > 0) { n++; d = new Date(d.getTime() - DAY); }
  return n;
}
on(/^\/today$/, async () => {
  const { due, fresh } = await queueToday();
  const t = S.log[todayKey()] || { rev: 0, neu: 0, ok: 0 };
  const st = streak(), activeCount = Object.keys(S.active).filter(k => S.active[k]).length;
  const total = due.length + fresh.length;
  main.innerHTML = `
  <h1>Hôm nay</h1>
  <p class="lead">${new Date().toLocaleDateString('vi-VN', { weekday: 'long', day: 'numeric', month: 'long' })}</p>
  <div class="today">
    <section class="due-block">
      <span class="kanji-bg" aria-hidden="true">復</span>
      <div><div class="big">${total}</div><div class="lbl">thẻ cần học hôm nay</div></div>
      <div class="split"><div><b>${due.length}</b>đến hạn ôn</div><div><b>${fresh.length}</b>thẻ mới</div></div>
      ${total ? `<a class="btn" href="#/review">Bắt đầu ôn tập</a>` : activeCount ? `<span>Bạn đã xong phần hôm nay. Có thể học thêm trong mục Học.</span>` : `<a class="btn" href="#/learn">Chọn bài để học</a>`}
    </section>
    <section class="streak">
      <div class="hanko ${st ? '' : 'off'}"><div><b>${st}</b><span>ngày</span></div></div>
      <div><h3>${st ? 'Chuỗi ngày học liên tiếp' : 'Chưa có chuỗi ngày học'}</h3>
      <div class="muted small">Hôm nay: ${t.rev} lượt ôn · ${t.neu} thẻ mới · ${t.rev ? Math.round(100 * t.ok / t.rev) : 0}% nhớ</div></div>
    </section>
  </div>
  <h2>Luyện nhanh</h2>
  <div class="grid-hub">
    <a class="hub" href="#/mock"><span class="glyph">試</span><div><h3>Đề thi thử N1</h3><p>Từ vựng, kanji, ngữ pháp và đọc hiểu, có tính giờ</p></div></a>
    <a class="hub" href="#/read"><span class="glyph">読</span><div><h3>Luyện đọc hiểu</h3><p>55 bài: 短文, 中文, 長文, 比較, 検索</p></div></a>
    <a class="hub" href="#/kana"><span class="glyph">あ</span><div><h3>Hiragana / Katakana</h3><p>Trắc nghiệm nhận diện kana</p></div></a>
  </div>
  ${!GH.ok() ? `<div class="status info" style="margin-top:20px">Tiến độ đang chỉ lưu trên thiết bị này. <a href="#/settings">Kết nối GitHub</a> để lưu lên GitHub và dùng chung giữa máy tính và điện thoại.</div>` : ''}`;
});

/* ---------------- Học (hub) ---------------- */
on(/^\/learn$/, async () => {
  const [V, K, G] = await Promise.all([decks(), load('kanji'), load('grammar')]);
  const cnt = p => Object.keys(S.srs).filter(k => k.startsWith(p)).length;
  const nv = V.reduce((a, d) => a + d.items.length, 0);
  main.innerHTML = `<h1>Học</h1><p class="lead">Chọn bài và bấm “Học bài này” để đưa thẻ vào lịch ôn tập hằng ngày.</p>
  <div class="grid-hub">
    <a class="hub" href="#/vocab"><span class="glyph">語</span><div><h3>Từ vựng</h3><p>${nv} từ · đã học ${cnt('v:')}</p></div></a>
    <a class="hub" href="#/kanji"><span class="glyph">漢</span><div><h3>Kanji N1</h3><p>${K.length} chữ theo 21 chương · đã học ${cnt('k:')}</p></div></a>
    <a class="hub" href="#/grammar"><span class="glyph">文</span><div><h3>Ngữ pháp</h3><p>${G.length} mẫu câu · đã học ${cnt('g:')}</p></div></a>
    <a class="hub" href="#/kana"><span class="glyph">あ</span><div><h3>Hiragana / Katakana</h3><p>Bảng chữ và trắc nghiệm</p></div></a>
  </div>`;
});

/* ---------------- Từ vựng ---------------- */
function deckProgress(prefix, ids) { let l = 0, m = 0; for (const id of ids) { const c = S.srs[prefix + id]; if (c) { l++; if (isMastered(c)) m++; } } return { l, m, n: ids.length }; }
on(/^\/vocab$/, async (q) => {
  const ds = await decks();
  const groups = [...new Set(ds.map(d => d.group))];
  main.innerHTML = `<a class="crumb" href="#/learn">‹ Học</a><h1>Từ vựng</h1>
  <input class="search" id="vs" type="search" placeholder="Tìm từ, cách đọc hoặc nghĩa tiếng Việt…" aria-label="Tìm từ vựng">
  <div id="vres"></div>
  <div id="vlist">${groups.map(g => `<div class="groupname">${esc(g)}</div><div class="list">${ds.filter(d => d.group === g).map(d => {
    const p = deckProgress('v:', d.items.map(i => i.id));
    return `<a class="item" href="#/vocab/${d.id}"><div class="body"><div class="row"><b>${esc(d.name)}</b>${S.active['v:' + d.id] ? '<span class="tag on">Đang học</span>' : ''}</div>
    <div class="sub">${d.items.length} từ · đã học ${p.l} · thuộc ${p.m}</div><div class="bar"><i style="width:${100 * p.l / Math.max(1, p.n)}%"></i></div></div></a>`;
  }).join('')}</div>`).join('')}
  <div class="groupname">Của tôi</div><a class="item" href="#/addword"><div class="glyph">＋</div><div class="body"><b>Thêm từ của bạn</b><div class="sub">Từ bạn tự thêm cũng được lưu lên GitHub</div></div></a></div>`;
  const all = await allVocab();
  const inp = $('#vs');
  inp.addEventListener('input', () => {
    const t = inp.value.trim().toLowerCase();
    $('#vlist').classList.toggle('hidden', !!t);
    if (!t) { $('#vres').innerHTML = ''; return; }
    const r = all.filter(i => (i.w + ' ' + i.r + ' ' + i.m + ' ' + i.hv).toLowerCase().includes(t)).slice(0, 80);
    $('#vres').innerHTML = r.length ? `<div class="words">${r.map(wordRow).join('')}</div>` : '<p class="muted">Không tìm thấy từ nào.</p>';
  });
});
function wordRow(i) {
  return `<div class="word"><div><div class="w">${esc(i.w)}</div><div class="r">${esc(i.r)}${i.hv ? ' · ' + esc(i.hv) : ''}</div></div>
  <div class="m">${esc(i.m)}${(i.ex || []).slice(0, 2).map(e => `<div class="ex">${esc(e)}</div>`).join('')}</div>${sayBtn(i.r || i.w)}</div>`;
}
on(/^\/vocab\/([\w-]+)$/, async (id) => {
  const d = (await decks()).find(x => x.id === id); if (!d) throw new Error('Không tìm thấy bài');
  const act = !!S.active['v:' + id];
  const p = deckProgress('v:', d.items.map(i => i.id));
  main.innerHTML = `<a class="crumb" href="#/vocab">‹ Từ vựng</a><h1>${esc(d.name)}</h1><p class="lead">${esc(d.group)} · ${d.items.length} từ · đã học ${p.l} · thuộc ${p.m}</p>
  <div class="row" style="margin-bottom:16px">
   <button class="btn ${act ? '' : 'primary'}" id="tog">${act ? 'Ngừng học bài này' : 'Học bài này'}</button>
   <a class="btn" href="#/review?deck=v:${id}&mode=browse">Lật thẻ (không chấm)</a>
   <a class="btn" href="#/quiz?deck=${id}">Trắc nghiệm nghĩa</a></div>
  <div class="words">${d.items.map(wordRow).join('')}</div>`;
  $('#tog').onclick = () => { S.active['v:' + id] = !act; if (act) delete S.active['v:' + id]; save(); toast(act ? 'Đã bỏ khỏi lịch học' : 'Đã thêm vào lịch học hằng ngày'); route(); };
});
on(/^\/addword$/, async () => {
  main.innerHTML = `<a class="crumb" href="#/vocab">‹ Từ vựng</a><h1>Thêm từ của bạn</h1><p class="lead">Từ mới sẽ vào bài “Từ tôi tự thêm” và có thể học bằng thẻ.</p>
  <form id="f" class="panel"><div class="field"><label for="w">Từ (kanji hoặc kana)</label><input id="w" required></div>
  <div class="field"><label for="r">Cách đọc</label><input id="r"></div>
  <div class="field"><label for="m">Nghĩa tiếng Việt</label><input id="m" required></div>
  <div class="field"><label for="e">Câu ví dụ</label><input id="e"></div>
  <button class="btn primary">Thêm từ</button></form>
  ${S.custom.length ? `<h2>Đã thêm (${S.custom.length})</h2><div class="words">${S.custom.map(c => wordRow(c).replace(/<\/div>$/, '') + `<button class="btn sm ghost" data-del="${c.id}">Xoá</button></div>`).join('')}</div>` : ''}`;
  $('#f').onsubmit = e => { e.preventDefault(); S.custom.push({ id: 'c' + Date.now(), w: $('#w').value.trim(), r: $('#r').value.trim(), hv: '', m: $('#m').value.trim(), ex: $('#e').value.trim() ? [$('#e').value.trim()] : [] }); S.active['v:custom'] = true; VIDX = null; save(); toast('Đã thêm từ'); route(); };
  $$('[data-del]').forEach(b => b.onclick = () => { S.custom = S.custom.filter(c => c.id !== b.dataset.del); delete S.srs['v:' + b.dataset.del]; VIDX = null; save(); route(); });
});

/* ---------------- Kanji ---------------- */
on(/^\/kanji$/, async () => {
  const K = await load('kanji');
  const chs = [...new Set(K.map(k => k.ch))].sort((a, b) => a - b);
  main.innerHTML = `<a class="crumb" href="#/learn">‹ Học</a><h1>Kanji N1</h1><p class="lead">${K.length} chữ, mỗi chương 15 chữ kèm âm Hán Việt, âm On/Kun, ví dụ và mẹo nhớ.</p>
  <input class="search" id="ks" type="search" placeholder="Tìm chữ kanji hoặc âm Hán Việt…" aria-label="Tìm kanji"><div id="kres"></div>
  <div class="list" id="klist">${chs.map(c => { const ks = K.filter(k => k.ch === c); const p = deckProgress('k:', ks.map(k => k.id));
    return `<a class="item" href="#/kanji/${c}"><div class="glyph">${esc(ks[0].k)}</div><div class="body"><div class="row"><b>Chương ${c}</b>${S.active['k:' + c] ? '<span class="tag on">Đang học</span>' : ''}</div>
    <div class="sub jp">${ks.map(k => k.k).join(' ')}</div><div class="bar"><i style="width:${100 * p.l / p.n}%"></i></div></div></a>`; }).join('')}</div>`;
  $('#ks').oninput = e => { const t = e.target.value.trim().toLowerCase(); $('#klist').classList.toggle('hidden', !!t);
    $('#kres').innerHTML = t ? `<div class="words">${K.filter(k => (k.k + k.hv + k.on + k.kun).toLowerCase().includes(t)).slice(0, 60).map(kanjiRow).join('') || ''}</div>` : ''; };
});
const kanjiRow = k => `<div class="word"><div><div class="w" style="font-size:2rem">${esc(k.k)}</div><div class="r">${esc(k.hv)}</div></div><div class="m"><div class="small">On: <span class="jp">${esc(k.on)}</span> · Kun: <span class="jp">${esc(k.kun)}</span></div>${k.ex.slice(0, 3).map(e => `<div class="ex">${esc(e)}</div>`).join('')}</div>${sayBtn(k.ex[0] || k.k)}</div>`;
on(/^\/kanji\/(\d+)$/, async (c) => {
  c = +c; const ks = (await load('kanji')).filter(k => k.ch === c); const act = !!S.active['k:' + c];
  main.innerHTML = `<a class="crumb" href="#/kanji">‹ Kanji</a><h1>Kanji · Chương ${c}</h1><p class="lead">${ks.length} chữ</p>
  <div class="row" style="margin-bottom:16px"><button class="btn ${act ? '' : 'primary'}" id="tog">${act ? 'Ngừng học chương này' : 'Học chương này'}</button><a class="btn" href="#/review?deck=k:${c}&mode=browse">Lật thẻ</a></div>
  <div class="words">${ks.map(kanjiRow).join('')}</div>`;
  $('#tog').onclick = () => { if (act) delete S.active['k:' + c]; else S.active['k:' + c] = true; save(); toast(act ? 'Đã bỏ khỏi lịch học' : 'Đã thêm vào lịch học'); route(); };
});

/* ---------------- Ngữ pháp ---------------- */
const GSETS = { book: 'Ngữ pháp N1 (giáo trình, 22 chương)', freq: 'Ngữ pháp hay xuất hiện trong đề thi' };
on(/^\/grammar$/, async () => {
  const G = await load('grammar');
  main.innerHTML = `<a class="crumb" href="#/learn">‹ Học</a><h1>Ngữ pháp</h1>
  <input class="search" id="gs" type="search" placeholder="Tìm mẫu ngữ pháp hoặc nghĩa…" aria-label="Tìm ngữ pháp">
  ${Object.entries(GSETS).map(([s, name]) => { const gs = G.filter(g => g.set === s); const act = !!S.active['g:' + s]; const p = deckProgress('g:', gs.map(g => g.id));
    return `<div class="row" style="margin:24px 0 8px"><b>${name}</b><span class="muted small">${gs.length} mẫu · đã học ${p.l}</span><span class="spacer"></span>
    <button class="btn sm ${act ? '' : 'primary'}" data-tog="${s}">${act ? 'Ngừng học' : 'Học phần này'}</button><a class="btn sm" href="#/review?deck=g:${s}&mode=browse">Lật thẻ</a></div>
    <div class="list">${gs.map(g => `<a class="item gi" href="#/grammar/${g.id}" data-s="${esc((g.title + ' ' + g.mean).toLowerCase())}"><div class="body"><b class="jp">${esc(g.title)}</b>${S.srs['g:' + g.id] ? ` <span class="tag ${isMastered(S.srs['g:' + g.id]) ? 'on' : ''}">${isMastered(S.srs['g:' + g.id]) ? 'Đã thuộc' : 'Đang học'}</span>` : ''}<div class="sub">${esc(g.mean.split(' • ').slice(0, 2).join(' • '))}</div></div></a>`).join('')}</div>`; }).join('')}`;
  $$('[data-tog]').forEach(b => b.onclick = () => { const k = 'g:' + b.dataset.tog; if (S.active[k]) delete S.active[k]; else S.active[k] = true; save(); route(); });
  $('#gs').oninput = e => { const t = e.target.value.trim().toLowerCase(); $$('.gi').forEach(a => a.classList.toggle('hidden', !!t && !a.dataset.s.includes(t))); };
});
function grammarBody(g) {
  return `${g.form.length ? `<div class="form-box">${g.form.map(esc).join('<br>')}</div>` : ''}
  <p style="font-size:1.1rem;font-weight:500">${esc(g.mean).replace(/ • /g, '<br>')}</p>
  ${g.use.length ? `<h3>Cách dùng</h3><ul>${g.use.map(u => `<li>${esc(u)}</li>`).join('')}</ul>` : ''}
  ${g.ex.length ? `<h3>Ví dụ</h3><ol class="gram-ex">${g.ex.map(e => `<li>${esc(e)} ${sayBtn(e).replace('icon-btn', 'icon-btn inline')}</li>`).join('')}</ol>` : ''}`;
}
on(/^\/grammar\/([\w]+)$/, async (id) => {
  const G = await load('grammar'); const i = G.findIndex(g => g.id === id); const g = G[i]; if (!g) throw new Error('Không tìm thấy mẫu ngữ pháp');
  const prev = G[i - 1]?.set === g.set ? G[i - 1] : null, next = G[i + 1]?.set === g.set ? G[i + 1] : null;
  main.innerHTML = `<a class="crumb" href="#/grammar">‹ Ngữ pháp</a><h1 class="jp">${esc(g.title)}</h1><p class="muted">${GSETS[g.set]}${g.ch ? ' · Chương ' + g.ch : ''}</p>
  <div class="panel">${grammarBody(g)}</div>
  <div class="row" style="margin-top:16px">${prev ? `<a class="btn" href="#/grammar/${prev.id}">‹ <span class="jp">${esc(prev.title)}</span></a>` : ''}<span class="spacer"></span>${next ? `<a class="btn" href="#/grammar/${next.id}"><span class="jp">${esc(next.title)}</span> ›</a>` : ''}</div>`;
});

/* ---------------- Thẻ ôn tập ---------------- */
function cardHTML(x, flipped) {
  const it = x.it;
  if (x.type === 'v') {
    const long = it.w.length > 7;
    return `<span class="kind tag">Từ vựng</span><span class="say">${sayBtn(it.r || it.w)}</span>
      <div class="front ${long ? 'long' : ''}">${esc(it.w)}</div>
      ${flipped ? `<div class="back">${it.r ? `<div class="reading">${esc(it.r)}</div>` : ''}${it.hv ? `<div class="hv">${esc(it.hv)}</div>` : ''}
      <div class="meaning">${esc(it.m)}</div>${(it.ex || []).length ? `<ul class="exs">${it.ex.slice(0, 3).map(e => `<li>${esc(e)}</li>`).join('')}</ul>` : ''}</div>` : ''}`;
  }
  if (x.type === 'k') {
    return `<span class="kind tag">Kanji</span><span class="say">${sayBtn(it.ex[0] || it.k)}</span><div class="front kanji">${esc(it.k)}</div>
      ${flipped ? `<div class="back"><div class="hv" style="font-size:1.1rem">${esc(it.hv)}</div>
      <div class="small">On: <span class="jp">${esc(it.on)}</span> · Kun: <span class="jp">${esc(it.kun)}</span></div>
      <ul class="exs">${it.ex.map(e => `<li>${esc(e)}</li>`).join('')}</ul>${it.tip ? `<div class="note">💡 <span class="jp">${esc(it.tip)}</span></div>` : ''}</div>` : ''}`;
  }
  return `<span class="kind tag">Ngữ pháp</span><div class="front long">${esc(it.title)}</div>
    ${flipped ? `<div class="back"><div class="note" style="width:100%">${grammarBody(it)}</div></div>` : ''}`;
}
on(/^\/review$/, async (q) => {
  let keys;
  const browse = q.mode === 'browse';
  if (q.deck) {
    const [t, id] = q.deck.split(':');
    if (t === 'v') keys = ((await decks()).find(d => d.id === id)?.items || []).map(i => 'v:' + i.id);
    if (t === 'k') keys = (await load('kanji')).filter(k => k.ch === +id).map(k => 'k:' + k.id);
    if (t === 'g') keys = (await load('grammar')).filter(g => g.set === id).map(g => 'g:' + g.id);
    keys = shuffle(keys);
  } else { const { due, fresh } = await queueToday(); keys = [...due, ...shuffle(fresh)]; }
  const queue = [];
  for (const k of keys) { const b = await buildItem(k); if (b) queue.push(b); }
  const total = queue.length; let done = 0, flipped = false, cur = null; const seenNew = new Set();
  const back = q.deck ? (q.deck[0] === 'v' ? `#/vocab/${q.deck.slice(2)}` : q.deck[0] === 'k' ? `#/kanji/${q.deck.slice(2)}` : '#/grammar') : '#/today';
  if (!total) { main.innerHTML = `<div class="done"><div class="hanko"><div><b>済</b><span>xong</span></div></div><h1>Không còn thẻ nào</h1><p class="lead">Hãy chọn thêm bài trong mục Học.</p><a class="btn primary" href="#/learn">Đến mục Học</a></div>`; return; }
  function render() {
    if (!queue.length) {
      main.innerHTML = `<div class="done"><div class="hanko"><div><b>済</b><span>xong</span></div></div><h1>Hoàn thành!</h1><p class="lead">Bạn đã ${browse ? 'xem' : 'ôn'} ${done} thẻ.</p><a class="btn primary" href="${back}">Quay lại</a></div>`;
      if (!browse) sync(); return;
    }
    cur = queue[0]; const c = S.srs[cur.key];
    main.innerHTML = `<div class="session-top"><a class="btn sm ghost" href="${back}" aria-label="Thoát">✕</a><div class="prog"><i style="width:${100 * done / (done + queue.length)}%"></i></div><span class="small muted">${done}/${done + queue.length}</span></div>
      <div class="card" id="card">${cardHTML(cur, flipped)}</div>
      ${!flipped ? `<button class="btn primary reveal" id="rev">Hiện đáp án <span class="muted small">(Space)</span></button>` :
        browse ? `<div class="row" style="margin-top:14px"><button class="btn" id="prevB">Thẻ trước</button><span class="spacer"></span><button class="btn primary" id="nextB">Tiếp theo</button></div>` :
        `<div class="grades">${[[1, 'Quên'], [2, 'Khó'], [3, 'Nhớ'], [4, 'Dễ']].map(([g, l]) => `<button class="g${g}" data-g="${g}"><b>${l}</b><small>${nextLabel(c, g)}</small></button>`).join('')}</div>`}`;
    $('#rev')?.addEventListener('click', flip); $('#card').addEventListener('click', e => { if (!flipped && !e.target.closest('button')) flip(); });
    $$('[data-g]').forEach(b => b.onclick = () => grade(+b.dataset.g));
    $('#nextB')?.addEventListener('click', () => { queue.push(queue.shift()); done++; flipped = false; if (done >= total) queue.length = 0; render(); });
    $('#prevB')?.addEventListener('click', () => { queue.unshift(queue.pop()); done = Math.max(0, done - 1); flipped = false; render(); });
  }
  function flip() { flipped = true; render(); }
  function grade(g) {
    const isNew = !S.srs[cur.key];
    S.srs[cur.key] = schedule(S.srs[cur.key], g);
    if (isNew && !seenNew.has(cur.key)) { logDay('neu'); seenNew.add(cur.key); }
    logDay('rev'); if (g > 1) logDay('ok');
    save();
    const x = queue.shift(); flipped = false;
    if (g === 1) queue.splice(Math.min(queue.length, 3), 0, x); else done++;
    render();
  }
  const key = e => {
    if (e.target.matches('input,textarea')) return;
    if (e.code === 'Space' || e.key === 'Enter') { e.preventDefault(); if (!flipped) flip(); else if (browse) $('#nextB')?.click(); }
    if (flipped && !browse && '1234'.includes(e.key)) grade(+e.key);
    if (browse && flipped && e.key === 'ArrowRight') $('#nextB')?.click();
  };
  document.addEventListener('keydown', key); cleanup = () => document.removeEventListener('keydown', key);
  render();
});

/* ---------------- Trắc nghiệm nghĩa theo bài ---------------- */
on(/^\/quiz$/, async (q) => {
  const d = (await decks()).find(x => x.id === q.deck); if (!d) throw new Error('Không tìm thấy bài');
  const pool = d.items.filter(i => i.m); const all = (await allVocab()).filter(i => i.m);
  const qs = shuffle(pool).slice(0, 20); let i = 0, right = 0;
  function render() {
    if (i >= qs.length) { main.innerHTML = `<div class="done"><div class="hanko"><div><b>${right}</b><span>/${qs.length}</span></div></div><h1>Kết quả: ${Math.round(100 * right / qs.length)}%</h1><div class="row" style="justify-content:center"><a class="btn" href="#/vocab/${d.id}">Quay lại bài</a><button class="btn primary" id="again">Làm lại</button></div></div>`; $('#again').onclick = () => route(); return; }
    const it = qs[i]; const opts = shuffle([it, ...pick(pool.filter(x => x.m !== it.m).length >= 3 ? pool.filter(x => x.m !== it.m) : all.filter(x => x.m !== it.m), 3)]);
    main.innerHTML = `<div class="session-top"><a class="btn sm ghost" href="#/vocab/${d.id}">✕</a><div class="prog"><i style="width:${100 * i / qs.length}%"></i></div><span class="small muted">${i + 1}/${qs.length}</span></div>
    <div class="card" style="min-height:200px"><span class="say">${sayBtn(it.r || it.w)}</span><div class="front ${it.w.length > 7 ? 'long' : ''}">${esc(it.w)}</div></div>
    <div class="choices wide">${opts.map(o => `<button class="choice" data-ok="${o === it}">${esc(o.m)}</button>`).join('')}</div>`;
    $$('.choice').forEach(b => b.onclick = () => {
      const ok = b.dataset.ok === 'true'; if (ok) right++;
      $$('.choice').forEach(x => { x.disabled = true; if (x.dataset.ok === 'true') x.classList.add('right'); }); if (!ok) b.classList.add('wrong');
      $('.card').insertAdjacentHTML('beforeend', `<div class="reading">${esc(it.r)}</div>`);
      setTimeout(() => { if (!document.body.contains(b)) return; i++; render(); }, ok ? 700 : 1600);
    });
  }
  render();
});

/* ---------------- Kana ---------------- */
const KANA_ROWS = [
  ['a', 'i', 'u', 'e', 'o'], ['ka', 'ki', 'ku', 'ke', 'ko'], ['sa', 'shi', 'su', 'se', 'so'], ['ta', 'chi', 'tsu', 'te', 'to'], ['na', 'ni', 'nu', 'ne', 'no'],
  ['ha', 'hi', 'fu', 'he', 'ho'], ['ma', 'mi', 'mu', 'me', 'mo'], ['ya', '', 'yu', '', 'yo'], ['ra', 'ri', 'ru', 're', 'ro'], ['wa', '', '', '', 'wo'], ['n', '', '', '', ''],
  ['ga', 'gi', 'gu', 'ge', 'go'], ['za', 'ji', 'zu', 'ze', 'zo'], ['da', 'dji', 'dzu', 'de', 'do'], ['ba', 'bi', 'bu', 'be', 'bo'], ['pa', 'pi', 'pu', 'pe', 'po']];
const HIRA = 'あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもや　ゆ　よらりるれろわ　　　をん　　　　がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ';
const KATA = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤ　ユ　ヨラリルレロワ　　　ヲン　　　　ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポ';
function kanaList(set) { const s = set === 'kata' ? KATA : HIRA; const out = []; KANA_ROWS.flat().forEach((r, i) => { if (r && s[i] !== '　') out.push({ k: s[i], r: r.replace('dji', 'ji').replace('dzu', 'zu'), id: set + s[i] }); }); return out; }
on(/^\/kana$/, async (q) => {
  const set = q.set || 'hira', L = kanaList(set), s = set === 'kata' ? KATA : HIRA;
  main.innerHTML = `<a class="crumb" href="#/learn">‹ Học</a><h1>${set === 'kata' ? 'Katakana' : 'Hiragana'}</h1>
  <div class="row" style="margin:6px 0 18px"><div class="seg"><button class="${set === 'hira' ? 'on' : ''}" data-set="hira">Hiragana</button><button class="${set === 'kata' ? 'on' : ''}" data-set="kata">Katakana</button></div>
  <span class="spacer"></span><a class="btn primary" href="#/kanaquiz?set=${set}">Làm trắc nghiệm</a></div>
  <div class="kana-grid">${KANA_ROWS.flat().map((r, i) => { const k = s[i]; if (!r || k === '　') return '<div class="kana-cell empty"></div>'; const st = S.kana[set + k]; const acc = st ? st.ok / st.n : null;
    return `<div class="kana-cell"><b>${k}</b><small>${r.replace('dji', 'ji').replace('dzu', 'zu')}</small><div class="acc" style="${acc !== null ? `background:${acc > .85 ? 'var(--moss)' : acc > .6 ? 'var(--amber)' : 'var(--shu)'}` : ''}"></div></div>`; }).join('')}</div>
  <p class="muted small">Vạch màu dưới mỗi chữ: xanh = nhớ tốt, vàng = tạm, đỏ = hay sai.</p>`;
  $$('[data-set]').forEach(b => b.onclick = () => location.hash = '#/kana?set=' + b.dataset.set);
});
on(/^\/kanaquiz$/, async (q) => {
  const set = q.set || 'hira'; const L = kanaList(set);
  const w = L.map(x => { const st = S.kana[x.id]; return { x, w: st ? 1.5 - st.ok / st.n + 1 / (st.n + 1) : 1.6 }; });
  const qs = []; for (let n = 0; n < 20; n++) { let r = Math.random() * w.reduce((a, b) => a + b.w, 0); for (const o of w) { r -= o.w; if (r <= 0) { qs.push(o.x); break; } } }
  let i = 0, right = 0;
  function render() {
    if (i >= qs.length) { save(); main.innerHTML = `<div class="done"><div class="hanko"><div><b>${right}</b><span>/${qs.length}</span></div></div><h1>${right >= 18 ? 'Rất tốt!' : 'Tiếp tục luyện nhé'}</h1><div class="row" style="justify-content:center"><a class="btn" href="#/kana?set=${set}">Bảng chữ</a><button class="btn primary" id="again">Làm lại</button></div></div>`; $('#again').onclick = () => route(); return; }
    const it = qs[i]; const rev = Math.random() < .35;
    const opts = shuffle([it, ...pick(L.filter(x => x.r !== it.r), 3)]);
    main.innerHTML = `<div class="session-top"><a class="btn sm ghost" href="#/kana?set=${set}">✕</a><div class="prog"><i style="width:${100 * i / qs.length}%"></i></div><span class="small muted">${i + 1}/${qs.length}</span></div>
    <div class="card" style="min-height:200px"><span class="say">${sayBtn(it.k)}</span><div class="front ${rev ? 'long' : 'kanji'}">${rev ? it.r : it.k}</div></div>
    <div class="choices">${opts.map(o => `<button class="choice ${rev ? 'jp' : ''}" style="text-align:center;font-size:${rev ? '1.6rem' : '1.2rem'}" data-ok="${o === it}">${rev ? o.k : o.r}</button>`).join('')}</div>`;
    $$('.choice').forEach(b => b.onclick = () => {
      const ok = b.dataset.ok === 'true'; const st = S.kana[it.id] ||= { n: 0, ok: 0 }; st.n++; if (ok) { st.ok++; right++; }
      $$('.choice').forEach(x => { x.disabled = true; if (x.dataset.ok === 'true') x.classList.add('right'); }); if (!ok) b.classList.add('wrong');
      setTimeout(() => { if (!document.body.contains(b)) return; i++; render(); }, ok ? 500 : 1300);
    });
  }
  render();
});

/* ---------------- Đọc hiểu ---------------- */
on(/^\/exam$/, async () => {
  const R = await load('reading');
  const ex = S.exams.slice(-5).reverse();
  main.innerHTML = `<h1>Thi thử</h1><p class="lead">Luyện theo đề tổng hợp có tính giờ, hoặc từng bài đọc hiểu.</p>
  <div class="grid-hub">
    <a class="hub" href="#/mock"><span class="glyph">試</span><div><h3>Đề thi thử N1</h3><p>Kanji, từ vựng, ngữ pháp + đọc hiểu, chấm điểm theo phần</p></div></a>
    <a class="hub" href="#/read"><span class="glyph">読</span><div><h3>Luyện đọc hiểu</h3><p>${R.reduce((a, g) => a + g.sets.length, 0)} bài có đáp án</p></div></a>
  </div>
  ${ex.length ? `<h2>Lần làm gần đây</h2><div class="list">${ex.map(examRow).join('')}</div><p><a href="#/stats">Xem toàn bộ lịch sử</a></p>` : ''}`;
});
const examRow = e => `<div class="item"><div class="glyph" style="font-size:1rem;font-family:var(--ui)">${Math.round(100 * e.score / e.total)}%</div><div class="body"><b>${esc(e.title)}</b><div class="sub">${new Date(e.at).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' })} · ${e.score}/${e.total} câu${e.secs ? ' · ' + Object.entries(e.secs).map(([k, v]) => `${k} ${v[0]}/${v[1]}`).join(', ') : ''}</div></div></div>`;
on(/^\/read$/, async () => {
  const R = await load('reading');
  const best = {}; for (const e of S.exams) if (e.set) best[e.set] = Math.max(best[e.set] ?? 0, e.score / e.total);
  main.innerHTML = `<a class="crumb" href="#/exam">‹ Thi thử</a><h1>Luyện đọc hiểu</h1>
  ${R.map(g => `<div class="groupname">${esc(g.title)}</div><div class="list">${g.sets.map(s => `<a class="item" href="#/read/${s.id}"><div class="glyph" style="font-size:1rem">${esc(s.title.replace(g.label, ''))}</div><div class="body"><b class="jp">${esc(s.title)}</b><div class="sub">${s.questions.length} câu hỏi${best[s.id] !== undefined ? ` · tốt nhất ${Math.round(best[s.id] * 100)}%` : ''}</div></div>${best[s.id] === 1 ? '<span class="tag on">Đúng hết</span>' : ''}</a>`).join('')}</div>`).join('')}`;
});
function passageHTML(s) {
  if (s.imgOnly || !s.passage.length) return '';
  return `<div class="passage">${s.passage.map(p => /^[AB]$/.test(p) ? `<p class="nb">${p}</p>` : /^(（注|\(注)/.test(p) ? `<p class="note">${esc(p)}</p>` : `<p>${esc(p)}</p>`).join('')}</div>`;
}
function pagesHTML(s, open) { return `<details class="box" ${open ? 'open' : ''}><summary>${open ? 'Đề bài (bản gốc)' : 'Xem bản gốc'}</summary><div class="pages" style="margin-top:10px">${s.img.map(u => `<img loading="lazy" src="${u}" alt="Trang đề gốc">`).join('')}</div></details>`; }
function questionsHTML(qs, pfx) {
  return qs.map((q, i) => `<div class="q" data-q="${pfx}${i}"><div class="qt">問${i + 1}　${esc(q.q)}</div><div class="opts">${q.options.map((o, j) => `<button class="opt" data-a="${j + 1}"><span class="n">${j + 1}</span><span>${esc(o)}</span></button>`).join('')}</div></div>`).join('');
}
function bindOpts(root) { $$('.opt', root).forEach(b => b.onclick = () => { if (b.closest('.graded')) return; $$('.opt', b.parentElement).forEach(x => x.classList.remove('sel')); b.classList.add('sel'); }); }
function gradeQs(root, list) { // list: [{el, answer}] → số đúng
  let ok = 0;
  for (const { el, answer, explain } of list) {
    el.classList.add('graded'); const sel = $('.opt.sel', el); const a = sel ? +sel.dataset.a : 0;
    $$('.opt', el).forEach(o => { if (+o.dataset.a === answer) o.classList.add('right'); });
    if (a === answer) ok++; else if (sel) sel.classList.add('wrong');
    if (explain && !$('.explain', el)) el.insertAdjacentHTML('beforeend', `<div class="small muted explain" style="margin-top:6px">${explain}</div>`);
  }
  return ok;
}
on(/^\/read\/(\w+)$/, async (id) => {
  const R = await load('reading'); let g, s;
  for (const x of R) { const f = x.sets.find(y => y.id === id); if (f) { g = x; s = f; } }
  if (!s) throw new Error('Không tìm thấy bài đọc');
  const all = R.flatMap(x => x.sets); const ix = all.indexOf(s); const next = all[ix + 1];
  main.innerHTML = `<a class="crumb" href="#/read">‹ Đọc hiểu</a><h1 class="jp">${esc(s.title)}</h1><p class="muted">${esc(g.title)}</p>
  ${s.imgOnly ? pagesHTML(s, true) : passageHTML(s) + pagesHTML(s, false)}
  <div id="qs">${questionsHTML(s.questions, '')}</div>
  <div class="row" style="margin-top:20px"><button class="btn primary" id="chk">Chấm điểm</button><span id="res"></span><span class="spacer"></span>${next ? `<a class="btn" href="#/read/${next.id}">Bài tiếp ›</a>` : ''}</div>`;
  bindOpts(main);
  $('#chk').onclick = () => {
    const list = $$('#qs .q').map((el, i) => ({ el, answer: s.questions[i].answer }));
    const ok = gradeQs(main, list);
    $('#res').innerHTML = `<b class="${ok === list.length ? 'pass' : ''}">Đúng ${ok}/${list.length}</b>`;
    $('#chk').disabled = true;
    S.exams.push({ id: 'e' + Date.now(), at: Date.now(), title: 'Đọc hiểu ' + s.title, set: s.id, score: ok, total: list.length }); save();
  };
});

/* ---------------- Đề thi thử tổng hợp ---------------- */
function gramCore(t) { return t.replace(/^[～〜~]/, '').split(/[／/・〜～（(]/)[0].replace(/[A-Z]/g, '').trim(); }
async function buildMock(cfg) {
  const [V, K, G, R] = await Promise.all([allVocab(), load('kanji'), load('grammar'), load('reading')]);
  const secs = [];
  // 1. 漢字読み — chọn cách đọc đúng
  const kv = V.filter(v => v.r && /[一-龥]/.test(v.w) && !/[／/]/.test(v.w) && v.r.length >= 2 && v.r.length <= 8);
  secs.push({ name: '漢字読み', vi: 'Chọn cách đọc đúng của từ', items: pick(kv, cfg.n1).map(v => {
    const sim = kv.filter(x => x.r !== v.r && (x.r[0] === v.r[0] || x.r.length === v.r.length));
    const ds = pick(sim.length >= 3 ? sim : kv.filter(x => x.r !== v.r), 3).map(x => x.r);
    const o = shuffle([v.r, ...ds]); return { q: v.w, jpq: true, options: o, answer: o.indexOf(v.r) + 1, explain: `${esc(v.w)}（${esc(v.r)}）: ${esc(v.m)}` }; }) });
  // 2. 語彙 — chọn nghĩa
  const mv = V.filter(v => v.m && v.m.length < 70);
  secs.push({ name: '語彙', vi: 'Chọn nghĩa đúng của từ', items: pick(mv, cfg.n2).map(v => {
    const o = shuffle([v.m, ...pick(mv.filter(x => x.m !== v.m), 3).map(x => x.m)]); return { q: v.w, jpq: true, vi: true, options: o, answer: o.indexOf(v.m) + 1, explain: `${esc(v.w)}（${esc(v.r)}）` }; }) });
  // 3. 文法 — điền mẫu ngữ pháp vào câu
  const cands = [];
  for (const g of G) { const core = gramCore(g.title); if (core.length < 2) continue; const ex = g.ex.find(e => e.includes(core)); if (ex) cands.push({ g, core, ex }); }
  const cores = [...new Set(cands.map(c => c.core))];
  secs.push({ name: '文法', vi: 'Chọn mẫu ngữ pháp điền vào ( )', items: pick(cands, cfg.n3).map(c => {
    const o = shuffle([c.core, ...pick(cores.filter(x => x !== c.core && !x.includes(c.core) && !c.core.includes(x)), 3)]);
    return { q: c.ex.replace(c.core, '（　　）'), jpq: true, options: o, answer: o.indexOf(c.core) + 1, explain: `<span class="jp">${esc(c.g.title)}</span>: ${esc(c.g.mean)}` }; }) });
  // 4. 読解
  const sets = [];
  const want = [['tanbun', cfg.r1], ['chuubun', cfg.r2], ['choubun', cfg.r3], ['hikaku', cfg.r4], ['kensaku', cfg.r5]];
  for (const [gid, n] of want) sets.push(...pick(R.find(x => x.id === gid).sets, n));
  return { secs, sets };
}
on(/^\/mock$/, async () => {
  main.innerHTML = `<a class="crumb" href="#/exam">‹ Thi thử</a><h1>Đề thi thử N1</h1><p class="lead">Mỗi lần tạo đề sẽ chọn ngẫu nhiên câu hỏi từ kho dữ liệu của bạn. Kết quả được lưu vào lịch sử.</p>
  <div class="panel">
   <div class="seg" id="preset" style="margin-bottom:16px"><button data-p="short" class="on">Ngắn · 30 phút</button><button data-p="full">Đầy đủ · 110 phút</button></div>
   <p class="small muted" id="pdesc"></p>
   <button class="btn primary" id="go">Bắt đầu làm bài</button></div>`;
  const P = { short: { n1: 6, n2: 7, n3: 10, r1: 2, r2: 1, r3: 0, r4: 1, r5: 0, min: 30 }, full: { n1: 6, n2: 14, n3: 20, r1: 4, r2: 3, r3: 1, r4: 1, r5: 1, min: 110 } };
  let p = 'short';
  const desc = () => { const c = P[p]; $('#pdesc').textContent = `${c.n1} câu đọc kanji · ${c.n2} câu từ vựng · ${c.n3} câu ngữ pháp · ${c.r1 + c.r2 + c.r3 + c.r4 + c.r5} bài đọc hiểu · ${c.min} phút`; };
  desc(); $$('#preset button').forEach(b => b.onclick = () => { p = b.dataset.p; $$('#preset button').forEach(x => x.classList.toggle('on', x === b)); desc(); });
  $('#go').onclick = async () => { const m = await buildMock(P[p]); runMock(m, P[p].min, p); };
});
function runMock(m, minutes, kind) {
  let left = minutes * 60, finished = false;
  const qhtml = (it, k) => `<div class="q" data-k="${k}"><div class="qt ${it.vi ? '' : ''}">${k.split('-')[1] * 1 + 1}. ${esc(it.q)}</div><div class="opts" style="${it.options.every(o => o.length < 14) ? 'grid-template-columns:repeat(auto-fit,minmax(140px,1fr))' : ''}">${it.options.map((o, j) => `<button class="opt" data-a="${j + 1}" style="${it.vi ? 'font-family:var(--ui)' : ''}"><span class="n">${j + 1}</span><span>${esc(o)}</span></button>`).join('')}</div></div>`;
  main.innerHTML = `<div class="timer"><span class="clock" id="clk"></span><span class="muted small">còn lại</span><span class="spacer"></span><button class="btn sm primary" id="sub">Nộp bài</button></div>
  <h1>Đề thi thử N1</h1>
  ${m.secs.map((s, si) => `<div class="sec-title">問題${si + 1}　${s.name} <span class="muted small" style="font-weight:400">— ${s.vi}</span></div>${s.items.map((it, i) => qhtml(it, si + '-' + i)).join('')}`).join('')}
  ${m.sets.length ? `<div class="sec-title">読解 <span class="muted small" style="font-weight:400">— Đọc hiểu</span></div>` + m.sets.map((s, si) => `<h2 class="jp">${esc(s.title)}</h2>${s.imgOnly ? pagesHTML(s, true) : passageHTML(s)}<div data-set="${si}">${questionsHTML(s.questions, 'r' + si + '-')}</div>`).join('') : ''}
  <div id="result"></div><div style="margin-top:20px"><button class="btn primary" id="sub2">Nộp bài</button></div>`;
  bindOpts(main);
  const fmt = s => `${String(s / 60 | 0).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
  const tick = () => { if (finished) return; left--; $('#clk').textContent = fmt(Math.max(0, left)); $('#clk').classList.toggle('low', left < 300); if (left <= 0) submit(); };
  $('#clk').textContent = fmt(left); const iv = setInterval(tick, 1000); cleanup = () => clearInterval(iv);
  const submit = () => {
    if (finished) return; finished = true; clearInterval(iv);
    const secs = {}; let score = 0, total = 0;
    m.secs.forEach((s, si) => { const list = s.items.map((it, i) => ({ el: $(`[data-k="${si}-${i}"]`), answer: it.answer, explain: it.explain })); const ok = gradeQs(main, list); secs[s.name] = [ok, list.length]; score += ok; total += list.length; });
    if (m.sets.length) { let ok = 0, n = 0; m.sets.forEach((s, si) => { const list = $$(`[data-set="${si}"] .q`).map((el, i) => ({ el, answer: s.questions[i].answer })); ok += gradeQs(main, list); n += list.length; }); secs['読解'] = [ok, n]; score += ok; total += n; }
    const pct = Math.round(100 * score / total), used = minutes * 60 - Math.max(0, left);
    S.exams.push({ id: 'e' + Date.now(), at: Date.now(), title: `Đề thi thử (${kind === 'full' ? 'đầy đủ' : 'ngắn'})`, score, total, secs, time: used }); save(); sync();
    $('#result').innerHTML = `<h2>Kết quả</h2><div class="score"><div><b class="${pct >= 60 ? 'pass' : 'fail'}">${pct}%</b>${score}/${total} câu · ${fmt(used)}</div>${Object.entries(secs).map(([k, v]) => `<div><b>${v[0]}/${v[1]}</b><span class="jp">${k}</span></div>`).join('')}</div><p class="muted small">Đáp án đúng được tô xanh, câu chọn sai tô đỏ. Cuộn lên để xem lại từng câu.</p><div class="row"><a class="btn primary" href="#/mock">Làm đề mới</a><a class="btn" href="#/stats">Xem tiến độ</a></div>`;
    $$('#sub,#sub2').forEach(b => b.disabled = true);
    $('#result').scrollIntoView({ behavior: 'smooth' });
  };
  $('#sub').onclick = $('#sub2').onclick = () => { const un = $$('.q').filter(q => !$('.opt.sel', q)).length; if (!un || confirm(`Còn ${un} câu chưa trả lời. Nộp bài?`)) submit(); };
}

/* ---------------- Tiến độ ---------------- */
on(/^\/stats$/, async () => {
  const [V, K, G] = await Promise.all([decks(), load('kanji'), load('grammar')]);
  const by = p => { const e = Object.entries(S.srs).filter(([k]) => k.startsWith(p)); return { l: e.length, m: e.filter(([, c]) => isMastered(c)).length }; };
  const v = by('v:'), k = by('k:'), g = by('g:');
  const nv = V.reduce((a, d) => a + d.items.length, 0);
  const totalRev = Object.values(S.log).reduce((a, d) => a + (d.rev || 0), 0), totalOk = Object.values(S.log).reduce((a, d) => a + (d.ok || 0), 0);
  // heatmap 18 tuần
  const weeks = 18, cell = 13, gap = 3; const end = new Date(); end.setHours(0, 0, 0, 0);
  const start = new Date(end.getTime() - ((weeks - 1) * 7 + ((end.getDay() + 6) % 7)) * DAY);
  let rects = ''; const mx = Math.max(10, ...Object.values(S.log).map(d => d.rev || 0));
  for (let d = new Date(start), i = 0; d <= end; d = new Date(d.getTime() + DAY), i++) {
    const n = S.log[todayKey(d)]?.rev || 0; const lvl = n ? Math.min(4, Math.ceil(4 * n / mx)) : 0;
    const col = ['var(--surface-2)', '#b9d2a8', '#8cb873', '#5f9446', 'var(--moss)'][lvl];
    rects += `<rect x="${(i / 7 | 0) * (cell + gap)}" y="${(i % 7) * (cell + gap)}" width="${cell}" height="${cell}" rx="2" fill="${col}"><title>${todayKey(d)}: ${n} lượt ôn</title></rect>`;
  }
  // biểu đồ điểm thi
  const ex = S.exams.filter(e => !e.set).slice(-15);
  const W = 560, H = 160;
  const pts = ex.map((e, i) => [20 + i * (W - 40) / Math.max(1, ex.length - 1), H - 20 - (H - 40) * e.score / e.total]);
  const chart = ex.length ? `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Điểm các đề thi thử">
    ${[0, 50, 100].map(p => `<line x1="20" x2="${W - 20}" y1="${H - 20 - (H - 40) * p / 100}" y2="${H - 20 - (H - 40) * p / 100}" stroke="var(--line)" stroke-dasharray="${p === 0 ? '' : '3 4'}"/><text x="0" y="${H - 16 - (H - 40) * p / 100}" font-size="10" fill="var(--ink-3)">${p}</text>`).join('')}
    <polyline fill="none" stroke="var(--indigo-2)" stroke-width="2" points="${pts.map(p => p.join(',')).join(' ')}"/>
    ${pts.map((p, i) => `<circle cx="${p[0]}" cy="${p[1]}" r="4" fill="var(--indigo-2)"><title>${esc(ex[i].title)}: ${Math.round(100 * ex[i].score / ex[i].total)}%</title></circle>`).join('')}</svg>` : '<p class="muted">Chưa có đề thi thử nào. <a href="#/mock">Làm đề đầu tiên</a></p>';
  main.innerHTML = `<h1>Tiến độ</h1><p class="lead">Chuỗi ${streak()} ngày · tổng ${totalRev} lượt ôn · nhớ ${totalRev ? Math.round(100 * totalOk / totalRev) : 0}%</p>
  <div class="stat-grid">
   <div class="stat"><b>${v.l}<span class="muted small">/${nv}</span></b><span>Từ vựng đã học · thuộc ${v.m}</span><div class="bar"><i style="width:${100 * v.l / nv}%"></i></div></div>
   <div class="stat"><b>${k.l}<span class="muted small">/${K.length}</span></b><span>Kanji đã học · thuộc ${k.m}</span><div class="bar"><i style="width:${100 * k.l / K.length}%"></i></div></div>
   <div class="stat"><b>${g.l}<span class="muted small">/${G.length}</span></b><span>Ngữ pháp đã học · thuộc ${g.m}</span><div class="bar"><i style="width:${100 * g.l / G.length}%"></i></div></div>
   <div class="stat"><b>${S.exams.length}</b><span>Lần làm bài thi / đọc hiểu</span></div>
  </div>
  <p class="muted small">“Thuộc” = thẻ có khoảng ôn từ 21 ngày trở lên.</p>
  <h2>Lịch học 18 tuần</h2><div class="panel heat"><svg width="${weeks * (cell + gap)}" height="${7 * (cell + gap)}">${rects}</svg>
  <div class="legend">Ít ${[0, 1, 2, 3, 4].map(l => `<svg width="12" height="12"><rect width="12" height="12" rx="2" fill="${['var(--surface-2)', '#b9d2a8', '#8cb873', '#5f9446', 'var(--moss)'][l]}"/></svg>`).join('')} Nhiều</div></div>
  <h2>Điểm đề thi thử</h2><div class="panel">${chart}</div>
  ${S.exams.length ? `<h2>Lịch sử làm bài</h2><div class="list">${S.exams.slice().reverse().slice(0, 30).map(examRow).join('')}</div>` : ''}`;
});

/* ---------------- Cài đặt & đồng bộ ---------------- */
on(/^\/settings$/, async () => {
  main.innerHTML = `<h1>Đồng bộ & cài đặt</h1><p class="lead">Tiến độ học (thẻ đã ôn, điểm thi, từ tự thêm) được lưu thành file JSON trong repo GitHub của bạn, nên dùng được trên cả máy tính và điện thoại.</p>
  ${syncErr ? `<div class="status err">${esc(syncErr)}</div>` : GH.ok() && lastSync ? `<div class="status ok">Đã đồng bộ lúc ${new Date(lastSync).toLocaleString('vi-VN')}</div>` : ''}
  <form id="gf" class="panel">
   <div class="field"><label for="owner">Tài khoản GitHub</label><input id="owner" value="${esc(CFG.owner || 'hungnxmt-collab')}" required autocomplete="off"></div>
   <div class="field"><label for="repo">Repo lưu dữ liệu</label><input id="repo" value="${esc(CFG.repo || 'hoc-tieng-nhat')}" required autocomplete="off"><span class="hint">Có thể là repo của ứng dụng, hoặc một repo riêng tư khác nếu bạn muốn giữ kín tiến độ.</span></div>
   <div class="row"><div class="field" style="flex:1;min-width:140px"><label for="branch">Nhánh</label><input id="branch" value="${esc(CFG.branch || 'userdata')}"></div>
   <div class="field" style="flex:2;min-width:180px"><label for="path">Đường dẫn file</label><input id="path" value="${esc(CFG.path || 'progress.json')}"></div></div>
   <div class="field"><label for="token">Personal access token</label><input id="token" type="password" value="${esc(CFG.token || '')}" autocomplete="off" placeholder="github_pat_…">
   <span class="hint">Tạo tại GitHub → Settings → Developer settings → Fine-grained tokens. Chỉ chọn repo trên, quyền <b>Contents: Read and write</b>. Token chỉ lưu trên thiết bị này.</span></div>
   <div class="row"><button class="btn primary">Lưu & đồng bộ</button>${GH.ok() ? '<button type="button" class="btn" id="now">Đồng bộ ngay</button><button type="button" class="btn ghost" id="out">Ngắt kết nối</button>' : ''}</div>
  </form>
  <h2>Học tập</h2>
  <div class="panel"><div class="field"><label for="npd">Số thẻ mới mỗi ngày</label><input id="npd" type="number" min="0" max="200" value="${S.settings.newPerDay}"></div>
   <div class="field"><label>Giao diện</label><div class="seg" id="theme">${[['auto', 'Theo hệ thống'], ['light', 'Sáng'], ['dark', 'Tối']].map(([k, l]) => `<button type="button" data-t="${k}" class="${S.settings.theme === k ? 'on' : ''}">${l}</button>`).join('')}</div></div></div>
  <h2>Sao lưu thủ công</h2>
  <div class="row"><button class="btn" id="exp">Tải file tiến độ (.json)</button><label class="btn">Nhập từ file<input type="file" id="imp" accept="application/json" class="hidden"></label></div>
  <h2>Cài lên màn hình chính</h2><p class="muted small">Trên điện thoại: mở trang này bằng Safari (iPhone) hoặc Chrome (Android) → Chia sẻ / Menu → “Thêm vào màn hình chính”. Ứng dụng chạy được cả khi không có mạng; tiến độ sẽ đồng bộ khi có mạng trở lại.</p>`;
  $('#gf').onsubmit = async e => { e.preventDefault(); CFG = { owner: $('#owner').value.trim(), repo: $('#repo').value.trim(), branch: $('#branch').value.trim() || 'userdata', path: $('#path').value.trim() || 'progress.json', token: $('#token').value.trim() }; localStorage.setItem(LS_CFG, JSON.stringify(CFG)); syncErr = null; await sync(true); };
  $('#now')?.addEventListener('click', () => sync(true));
  $('#out')?.addEventListener('click', () => { CFG = {}; localStorage.removeItem(LS_CFG); setPill(); route(); });
  $('#npd').onchange = e => { S.settings.newPerDay = Math.max(0, Math.min(200, +e.target.value || 0)); save(); toast('Đã lưu'); };
  $$('#theme button').forEach(b => b.onclick = () => { S.settings.theme = b.dataset.t; applyTheme(); save(); route(); });
  $('#exp').onclick = () => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(S, null, 1)], { type: 'application/json' })); a.download = `tien-do-n1-${todayKey()}.json`; a.click(); };
  $('#imp').onchange = async e => { try { const d = JSON.parse(await e.target.files[0].text()); S = merge(S, d); save(); toast('Đã nhập dữ liệu'); route(); } catch { toast('File không hợp lệ'); } };
});

/* ---------------- khởi động ---------------- */
setPill();
route();
if (GH.ok()) sync();
if ('serviceWorker' in navigator && location.protocol === 'https:') navigator.serviceWorker.register('sw.js');
