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
const emptyState = () => ({ v: 1, updated: 0, srs: {}, active: {}, log: {}, exams: [], kana: {}, custom: [], plan: {}, settings: { newPerDay: 20, theme: 'auto', planStart: '' } });
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
  const r = await fetch(`data/${name}.json`, { cache: 'no-cache' });
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
document.addEventListener('click', e => { const b = e.target.closest('[data-say]'); if (b) { e.preventDefault(); e.stopPropagation(); speak(b.dataset.say); $$('.say-t.on').forEach(x => x.classList.remove('on')); if (b.classList.contains('say-t')) { b.classList.add('on'); setTimeout(() => b.classList.remove('on'), 1200); } } });
// Âm thanh gốc (file nghe từ vựng): au = [phần, đầu, cuối, đầu-từ, cuối-từ]
const AU = new Audio(); let auEnd = 0; AU.preload = 'none';
AU.addEventListener('timeupdate', () => { if (auEnd && AU.currentTime >= auEnd) { AU.pause(); auEnd = 0; } });
function playClip(part, a, b) {
  const src = typeof part === 'string' ? part : `audio/vocab/part${String(part).padStart(2, '0')}.mp3`;
  speechSynthesis?.cancel?.(); auEnd = b;
  const go = () => { AU.currentTime = a; AU.play().catch(() => { }); };
  if (!AU.src.endsWith(src)) { AU.src = src; AU.addEventListener('loadedmetadata', go, { once: true }); AU.load(); } else go();
}
document.addEventListener('click', e => { const f = e.target.closest('[data-src]'); if (f) { e.preventDefault(); e.stopPropagation(); playClip(f.dataset.src, 0, 9999); return; } const b = e.target.closest('[data-au]'); if (b) { e.preventDefault(); e.stopPropagation(); const [p, x, y] = b.dataset.au.split(',').map(Number); playClip(p, x, y); } });
const vSay = it => it.au3 ? `<span class="au-btns"><button class="icon-btn" data-src="${it.au3}" aria-label="Nghe từ và câu ví dụ (audio sách)" title="Nghe từ + câu ví dụ (audio sách)">${ICON.speak}</button></span>` : it.au ? `<span class="au-btns">${it.au[3] != null ? `<button class="icon-btn" data-au="${it.au[0]},${it.au[3]},${it.au[4]}" aria-label="Nghe từ (giọng người đọc)" title="Nghe từ (giọng người đọc)">${ICON.speak}</button>` : sayBtn(it.r || it.w)}<button class="icon-btn ex-au" data-au="${it.au[0]},${it.au[1]},${it.au[2]}" aria-label="Nghe từ và câu ví dụ" title="Nghe từ + câu ví dụ">例</button></span>` : sayBtn(it.r || it.w);
// Chữ bấm để nghe: mỗi cụm là một vùng bấm riêng
const sayT = (shown, spoken) => `<span class="say-t" data-say="${esc(String(spoken ?? shown).replace(/[-‐.]/g, '').replace(/[()（）]/g, ''))}" title="Bấm để nghe">${esc(shown)}</span>`;
const sayList = (txt) => String(txt || '').split(/[、,，・\s]+/).filter(x => x.trim()).map(x => sayT(x)).join('<span class="muted">、</span>');
const sayAllBtn = parts => `<button class="icon-btn" data-say="${esc(parts.filter(Boolean).map(p => String(p).replace(/[-‐.()（）]/g, '')).join('。'))}" aria-label="Đọc tất cả" title="Đọc tất cả">${ICON.speak}</button>`;
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
  out.plan = { ...(a.plan || {}) }; for (const [k, v] of Object.entries(b.plan || {})) if (!out.plan[k] || (v.t || 0) > (out.plan[k].t || 0)) out.plan[k] = v;
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
let route = async function () {
  if (cleanup) { cleanup(); cleanup = null; }
  const h = location.hash.slice(1) || '/today';
  const [path, qs] = h.split('?');
  const q = Object.fromEntries(new URLSearchParams(qs || ''));
  const top = path.split('/')[1];
  $$('#nav a[data-nav]').forEach(a => a.classList.toggle('on', a.dataset.nav === ({ skill: 'learn', vocab: 'learn', kanji: 'learn', grammar: 'learn', kana: 'learn', plan: 'learn', keigo: 'learn', audio: 'learn', try: 'learn', read: 'learn', ldrill: 'learn', drill: 'learn', addword: 'learn', quiz: 'learn', tests: 'exam', test: 'exam', review: 'today', mock: 'exam' }[top] || top)));
  for (const [re, fn] of routes) { const m = path.match(re); if (m) { try { await fn(...m.slice(1).map(decodeURIComponent), q); } catch (e) { main.innerHTML = `<div class="status err">${esc(e.message)}</div>`; console.error(e); } main.focus({ preventScroll: true }); return; } }
  location.hash = '#/today';
}
document.addEventListener('click', e => { const w = e.target.closest('.crop-wrap'); if (w) w.classList.toggle('zoom'); });
window.addEventListener('hashchange', () => { route(); window.scrollTo(0, 0); });


/* ---------------- Số người đang truy cập ----------------
   Không có máy chủ riêng: mỗi tab gửi "nhịp tim" qua một MQTT broker công cộng (WebSocket),
   đếm số mã ngẫu nhiên đã gửi nhịp tim trong 75 giây gần nhất. Không gửi bất kỳ thông tin cá nhân nào. */
const PRES = {
  url: 'wss://broker.emqx.io:8084/mqtt', base: 'hungnxmt/hoc-tieng-nhat/online/v1',
  id: Math.random().toString(36).slice(2, 10), seen: new Map(), n: 0, ws: null, retry: 2000, beat: null, ping: null,
};
const mqtt = {
  str(s) { const b = new TextEncoder().encode(s); return [b.length >> 8, b.length & 255, ...b]; },
  pkt(type, body) {
    const len = []; let x = body.length;
    do { let d = x % 128; x = Math.floor(x / 128); if (x > 0) d |= 128; len.push(d); } while (x > 0);
    return new Uint8Array([type, ...len, ...body]);
  },
  connect(cid, willTopic, willMsg, keep) {
    return this.pkt(0x10, [...this.str('MQTT'), 4, 0x02 | 0x04, keep >> 8, keep & 255, ...this.str(cid), ...this.str(willTopic), ...this.str(willMsg)]);
  },
  subscribe(topic) { return this.pkt(0x82, [0, 1, ...this.str(topic), 0]); },
  publish(topic, msg) { return this.pkt(0x30, [...this.str(topic), ...new TextEncoder().encode(msg)]); },
  // tách các gói tin trong buffer; trả về [{type, topic, msg}], phần dư giữ lại
  parse(buf) {
    const out = []; let i = 0;
    while (i + 2 <= buf.length) {
      let mul = 1, len = 0, j = i + 1, d;
      do { if (j >= buf.length) return [out, buf.slice(i)]; d = buf[j++]; len += (d & 127) * mul; mul *= 128; } while (d & 128);
      if (j + len > buf.length) break;
      const type = buf[i] >> 4, body = buf.subarray(j, j + len);
      if (type === 3) {
        const tl = (body[0] << 8) | body[1], qos = (buf[i] >> 1) & 3, off = 2 + tl + (qos ? 2 : 0);
        out.push({ type, topic: new TextDecoder().decode(body.subarray(2, 2 + tl)), msg: new TextDecoder().decode(body.subarray(off)) });
      } else out.push({ type });
      i = j + len;
    }
    return [out, buf.slice(i)];
  },
};
function presCount() {
  const now = Date.now();
  for (const [k, t] of PRES.seen) if (now - t > 75000) PRES.seen.delete(k);
  PRES.n = PRES.seen.size + (PRES.seen.has(PRES.id) ? 0 : 1);
  presShow();
}
function presShow() {
  const ok = PRES.ws && PRES.ws.readyState === 1;
  $$('.online-pill').forEach(el => { el.hidden = !ok; el.innerHTML = `<i></i>${PRES.n} người đang học`; });
}
function presConnect() {
  if (!('WebSocket' in window) || location.protocol === 'file:') return;
  let ws, rest = new Uint8Array(0);
  try { ws = new WebSocket(PRES.url, ['mqtt']); } catch { return; }
  ws.binaryType = 'arraybuffer'; PRES.ws = ws;
  const me = `${PRES.base}/u/${PRES.id}`, send = p => { if (ws.readyState === 1) ws.send(p); };
  const beat = () => send(mqtt.publish(me, '1'));
  ws.onopen = () => send(mqtt.connect('n1-' + PRES.id, me, '0', 60));
  ws.onmessage = ev => {
    const a = new Uint8Array(ev.data), b = new Uint8Array(rest.length + a.length); b.set(rest); b.set(a, rest.length);
    const [pk, r] = mqtt.parse(b); rest = r;
    for (const p of pk) {
      if (p.type === 2) {                       // CONNACK
        PRES.retry = 2000;
        send(mqtt.subscribe(PRES.base + '/#'));
        PRES.seen.set(PRES.id, Date.now()); beat(); send(mqtt.publish(PRES.base + '/hello', PRES.id));
        clearInterval(PRES.beat); PRES.beat = setInterval(() => { beat(); presCount(); }, 25000);
        clearInterval(PRES.ping); PRES.ping = setInterval(() => send(new Uint8Array([0xC0, 0])), 45000);
        presCount();
      } else if (p.type === 3) {
        if (p.topic === PRES.base + '/hello') { if (p.msg !== PRES.id) setTimeout(beat, Math.random() * 1500); continue; }
        const m = p.topic.match(/\/u\/([a-z0-9]{1,16})$/);
        if (!m) continue;
        if (p.msg === '1') PRES.seen.set(m[1], Date.now()); else PRES.seen.delete(m[1]);
        presCount();
      }
    }
  };
  ws.onclose = () => {
    clearInterval(PRES.beat); clearInterval(PRES.ping); PRES.seen.clear(); presShow();
    if (PRES.ws === ws) { PRES.ws = null; setTimeout(presConnect, PRES.retry); PRES.retry = Math.min(PRES.retry * 2, 120000); }
  };
  ws.onerror = () => {};
}
window.addEventListener('pagehide', () => { const ws = PRES.ws; if (ws && ws.readyState === 1) { ws.send(mqtt.publish(`${PRES.base}/u/${PRES.id}`, '0')); ws.send(new Uint8Array([0xE0, 0])); } });
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible' && !PRES.ws) { PRES.retry = 2000; presConnect(); } });
const _route = route;
route = async (...a) => { await _route(...a); presShow(); };
presConnect();

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
  <div class="h1row"><h1>Hôm nay</h1><span class="online-pill" hidden title="Số người đang mở ứng dụng (cập nhật khoảng 30 giây)"></span></div>
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
  ${await todayPlanHTML()}
  <h2>Học theo kỹ năng</h2>
  <div class="quick">${Object.entries(SKILLS).map(([k, v]) => `<a href="#/skill/${k}"><span class="glyph">${v.glyph}</span><b>${v.name}</b></a>`).join('')}<a href="#/exam"><span class="glyph">試</span><b>Thi thử</b></a></div>
  ${!GH.ok() ? `<div class="status info" style="margin-top:20px">Tiến độ đang chỉ lưu trên thiết bị này. <a href="#/settings">Kết nối GitHub</a> để lưu lên GitHub và dùng chung giữa máy tính và điện thoại.</div>` : ''}`;
});

/* ---------------- Học theo kỹ năng ---------------- */
// Mỗi kỹ năng: ① Học (tài liệu) → ② Ôn → ③ Luyện dạng đề JLPT (問題 tương ứng, từ đề thật) → ④ Bài tập / tài liệu thêm
const SKILLS = {
  kanji: { name: 'Kanji', jp: '漢字', glyph: '漢', part: '文字・語彙', types: [1] },
  vocab: { name: 'Từ vựng', jp: '語彙', glyph: '語', part: '文字・語彙', types: [2, 3, 4] },
  grammar: { name: 'Ngữ pháp', jp: '文法', glyph: '文', part: '文法', types: [5, 6, 7] },
  reading: { name: 'Đọc hiểu', jp: '読解', glyph: '読', part: '読解', types: [8, 9, 10, 11, 12, 13] },
  listening: { name: 'Nghe hiểu', jp: '聴解', glyph: '聴', part: '聴解', types: [1, 2, 3, 4, 5] },
};
const TYPE_TIP = {
  1: 'Chọn cách đọc đúng của từ gạch chân. Chú ý trường âm, âm đục, っ.',
  2: 'Chọn từ hợp ngữ cảnh. Đọc cả câu, để ý từ đi kèm (collocation).',
  3: 'Chọn từ/cụm gần nghĩa nhất với phần gạch chân.',
  4: 'Chọn câu dùng từ đúng nhất (cả nghĩa lẫn cách kết hợp).',
  5: 'Chọn mẫu ngữ pháp điền vào ( ). Xét vế trước/sau và sắc thái.',
  6: 'Sắp xếp 4 cụm, chọn cụm ở vị trí ★. Ghép cụm chắc chắn trước.',
  7: 'Điền từ/ngữ pháp vào đoạn văn: đọc mạch văn, từ nối, chủ ngữ.',
  8: '4 đoạn ~200 chữ, mỗi đoạn 1 câu: ý chính, mục đích văn bản.',
  9: '3 đoạn ~500 chữ, mỗi đoạn 3 câu: lý do, nguyên nhân, ý kiến tác giả.',
  10: '1 bài ~1000 chữ, 4 câu: theo dõi lập luận, câu cuối hỏi ý chính.',
  11: 'So sánh 2 bài A/B: điểm chung, khác biệt giữa hai quan điểm.',
  12: 'Bài nghị luận dài: chủ trương, ý kiến của tác giả.',
  13: 'Tìm thông tin trong thông báo/bảng: đọc câu hỏi trước, dò điều kiện.',
};
const LTYPE = {
  1: ['課題理解', 'Nghe và chọn việc cần làm tiếp theo. Câu hỏi được nói trước — nghe kỹ câu hỏi.'],
  2: ['ポイント理解', 'Đọc lựa chọn trong đề trước, nghe tìm lý do/điểm chính.'],
  3: ['概要理解', 'Không in câu hỏi: nghe toàn bộ rồi chọn nội dung chính/ý kiến người nói.'],
  4: ['即時応答', 'Nghe 1 câu ngắn, chọn câu đáp lại tự nhiên nhất (3 lựa chọn).'],
  5: ['統合理解', 'Nghe đoạn dài nhiều người nói, so sánh thông tin, có thể ghi chú.'],
};
const VOC_ORDER = ['Chinh phục từ vựng N1', 'はじめての N1 単語3000 (Hàn–Việt)', 'Từ vựng N1 FULL', 'N1 Trainingbook (theo ngày)', 'Từ vựng N1 tổng hợp', 'Chuyên đề N1', 'Tiếp khách nhà hàng', 'Kính ngữ'];
const VOC_NOTE = {
  'Chinh phục từ vựng N1': 'Nên học đầu tiên · 111 bài theo chủ đề · audio giọng người đọc',
  'はじめての N1 単語3000 (Hàn–Việt)': 'Mở rộng theo 14 chủ đề · audio từng từ + ví dụ',
  'Từ vựng N1 FULL': 'Ôn tổng hợp theo giáo trình lớp',
  'N1 Trainingbook (theo ngày)': 'Mỗi ngày một ít',
  'Chuyên đề N1': 'Phó từ, từ nối, động từ ghép, kanji khó… (rất hay ra trong đề)',
};
function realExamPairs(I) {
  // ghép đề đọc + đề nghe theo kỳ thi
  const by = {};
  for (const x of I) {
    let m = x.id.match(/^(jr|jl|jn|ls)(\d{4})(\d{2})$/) || (x.id === 'de12210' ? [0, 'de', '2021', '12'] : null);
    if (!m) continue;
    const k = m[2] + '-' + m[3]; by[k] ||= { ym: k };
    if (m[1] === 'ls') by[k].listen = x; else if (!by[k].read || m[1] === 'de') by[k].read = x;
  }
  return Object.values(by).sort((a, b) => b.ym.localeCompare(a.ym));
}
async function skillStats() {
  const [V, K, G] = await Promise.all([decks(), load('kanji'), load('grammar')]);
  const cnt = p => { let l = 0, m = 0; for (const [k, c] of Object.entries(S.srs)) if (k.startsWith(p)) { l++; if (isMastered(c)) m++; } return { l, m }; };
  const res = (filter) => { const xs = S.exams.filter(filter); if (!xs.length) return null; const s = xs.reduce((a, e) => [a[0] + e.score, a[1] + e.total], [0, 0]); return Math.round(100 * s[0] / s[1]); };
  return {
    vocab: { n: V.reduce((a, d) => a + d.items.length, 0), ...cnt('v:'), acc: res(e => [2, 3, 4].includes(e.drill)) },
    kanji: { n: K.length, ...cnt('k:'), acc: res(e => e.drill === 1) },
    grammar: { n: G.length, ...cnt('g:'), acc: res(e => [5, 6, 7].includes(e.drill)) },
    reading: { n: (await load('reading')).reduce((a, g) => a + g.sets.length, 0), acc: res(e => e.drill >= 8 || (e.set && !e.test)) },
    listening: { n: 29, acc: res(e => e.test?.startsWith('ls') || e.ldrill) },
  };
}
on(/^\/learn$/, async () => {
  const st = await skillStats(); const { due, fresh } = await queueToday();
  const dueBy = p => [...due, ...fresh].filter(k => k.startsWith(p)).length;
  const card = (id, sub, extra = '') => { const s = SKILLS[id]; return `<a class="skill" href="#/skill/${id}"><span class="glyph">${s.glyph}</span><div class="body"><div class="row"><h3>${s.name} <span class="jp muted" style="font-weight:400">${s.jp}</span></h3>${extra}</div><p>${sub}</p></div><span class="chev">›</span></a>`; };
  const badge = n => n ? `<span class="tag on">${n} thẻ hôm nay</span>` : '';
  main.innerHTML = `<h1>Học theo kỹ năng</h1><p class="lead">Sắp xếp đúng theo cấu trúc đề JLPT N1. Mỗi kỹ năng đi theo 4 bước: <b>① Học</b> tài liệu → <b>② Ôn</b> bằng thẻ → <b>③ Luyện dạng đề</b> thật → <b>④ Bài tập</b> thêm.</p>
  <div class="part-title"><span>言語知識</span> Kiến thức ngôn ngữ <span class="muted small">· phần thi 1 (110 phút, chung với đọc hiểu)</span></div>
  <div class="skills">
   ${card('kanji', `${st.kanji.n} chữ · đã học ${st.kanji.l} · thuộc ${st.kanji.m} · dạng 問題1`, badge(dueBy('k:')))}
   ${card('vocab', `${st.vocab.n.toLocaleString('vi')} từ · đã học ${st.vocab.l} · thuộc ${st.vocab.m} · dạng 問題2–4`, badge(dueBy('v:')))}
   ${card('grammar', `${st.grammar.n} mẫu · đã học ${st.grammar.l} · thuộc ${st.grammar.m} · dạng 問題5–7`, badge(dueBy('g:')))}
  </div>
  <div class="part-title"><span>読解</span> Đọc hiểu <span class="muted small">· 問題8–13</span></div>
  <div class="skills">${card('reading', `${st.reading.n} bài luyện + đọc hiểu trong ${realExamPairs(await load('exams/index')).length} đề thật${st.reading.acc != null ? ` · đúng ${st.reading.acc}%` : ''}`)}</div>
  <div class="part-title"><span>聴解</span> Nghe hiểu <span class="muted small">· phần thi 2 (~55 phút)</span></div>
  <div class="skills">${card('listening', `29 đề nghe thật có audio · thư viện nghe sách${st.listening.acc != null ? ` · đúng ${st.listening.acc}%` : ''}`)}</div>
  <div class="part-title"><span>基礎</span> Nền tảng & lộ trình</div>
  <div class="grid-hub">
    <a class="hub" href="#/plan"><span class="glyph">道</span><div><h3>Lộ trình 28 tuần</h3><p>Lịch học từng buổi, liên kết đến bài cần học</p></div></a>
    <a class="hub" href="#/kana"><span class="glyph">あ</span><div><h3>Hiragana / Katakana</h3><p>Bảng chữ và trắc nghiệm</p></div></a>
  </div>`;
});
const step = (n, title, sub, body) => `<section class="step"><div class="step-h"><span class="step-n">${n}</span><div><h2>${title}</h2>${sub ? `<p class="muted small">${sub}</p>` : ''}</div></div>${body}</section>`;
const tile = (href, glyph, title, sub, extra = '') => `<a class="item" href="${href}"><div class="glyph" style="${glyph.length > 2 ? 'font-size:.9rem;font-family:var(--ui)' : ''}">${glyph}</div><div class="body"><b>${title}</b>${sub ? `<div class="sub">${sub}</div>` : ''}</div>${extra}</a>`;
async function drillCounts() {
  const I = (await load('exams/index')).filter(x => x.fmt !== 'practice' && !x.paper);
  const c = {}; for (const x of I) for (const [n, k] of x.secs) c[n] = (c[n] || 0) + k; return c;
}
const drillList = async (types) => { const c = await drillCounts(); return `<div class="list">${types.map(t => tile(`#/drill?type=${t}`, '問' + t, `<span class="jp">${esc(DRILL[t])}</span>`, `${TYPE_TIP[t]} · ${c[t] || 0} câu từ đề thật & đề thi thử`)).join('')}</div>`; };
const setList = (I, re, label) => { const xs = I.filter(x => re.test(x.set)); if (!xs.length) return ''; const sets = [...new Set(xs.map(x => x.set))];
  return sets.map(s => tile(`#/tests?set=${encodeURIComponent(s)}`, '本', esc(s), `${xs.filter(x => x.set === s).length} bài · ${xs.filter(x => x.set === s).reduce((a, x) => a + x.nq, 0)} câu có đáp án${label ? ' · ' + label : ''}`)).join(''); };
on(/^\/skill\/(\w+)$/, async (id) => {
  const s = SKILLS[id]; if (!s) throw new Error('Không có kỹ năng này');
  const I = await load('exams/index'); const st = (await skillStats())[id];
  const { due, fresh } = await queueToday(); const pre = { vocab: 'v:', kanji: 'k:', grammar: 'g:' }[id];
  const nToday = pre ? [...due, ...fresh].filter(k => k.startsWith(pre)).length : 0;
  const nav = Object.entries(SKILLS).map(([k, v]) => `<a class="${k === id ? 'on' : ''}" href="#/skill/${k}">${v.name}</a>`).join('');
  let html = `<a class="crumb" href="#/learn">‹ Học theo kỹ năng</a><div class="skilltabs">${nav}</div>
  <h1>${s.name} <span class="jp muted" style="font-weight:400">${s.jp}</span></h1>`;
  if (id === 'vocab') {
    const ds = await decks(); const groups = VOC_ORDER.filter(g => ds.some(d => d.group === g)).concat([...new Set(ds.map(d => d.group))].filter(g => !VOC_ORDER.includes(g)));
    html += `<p class="lead">Học theo bộ, bấm “Học bài này” ở từng bài để đưa vào lịch ôn. Đã học ${st.l}/${st.n.toLocaleString('vi')} từ, thuộc ${st.m}.</p>
    ${step(1, 'Học từ mới', 'Các bộ từ vựng, xếp theo thứ tự nên học', `<div class="list">${groups.map((g, i) => { const gd = ds.filter(d => d.group === g); const p = deckProgress('v:', gd.flatMap(d => d.items.map(x => x.id)));
      return tile(`#/vocab?g=${encodeURIComponent(g)}`, String(i + 1), esc(g), `${VOC_NOTE[g] ? esc(VOC_NOTE[g]) + ' · ' : ''}${gd.length} bài · ${p.n} từ · đã học ${p.l}`, gd.some(d => S.active['v:' + d.id]) ? '<span class="tag on">Đang học</span>' : ''); }).join('')}
      ${tile('#/vocab', '🔍', 'Tra cứu tất cả từ', 'Tìm theo chữ, cách đọc hoặc nghĩa')}${tile('#/addword', '＋', 'Thêm từ của bạn', 'Lưu cùng tiến độ lên GitHub')}</div>`)}
    ${step(2, 'Ôn tập', '', `<div class="list">${tile('#/review?skill=v', '復', `Ôn từ vựng hôm nay`, `${nToday} thẻ đến hạn / mới`)}${tile('#/audio', '聴', 'Nghe từ vựng', '5 giờ Chinh phục từ vựng + 70 bài 単語3000, có chép lời')}</div>`)}
    ${step(3, 'Luyện dạng đề JLPT', 'Câu hỏi lấy từ đề thật và đề thi thử', await drillList(s.types))}
    ${step(4, 'Bài tập thêm', '', `<div class="list">${setList(I, /Test từ vựng/)}</div>`)}`;
  }
  if (id === 'kanji') {
    const K = await load('kanji'); const chs = [...new Set(K.map(k => k.ch))];
    const kd = (await decks()).filter(d => /kanji|漢字/i.test(d.name));
    html += `<p class="lead">${K.length} chữ Hán thường gặp ở N1, 21 chương × 15 chữ, kèm âm Hán Việt, On/Kun, ví dụ, mẹo nhớ.</p>
    ${step(1, 'Học chữ', 'Mỗi chương 15 chữ — bấm vào chương, chọn “Học chương này”', `<div class="list">${tile('#/kanji', '漢', `315 kanji N1 · ${chs.length} chương`, `đã học ${st.l} · thuộc ${st.m}`)}${kd.map(d => tile(`#/vocab/${d.id}`, '字', esc(d.name), `${esc(d.group)} · ${d.items.length} từ`)).join('')}</div>`)}
    ${step(2, 'Ôn tập', '', `<div class="list">${tile('#/review?skill=k', '復', 'Ôn kanji hôm nay', `${nToday} thẻ đến hạn / mới`)}</div>`)}
    ${step(3, 'Luyện dạng đề JLPT', 'Đọc kanji là phần dễ lấy điểm nhất', await drillList(s.types))}`;
  }
  if (id === 'grammar') {
    const G = await load('grammar');
    const order = [['book', 'Nên học đầu tiên · 22 chương có bài giảng'], ['freq', 'Ôn trọng tâm trước khi thi'], ['try', 'Học qua bài đọc/nghe, có audio'], ['th', 'Tổng hợp để tra cứu, ôn rộng'], ['cn', 'Đầy đủ nhất, kèm bài tập']];
    html += `<p class="lead">${G.length} mẫu ngữ pháp từ 5 nguồn. Đã học ${st.l}, thuộc ${st.m}.</p>
    ${step(1, 'Học mẫu ngữ pháp', 'Theo thứ tự nên học', `<div class="list">${order.map(([k, note], i) => { const gs = G.filter(g => g.set === k); const p = deckProgress('g:', gs.map(g => g.id));
      return tile(`#/grammar?set=${k}`, String(i + 1), esc(GSETS[k]), `${note} · ${gs.length} mẫu · đã học ${p.l}`, S.active['g:' + k] ? '<span class="tag on">Đang học</span>' : ''); }).join('')}
      ${tile('#/try', 'T', 'Sách TRY! N1', '10 bài đọc/nghe → ngữ pháp, xem trang gốc')}${tile('#/keigo', '敬', 'Kính ngữ', '34 động từ 尊敬語・謙譲語, quy tắc, trắc nghiệm')}${tile('#/grammar', '🔍', 'Tra cứu tất cả mẫu', '')}</div>`)}
    ${step(2, 'Ôn tập', '', `<div class="list">${tile('#/review?skill=g', '復', 'Ôn ngữ pháp hôm nay', `${nToday} thẻ đến hạn / mới`)}</div>`)}
    ${step(3, 'Luyện dạng đề JLPT', '', await drillList(s.types))}
    ${step(4, 'Bài tập thêm', '', `<div class="list">${setList(I, /Cẩm nang|TRY|Test từ vựng-ngữ pháp N1$/)}</div>`)}`;
  }
  if (id === 'reading') {
    const R = await load('reading'); const done = new Set(S.exams.filter(e => e.set).map(e => e.set));
    html += `<p class="lead">Đọc hiểu chiếm 6 dạng (問題8–13). Luyện từng dạng cho quen, sau đó làm cả đề để luyện phân bổ thời gian.</p>
    ${step(1, 'Hiểu từng dạng bài', '', `<div class="list">${s.types.map(t => tile(`#/drill?type=${t}`, '問' + t, `<span class="jp">${esc(DRILL[t])}</span>`, TYPE_TIP[t])).join('')}</div>`)}
    ${step(2, 'Luyện bài đọc', 'Bài đọc lẻ có đáp án, chia theo độ dài', `<div class="list">${R.map(g => tile(`#/read?g=${g.id}`, '読', esc(g.title), `${g.sets.length} bài · đã làm ${g.sets.filter(x => done.has(x.id)).length}`)).join('')}</div>`)}
    ${step(3, 'Luyện dạng đề JLPT', 'Mỗi lượt một bài đọc hoàn chỉnh từ đề thật / đề thi thử', await drillList(s.types))}
    ${step(4, 'Tài liệu thêm', '', `<div class="list">${setList(I, /bổ trợ đọc hiểu/)}${tile('#/try', 'T', 'Sách TRY! N1', 'Bài đọc theo thể loại: tin tức, tiểu thuyết, nghị luận…')}</div>`)}`;
  }
  if (id === 'listening') {
    const P = realExamPairs(I).filter(p => p.listen);
    html += `<p class="lead">5 dạng nghe (問題1–5). Luyện từng dạng bằng đề thật có audio; mỗi 問題 tự tua đúng đoạn và có script để đối chiếu.</p>
    ${step(1, 'Luyện theo dạng', 'Mỗi lượt lấy ngẫu nhiên một đề, chỉ làm dạng đã chọn', `<div class="list">${Object.entries(LTYPE).map(([t, [jp, tip]]) => tile(`#/ldrill?type=${t}`, '問' + t, `<span class="jp">${jp}</span>`, `${tip} · ${P.length} đề`)).join('')}</div>`)}
    ${step(2, 'Làm cả phần nghe', '~55 phút, như thi thật', `<div class="list">${P.slice(0, 6).map(p => tile(`#/test/${p.listen.id}?mode=practice`, p.ym.slice(2).replace('-', '/'), `Tháng ${+p.ym.slice(5)}/${p.ym.slice(0, 4)}`, `${p.listen.nq} câu`)).join('')}${tile('#/exam', '…', `Xem cả ${P.length} đề`, 'Trong mục Thi thử')}</div>`)}
    ${step(3, 'Thư viện nghe', 'Nghe hằng ngày để quen tốc độ, có chép lời', `<div class="list">${tile('#/audio', '聴', 'Nghe từ vựng · TRY! N1 · 単語3000', 'Nhớ vị trí đang nghe, chỉnh tốc độ, chạm câu để tua')}${tile('#/try', 'T', 'TRY! N1 — bài đọc/nghe theo chương', 'まとめの問題 có câu nghe')}</div>`)}`;
  }
  main.innerHTML = html;
  const t = $('.skilltabs a.on'); if (t) t.parentElement.scrollLeft = t.offsetLeft - t.parentElement.clientWidth / 2 + t.clientWidth / 2;
});
// Luyện nghe theo dạng: chọn ngẫu nhiên một đề nghe, mở đúng 問題
on(/^\/ldrill$/, async (q) => {
  const P = realExamPairs(await load('exams/index')).filter(p => p.listen);
  const p = P[Math.floor(Math.random() * P.length)];
  location.replace(`#/test/${p.listen.id}?mode=practice&sec=${q.type || 1}`);
});

/* ---------------- Từ vựng ---------------- */
function deckProgress(prefix, ids) { let l = 0, m = 0; for (const id of ids) { const c = S.srs[prefix + id]; if (c) { l++; if (isMastered(c)) m++; } } return { l, m, n: ids.length }; }
on(/^\/vocab$/, async (q) => {
  const ds = await decks();
  const groups = [...new Set(ds.map(d => d.group))].filter(g => !q.g || g === q.g);
  main.innerHTML = `<a class="crumb" href="#/skill/vocab">‹ Từ vựng</a><h1>${q.g ? esc(q.g) : 'Tra cứu từ vựng'}</h1>
  <input class="search" id="vs" type="search" placeholder="Tìm từ, cách đọc hoặc nghĩa tiếng Việt…" aria-label="Tìm từ vựng">
  <div id="vres"></div>
  <div id="vlist">${groups.map((g, gi) => `<details class="grp" ${gi === 0 || q.g || ds.some(d => d.group === g && S.active['v:' + d.id]) ? 'open' : ''}><summary class="groupname">${esc(g)} <span class="muted small">· ${ds.filter(d => d.group === g).length} bài · ${ds.filter(d => d.group === g).reduce((a, d) => a + d.items.length, 0)} từ</span></summary><div class="list">${ds.filter(d => d.group === g).map(d => {
    const p = deckProgress('v:', d.items.map(i => i.id));
    return `<a class="item" href="#/vocab/${d.id}"><div class="body"><div class="row"><b>${esc(d.name)}</b>${S.active['v:' + d.id] ? '<span class="tag on">Đang học</span>' : ''}</div>
    <div class="sub">${d.items.length} từ · đã học ${p.l} · thuộc ${p.m}</div><div class="bar"><i style="width:${100 * p.l / Math.max(1, p.n)}%"></i></div></div></a>`;
  }).join('')}</div></details>`).join('')}
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
const exHTML = (i, n) => (i.ex || []).slice(0, n).map((e, k) => `<div class="ex">${sayT(e)}${i.exvi?.[k] ? `<div class="exvi">${esc(i.exvi[k])}</div>` : ''}</div>`).join('');
function wordRow(i) {
  return `<div class="word"><div><div class="w">${sayT(i.w, i.r || i.w)}</div><div class="r">${i.r ? sayT(i.r) : ''}${i.hv ? ' · ' + esc(i.hv) : ''}</div></div>
  <div class="m">${esc(i.m)}${i.chk ? ' <span class="tag warn" title="Chữ nhận dạng tự động chưa khớp từ điển — hãy xem ảnh gốc">cần đối chiếu</span>' : ''}${exHTML(i, 2)}${(i.rel || []).map(r => `<div class="small muted">＋ <span class="jp">${esc(r)}</span></div>`).join('')}${i.img ? `<details class="small"><summary>Xem bản gốc</summary><img loading="lazy" src="${i.img}" alt="Mục từ trong sách" style="width:100%;max-width:640px;margin-top:4px;border:1px solid var(--line)"></details>` : ''}</div>${vSay(i)}</div>`;
}
on(/^\/vocab\/([\w-]+)$/, async (id) => {
  const d = (await decks()).find(x => x.id === id); if (!d) throw new Error('Không tìm thấy bài');
  const act = !!S.active['v:' + id];
  const p = deckProgress('v:', d.items.map(i => i.id));
  main.innerHTML = `<a class="crumb" href="#/vocab?g=${encodeURIComponent(d.group)}">‹ ${esc(d.group)}</a><h1>${esc(d.name)}</h1><p class="lead">${esc(d.group)} · ${d.items.length} từ · đã học ${p.l} · thuộc ${p.m}</p>
  <div class="row" style="margin-bottom:16px">
   <button class="btn ${act ? '' : 'primary'}" id="tog">${act ? 'Ngừng học bài này' : 'Học bài này'}</button>
   <a class="btn" href="#/review?deck=v:${id}&mode=browse">Lật thẻ (không chấm)</a>${d.audio ? `<a class="btn" href="#/audio?f=${encodeURIComponent(d.audio)}">▶ Nghe cả bài</a>` : ''}
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
  main.innerHTML = `<a class="crumb" href="#/skill/kanji">‹ Kanji</a><h1>Kanji N1</h1><p class="lead">${K.length} chữ, mỗi chương 15 chữ kèm âm Hán Việt, âm On/Kun, ví dụ và mẹo nhớ.</p>
  <input class="search" id="ks" type="search" placeholder="Tìm chữ kanji hoặc âm Hán Việt…" aria-label="Tìm kanji"><div id="kres"></div>
  <div class="list" id="klist">${chs.map(c => { const ks = K.filter(k => k.ch === c); const p = deckProgress('k:', ks.map(k => k.id));
    return `<a class="item" href="#/kanji/${c}"><div class="glyph">${esc(ks[0].k)}</div><div class="body"><div class="row"><b>Chương ${c}</b>${S.active['k:' + c] ? '<span class="tag on">Đang học</span>' : ''}</div>
    <div class="sub jp">${ks.map(k => k.k).join(' ')}</div><div class="bar"><i style="width:${100 * p.l / p.n}%"></i></div></div></a>`; }).join('')}</div>`;
  $('#ks').oninput = e => { const t = e.target.value.trim().toLowerCase(); $('#klist').classList.toggle('hidden', !!t);
    $('#kres').innerHTML = t ? `<div class="words">${K.filter(k => (k.k + k.hv + k.on + k.kun).toLowerCase().includes(t)).slice(0, 60).map(kanjiRow).join('') || ''}</div>` : ''; };
});
const exVi = (k, i) => k.exm && k.exm[i] ? ` <span class="exvi">— ${esc(k.exm[i])}</span>` : '';
const kanjiRow = k => `<div class="word"><div><div class="w" style="font-size:2rem">${sayT(k.k)}</div><div class="r">${esc(k.hv)}</div>${k.m ? `<div class="kvi">${esc(k.m)}</div>` : ''}</div><div class="m"><div class="small">On: <span class="jp">${sayList(k.on)}</span> · Kun: <span class="jp">${sayList(k.kun)}</span></div>${k.ex.map((e, i) => `<div class="ex">${sayT(e)}${exVi(k, i)}</div>`).join('')}${k.tip ? `<div class="small muted">💡 ${sayT(k.tip)}${k.tipm ? `<div class="tipvi">→ ${esc(k.tipm)}</div>` : ''}</div>` : ''}</div>${sayAllBtn([k.k, k.on, k.kun.replace(/[()（）]/g, ''), ...k.ex])}</div>`;
on(/^\/kanji\/(\d+)$/, async (c) => {
  c = +c; const ks = (await load('kanji')).filter(k => k.ch === c); const act = !!S.active['k:' + c];
  main.innerHTML = `<a class="crumb" href="#/kanji">‹ Kanji</a><h1>Kanji · Chương ${c}</h1><p class="lead">${ks.length} chữ</p>
  <div class="row" style="margin-bottom:16px"><button class="btn ${act ? '' : 'primary'}" id="tog">${act ? 'Ngừng học chương này' : 'Học chương này'}</button><a class="btn" href="#/review?deck=k:${c}&mode=browse">Lật thẻ</a></div>
  <div class="words">${ks.map(kanjiRow).join('')}</div>`;
  $('#tog').onclick = () => { if (act) delete S.active['k:' + c]; else S.active['k:' + c] = true; save(); toast(act ? 'Đã bỏ khỏi lịch học' : 'Đã thêm vào lịch học'); route(); };
});

/* ---------------- Ngữ pháp ---------------- */
const GSETS = { book: 'Ngữ pháp N1 (giáo trình, 22 chương)', freq: 'Ngữ pháp hay xuất hiện trong đề thi', th: 'Tổng hợp ngữ pháp N1', cn: 'Cẩm nang ngữ pháp N1', try: 'TRY! N1 – 123 mẫu theo bài đọc (OCR từ sách)' };
on(/^\/grammar$/, async (q) => {
  const G = await load('grammar');
  main.innerHTML = `<a class="crumb" href="#/skill/grammar">‹ Ngữ pháp</a><h1>${q.set ? esc(GSETS[q.set] || 'Ngữ pháp') : 'Tra cứu ngữ pháp'}</h1>
  <input class="search" id="gs" type="search" placeholder="Tìm mẫu ngữ pháp hoặc nghĩa…" aria-label="Tìm ngữ pháp">
  ${Object.entries(GSETS).filter(([s]) => !q.set || s === q.set).map(([s, name]) => { const gs = G.filter(g => g.set === s); const act = !!S.active['g:' + s]; const p = deckProgress('g:', gs.map(g => g.id));
    const grps = [...new Set(gs.map(g => g.grp || ''))];
    const itemsHTML = grps.map(gr => `${gr ? `<div class="subgrp">${esc(gr)}</div>` : ''}<div class="list">${gs.filter(g => (g.grp || '') === gr).map(g => `<a class="item gi" href="#/grammar/${g.id}" data-s="${esc((g.title + ' ' + g.mean).toLowerCase())}"><div class="body"><b class="jp">${esc(g.title)}</b>${S.srs['g:' + g.id] ? ` <span class="tag ${isMastered(S.srs['g:' + g.id]) ? 'on' : ''}">${isMastered(S.srs['g:' + g.id]) ? 'Đã thuộc' : 'Đang học'}</span>` : ''}<div class="sub">${esc(g.mean.split(' • ').slice(0, 2).join(' • '))}</div></div></a>`).join('')}</div>`).join('');
    return `<details class="grp gset" ${s === 'book' || act || q.set ? 'open' : ''}><summary class="row" style="margin:20px 0 8px"><b>${name}</b><span class="muted small">${gs.length} mẫu · đã học ${p.l}</span><span class="spacer"></span>
    <button class="btn sm ${act ? '' : 'primary'}" data-tog="${s}">${act ? 'Ngừng học' : 'Học phần này'}</button><a class="btn sm" href="#/review?deck=g:${s}&mode=browse">Lật thẻ</a></summary>
    ${itemsHTML}</details>`; }).join('')}`;
  $$('[data-tog]').forEach(b => b.onclick = () => { const k = 'g:' + b.dataset.tog; if (S.active[k]) delete S.active[k]; else S.active[k] = true; save(); route(); });
  $$('[data-tog]').forEach(b => b.addEventListener('click', e => e.preventDefault(), true));
  $('#gs').oninput = e => { const t = e.target.value.trim().toLowerCase(); if (t) $$('details.gset').forEach(d => d.open = true); $$('.gi').forEach(a => a.classList.toggle('hidden', !!t && !a.dataset.s.includes(t))); };
});
function grammarBody(g) {
  return `${g.form.length ? `<div class="form-box">${g.form.map(esc).join('<br>')}</div>` : ''}
  <p style="font-size:1.1rem;font-weight:500">${esc(g.mean).replace(/ • /g, '<br>')}</p>
  ${g.use.length ? `<h3>Cách dùng</h3><ul>${g.use.map(u => `<li>${esc(u)}</li>`).join('')}</ul>` : ''}
  ${g.pg ? `<p class="small"><a href="#/try/p/${g.pg}">Xem trang sách gốc (tr. ${g.pg}) ›</a> <span class="muted">— phần giải thích và ví dụ dưới đây là chữ nhận dạng tự động, có thể sai vài chữ.</span></p>` : ''}
  ${g.ex.length ? `<h3>Ví dụ</h3><ol class="gram-ex">${g.ex.map((e, k) => `<li>${esc(e)} ${sayBtn(e).replace('icon-btn', 'icon-btn inline')}${g.exvi?.[k] ? `<div class="exvi">${esc(g.exvi[k])}</div>` : ''}</li>`).join('')}</ol>` : ''}
  ${(g.notes || []).map(n => `<div class="lesson-note"><h3>${esc(n.src)}</h3>
    <p><b>意味:</b> ${esc(n.mean)}</p>${n.form ? `<div class="form-box">${esc(n.form)}</div>` : ''}
    <p><b>注意:</b> ${esc(n.note)}</p>
    ${n.img?.length ? `<details><summary>Xem slide (${n.img.length})</summary><div class="pages">${n.img.map(u => `<img loading="lazy" src="${u}" alt="Slide bài giảng">`).join('')}</div></details>` : ''}</div>`).join('')}`;
}
on(/^\/grammar\/([\w]+)$/, async (id) => {
  const G = await load('grammar'); const i = G.findIndex(g => g.id === id); const g = G[i]; if (!g) throw new Error('Không tìm thấy mẫu ngữ pháp');
  const prev = G[i - 1]?.set === g.set ? G[i - 1] : null, next = G[i + 1]?.set === g.set ? G[i + 1] : null;
  main.innerHTML = `<a class="crumb" href="#/grammar?set=${g.set}">‹ ${esc(GSETS[g.set])}</a><h1 class="jp">${esc(g.title)}</h1><p class="muted">${GSETS[g.set]}${g.ch ? ' · Chương ' + g.ch : ''}${g.grp ? ' · ' + esc(g.grp) : ''}</p>
  <div class="panel">${grammarBody(g)}</div>
  <div class="row" style="margin-top:16px">${prev ? `<a class="btn" href="#/grammar/${prev.id}">‹ <span class="jp">${esc(prev.title)}</span></a>` : ''}<span class="spacer"></span>${next ? `<a class="btn" href="#/grammar/${next.id}"><span class="jp">${esc(next.title)}</span> ›</a>` : ''}</div>`;
});

on(/^\/grammar\/ch\/(\d+)$/, async (c) => {
  const gs = (await load('grammar')).filter(g => g.set === 'book' && g.ch === +c);
  main.innerHTML = `<a class="crumb" href="#/grammar">‹ Ngữ pháp</a><h1>Ngữ pháp · Chương ${c}</h1><p class="lead">${gs.length} mẫu</p>
  <div class="list">${gs.map(g => `<a class="item" href="#/grammar/${g.id}"><div class="body"><b class="jp">${esc(g.title)}</b><div class="sub">${esc(g.mean)}</div></div></a>`).join('')}</div>`;
});

/* ---------------- Lộ trình ---------------- */
const READMAP = { '短文': 'tanbun', '中文': 'chuubun', '長文': 'choubun', '比較': 'hikaku', '情報検索': 'kensaku' };
function linkPlan(t, secs) {
  let h = esc(t);
  h = h.replace(/(Kanji\s*(?:[Cc]hương|C)\s*)(\d+)/g, (m, a, n) => `<a href="#/kanji/${n}">${a}${n}</a>`);
  h = h.replace(/(NP\s*(?:[Cc]hương|C)\s*)(\d+)/g, (m, a, n) => `<a href="#/grammar/ch/${n}">${a}${n}</a>`);
  h = h.replace(/(?<![\d/.])([1-6]\.\d{1,2})(?![\d/])/g, (m, sec) => secs.has(sec) ? `<a href="#/vocab/dm${sec.replace('.', '_')}">${sec}</a>` : m);
  h = h.replace(/(短文|中文|長文|比較|情報検索)\s*(\d+)/g, (m, k, n) => `<a href="#/read/${READMAP[k]}${n}">${k}${n}</a>`);
  return h.replace(/\n-{3,}\n?/g, '<hr>').replace(/\n/g, '<br>');
}
function planDate(w, d) { const st = S.settings.planStart; if (!st) return null; const t = new Date(st + 'T00:00:00'); t.setDate(t.getDate() + (w - 1) * 7 + d); return t; }
function mondayOf(d = new Date()) { const t = new Date(d); t.setHours(0, 0, 0, 0); t.setDate(t.getDate() - (t.getDay() + 6) % 7); return t; }
async function todayPlanHTML() {
  if (!S.settings.planStart) return '';
  const P = await load('plan'); const secs = new Set((await load('vocab')).filter(d => d.sec).map(d => d.sec));
  const diff = Math.round((startOfDay() - new Date(S.settings.planStart + 'T00:00:00').getTime()) / DAY);
  const w = Math.floor(diff / 7) + 1, d = diff % 7;
  const wk = P.weeks[w - 1]; if (diff < 0 || !wk) return '';
  const day = wk.days[d]; if (!day?.text) return '';
  const done = S.plan[day.id]?.done;
  return `<h2>Lộ trình hôm nay · Tuần ${w}</h2><div class="panel plan-today ${done ? 'done' : ''}"><div class="plan-text">${linkPlan(day.text, secs)}</div>
    <div class="row" style="margin-top:12px"><button class="btn sm ${done ? '' : 'primary'}" onclick="togglePlan('${day.id}')">${done ? 'Bỏ đánh dấu' : 'Đánh dấu đã xong'}</button><a class="btn sm" href="#/plan?w=${w}">Xem cả tuần</a></div></div>`;
}
window.togglePlan = id => { const v = S.plan[id]; S.plan[id] = { done: !(v && v.done), t: Date.now() }; save(); route(); };
on(/^\/plan$/, async (q) => {
  const P = await load('plan'); const secs = new Set((await load('vocab')).filter(d => d.sec).map(d => d.sec));
  const DOW = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật'];
  const total = P.weeks.reduce((a, w) => a + w.days.filter(d => d.text).length, 0);
  const done = Object.values(S.plan).filter(v => v.done).length;
  const todayT = startOfDay();
  main.innerHTML = `<a class="crumb" href="#/learn">‹ Học</a><h1>Lộ trình học N1</h1><p class="lead">${esc(P.title.replace(/\s*\(KG.*$/, ''))} · đã xong ${done}/${total} buổi</p>
  <div class="panel" style="margin-bottom:16px"><div class="row"><label for="ps"><b>Ngày bắt đầu (thứ 2 của tuần 1)</b></label>
   <input id="ps" type="date" value="${S.settings.planStart || ''}" class="date-in"><button class="btn sm" id="psNow">Bắt đầu từ tuần này</button>
   ${S.settings.planStart ? '<button class="btn sm ghost" id="psClear">Bỏ ngày</button>' : ''}</div>
   <p class="muted small" style="margin:8px 0 0">Đặt ngày bắt đầu để ứng dụng tính ngày cho từng buổi và hiện việc cần làm trên trang Hôm nay. Bấm vào chữ xanh để mở đúng bài trong ứng dụng.</p></div>
  <div class="bar" style="margin-bottom:18px"><i style="width:${100 * done / total}%"></i></div>
  ${P.weeks.map(w => { const wd = w.days.filter(d => d.text); const wdone = wd.filter(d => S.plan[d.id]?.done).length;
    const isNow = w.days.some((d, i) => planDate(w.n, i)?.getTime() === todayT);
    return `<details class="box week" id="wk${w.n}" ${(q.w ? +q.w === w.n : isNow) ? 'open' : ''}><summary>Tuần ${w.n}${planDate(w.n, 0) ? ` <span class="muted small">· ${planDate(w.n, 0).toLocaleDateString('vi-VN', { day: 'numeric', month: 'numeric' })}–${planDate(w.n, 6).toLocaleDateString('vi-VN', { day: 'numeric', month: 'numeric' })}</span>` : ''} <span class="tag ${wdone === wd.length ? 'on' : ''}">${wdone}/${wd.length}</span></summary>
    <div class="days">${w.days.map((d, i) => { if (!d.text) return ''; const dt = planDate(w.n, i); const ok = S.plan[d.id]?.done; const off = /^NGHỈ/.test(d.text);
      return `<div class="day ${ok ? 'done' : ''} ${dt?.getTime() === todayT ? 'today' : ''} ${off ? 'off' : ''}"><label class="chk"><input type="checkbox" data-d="${d.id}" ${ok ? 'checked' : ''} ${off ? 'disabled' : ''}><span><b>${DOW[i]}</b>${dt ? ` <span class="muted small">${dt.toLocaleDateString('vi-VN', { day: 'numeric', month: 'numeric' })}</span>` : ''}</span></label><div class="plan-text">${linkPlan(d.text, secs)}</div></div>`; }).join('')}</div></details>`; }).join('')}
  ${P.note ? `<p class="muted small">${esc(P.note)}</p>` : ''}`;
  $$('[data-d]').forEach(c => c.onchange = () => { S.plan[c.dataset.d] = { done: c.checked, t: Date.now() }; save(); c.closest('.day').classList.toggle('done', c.checked); });
  $('#ps').onchange = e => { S.settings.planStart = e.target.value; save(); route(); };
  $('#psNow').onclick = () => { S.settings.planStart = todayKey(mondayOf()); save(); route(); };
  $('#psClear')?.addEventListener('click', () => { S.settings.planStart = ''; save(); route(); });
  if (q.w) document.getElementById('wk' + q.w)?.scrollIntoView();
});

/* ---------------- Thẻ ôn tập ---------------- */
function cardHTML(x, flipped) {
  const it = x.it;
  if (x.type === 'v') {
    const long = it.w.length > 7;
    return `<span class="kind tag">Từ vựng</span><span class="say">${vSay(it)}</span>
      <div class="front ${long ? 'long' : ''}">${esc(it.w)}</div>
      ${flipped ? `<div class="back">${it.r ? `<div class="reading">${esc(it.r)}</div>` : ''}${it.hv ? `<div class="hv">${esc(it.hv)}</div>` : ''}
      <div class="meaning">${esc(it.m)}</div>${(it.ex || []).length ? `<ul class="exs">${it.ex.slice(0, 3).map((e, k) => `<li>${esc(e)}${it.exvi?.[k] ? `<div class="exvi">${esc(it.exvi[k])}</div>` : ''}</li>`).join('')}</ul>` : ''}</div>` : ''}`;
  }
  if (x.type === 'k') {
    return `<span class="kind tag">Kanji</span><span class="say">${sayBtn(it.ex[0] || it.k)}</span><div class="front kanji">${esc(it.k)}</div>
      ${flipped ? `<div class="back"><div class="hv" style="font-size:1.1rem">${esc(it.hv)}</div>${it.m ? `<div class="kvi">${esc(it.m)}</div>` : ''}
      <div class="small">On: <span class="jp">${sayList(it.on)}</span> · Kun: <span class="jp">${sayList(it.kun)}</span></div>
      <ul class="exs">${it.ex.map((e, i) => `<li>${sayT(e)}${exVi(it, i)}</li>`).join('')}</ul>${it.tip ? `<div class="note">💡 <span class="jp">${sayT(it.tip)}</span>${it.tipm ? `<div class="tipvi">→ ${esc(it.tipm)}</div>` : ''}</div>` : ''}</div>` : ''}`;
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
  } else { const { due, fresh } = await queueToday(); keys = [...due, ...shuffle(fresh)]; if (q.skill) keys = keys.filter(k => k.startsWith(q.skill + ':')); }
  const queue = [];
  for (const k of keys) { const b = await buildItem(k); if (b) queue.push(b); }
  const total = queue.length; let done = 0, flipped = false, cur = null; const seenNew = new Set();
  const back = q.deck ? (q.deck[0] === 'v' ? `#/vocab/${q.deck.slice(2)}` : q.deck[0] === 'k' ? `#/kanji/${q.deck.slice(2)}` : `#/grammar?set=${q.deck.slice(2)}`) : q.skill ? `#/skill/${{ v: 'vocab', k: 'kanji', g: 'grammar' }[q.skill]}` : '#/today';
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
    $('#rev')?.addEventListener('click', flip); $('#card').addEventListener('click', e => { if (!flipped && !e.target.closest('button,[data-say]')) flip(); });
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
    <div class="card" style="min-height:200px"><span class="say">${vSay(it)}</span><div class="front ${it.w.length > 7 ? 'long' : ''}">${esc(it.w)}</div></div>
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
  const I = (await load('exams/index')).filter(x => x.id !== 'jn202112');
  const best = {}; for (const e of S.exams) if (e.test) best[e.test] = Math.max(best[e.test] ?? 0, e.score / e.total);
  const pct = id => best[id] !== undefined ? `<span class="tag ${best[id] >= .6 ? 'on' : ''}">${Math.round(best[id] * 100)}%</span>` : '';
  const P = realExamPairs(I); const ex = S.exams.slice(-5).reverse();
  const mockSets = [...new Set(I.filter(x => x.fmt === 'jlpt' && !/thật|JLPT N1 (chính thức|20)/.test(x.set) && !x.paper).map(x => x.set))];
  main.innerHTML = `<h1>Thi thử</h1><p class="lead">Làm đề hoàn chỉnh như thi thật. Muốn luyện riêng từng kỹ năng hoặc từng dạng câu, vào mục <a href="#/learn">Học</a>.</p>
  <div class="grid-hub">
    <a class="hub" href="#real"><span class="glyph">本</span><div><h3>Đề thật JLPT N1</h3><p>${P.length} kỳ thi 2010–2025 · đọc + nghe</p></div></a>
    <a class="hub" href="#/tests?set=${encodeURIComponent(mockSets[0] || '')}"><span class="glyph">模</span><div><h3>Đề thi thử</h3><p>36 đề + đề test đầu vào</p></div></a>
    <a class="hub" href="#/mock"><span class="glyph">試</span><div><h3>Đề tự sinh ngẫu nhiên</h3><p>Trộn từ kho từ vựng, kanji, ngữ pháp, đọc hiểu</p></div></a>
  </div>
  <h2 id="real">Đề thật theo kỳ thi</h2>
  <p class="small muted">Phần 1 “Kiến thức + Đọc” 110 phút · Phần 2 “Nghe” ~55 phút. “Luyện” = xem đáp án ngay từng câu; “Thi” = tính giờ, chấm khi nộp.</p>
  <div class="list">${P.map(p => `<div class="item exrow"><div class="glyph" style="font-size:.85rem;font-family:var(--ui)">${+p.ym.slice(5)}/${p.ym.slice(2, 4)}</div>
    <div class="body"><b>Tháng ${+p.ym.slice(5)}/${p.ym.slice(0, 4)}</b><div class="sub">${p.read ? (p.read.paper ? 'làm trên đề gốc' : p.read.id.startsWith('jr') ? 'bản scan' : 'bản chữ') : ''}${p.listen ? ' · có audio nghe' : ' · chưa có phần nghe'}</div></div>
    <div class="exbtns">${p.read ? `<div><span class="small muted">Đọc ${pct(p.read.id)}</span><a class="btn sm" href="#/test/${p.read.id}?mode=practice">Luyện</a><a class="btn sm primary" href="#/test/${p.read.id}?mode=timed">Thi 110′</a></div>` : ''}
    ${p.listen ? `<div><span class="small muted">Nghe ${pct(p.listen.id)}</span><a class="btn sm" href="#/test/${p.listen.id}?mode=practice">Luyện</a><a class="btn sm primary" href="#/test/${p.listen.id}?mode=timed">Thi 55′</a></div>` : ''}</div></div>`).join('')}</div>
  <h2>Đề thi thử & bài tập</h2>
  <div class="list">${[...new Set(I.filter(x => !realExamPairs([x]).length).map(x => x.set))].map(st => { const xs = I.filter(x => x.set === st);
    return `<a class="item" href="#/tests?set=${encodeURIComponent(st)}"><div class="glyph">本</div><div class="body"><b>${esc(st)}</b><div class="sub">${xs.length} bài · ${xs.reduce((a, x) => a + x.nq, 0)} câu</div></div><span class="chev">›</span></a>`; }).join('')}</div>
  ${ex.length ? `<h2>Lần làm gần đây</h2><div class="list">${ex.map(examRow).join('')}</div><p><a href="#/stats">Xem toàn bộ lịch sử</a></p>` : ''}`;
  $$('a[href="#real"]').forEach(a => a.onclick = e => { e.preventDefault(); $('#real').scrollIntoView({ behavior: 'smooth' }); });
});
const examRow = e => `<div class="item"><div class="glyph" style="font-size:1rem;font-family:var(--ui)">${Math.round(100 * e.score / e.total)}%</div><div class="body"><b>${esc(e.title)}</b><div class="sub">${new Date(e.at).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' })} · ${e.score}/${e.total} câu${e.secs ? ' · ' + Object.entries(e.secs).map(([k, v]) => `${k} ${v[0]}/${v[1]}`).join(', ') : ''}</div></div></div>`;
on(/^\/read$/, async (q) => {
  const R = (await load('reading')).filter(g => !q.g || g.id === q.g);
  const best = {}; for (const e of S.exams) if (e.set) best[e.set] = Math.max(best[e.set] ?? 0, e.score / e.total);
  main.innerHTML = `<a class="crumb" href="#/skill/reading">‹ Đọc hiểu</a><h1>${q.g && R[0] ? esc(R[0].title) : 'Luyện đọc hiểu'}</h1>
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
  main.innerHTML = `<a class="crumb" href="#/read?g=${g.id}">‹ ${esc(g.title)}</a><h1 class="jp">${esc(s.title)}</h1><p class="muted">${esc(g.title)}</p>
  ${s.imgOnly ? pagesHTML(s, true) : passageHTML(s) + pagesHTML(s, false)}
  <div id="qs">${questionsHTML(s.questions, '')}</div>
  <div class="row" style="margin-top:20px"><button class="btn primary" id="chk">Chấm điểm</button><span id="res"></span><span class="spacer"></span>${next ? `<a class="btn" href="#/read/${next.id}">Bài tiếp ›</a>` : ''}</div>`;
  bindOpts(main);
  $('#chk').onclick = () => {
    const list = $$('#qs .q').map((el, i) => ({ el, answer: s.questions[i].answer, explain: s.questions[i].explain && esc(s.questions[i].explain) }));
    const ok = gradeQs(main, list);
    $('#res').innerHTML = `<b class="${ok === list.length ? 'pass' : ''}">Đúng ${ok}/${list.length}</b>`;
    $('#chk').disabled = true;
    S.exams.push({ id: 'e' + Date.now(), at: Date.now(), title: 'Đọc hiểu ' + s.title, set: s.id, score: ok, total: list.length }); save();
  };
});

/* ---------------- Sách TRY! N1 ---------------- */
on(/^\/try$/, async () => {
  const B = await load('try'); const G = await load('grammar'); const gid = n => 'try' + n;
  main.innerHTML = `<a class="crumb" href="#/learn">‹ Học</a><h1>Sách TRY! N1 <span class="muted" style="font-size:.9rem">文法から伸ばす日本語</span></h1>
  <p class="lead">Mỗi bài gồm một bài đọc/nghe có audio, các mẫu ngữ pháp rút ra từ bài, và まとめの問題 ôn tập. Bấm số trang để xem trang sách gốc (có bài tập やってみよう!; đáp án ở phần 別冊 cuối sách).</p>
  <div class="row" style="margin-bottom:12px"><a class="btn" href="#/grammar">Học 123 mẫu bằng thẻ (Ngữ pháp › TRY! N1)</a><a class="btn" href="#/try/p/11">Mục lục sách</a></div>
  ${B.chapters.map(c => `<details class="grp" ${c.no === 1 && c.page === 16 ? 'open' : ''}><summary class="groupname"><span class="jp">${c.no}. ${esc(c.kind)}「${esc(c.title)}」</span> <span class="muted small">· tr. ${c.page}–${c.end}</span></summary>
    <div class="row" style="margin:8px 0">${c.tracks.map(f => `<a class="btn sm" href="#/audio?f=${encodeURIComponent(f)}">▶ Nghe bài đọc</a>`).join('')}<a class="btn sm" href="#/try/p/${c.page}">Đọc trang ${c.page}</a>${c.matome ? `<a class="btn sm primary" href="#/test/trym${c.no}?mode=practice">まとめの問題</a>` : ''}</div>
    <div class="list">${c.items.map(i => `<div class="item"><div class="glyph" style="font-size:.9rem;font-family:var(--ui)">${i.n}</div><div class="body"><a href="#/grammar/${gid(i.n)}"><b class="jp">～${esc(i.pat)}</b></a> <span class="small muted jp">${esc(i.ex)}</span><div class="sub">${esc(i.vi)}</div></div><a class="btn sm ghost" href="#/try/p/${i.page}">tr. ${i.page}</a></div>`).join('')}</div></details>`).join('')}
  <h2>Phụ lục</h2><div class="list">${B.extra.map(x => `<a class="item" href="#/try/p/${x.page}"><div class="body"><b>${esc(x.title)}</b><div class="sub">tr. ${x.page}</div></div></a>`).join('')}</div>`;
});
on(/^\/try\/p\/(\d+)$/, async (n) => {
  const B = await load('try'); n = Math.max(1, Math.min(B.pages, +n));
  const nav = `<div class="row"><a class="btn sm" href="#/try/p/${n - 1}" ${n <= 1 ? 'hidden' : ''}>‹ Trang ${n - 1}</a><span class="spacer"></span><span class="small muted">Trang ${n}/${B.pages}</span><span class="spacer"></span><a class="btn sm" href="#/try/p/${n + 1}" ${n >= B.pages ? 'hidden' : ''}>Trang ${n + 1} ›</a></div>`;
  main.innerHTML = `<a class="crumb" href="#/try">‹ Sách TRY! N1</a>${nav}<div class="crop-wrap book-page"><img src="img/try/p${String(n).padStart(3, '0')}.webp" alt="Trang ${n}"></div>${nav}`;
  const k = e => { if (e.key === 'ArrowRight' && n < B.pages) location.hash = '#/try/p/' + (n + 1); if (e.key === 'ArrowLeft' && n > 1) location.hash = '#/try/p/' + (n - 1); };
  document.addEventListener('keydown', k); cleanup = () => document.removeEventListener('keydown', k);
});

/* ---------------- Nghe ---------------- */
on(/^\/audio$/, async (q) => {
  const A = await load('audio');
  const PK = 'n1.audiopos'; let pos = {}; try { pos = JSON.parse(localStorage.getItem(PK)) || {}; } catch { }
  const fmt = s => `${s / 3600 >= 1 ? (s / 3600 | 0) + ':' : ''}${String((s % 3600) / 60 | 0).padStart(2, '0')}:${String(s % 60 | 0).padStart(2, '0')}`;
  const all = A.flatMap(g => g.tracks.map(t => ({ ...t, g: g.id })));
  let cur = all.find(t => t.f === (q.f || pos._last)) || all[0];
  main.innerHTML = `<a class="crumb" href="#/learn">‹ Học</a><h1>Nghe</h1><p class="lead">Bấm một bài để phát. Ứng dụng nhớ chỗ bạn đang nghe ở từng bài và tự chuyển sang bài kế tiếp.</p>
  <div class="panel player"><div class="jp" id="now" style="font-weight:700"></div>
   <audio id="au" controls preload="metadata" style="width:100%;margin:10px 0"></audio>
   <div class="row"><button class="btn sm" id="back">−10s</button><button class="btn sm" id="fwd">+10s</button><span class="spacer"></span><span class="small muted">Tốc độ</span><div class="seg" id="spd">${[0.75, 1, 1.25, 1.5].map(v => `<button data-v="${v}">${v}×</button>`).join('')}</div></div>
   <details class="tx-wrap" id="txw" open><summary class="small">Bản chép lời <span class="muted">(tự động — chạm một dòng để nghe từ đó)</span></summary><div class="transcript jp" id="tx"></div></details></div>
  ${A.map(g => `<h2>${esc(g.title)}</h2><p class="small muted">${esc(g.desc)}</p><div class="list">${g.tracks.map(t => `<a class="item track" href="javascript:void 0" data-f="${t.f}"><div class="glyph" style="font-size:.9rem;font-family:var(--ui)">▶</div><div class="body"><b>${esc(t.t)}</b><div class="sub">${fmt(t.d)}${pos[t.f] ? ' · đang nghe ở ' + fmt(pos[t.f]) : ''}</div></div></a>`).join('')}</div>`).join('')}`;
  const au = $('#au'); let rate = 1; try { rate = +localStorage.getItem('n1.rate') || 1; } catch { }
  const setRate = v => { rate = v; au.playbackRate = v; $$('#spd button').forEach(b => b.classList.toggle('on', +b.dataset.v === v)); try { localStorage.setItem('n1.rate', v); } catch { } };
  const savePos = () => { if (!cur) return; pos[cur.f] = au.currentTime > cur.d - 3 ? 0 : au.currentTime; pos._last = cur.f; try { localStorage.setItem(PK, JSON.stringify(pos)); } catch { } };
  const open = (t, play) => {
    cur = t; au.src = t.f; $('#now').textContent = A.find(g => g.id === t.g).title + ' — ' + t.t;
    $('#tx').innerHTML = (t.seg || []).map((x, k) => `<p data-k="${k}">${esc(x[2])}</p>`).join('') || '<p class="muted">Không có bản chép lời.</p>'; $('#txw').hidden = !(t.seg || []).length; lastK = -1;
    $$('.track').forEach(a => a.classList.toggle('on', a.dataset.f === t.f));
    au.onloadedmetadata = () => { if (pos[t.f]) au.currentTime = pos[t.f]; au.playbackRate = rate; if (play) au.play().catch(() => { }); };
  };
  $$('.track').forEach(a => a.onclick = () => { savePos(); open(all.find(t => t.f === a.dataset.f), true); });
  $$('#spd button').forEach(b => b.onclick = () => setRate(+b.dataset.v));
  $('#back').onclick = () => au.currentTime = Math.max(0, au.currentTime - 10);
  $('#fwd').onclick = () => au.currentTime += 10;
  let last = 0, lastK = -1; au.ontimeupdate = () => {
    if (Date.now() - last > 4000) { last = Date.now(); savePos(); }
    const sg = cur.seg || []; const ct = au.currentTime; let k = -1;
    for (let i = 0; i < sg.length; i++) { if (sg[i][0] <= ct + .05) k = i; else break; }
    if (k !== lastK) { lastK = k; $$('#tx p.on').forEach(p => p.classList.remove('on')); const p = k >= 0 && $(`#tx p[data-k="${k}"]`); if (p) { p.classList.add('on'); const box = $('#tx'); box.scrollTop = p.offsetTop - box.offsetTop - box.clientHeight / 3; } }
  };
  $('#tx').onclick = e => { const p = e.target.closest('p[data-k]'); if (!p) return; au.currentTime = cur.seg[+p.dataset.k][0]; au.play().catch(() => { }); };
  au.onended = () => { pos[cur.f] = 0; savePos(); const i = all.indexOf(cur); if (all[i + 1] && all[i + 1].g === cur.g) open(all[i + 1], true); };
  au.onratechange = () => { if (au.playbackRate !== rate) setRate(au.playbackRate); };
  setRate(rate); open(cur, false);
  cleanup = () => { savePos(); au.pause(); };
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

/* ---------------- Đề thi đầy đủ ---------------- */
const ul = s => esc(s).replace(/⟦/g, '<u>').replace(/⟧/g, '</u>');
function jpParas(text) {
  const ls = text.split('\n').filter(l => l.trim()); if (!ls.length) return '';
  const mx = Math.max(...ls.map(l => l.length)); const out = []; let buf = '', prev = '';
  for (const l of ls) {
    if (buf && prev.length >= mx * 0.8 && !/^([（(][0-9０-９]+[)）]|[（(]注|＊|※|[AB]\s|[AB]$)/.test(l)) buf += l; else { if (buf) out.push(buf); buf = l; }
    prev = l;
  }
  if (buf) out.push(buf);
  return out.map(p => /^[（(][0-9０-９]+[)）]$|^[AB]$/.test(p) ? `<p class="nb">${ul(p)}</p>` : /^(（注|\(注|＊|※)/.test(p) ? `<p class="note">${ul(p)}</p>` : `<p>${ul(p)}</p>`).join('');
}
const SEC_GROUP = n => n <= 4 ? '文字・語彙' : n <= 7 ? '文法' : '読解';
const scanTxt = () => { let v = null; try { v = localStorage.getItem('n1.scantxt'); } catch { } return v === null ? matchMedia('(max-width: 700px)').matches : v === '1'; };
// Cắt vùng ảnh trang scan: img = [[trang, y0, y1, rộng, cao]] theo toạ độ ảnh gốc (margin-top % tính theo bề rộng)
function cropHTML(img) {
  return `<div class="crop-wrap" title="Chạm để phóng to / thu nhỏ">${img.map(([p, y0, y1, W, H, x0 = 0, x1 = W]) => { const cw = x1 - x0;
    return `<div class="crop" style="aspect-ratio:${cw}/${y1 - y0};width:min(100%,${Math.round(cw / W * 960)}px);--zw:${Math.round(cw / W * 960)}px"><img loading="lazy" src="data/scan/p${String(p).padStart(3, '0')}.webp" style="width:${(W / cw * 100).toFixed(3)}%;margin-left:${(-x0 / cw * 100).toFixed(3)}%;margin-top:${(-y0 / cw * 100).toFixed(3)}%" alt="Đề gốc trang ${p}"></div>`; }).join('')}</div>`;
}
const numOpts = () => `<div class="opts nums">${[1, 2, 3, 4].map(j => `<button class="opt" data-a="${j}"><span class="n">${j}</span></button>`).join('')}</div>`;
function testBlocks(sec, pfx) {
  const txt = scanTxt();
  return sec.blocks.map(b => b.pq ? `<div class="q pq" data-n="${pfx}${b.n}"><span class="pn">${b.lab || b.n}</span>${numOpts()}</div>` : b.img && !txt ? (b.t === 'text' ? `<div class="passage scan">${cropHTML(b.img)}</div>` : `<div class="q scan" data-n="${pfx}${b.n}">${cropHTML(b.img)}${numOpts()}</div>`) :
    b.img && b.t === 'q' && b.o.length !== 4 ? `<div class="q scan" data-n="${pfx}${b.n}"><div class="qt">${b.n}．${b.q ? ul(b.q) : ''}</div>${cropHTML(b.img)}${numOpts()}</div>` :
    b.t === 'text' ? `<div class="passage">${jpParas(b.text)}</div>` : b.t === 'pre' ? `<pre class="passage pre">${esc(b.text)}</pre>` :
    `<div class="q" data-n="${pfx}${b.n}"><div class="qt">${b.n}．${b.q ? ul(b.q) : ''}</div><div class="opts" style="${b.o.every(o => o.length < 12) ? 'grid-template-columns:repeat(auto-fit,minmax(140px,1fr))' : ''}">${b.o.map((o, j) => `<button class="opt" data-a="${j + 1}"><span class="n">${j + 1}</span><span>${ul(o)}</span></button>`).join('')}</div></div>`).join('');
}
on(/^\/tests$/, async (q) => {
  const I = (await load('exams/index')).filter(x => x.id !== 'jn202112' && (!q.set || x.set === q.set));
  const best = {}; for (const e of S.exams) if (e.test) best[e.test] = Math.max(best[e.test] ?? 0, e.score / e.total);
  const sets = [...new Set(I.map(x => x.set))];
  main.innerHTML = `<a class="crumb" href="#/exam">‹ Thi thử</a><h1>${q.set ? esc(q.set) : 'Tất cả đề & bài tập'}</h1><p class="lead">${I.length} đề/bài, ${I.reduce((a, x) => a + x.nq, 0)} câu có đáp án. Đề JLPT đầy đủ tính giờ 110 phút; bài tập tính giờ theo số câu. Chọn “Luyện tập” để xem đáp án ngay sau mỗi câu.</p>
  ${sets.map((st, si) => `<details class="grp" ${si === 0 || q.set ? 'open' : ''}><summary class="groupname">${esc(st)} <span class="muted small">· ${I.filter(x => x.set === st).length} bài · ${I.filter(x => x.set === st).reduce((a, x) => a + x.nq, 0)} câu</span></summary><div class="list">${I.filter(x => x.set === st).map(x => `<div class="item"><div class="glyph" style="font-size:.95rem;font-family:var(--ui)">${best[x.id] !== undefined ? Math.round(best[x.id] * 100) + '%' : '–'}</div>
    <div class="body"><b>${esc(x.title)}</b><div class="sub">${x.nq} câu · ${x.secs.length} phần</div></div>
    <a class="btn sm" href="#/test/${x.id}?mode=practice">Luyện tập</a><a class="btn sm primary" href="#/test/${x.id}?mode=timed">Thi ${x.min || 110}′</a></div>`).join('')}</div></details>`).join('')}
  ${q.set ? '' : ''}`;
});
on(/^\/test\/(\w+)$/, async (id, q) => {
  const I = await load('exams/index'); const meta = I.find(x => x.id === id); if (!meta) throw new Error('Không tìm thấy đề');
  const E0 = await load('exams/' + id); const E = q.sec ? { ...E0, sections: E0.sections.filter(s => s.no === +q.sec), title: E0.title + ' · 問題' + q.sec } : E0; const timed = q.mode !== 'practice'; const LIM = meta.min || 110, JL = meta.fmt !== 'practice';
  const DK = 'n1.draft.' + id + (q.sec ? '.' + q.sec : ''); let draft = {}; try { draft = JSON.parse(localStorage.getItem(DK)) || {}; } catch { }
  let left = draft.left ?? LIM * 60, finished = false;
  main.innerHTML = `<div class="timer">${timed ? `<span class="clock" id="clk"></span><span class="muted small">còn lại</span>` : `<span class="muted small">Chế độ luyện tập — chọn đáp án để xem đúng/sai</span>`}<span class="spacer"></span><span class="small muted" id="cnt"></span>${timed ? '<button class="btn sm primary" id="sub">Nộp bài</button>' : ''}</div>
  <a class="crumb" href="${q.sec && id.startsWith('ls') ? '#/skill/listening' : '#/exam'}">‹ ${q.sec && id.startsWith('ls') ? 'Nghe hiểu' : 'Thi thử'}</a><h1>${esc(E.title)}</h1><p class="muted">${esc(E.set)}${q.sec && id.startsWith('ls') ? ` · <a href="#/ldrill?type=${q.sec}">Đề khác cùng dạng ›</a>` : ''}</p>
  ${E.scan ? `<div class="row" style="margin-bottom:8px"><div class="seg" id="scanmode"><button data-m="0" class="${scanTxt() ? '' : 'on'}">Ảnh đề gốc</button><button data-m="1" class="${scanTxt() ? 'on' : ''}">Chữ (nhận dạng OCR)</button></div></div><p class="small muted">Đề scan: “Ảnh đề gốc” hiển thị đúng bản in; “Chữ” là văn bản nhận dạng tự động (có thể sai vài chữ, câu nào tách lỗi vẫn hiện ảnh gốc). Đáp án đã đối chiếu thủ công với bảng đáp án chính thức.</p>` : ''}
  ${I.some(x => x.id === 'ls' + id.slice(2)) && !id.startsWith('ls') ? `<p><a class="btn sm" href="#/test/ls${id.slice(2)}?mode=practice">▶ Phần nghe hiểu của đề này</a></p>` : ''}
  ${E.audio ? `<div class="pq-au panel" style="margin-bottom:10px"><span class="small"><b>Toàn bộ bài nghe</b></span><audio controls preload="none" src="${E.audio}" style="flex:1"></audio></div>` : ''}
  ${E.paper ? `${E.note ? `<p class="small muted">${esc(E.note)}</p>` : ''}<p class="small muted">Đọc đề trên ảnh gốc, chọn đáp án trong phiếu trả lời${matchMedia('(max-width: 900px)').matches ? ' (nút “Phiếu trả lời” ở góc dưới)' : ' bên phải'}. ${E.sections.some(x => x.au) ? '' : 'Phần nghe hiểu không có file âm thanh nên không đưa vào.'}</p>
  <div class="paper"><div class="paper-pages">${E.paper.map((u, i) => `<img loading="${i < 2 ? 'eager' : 'lazy'}" src="${u}" alt="Trang ${i + 1}">`).join('')}</div>
  <div class="paper-sheet" id="sheet"><div class="sheet-head"><b>Phiếu trả lời</b><button class="btn sm ghost" id="sheetx">Đóng</button></div>${E.sections.map(s => `<div class="pq-sec"><div class="pq-title jp">${/^問題/.test(s.name) ? esc(s.name) : `問題${s.no} <span class="muted small">${esc(s.name)}</span>`}</div>${(s.au || []).map((u, k) => `<div class="pq-au"><span class="small muted">${s.au.length > 1 ? (k + 1) + '番' : 'Audio'}</span><audio controls preload="none" src="${typeof u === 'string' ? u : u.f + '#t=' + u.a + (u.b ? ',' + u.b : '')}"></audio></div>`).join('')}${testBlocks(s, '')}</div>`).join('')}${E.script ? `<details class="small" style="margin-top:8px"><summary>${E.id.startsWith('ls') ? 'Đáp án + script nghe (原文)' : 'Đáp án chi tiết + script nghe (trang sách)'}</summary>${E.script.map(u => `<img loading="lazy" src="${u}" alt="Trang đáp án" style="width:100%;margin-top:6px">`).join('')}</details>` : ''}</div></div>
  <button class="btn primary sheet-fab" id="sheetbtn">Phiếu trả lời</button>` :
  E.sections.map(s => `<div class="sec-title">問題${s.no}　<span class="jp" style="font-weight:500">${esc(s.instr)}</span></div>${testBlocks(s, '')}`).join('')}
  <div id="result"></div>${timed ? '<div style="margin-top:20px"><button class="btn primary" id="sub2">Nộp bài</button></div>' : ''}`;
  const all = E.sections.flatMap(s => s.blocks.filter(b => b.t === 'q').map(b => ({ ...b, sec: s.no })));
  const byN = Object.fromEntries(all.map(b => [b.n, b]));
  const counter = () => { const c = $$('.q').filter(x => $('.opt.sel,.opt.right,.opt.wrong', x)).length; $('#cnt').textContent = `${c}/${all.length} câu`; };
  for (const [n, a] of Object.entries(draft.ans || {})) { const el = $(`.q[data-n="${n}"] .opt[data-a="${a}"]`); if (el) el.classList.add('sel'); }
  const saveDraft = () => { try { const ans = {}; $$('.q').forEach(x => { const s = $('.opt.sel', x); if (s) ans[x.dataset.n] = +s.dataset.a; }); localStorage.setItem(DK, JSON.stringify({ ans, left })); } catch { } };
  $$('.opt', main).forEach(b => b.onclick = () => {
    const qe = b.closest('.q'); if (qe.classList.contains('graded')) return;
    $$('.opt', qe).forEach(x => x.classList.remove('sel')); b.classList.add('sel');
    if (!timed) { gradeQs(main, [{ el: qe, answer: byN[qe.dataset.n].a, explain: byN[qe.dataset.n].note && esc(byN[qe.dataset.n].note) }]);
      const gd = $$('.q.graded'); if (gd.length === all.length && !finished) { finished = true; const ok = gd.filter(x => $('.opt.right.sel', x)).length;
        S.exams.push({ id: 'e' + Date.now(), at: Date.now(), title: E.title + ' (luyện tập)', test: id, score: ok, total: all.length, ...(q.sec && id.startsWith('ls') ? { ldrill: +q.sec } : {}) }); save();
        toast(`Xong: đúng ${ok}/${all.length}`); } }
    else saveDraft();
    counter();
  });
  counter();
  if (E.paper) { $('#sheetbtn').onclick = () => $('#sheet').classList.add('open'); $('#sheetx').onclick = () => $('#sheet').classList.remove('open'); }
  $$('#scanmode button').forEach(b => b.onclick = () => { saveDraft(); try { localStorage.setItem('n1.scantxt', b.dataset.m); } catch { } cleanup && cleanup(); cleanup = null; route(); });
  if (timed) {
    const fmt = s => `${String(s / 60 | 0).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
    $('#clk').textContent = fmt(left);
    const iv = setInterval(() => { if (finished) return; left--; $('#clk').textContent = fmt(Math.max(0, left)); $('#clk').classList.toggle('low', left < 600); if (left % 15 === 0) saveDraft(); if (left <= 0) submit(); }, 1000);
    cleanup = () => { clearInterval(iv); if (!finished) saveDraft(); };
    const submit = () => {
      if (finished) return; finished = true; clearInterval(iv);
      const groups = {}, secs = {}; let score = 0;
      for (const b of all) {
        const el = $(`.q[data-n="${b.n}"]`); const ok = gradeQs(main, [{ el, answer: b.a, explain: b.note && esc(b.note) }]);
        const g = JL ? SEC_GROUP(b.sec) : '問題' + b.sec; groups[g] ||= [0, 0]; groups[g][0] += ok; groups[g][1]++;
        const k = '問題' + b.sec; secs[k] ||= [0, 0]; secs[k][0] += ok; secs[k][1]++; score += ok;
      }
      const used = LIM * 60 - Math.max(0, left), pct = Math.round(100 * score / all.length);
      S.exams.push({ id: 'e' + Date.now(), at: Date.now(), title: E.title, test: id, score, total: all.length, secs: groups, time: used }); save(); sync();
      try { localStorage.removeItem(DK); } catch { }
      $('#result').innerHTML = `<h2>Kết quả</h2><div class="score"><div><b class="${pct >= 60 ? 'pass' : 'fail'}">${pct}%</b>${score}/${all.length} câu · ${fmt(used)}</div>${Object.entries(groups).map(([k, v]) => `<div><b>${v[0]}/${v[1]}</b><span class="jp">${k}</span></div>`).join('')}</div>
      <details class="box ${JL ? '' : 'hidden'}"><summary>Điểm từng 問題</summary><div class="score">${Object.entries(secs).map(([k, v]) => `<div><b>${v[0]}/${v[1]}</b><span class="jp">${k}</span></div>`).join('')}</div></details>
      <p class="muted small">Đáp án đúng tô xanh, câu chọn sai tô đỏ. Cuộn lên để xem lại.</p><div class="row"><a class="btn primary" href="#/tests">Chọn đề khác</a><a class="btn" href="#/stats">Xem tiến độ</a></div>`;
      $$('#sub,#sub2').forEach(b => b.disabled = true); $('#result').scrollIntoView({ behavior: 'smooth' });
    };
    $('#sub').onclick = $('#sub2').onclick = () => { const un = all.length - $$('.q').filter(x => $('.opt.sel', x)).length; if (!un || confirm(`Còn ${un} câu chưa trả lời. Nộp bài?`)) submit(); };
  }
});
const DRILL = { 1: '漢字読み · Cách đọc kanji', 2: '文脈規定 · Điền từ theo ngữ cảnh', 3: '言い換え類義 · Từ đồng nghĩa', 4: '用法 · Cách dùng từ', 5: '文法形式の判断 · Chọn ngữ pháp', 6: '文の組み立て · Sắp xếp câu (★)', 7: '文章の文法 · Ngữ pháp trong đoạn văn', 8: '内容理解（短文）', 9: '内容理解（中文）', 10: '内容理解（長文）', 11: '統合理解 · Đọc so sánh A/B', 12: '主張理解（長文）', 13: '情報検索 · Tìm thông tin' };
on(/^\/drill$/, async (q) => {
  const I = (await load('exams/index')).filter(x => x.fmt !== 'practice' && !x.paper);
  if (!q.type) {
    const cnt = {}; for (const x of I) for (const [n, c] of x.secs) cnt[n] = (cnt[n] || 0) + c;
    main.innerHTML = `<a class="crumb" href="#/learn">‹ Học theo kỹ năng</a><h1>Luyện theo dạng câu</h1><p class="lead">Câu hỏi gom từ ${I.length} đề. Dạng 1–6: 10 câu ngẫu nhiên mỗi lượt; dạng 7–13: một bài đọc hoàn chỉnh.</p>
    <div class="list">${Object.entries(DRILL).map(([n, name]) => `<a class="item" href="#/drill?type=${n}"><div class="glyph" style="font-size:1rem;font-family:var(--ui)">${n}</div><div class="body"><b class="jp">問題${n}　${name}</b><div class="sub">${cnt[n] || 0} câu trong kho</div></div></a>`).join('')}</div>`;
    return;
  }
  const type = +q.type; const ids = shuffle(I.filter(x => x.secs.some(s => s[0] === type)).map(x => x.id));
  let html = '', items = [];
  if (type <= 6) {
    const pool = [];
    for (const id of ids.slice(0, 12)) { const E = await load('exams/' + id); const s = E.sections.find(z => z.no === type); if (s) for (const b of s.blocks) if (b.t === 'q') pool.push({ ...b, src: E.title }); }
    items = pick(pool, 10).map((b, i) => ({ ...b, n: i + 1 }));
    html = items.map(b => testBlocks({ blocks: [b] }, 'd') + `<div class="muted small" style="margin-top:2px">${esc(b.src)}</div>`).join('');
  } else {
    const E = await load('exams/' + ids[0]); const s = E.sections.find(z => z.no === type);
    items = s.blocks.filter(b => b.t === 'q'); html = `<p class="muted small">${esc(E.title)}</p>` + testBlocks(s, 'd');
  }
  const inst = items.length ? '' : '<p class="muted">Không có câu hỏi.</p>';
  main.innerHTML = `<a class="crumb" href="#/skill/${+q.type === 1 ? 'kanji' : +q.type <= 4 ? 'vocab' : +q.type <= 7 ? 'grammar' : 'reading'}">‹ ${+q.type === 1 ? 'Kanji' : +q.type <= 4 ? 'Từ vựng' : +q.type <= 7 ? 'Ngữ pháp' : 'Đọc hiểu'}</a><h1 class="jp">問題${type}　${esc(DRILL[type])}</h1>${inst}${html}
  <div class="row" style="margin-top:20px"><span id="res"></span><span class="spacer"></span><button class="btn primary" id="again">Lượt mới</button></div>`;
  let right = 0, done = 0;
  $$('.opt', main).forEach(b => b.onclick = () => {
    const qe = b.closest('.q'); if (qe.classList.contains('graded')) return;
    b.classList.add('sel'); const it = items.find(x => 'd' + x.n === qe.dataset.n);
    right += gradeQs(main, [{ el: qe, answer: it.a }]); done++;
    $('#res').innerHTML = `<b>Đúng ${right}/${done}</b>`;
    if (done === items.length) { S.exams.push({ id: 'e' + Date.now(), at: Date.now(), title: 'Luyện dạng 問題' + type, score: right, total: done, drill: type }); save(); }
  });
  $('#again').onclick = () => route();
});

/* ---------------- Kính ngữ ---------------- */
on(/^\/keigo$/, async (q) => {
  const K = await load('keigo');
  if (q.quiz) {
    const qs = shuffle(K.verbs).slice(0, 12).map(v => { const kind = Math.random() < .5 ? 'son' : 'ken'; return { v, kind }; }).filter(x => x.v[x.kind] && x.v[x.kind] !== '―');
    let i = 0, right = 0;
    const render = () => {
      if (i >= qs.length) { main.innerHTML = `<div class="done"><div class="hanko"><div><b>${right}</b><span>/${qs.length}</span></div></div><h1>Kết quả kính ngữ</h1><div class="row" style="justify-content:center"><a class="btn" href="#/keigo">Bảng kính ngữ</a><button class="btn primary" id="again">Làm lại</button></div></div>`; $('#again').onclick = () => route(); return; }
      const { v, kind } = qs[i]; const ans = v[kind];
      const opts = shuffle([ans, ...pick(K.verbs.filter(x => x !== v).map(x => x[kind]).filter(x => x && x !== '―'), 3)]);
      main.innerHTML = `<div class="session-top"><a class="btn sm ghost" href="#/keigo">✕</a><div class="prog"><i style="width:${100 * i / qs.length}%"></i></div><span class="small muted">${i + 1}/${qs.length}</span></div>
      <div class="card" style="min-height:180px"><span class="kind tag">${kind === 'son' ? '尊敬語 · tôn kính' : '謙譲語 · khiêm nhường'}</span><div class="front long">${esc(v.v)}</div></div>
      <div class="choices wide">${opts.map(o => `<button class="choice jp" data-ok="${o === ans}">${esc(o)}</button>`).join('')}</div>`;
      $$('.choice').forEach(b => b.onclick = () => { const ok = b.dataset.ok === 'true'; if (ok) right++; $$('.choice').forEach(x => { x.disabled = true; if (x.dataset.ok === 'true') x.classList.add('right'); }); if (!ok) b.classList.add('wrong'); setTimeout(() => { if (!document.body.contains(b)) return; i++; render(); }, ok ? 700 : 1800); });
    };
    render(); return;
  }
  main.innerHTML = `<a class="crumb" href="#/learn">‹ Học</a><h1>Kính ngữ 敬語</h1>
  <div class="row" style="margin-bottom:16px"><a class="btn primary" href="#/keigo?quiz=1">Trắc nghiệm kính ngữ</a><a class="btn" href="#/vocab/keigo">Học bằng thẻ</a></div>
  <div class="stat-grid" style="margin-bottom:16px">${[['尊敬語', K.usage.son], ['謙譲語', K.usage.ken], ['丁寧語', K.usage.tei]].map(([a, b]) => `<div class="stat"><b class="jp" style="font-size:1.2rem">${a}</b><span>${esc(b)}</span></div>`).join('')}</div>
  <div class="table-wrap"><table class="kt"><thead><tr><th>基本形</th><th>尊敬語</th><th>謙譲語</th><th>丁寧語</th></tr></thead><tbody>
  ${K.verbs.map(v => `<tr><td><b>${esc(v.v)}</b></td><td>${esc(v.son)}</td><td>${esc(v.ken)}</td><td>${esc(v.tei)}</td></tr>`).join('')}</tbody></table></div>
  <h2>Công thức</h2><div class="panel jp">${K.rules.map(r => `<p>${r.map(esc).join('<br>').replace(/・/g, '<br>・').replace(/^<br>/, '')}</p>`).join('')}</div>
  <h2>Lỗi kính ngữ hay gặp</h2><div class="table-wrap"><table class="kt"><thead><tr><th>✗ Sai</th><th>✓ Đúng</th></tr></thead><tbody>${K.mistakes.map(m => `<tr><td>${esc(m.bad)}</td><td>${esc(m.good)}</td></tr>`).join('')}</tbody></table></div>
  ${K.phrases?.length ? `<h2>Câu mẫu kính ngữ (bài nghe ôn tập)</h2>${[...new Set(K.phrases.map(p => p.sec))].map(sec => `<details class="box"><summary>${esc(sec)}</summary>${K.phrases.filter(p => p.sec === sec).map(p => `<h3 class="jp" style="margin-top:12px">${esc(p.title)}</h3><ul class="gram-ex">${p.ex.map(e => `<li>${esc(e)} ${sayBtn(e).replace('icon-btn', 'icon-btn inline')}</li>`).join('')}</ul>`).join('')}</details>`).join('')}` : ''}
  <h2>Từ thường → cách nói trang trọng</h2><div class="table-wrap"><table class="kt"><thead><tr><th>Thường ngày</th><th>Công việc</th></tr></thead><tbody>${K.formal.map(m => `<tr><td>${esc(m.plain)}</td><td>${esc(m.formal)}</td></tr>`).join('')}</tbody></table></div>`;
});

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
  const ex = S.exams.filter(e => !e.set && !e.drill).slice(-15);
  const W = 560, H = 160;
  const pts = ex.map((e, i) => [20 + i * (W - 40) / Math.max(1, ex.length - 1), H - 20 - (H - 40) * e.score / e.total]);
  const chart = ex.length ? `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Điểm các đề thi thử">
    ${[0, 50, 100].map(p => `<line x1="20" x2="${W - 20}" y1="${H - 20 - (H - 40) * p / 100}" y2="${H - 20 - (H - 40) * p / 100}" stroke="var(--line)" stroke-dasharray="${p === 0 ? '' : '3 4'}"/><text x="0" y="${H - 16 - (H - 40) * p / 100}" font-size="10" fill="var(--ink-3)">${p}</text>`).join('')}
    <polyline fill="none" stroke="var(--indigo-2)" stroke-width="2" points="${pts.map(p => p.join(',')).join(' ')}"/>
    ${pts.map((p, i) => `<circle cx="${p[0]}" cy="${p[1]}" r="4" fill="var(--indigo-2)"><title>${esc(ex[i].title)}: ${Math.round(100 * ex[i].score / ex[i].total)}%</title></circle>`).join('')}</svg>` : '<p class="muted">Chưa có đề thi thử nào. <a href="#/mock">Làm đề đầu tiên</a></p>';
  const SS = await skillStats();
  const skillHTML = `<h2>Theo kỹ năng</h2><div class="skillstats">${Object.entries(SKILLS).map(([k, v]) => { const x = SS[k];
    const learn = x.l != null ? `<div><b>${x.l}</b> đã học · <b>${x.m}</b> thuộc</div><div class="bar"><i style="width:${100 * x.m / Math.max(1, x.n)}%"></i></div>` : '';
    return `<a class="sk" href="#/skill/${k}"><span class="glyph">${v.glyph}</span><div><b>${v.name}</b>${learn}<div class="small muted">${x.acc != null ? `Luyện đề: đúng ${x.acc}%` : 'Chưa luyện đề dạng này'}</div></div></a>`; }).join('')}</div>`;
  main.innerHTML = `<h1>Tiến độ</h1><p class="lead">Chuỗi ${streak()} ngày · tổng ${totalRev} lượt ôn · nhớ ${totalRev ? Math.round(100 * totalOk / totalRev) : 0}%</p>
  ${skillHTML}
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
if ('serviceWorker' in navigator && location.protocol === 'https:') {
  const had = !!navigator.serviceWorker.controller;
  navigator.serviceWorker.register('sw.js', { updateViaCache: 'none' }).then(r => { r.update(); setInterval(() => r.update(), 10 * 60 * 1000); document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') r.update(); }); });
  // có phiên bản mới → tự tải lại một lần
  let reloaded = false;
  navigator.serviceWorker.addEventListener('controllerchange', () => { if (had && !reloaded) { reloaded = true; location.reload(); } });
}
