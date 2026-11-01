# はじめての日本語能力試験 N1 単語3000 (bản Hàn–Việt): tách 1 trang (ảnh 300dpi) thành các mục từ.
# Mỗi vùng chữ được nhận dạng bằng nhiều cấu hình tesseract rồi bỏ phiếu từng chữ; từ đầu mục được sửa theo JMdict.
# python3 haji.py page.png [page.json]
import sys, re, json, subprocess, tempfile, os, csv, io, unicodedata, difflib, pickle, collections
import cv2, numpy as np
sys.path.insert(0, '/home/claude/scripts'); import vnfix

KAN = re.compile(r'[一-龥々〆ヶ]'); HANGUL = re.compile(r'[가-힣ㄱ-ㅎㅏ-ㅣ]')
FAST = '/usr/share/tesseract-ocr/5/tessdata'; BEST = '/home/claude/tools-node/tessdata_best'
VIE_CFG = [(FAST, 1, 175), (BEST, 1, 205), (FAST, .6, 175)]
JPN_CFG = [(BEST, 1.5, 175), (FAST, 1, 175), (BEST, 1, 175)]
_JM = None
def JM():
    global _JM
    if _JM is None: _JM = pickle.load(open('/home/claude/dict/jm.pkl', 'rb'))
    return _JM

def tess(img, td, lang, psm=6, extra=()):
    fd, p = tempfile.mkstemp(suffix='.png'); os.close(fd); cv2.imwrite(p, img)
    r = subprocess.run(['tesseract', p, '-', '--tessdata-dir', td, '-l', lang, '--psm', str(psm), *extra, 'tsv'], capture_output=True, text=True).stdout
    os.remove(p); return r

def lines_of(tsv, sc):
    L = {}
    for w in csv.DictReader(io.StringIO(tsv), delimiter='\t', quoting=csv.QUOTE_NONE):
        if w.get('level') != '5' or not (w['text'] or '').strip(): continue
        L.setdefault((w['block_num'], w['par_num'], w['line_num']), []).append(
            dict(x=int(w['left']) / sc, y=int(w['top']) / sc, w=int(w['width']) / sc, h=int(w['height']) / sc, t=w['text'], c=float(w['conf'])))
    out = []
    for ws in L.values():
        ws.sort(key=lambda w: w['x'])
        out.append(dict(ws=ws, y0=min(w['y'] for w in ws), y1=max(w['y'] + w['h'] for w in ws), h=float(np.median([w['h'] for w in ws]))))
    return sorted(out, key=lambda l: l['y0'])

def stack(gray, regions):
    """Ghép các vùng (y0,y1,x0,x1) thành 1 ảnh dọc, trả về ảnh + danh sách (offset, region)."""
    if not regions: return None, []
    W = max(r[3] - r[2] for r in regions) + 40; parts = []; offs = []; y = 20
    for r in regions:
        c = gray[r[0]:r[1], r[2]:r[3]]
        if c.size == 0: offs.append((y, r)); continue
        pad = np.full((c.shape[0] + 140, W), 255, np.uint8); pad[20:20 + c.shape[0], 20:20 + c.shape[1]] = c
        parts.append(pad); offs.append((y, r)); y += pad.shape[0]
    img = np.vstack([np.full((20, W), 255, np.uint8)] + parts)
    return img, offs

def one(gray, r, td, sc, th):
    c = gray[r[0]:r[1], r[2]:r[3]]
    if c.size == 0: return []
    c = np.where(c > th, 255, c).astype(np.uint8)
    c = cv2.copyMakeBorder(c, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)
    if sc != 1: c = cv2.resize(c, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
    ls = lines_of(tess(c, td, 'jpn'), sc)
    return [dict(l, y0=l['y0'] - 20 + r[0], y1=l['y1'] - 20 + r[0], ws=[dict(w, x=w['x'] - 20 + r[2]) for w in l['ws']]) for l in ls]

def run_stacked(gray, regions, td, sc, th, lang):
    img, offs = stack(gray, regions)
    if img is None: return [[] for _ in regions]
    img = np.where(img > th, 255, img).astype(np.uint8)
    if sc != 1: img = cv2.resize(img, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_CUBIC)
    ls = lines_of(tess(img, td, lang), sc)
    res = [[] for _ in regions]
    for l in ls:
        cy = (l['y0'] + l['y1']) / 2
        for i, (o, r) in enumerate(offs):
            if o + 20 <= cy <= o + 20 + (r[1] - r[0]):
                l = dict(l, y0=l['y0'] - o - 20 + r[0], y1=l['y1'] - o - 20 + r[0], ws=[dict(w, x=w['x'] - 20 + r[2]) for w in l['ws']]); res[i].append(l); break
    return res

NFC = lambda s: unicodedata.normalize('NFC', s)
VOK = re.compile(r"^[A-Za-zÀ-ỹĐđ0-9.,;:!?()'\"“”‘’…%/~〜-]+$")
def vclean(t):   # bỏ ký tự rác (dòng chữ Hàn đọc nhầm sang Latin)
    toks = t.split(); good = [x for x in toks if VOK.match(x)]
    return ' '.join(good) if len(good) >= .7 * len(toks) else ''
def vtext(l): return NFC(' '.join(w['t'] for w in l['ws'])).strip()
def jtext(l): return unicodedata.normalize('NFKC', ''.join(w['t'] for w in l['ws'])).replace(' ', '')

def vote(cands, unit):
    """Bỏ phiếu: chọn ứng viên trung tâm rồi thay từng đơn vị (từ / ký tự) theo đa số."""
    cands = [c for c in cands if c]
    if not cands: return ''
    sp = (lambda s: s.split()) if unit == 'w' else list
    toks = [sp(c) for c in cands]
    best = max(range(len(toks)), key=lambda i: sum(difflib.SequenceMatcher(None, toks[i], toks[j]).ratio() for j in range(len(toks)) if j != i))
    base = toks[best]; slots = [collections.Counter({t: 1}) for t in base]
    for j, o in enumerate(toks):
        if j == best: continue
        for tag, a0, a1, b0, b1 in difflib.SequenceMatcher(None, base, o, autojunk=False).get_opcodes():
            if tag == 'equal':
                for k in range(a1 - a0): slots[a0 + k][base[a0 + k]] += 1
            elif tag == 'replace' and a1 - a0 == b1 - b0:
                for k in range(a1 - a0): slots[a0 + k][o[b0 + k]] += 1
    out = [s.most_common(1)[0][0] for s in slots]
    return ' '.join(out) if unit == 'w' else ''.join(out)

def reading(word_line, furi):
    chars = []
    for w in word_line['ws']:
        t = unicodedata.normalize('NFKC', w['t']); n = len(t)
        for i, c in enumerate(t): chars.append((c, w['x'] + w['w'] * i / n, w['x'] + w['w'] * (i + 1) / n))
    fur = []
    for l in furi:
        for w in l['ws']:
            t = re.sub(r'[^ぁ-ん]', '', unicodedata.normalize('NFKC', w['t'])); n = len(t)
            for i, c in enumerate(t): fur.append((c, w['x'] + w['w'] * (i + .5) / max(n, 1)))
    runs = []; k = 0
    while k < len(chars):
        if KAN.match(chars[k][0]):
            j = k
            while j < len(chars) and KAN.match(chars[j][0]): j += 1
            runs.append((k, j, chars[k][1], chars[j - 1][2])); k = j
        else: k += 1
    if not runs: return re.sub(r'[^ぁ-んァ-ンー]', '', ''.join(c[0] for c in chars))
    assign = {i: [] for i in range(len(runs))}
    for f in fur:   # mỗi chữ furigana thuộc về cụm kanji gần nhất
        d = [0 if r[2] - 15 <= f[1] <= r[3] + 15 else min(abs(f[1] - r[2]), abs(f[1] - r[3])) for r in runs]
        i = int(np.argmin(d))
        if d[i] < 60: assign[i].append(f)
    if any(not v for v in assign.values()): return ''
    out = ''; k = 0; ri = 0
    while k < len(chars):
        if ri < len(runs) and k == runs[ri][0]:
            out += ''.join(f[0] for f in sorted(assign[ri], key=lambda f: f[1])); k = runs[ri][1]; ri += 1
        else:
            if re.match(r'[ぁ-んァ-ンー]', chars[k][0]): out += chars[k][0]
            k += 1
    return out

def lev(a, b):
    d = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        p, d[0] = d[0], i
        for j, cb in enumerate(b, 1): p, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, p + (ca != cb))
    return d[-1]

ENDS = ['', 'る', 'む', 'う', 'く', 'ぐ', 'す', 'つ', 'ぬ', 'ぶ', 'い', 'しい', 'に', 'と']
def fix_word(cands, rd, hl=''):
    """Chọn từ đầu mục: chấm điểm ứng viên (OCR ô trái, đoạn tô hồng trong câu ví dụ, JMdict theo cách đọc)."""
    jm = JM(); core = lambda w: re.split(r'[〈<(（\[［]', w)[0].strip()
    tail = ''
    for c in cands:
        m = re.search(r'[〈<(（\[［《].*$', c)
        if m: tail = m.group(0); break
        if re.search(r'[一-龥]する\)$', c): tail = '〈する〉'; break
    tail = tail.replace('<', '〈').replace('>', '〉').replace('《', '〈').replace('》', '〉')
    tail = re.sub(r'^[〈(（<《\s]+(する|な|の|に|と)\s*[〉)）>》]?.*', r'〈\1〉', tail)
    tail = re.sub(r'^[\[［]\s*(と|に)\s*[\]］」]?.*', r'［\1］', tail)
    tail = re.sub(r'^[\[［]\s*[ー~〜～-]+\s*ない.*', '［〜ない］', tail)
    if tail and not re.fullmatch(r'〈(する|な|の|に|と)〉|［(と|に|〜ない)］', tail): tail = ''
    cores = [re.sub(r'する\)$', '', core(c)) if tail == '〈する〉' else core(c) for c in cands]
    cores = [c for c in cores if c]
    pool = set(cores)
    if hl:   # đoạn tô hồng trong câu ví dụ: thử các đoạn con + đuôi từ điển
        hl = re.sub(r'ー(?=[一-龥])|(?<=[一-龥])ー(?=[一-龥])', '一', hl)
        hl = hl.lstrip('、。をがはにでとものへ')
        for a0 in range(min(2, len(hl))):
          for n in range(len(hl) - a0, 0, -1):
            p = hl[a0:a0 + n]
            for e in ENDS:
                c = p + e
                if c in jm['k2r'] or (a0 == 0 and c in jm['kana'] and len(c) > 2 and (len(c) >= len(hl) - 2)): pool.add(c)
    if rd and rd in jm['r2k']: pool |= jm['r2k'][rd]
    def readings(c): return jm['k2r'].get(c) or ({c} if c in jm['kana'] else set())
    def score(c):
        rs = readings(c); sim = max((difflib.SequenceMatcher(None, c, x).ratio() for x in cores), default=0)
        if c in ('する', 'な', 'の') : return -9
        stem = re.sub(r'[ぁ-ん]{1,2}$', '', c) if KAN.search(c) else c
        inhl = bool(hl and stem and stem in hl)
        return (3 if rs else 0) + (2 if rd and len(rd) >= 2 and rd in rs else 0) + 3 * sim + ((3 if len(stem) >= 2 or c in cores else 1) if inhl else 0) + (1.5 if inhl and len(stem) >= 2 and len(stem) >= len(re.sub(r'[ぁ-ん]+$', '', hl)) else 0) + (1 if c in cores else 0) + .2 * min(len(c), 6)
    if not pool: return '', rd
    best = max(sorted(pool), key=score)
    rs = readings(best)
    r = rd if rd in rs else (min(rs, key=lambda x: lev(x, rd)) if rs and rd else (next(iter(rs)) if len(rs) == 1 else rd))
    return best + tail, r

def fix_example(ex, word):
    w = re.split(r'[〈［]', word)[0]
    if not w or w in ex or len(w) < 1: return ex
    stem = w[:-1] if len(w) > 2 and re.match(r'[ぁ-ん]', w[-1]) else w   # động từ/tính từ chia
    if stem in ex: return ex
    n = len(stem); best = None
    for i in range(len(ex) - n + 1):
        d = lev(ex[i:i + n], stem)
        if d <= max(1, n // 3) and (best is None or d < best[0]): best = (d, i)
    if best and n >= 3: ex = ex[:best[1]] + stem + ex[best[1] + n:]
    return ex

def highlight(im_bgr, r, lines):
    """Các ký tự tô hồng (từ đầu mục) trong dòng câu ví dụ."""
    out = ''
    for l in lines:
        y0, y1 = int(l['y0']), int(l['y0'] + .8 * (l['y1'] - l['y0']))
        crop = im_bgr[y0:y1].astype(int)
        mg = (crop[:, :, 2] > 170) & (crop[:, :, 1] < 120) & (crop[:, :, 0] > 80)
        colm = mg.sum(0) > 2
        for w in l['ws']:
            t = unicodedata.normalize('NFKC', w['t']); n = len(t)
            for i, ch in enumerate(t):
                a, b = int(w['x'] + w['w'] * i / n), int(w['x'] + w['w'] * (i + 1) / n)
                if b > a and colm[a:b].mean() > .25: out += ch
                elif out and not out.endswith('|'): out += '|'
    return out.split('|')[0] if out else ''

def from_example(ex, cands):
    """Từ đầu mục luôn xuất hiện (tô hồng) trong câu ví dụ: lấy đoạn con của câu giống ứng viên nhất và có trong JMdict."""
    jm = JM(); out = []
    for c in cands:
        c = re.split(r'[〈<(（\[［]', c)[0].strip()
        if not c: continue
        if len(c) < 2: continue
        for n in {len(c), len(c) - 1, len(c) + 1}:
            if n < 2: continue
            best = None
            for i in range(len(ex) - n + 1):
                sub = ex[i:i + n]
                if sub in jm['k2r'] or (sub in jm['kana'] and len(sub) > 2):
                    d = lev(sub, c)
                    if d <= max(1, len(c) // 2) and (best is None or d < best[0]): best = (d, sub)
            if best: out.append(best[1])
    return out

POSMAP = {'回': '副', '名': '名', '動': '動', '副': '副', '形': '形', '慣': '慣', '連': '連', '接': '接', '感': '感', '代': '代'}
def pos_icon(crop):
    """Ô xám chữ trắng (名/動/副/形/慣…): lấy phần chữ trắng bên trong ô xám, nhận dạng 1 ký tự."""
    m = (crop < 175).astype(np.uint8)
    ys, xs = np.where(m)
    if len(ys) < 200: return ''
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    box = crop[y0 + 4:y1 - 3, x0 + 4:x1 - 3]
    if box.size == 0 or min(box.shape) < 5: return ''
    ch = np.where(box > 185, 0, 255).astype(np.uint8)
    ch = cv2.copyMakeBorder(cv2.resize(ch, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC), 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)
    outs = []
    for td in (BEST,):
        r = subprocess.run(['tesseract', '-', '-', '--tessdata-dir', td, '-l', 'jpn', '--psm', '10'], input=cv2.imencode('.png', ch)[1].tobytes(), capture_output=True).stdout.decode()
        r = re.sub(r'\s', '', r)
        if r: outs.append(r)
    for r in outs:
        for c in r:
            if c in POSMAP: return POSMAP[c]
    return outs[0][:2] if outs else ''

def page(png):
    im = cv2.imread(png); H, W = im.shape[:2]
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    b_, g_, r_ = [im[:, :, i].astype(int) for i in range(3)]
    mag = (r_ > 170) & (g_ < 100) & (b_ > 80)
    cols = mag[int(H * .1):int(H * .9)].sum(0); vx = [x for x in range(W) if cols[x] > H * .25]
    if not vx: return []
    xmid = int(np.median(vx))
    rowsum = mag.sum(1); rl = [y for y in range(int(H * .04), int(H * .96)) if W * .4 < rowsum[y] < W * .9]
    starts, ends = [], []
    for y in rl[::3]:
        xs = np.where(mag[y])[0]
        if not len(xs): continue
        br = np.where(np.diff(xs) > 3)[0]; segs = np.split(xs, br + 1); sgm = max(segs, key=len)
        if len(sgm) > W * .4: starts.append(sgm[0]); ends.append(sgm[-1])
    x0t, x1t = (int(np.median(starts)), int(np.median(ends))) if starts else (xmid - 600, W - 180)
    bw = (g < 140).astype(np.uint8) * 255
    cs, _ = cv2.findContours(bw, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for c in cs:
        x, y, w, h = cv2.boundingRect(c)
        if 48 <= w <= 68 and 48 <= h <= 68 and abs(w - h) < 8 and x0t - 200 < x < x0t and g[y + 10:y + h - 10, x + 10:x + w - 10].mean() > 238:
            if not any(abs(y - b[1]) < 30 for b in boxes): boxes.append((x, y, w, h))
    boxes.sort(key=lambda b: b[1])
    pink = (r_ > 225) & (g_ > 175) & (g_ < 238) & (b_ > 195) & ((r_ - g_) > 12)
    E = []
    for i, (bx, by, bw_, bh) in enumerate(boxes):
        top = by - 95; bot = boxes[i + 1][1] - 95 if i + 1 < len(boxes) else int(H * .95)
        pr = pink[top:bot, x0t + 10:xmid - 10].mean(1) > .35
        runs = []; s0 = None
        for y, v in enumerate(list(pr) + [False]):
            if v and s0 is None: s0 = y
            if not v and s0 is not None:
                if runs and s0 - runs[-1][1] <= 12: runs[-1][1] = y
                else: runs.append([s0, y])
                s0 = None
        runs = [r for r in runs if r[1] - r[0] >= 40]
        if not runs: continue
        p0 = top + runs[0][0]; p1 = top + runs[0][1]
        E.append(dict(box=(bx, by, bw_, bh), top=top, bot=bot, p0=p0, p1=p1,
                      Lw=(top, p0, x0t + 8, xmid - 6), Lp=(p0, p1, x0t + 8, xmid - 6), Rw=(top, p0, xmid + 8, x1t - 4), Rp=(p0, p1, xmid + 8, x1t - 4),
                      Pl=(p1 + 4, bot - 10, x0t, x1t)))
    if not E: return []
    # --- số thứ tự & từ loại
    for e in E:
        bx, by, bw_, bh = e['box']
        num = g[e['top']:by - 2, bx - 120:x0t - 4]
        nr = re.sub(r'\D', '', tess(num, FAST, 'eng', 7, ('-c', 'tessedit_char_whitelist=0123456789')).split('\n')[-2].split('\t')[-1] if False else
                    subprocess.run(['tesseract', '-', '-', '-l', 'eng', '--psm', '7', '-c', 'tessedit_char_whitelist=0123456789'], input=cv2.imencode('.png', num)[1].tobytes(), capture_output=True).stdout.decode())
        e['n'] = int(nr) if nr else None
        e['pos'] = pos_icon(g[by + bh + 2:by + bh + 85, bx - 14:bx + bw_ + 14])
    vie = collections.defaultdict(list)
    for td, sc, th in VIE_CFG:
        for key in ('Lp', 'Rp'):
            res = run_stacked(g, [e[key] for e in E], td, sc, th, 'vie')
            for i, ls in enumerate(res):
                keep = [vclean(vtext(l)) for l in ls if np.mean([w['c'] for w in l['ws']]) >= 62]
                vie[(i, key)].append(' '.join(t for t in keep if re.search('[A-Za-zÀ-ỹ]', t)))
    jp = collections.defaultdict(list); furi = {}; hls = {}
    for ci, (td, sc, th) in enumerate(JPN_CFG):
        for key in ('Lw', 'Rw'):
            res = run_stacked(g, [e[key] for e in E], td, sc, th, 'jpn') if key == 'Rw' else ([one(g, e[key], td, sc, th) for e in E] if ci < 2 else [[] for e in E])
            for i, ls in enumerate(res):
                big = [l for l in ls if l['h'] >= 40]
                if key == 'Lw':
                    jp[(i, key)].append(jtext(big[0]) if big else '')
                    if big:
                        sm = [l for l in ls if l['h'] < 40 and l['y0'] > big[0]['y0'] + 10 and re.search('[ぁ-ん]', jtext(l))]
                        furi.setdefault(i, []).append((big[0], sm))
                else:
                    jp[(i, key)].append(''.join(jtext(l) for l in big))
                    if ci == 0: hls[i] = highlight(im, E[i][key], big)
    plus = run_stacked(g, [e['Pl'] for e in E], BEST, 1, 175, 'jpn+kor+vie')
    out = []
    for i, e in enumerate(E):
        rd = ''
        if i in furi:
            fs = furi[i]; texts = [''.join(jtext(l) for l in sm) for _, sm in fs]
            if any(texts):
                v = vote(texts, 'c')
                for k in sorted(range(len(fs)), key=lambda j: -difflib.SequenceMatcher(None, texts[j], v).ratio()):
                    rd = reading(*fs[k])
                    if rd: break
            if not rd:
                b0 = fs[0][0]; r = E[i]['Lw']
                fl = one(g, (int(b0['y0'] + .75 * (b0['y1'] - b0['y0'])), min(int(b0['y1']) + 40, r[1]), r[2], r[3]), BEST, 2, 175)
                rd = reading(b0, [l for l in fl if re.search('[ぁ-ん]', jtext(l))])
        ex = vote(jp[(i, 'Rw')], 'c')
        word, rd2 = fix_word(jp[(i, 'Lw')], rd, hls.get(i, ''))
        ex = fix_example(ex, word)
        vi = vote(vie[(i, 'Lp')], 'w'); exvi = vote(vie[(i, 'Rp')], 'w')
        vi = vnfix.fix_line(vi, [c.split() for c in vie[(i, 'Lp')]]); exvi = vnfix.fix_line(exvi, [c.split() for c in vie[(i, 'Rp')]])
        pl = []
        for l in plus[i]:
            if l['h'] < 28: continue
            t = NFC(' '.join(w['t'] for w in l['ws']))
            m = re.match(r'^\W*([一-龥々ぁ-んァ-ンー〈〉()（）]+)', t.replace(' ', ''))
            vm = re.search(r'/\s*([^/]*[A-Za-zÀ-ỹ][^/]*)$', t)
            if m and vm: pl.append(dict(w=m.group(1), vi=vnfix.fix_line(vm.group(1).strip())))
        out.append(dict(n=e['n'], w=word, r=rd2 or rd, pos=e['pos'], hl=hls.get(i, ''), cands=jp[(i, 'Lw')], vi=vi, ex=ex, exvi=exvi, plus=pl,
                        img=[e['top'], e['p1'] + 6, x0t - 170, x1t + 8, W, H]))
    return out

if __name__ == '__main__':
    r = page(sys.argv[1])
    if len(sys.argv) > 2: json.dump(r, open(sys.argv[2], 'w'), ensure_ascii=False)
    else: print(json.dumps(r, ensure_ascii=False, indent=1))
