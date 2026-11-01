# Ghép OCR sách はじめての N1 単語3000 với audio CD2 (1.852 file, mỗi file 1 mục: từ + câu ví dụ, đã chép lời).
# - Căn OCR ↔ số mục audio bằng quy hoạch động theo độ giống câu ví dụ (OCR có thể sót mục).
# - Chọn từ đầu mục: xác nhận chéo OCR (chữ + furigana) với từ đọc trong audio qua JMdict.
# - Mục OCR bị sót: lấy từ + ví dụ từ audio. Chia bộ thẻ theo 14 chương × 5 bài của sách.
import json, glob, re, sys, pickle, os, difflib
sys.path.insert(0, '/home/claude/scripts')
from haji import vclean
from PIL import Image
JM = pickle.load(open('/home/claude/dict/jm.pkl', 'rb'))
REPO = '/home/claude/hoc-tieng-nhat'; IMGDIR = f'{REPO}/img/w3000'; os.makedirs(IMGDIR, exist_ok=True)
POS = {'名': 'danh từ', '動': 'động từ', '副': 'phó từ', '形': 'tính từ', '慣': 'quán ngữ', '連': 'liên từ', '接': 'tiếp từ', '感': 'cảm thán'}
ST = json.load(open('/home/claude/raw/cd/struct.json')); ASR = json.load(open('/home/claude/raw/cd/asr.json'))
clean = lambda t: re.sub(r'[\s、。！？!?「」『』()（）・…]', '', t or '')
core = lambda w: re.split(r'[〈［]', w)[0]
KAN = re.compile(r'[一-龥々]')
# --- audio: tách từ đầu mục / câu ví dụ theo khoảng lặng giữa các token
clips = {}
for k, v in ASR.items():
    n = int(k); tok, ts = v['tok'], v['ts']
    cut = None
    for i in range(1, len(tok)):
        if ts[i] - ts[i - 1] > .45 and ''.join(tok[:i]).strip(): cut = i; break
    hw = ''.join(tok[:cut]).strip() if cut else ''
    ex = ''.join(tok[cut:]).strip() if cut else v['t']
    hw = re.sub(r'[\s。、？?！!]', '', hw); ex = re.sub(r'\s+', '', ex)
    if hw and ex.startswith(hw) and len(ex) > len(hw) + 3: ex = ex[len(hw):]   # từ đọc lặp
    clips[n] = dict(hw=hw, ex=ex, raw=v['t'])
N = max(clips)
# --- OCR theo thứ tự trang
ocr = []
for f in sorted(glob.glob('/home/claude/raw/haji/json/p*.json')):
    p = int(re.search(r'p(\d+)', f).group(1))
    for e in json.load(open(f)): e['page'] = p; ocr.append(e)
M = len(ocr)
def sim(e, c):
    a, b = clean(e['ex']), clean(c['ex'])
    s = difflib.SequenceMatcher(None, a, b, autojunk=False).ratio() if a and b else 0
    w = core(e['w'])
    if w and (w in c['raw'] or (c['hw'] and (c['hw'] in w or w in c['hw']))): s += .3
    return s
# --- quy hoạch động có dải: OCR i ↔ clip j (j - i trong [-5, 80])
NEG = -1e9; LO, HI = -5, 80
score = {(0, 0): 0.}; back = {}
for i in range(M + 1):
    for j in range(max(0, i + LO), min(N, i + HI) + 1):
        if (i, j) == (0, 0): continue
        best = (NEG, None)
        if i > 0 and j > 0 and (i - 1, j - 1) in score:
            s = sim(ocr[i - 1], clips[j]); s = s if s > .35 else s - 1.2
            best = max(best, (score[(i - 1, j - 1)] + s, 'm'))
        if j > 0 and (i, j - 1) in score: best = max(best, (score[(i, j - 1)] - .05, 'c'))      # clip không có OCR
        if i > 0 and (i - 1, j) in score: best = max(best, (score[(i - 1, j)] - .6, 'o'))       # OCR thừa
        if best[1]: score[(i, j)] = best[0]; back[(i, j)] = best[1]
i, j = M, N; pairs = {}
while (i, j) != (0, 0):
    b = back[(i, j)]
    if b == 'm': pairs[j] = ocr[i - 1]; i -= 1; j -= 1
    elif b == 'c': j -= 1
    else: i -= 1
print('matched', len(pairs), 'of clips', N, 'ocr', M, file=sys.stderr)
# --- dựng mục
def readings(w): return JM['k2r'].get(w) or ({w} if w in JM['kana'] else set())
def stem_of(w): return re.sub(r'[ぁ-ん]{1,2}$', '', w) if KAN.search(w) else w
out = []; stats = dict(asr_fix=0, ocr_only=0, from_audio=0, flag=0)
for n in range(1, N + 1):
    c = clips[n]; e = pairs.get(n)
    if e:
        w = e['w']; cw = core(w); tail = w[len(cw):]
        rd = e['r']; vi = vclean(e['vi']); exvi = vclean(e['exvi']); ex = e['ex']
        st = stem_of(cw)
        ok_ocr = bool(readings(cw)) and (not rd or rd in readings(cw))
        heard = bool(st) and (st in c['raw'] or st in c['hw'])
        # sửa theo audio: từ đọc trong audio có trong từ điển và cách đọc khớp furigana / OCR không chắc chắn
        h = c['hw']
        if h and h != cw and readings(h) and not heard:
            hs = stem_of(h)
            if not ok_ocr or (not (st and st in ex) and hs and hs in ex):
                cw = h; rs = readings(h); rd = rd if rd in rs else (min(rs, key=lambda x: difflib.SequenceMatcher(None, x, rd or '').ratio() * -1) if rs else rd)
                stats['asr_fix'] += 1; st = stem_of(cw); heard = True; ok_ocr = True
        # ví dụ: OCR lỗi nặng (ký tự lạ) thì dùng câu nghe được
        a, b = clean(ex), clean(c['ex'])
        if not a or re.search(r'[A-Za-z0-9]{3,}|[|_]', ex) or difflib.SequenceMatcher(None, a, b).ratio() < .5: ex = c['ex'] or ex
        inex = bool(st) and st in ex
        single = len(cw) == 1 and KAN.search(cw) and re.search(re.escape(cw) + r'[一-龥]', ex or '')
        chk = not (ok_ocr and (heard or inex)) or not rd or not vi or not exvi or bool(single) or len(cw) == 0
        it = dict(id=f'h3k{n}', w=cw + tail, r=rd, hv='', m=vi + (f' ({POS[e["pos"]]})' if e.get('pos') in POS else ''),
                  ex=[ex] if ex else [], exvi=[exvi] if exvi else [])
        rel = [x for x in e.get('plus', []) if re.fullmatch(r'[一-龥ぁ-んァ-ンー〈〉]{2,}', x.get('w') or '') and (KAN.search(x['w']) or len(x['w']) >= 3)]
        rel = [f"{x['w']}: {v}" for x in rel for v in [vclean(x['vi'])] if len(v) >= 3 and not re.search(r'\d\)', v)]
        if rel: it['rel'] = rel
        if chk:
            png = f'/home/claude/raw/haji/png_p{e["page"]:03d}.png'
            if os.path.exists(png):
                y0, y1, x0, x1, W, H = e['img']
                im = Image.open(png).convert('RGB').crop((max(0, x0), max(0, y0), min(W, x1), min(H, y1)))
                im = im.resize((900, round(im.height * 900 / im.width)), Image.LANCZOS)
                im.save(f'{IMGDIR}/{n}.webp', 'WEBP', quality=60, method=6); it['img'] = f'img/w3000/{n}.webp'
            it['chk'] = 1; stats['flag'] += 1
    else:   # OCR sót mục này: dùng audio
        h = c['hw']; rs = sorted(readings(h))
        it = dict(id=f'h3k{n}', w=h or '（nghe audio）', r=rs[0] if len(rs) == 1 else '', hv='', m='(OCR sót mục này — nghĩa xem trong sách; từ và ví dụ lấy từ audio)',
                  ex=[c['ex']] if c['ex'] else [], exvi=[], chk=1, src='audio'); stats['from_audio'] += 1
    it['au3'] = f'audio/w3k/{n:04d}.mp3'
    out.append(it)
# --- bộ thẻ theo bài
secs = ST['secs']; decks = []
order = sorted(secs, key=lambda k: tuple(map(int, k.split('-'))))
for k in order:
    its = [it for it in out if ST['ent'][it['id'][3:]] == k]
    a, b = k.split('-')
    decks.append(dict(id=f'h3k_{a}_{b}', group='はじめての N1 単語3000 (Hàn–Việt)', sec=f'Chương {a}', name=f'{a}-{b} · {secs[k]["name"]}',
                      items=its, audio=f'audio/w3ks/{secs[k]["file"].replace(".mp3", "")}.mp3'))
json.dump(decks, open('/home/claude/raw/haji/decks.json', 'w'), ensure_ascii=False)
print(stats, 'decks', len(decks), 'items', len(out), file=sys.stderr)
