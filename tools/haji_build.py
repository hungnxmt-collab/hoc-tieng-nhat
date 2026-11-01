# Ghép kết quả OCR từng trang của はじめての N1 単語3000 thành các bộ thẻ (100 từ/bộ),
# đánh dấu mục nghi ngờ (không có trong JMdict, thiếu cách đọc/nghĩa/ví dụ) và cắt ảnh gốc cho các mục đó.
import json, glob, re, sys, pickle, unicodedata, os
sys.path.insert(0, '/home/claude/scripts'); import vnfix
from haji import vclean
from PIL import Image
JM = pickle.load(open('/home/claude/dict/jm.pkl', 'rb'))
REPO = '/home/claude/hoc-tieng-nhat'; IMGDIR = f'{REPO}/img/w3000'; os.makedirs(IMGDIR, exist_ok=True)
POS = {'名': 'danh từ', '動': 'động từ', '副': 'phó từ', '形': 'tính từ', '慣': 'quán ngữ', '連': 'liên từ', '接': 'tiếp từ', '感': 'cảm thán'}
items = []
for f in sorted(glob.glob('/home/claude/raw/haji/json/p*.json')):
    p = int(re.search(r'p(\d+)', f).group(1))
    for e in json.load(open(f)):
        e['page'] = p; items.append(e)
# số thứ tự: sửa số OCR sai bằng thứ tự liên tiếp
for k, e in enumerate(items):
    prev = items[k - 1]['n'] if k else 0
    if not e['n'] or (prev and not (prev < e['n'] <= prev + 3)):
        e['n'] = (prev or 0) + 1
items.sort(key=lambda e: e['n'])
core = lambda w: re.split(r'[〈［]', w)[0]
out = []; flagged = 0
for e in items:
    vi = vclean(e['vi']); exvi = vclean(e['exvi'])
    w = core(e['w']); ok = (w in JM['k2r'] and (not e['r'] or e['r'] in JM['k2r'][w])) or (w in JM['kana'])
    stem = re.sub(r'[ぁ-ん]{1,2}$', '', w) if re.search(r'[一-龥]', w) else w
    inex = bool(stem) and stem in e['ex']
    chk = not ok or not e['r'] or not vi or not e['ex'] or not exvi or not inex
    it = dict(id=f'h3k{e["n"]}', w=e['w'], r=e['r'], hv='', m=vi + (f' ({POS[e["pos"]]})' if e.get('pos') in POS else ''),
              ex=[e['ex']] if e['ex'] else [], exvi=[exvi] if exvi else [])
    rel = [x for x in e.get('plus', []) if x.get('w') and x.get('vi')]
    if rel: it['rel'] = [f"{x['w']}: {vclean(x['vi'])}" for x in rel]
    if chk:
        flagged += 1
        png = f'/home/claude/raw/haji/png_p{e["page"]:03d}.png'
        if os.path.exists(png):
            y0, y1, x0, x1, W, H = e['img']
            im = Image.open(png).convert('RGB').crop((max(0, x0), max(0, y0), min(W, x1), min(H, y1)))
            im = im.resize((900, round(im.height * 900 / im.width)), Image.LANCZOS)
            im.save(f'{IMGDIR}/{e["n"]}.webp', 'WEBP', quality=60, method=6)
            it['img'] = f'img/w3000/{e["n"]}.webp'
        it['chk'] = 1
    out.append(it)
# bộ 100 từ
decks = []
for k in range(0, len(out), 100):
    part = out[k:k + 100]
    a, b = part[0]['id'][3:], part[-1]['id'][3:]
    decks.append(dict(id=f'h3k_{k // 100 + 1}', group='はじめての N1 単語3000 (Hàn–Việt, OCR)', sec='', name=f'#{a}–{b}', items=part))
json.dump(decks, open('/home/claude/raw/haji/decks.json', 'w'), ensure_ascii=False)
print('items', len(out), 'flagged', flagged, 'decks', len(decks), 'range', out[0]['id'], out[-1]['id'], file=sys.stderr)
nums = [int(i['id'][3:]) for i in out]; gaps = [n for n in range(nums[0], nums[-1]) if n not in set(nums)]
print('missing numbers', len(gaps), gaps[:30], file=sys.stderr)
