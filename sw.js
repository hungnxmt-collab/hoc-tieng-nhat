const V='n1-v10';
const CORE=['./','index.html','styles.css','app.js','manifest.webmanifest','icon.svg','data/vocab.json','data/kanji.json','data/grammar.json','data/reading.json','data/plan.json'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(CORE)));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))));self.clients.claim();});
self.addEventListener('fetch',e=>{
  const u=new URL(e.request.url);
  if(e.request.method!=='GET'||u.hostname==='api.github.com'||e.request.headers.has('range')||u.pathname.includes('/audio/'))return;
  // mạng trước cho code/dữ liệu (luôn mới nhất), dùng bộ nhớ đệm khi offline
  e.respondWith(fetch(e.request).then(r=>{if(r.ok&&(u.origin===location.origin||u.hostname.includes('fonts.')))caches.open(V).then(c=>c.put(e.request,r.clone()));return r;}).catch(()=>caches.match(e.request,{ignoreSearch:true})));
});
