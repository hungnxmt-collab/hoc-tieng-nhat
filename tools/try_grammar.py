# Trích 123 mẫu ngữ pháp TRY! N1 từ OCR trang sách: giải thích (どう使う?) + câu ví dụ.
# Lọc dòng theo chiều cao chữ (furigana ~22px, tiếng Trung ~32px, thân bài ~45px), sửa chữ sai của chính mẫu ngữ pháp trong ví dụ.
import csv, re, sys, json, unicodedata, difflib, collections
sys.path.insert(0, '/home/claude/raw/try'); from toc import ITEMS, PLUS
PG = '/home/claude/raw/try/pg'
CIRC = '①②③④⑤⑥⑦⑧⑨'
def page_lines(p):
    rows = collections.defaultdict(list)
    try: f = open(f'{PG}/p{p:03d}.tsv', encoding='utf-8')
    except FileNotFoundError: return []
    for r in csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE):
        if r['level'] == '5' and (r['text'] or '').strip(): rows[(r['block_num'], r['par_num'], r['line_num'])].append(r)
    out = []
    for ws in rows.values():
        ws.sort(key=lambda w: int(w['left'])); hs = sorted(int(w['height']) for w in ws)
        t = unicodedata.normalize('NFKC', ''.join(w['text'] for w in ws))
        out.append(dict(p=p, y=int(ws[0]['top']), x=int(ws[0]['left']), h=hs[len(hs) // 2], t=t))
    return sorted(out, key=lambda l: l['y'])
def lev(a, b):
    d = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        p, d[0] = d[0], i
        for j, cb in enumerate(b, 1): p, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, p + (ca != cb))
    return d[-1]
def fix_pat(s, pat):
    """Sửa chữ OCR sai trong chính cụm ngữ pháp (vd. に條るまで → に至るまで)."""
    for core in [c for c in re.split(r'[〜～・/]', pat) if len(c) >= 2]:
        core = re.sub(r'[()（）]', '', core)
        if core in s: continue
        n = len(core); best = None
        for i in range(len(s) - n + 1):
            d = lev(s[i:i + n], core)
            if d == 1 and (best is None or i < best): best = i
        if best is not None: s = s[:best] + core + s[best + n:]
    return s
def clean(t):
    t = re.sub(r'[|_\\/]', '', t)
    m = re.search(r'^(.*?[。!?」])[^。!?」]{0,8}$', t)   # rác minh hoạ sau dấu kết câu
    return (m.group(1) if m else t).strip()
items = []
for k, it in enumerate(ITEMS):
    nxt = ITEMS[k + 1]['page'] if k + 1 < len(ITEMS) else it['page'] + 2
    L = []
    for p in range(it['page'], max(it['page'], nxt) + 1): L += page_lines(p)
    body = [l for l in L if 37 <= l['h'] <= 62]
    heads = [i for i, l in enumerate(L) if l['h'] >= 56]
    # dòng tiêu đề của mẫu này và của mẫu kế tiếp
    def hscore(l, ex): return difflib.SequenceMatcher(None, re.sub(r'^\W*\d*', '', l['t']), ex).ratio()
    hs = [L[i] for i in heads if L[i]['p'] == it['page']] or [L[i] for i in heads]
    start = max(hs, key=lambda l: hscore(l, it['ex'])) if hs else None
    end = None
    if k + 1 < len(ITEMS):
        hn = [L[i] for i in heads if L[i]['p'] == ITEMS[k + 1]['page']]
        if hn:
            end = max(hn, key=lambda l: hscore(l, ITEMS[k + 1]['ex']))
            if hscore(end, ITEMS[k + 1]['ex']) < .3: end = None
    key = lambda l: (l['p'], l['y'])
    seg = [l for l in body if (not start or key(l) > key(start)) and (not end or key(l) < key(end))]
    stop = next((i for i, l in enumerate(seg) if re.search(r'(やっ.?てみよう|まとめの問題|Check|\(a\.)', l['t'])), len(seg))
    seg = seg[:stop]
    expl, exs, cur = [], [], None
    for l in seg:
        t = l['t']
        m = re.match(rf'^(?:[{CIRC}]|[1-9](?=[一-龥ぁ-んァ-ンー「『A-Z]))', t)
        want = len(exs) + (1 if cur else 0) + 1
        if m and (t[0] in CIRC or int(t[0]) in (want, 1)):
            if cur: exs.append(cur)
            cur = t[1:]; continue
        if cur is not None:
            if not re.search(r'[。!?」]$', clean(cur)) and not re.search(r'(どう使う|\+|\(a\.|やっ.?てみよう)', t): cur += t; continue
            exs.append(cur); cur = None
        if not exs and re.search(r'[ぁ-ん]', t) and '+' not in t and not re.search(r'どう使う', t) and len(expl) < 6 and len(t) > 8:
            expl.append(t)
    if cur: exs.append(cur)
    exs = [fix_pat(clean(e), it['pat']) for e in exs]
    exs = [re.split(r'やっ.?てみよう', e)[0] for e in exs if not re.search(r'\(a\.', e)]
    exs = [e for e in exs if len(e) >= 8][:6]
    expl = fix_pat(''.join(expl), it['pat'])
    expl = re.sub(r'「[へーンノ](?=[一-龥ぁ-んァ-ン])', '「〜', expl).replace('...へ', '…〜').replace('...', '…')
    items.append(dict(it, expl=expl, exs=exs))
if __name__ == '__main__':
    json.dump(items, open('/home/claude/raw/try/grammar.json', 'w'), ensure_ascii=False, indent=0)
    for x in items[:int(sys.argv[1]) if len(sys.argv) > 1 else 5]:
        print(x['n'], x['pat'], '|', x['expl'][:90]); [print('   ', e) for e in x['exs']]
