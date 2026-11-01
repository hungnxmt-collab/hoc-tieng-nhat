# Đề đánh máy chụp lại (7/2019, 12/2019): ô số câu bị OCR thành ký tự rác → nhận câu hỏi theo cấu trúc
# (dòng ngay trước dòng lựa chọn). Lựa chọn A–D hoặc 1–4. Phân 13 問題 theo khung chuẩn N1.
# python3 parse_plain_exam.py PGDIR first last ABCD|1234 key.json out.json ID "title"
import sys, re, csv, json, unicodedata, glob
pgdir, first, last, mode, keyf, outf, eid, title = sys.argv[1:9]
first, last = int(first), int(last)
KEY = {int(k): v for k, v in json.load(open(keyf)).items()}
RANGES = [(1, 6), (7, 13), (14, 19), (20, 25), (26, 35), (36, 40), (41, 45), (46, 49), (50, 58), (59, 62), (63, 64), (65, 68), (69, 71)]
SECNAME = ['漢字読み', '文脈規定', '言い換え類義', '用法', '文法形式の判断', '文の組み立て', '文章の文法', '内容理解（短文）', '内容理解（中文）', '内容理解（長文）', '統合理解', '主張理解（長文）', '情報検索']
CJK = r'[　-ヿ一-鿿＀-￯（）「」『』【】、。・〜ー]'
NOISE = set('*+をかトト条ネ委人ヶやよ示時生本守いIL|ご入系第キ和肖ゃ症ム>は')
def norm(t):
    t = unicodedata.normalize('NFKC', t)
    toks = t.split()
    while toks and len(toks[0]) == 1 and toks[0] in NOISE and len(toks) > 2: toks.pop(0)
    while toks and len(toks[-1]) <= 2 and all(c in NOISE or not c.isalnum() for c in toks[-1]) and len(toks) > 2: toks.pop()
    t = ' '.join(toks)
    for _ in range(2): t = re.sub(rf'({CJK}) (?={CJK})', r'\1', t)
    t = re.sub(r'([぀-鿿]) (?=[぀-鿿])', r'\1', t)
    return t.strip()
L = []
for p in range(first, last + 1):
    f = f'{pgdir}/p{p:03d}.tsv'
    rows = {}; W = H = 0
    for r in csv.DictReader(open(f, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE):
        if r['level'] == '1': W, H = int(r['width']), int(r['height'])
        if r['level'] != '5' or not (r['text'] or '').strip(): continue
        rows.setdefault((r['block_num'], r['par_num'], r['line_num']), []).append(r)
    for ws in rows.values():
        ws.sort(key=lambda r: int(r['left']))
        raw = ' '.join(w['text'] for w in ws)
        y0 = min(int(w['top']) for w in ws); y1 = max(int(w['top']) + int(w['height']) for w in ws)
        if re.search(r'(Website|Hotline|Fanpage|Zalo|nhatngu|帝京|成都|内部資料|www\.|QQ)', raw, re.I) or y0 < H * .03 or y0 > H * .965: continue
        t = norm(raw)
        if len(t) < 2: continue
        L.append(dict(p=p, y0=y0, y1=y1, t=t, W=W, H=H))
    L.sort(key=lambda l: (l['p'], l['y0']))
M = ['A', 'B', 'C', 'D'] if mode == 'ABCD' else ['1', '2', '3', '4']
FIX = {'Al': 'A.', 'AA': 'A.', 'A,': 'A.', 'Bl': 'B.', 'Cl': 'C.', 'Dl': 'D.'}
def opts(t, start):
    if mode == 'ABCD':
        for k, v in FIX.items(): t = re.sub(rf'(^|\s){k}(?=\s)', rf'\1{v}', t)
        rx = r'(?:^|\s)([A-D])\s*[.．,、]?\s*(?=\S)'
    else:
        rx = r'(?:^|\s|_)([1-4])\s*[.．]?\s*_?\s*(?=[^\s\d年月日時分回歳%])'
    pos = []; want = start
    for m in re.finditer(rx, t):
        if m.group(1) == M[want - 1] if want <= 4 else False:
            pos.append((m.start(), m.end())); want += 1
            if want > 4: break
    if not pos or pos[0][0] > 2: return []
    return [re.sub(r'[\s_]+$', '', t[b:(pos[i + 1][0] if i + 1 < len(pos) else len(t))]).strip(' _') for i, (a, b) in enumerate(pos)]
STOP = re.compile(r'(聴解|聴\s*解|問題用紙を開けて|第三部分|では、まず質問を聞いて)')
qs = []; texts = []; buf = []; q = None
for i, l in enumerate(L):
    t = l['t']
    if STOP.search(t) and len(qs) >= 60: break
    if re.match(r'^(問題|第[一二]部分|言語知識|読解)', t) and len(t) < 90:
        if buf: texts.append((len(qs), buf)); buf = []
        continue
    if q is not None and len(q['o']) < 4:
        got = opts(t, len(q['o']) + 1)
        if got: q['o'] += got; q['_l'].append(l); continue
        if q['o']: q['o'][-1] += t; q['_l'].append(l); continue
    got = opts(t, 1)
    if got:   # dòng lựa chọn đầu tiên → các dòng trước đó là câu hỏi
        stem = []
        if buf:
            stem = [buf.pop()]
            if buf and (len(stem[0]['t']) < 14 or not re.search(r'[。?？」]$', buf[-1]['t'])) and len(buf[-1]['t']) < 80 and not re.search(r'[。」]$', buf[-1]['t']): stem.insert(0, buf.pop())
        if buf: texts.append((len(qs), buf)); buf = []
        n = len(qs) + 1
        stxt = re.sub(r'^\S{1,3}?\s*(?=\S)', '', ' '.join(s['t'] for s in stem)) if stem and re.match(r'^(\d{1,2}|[^\s]{1,2})\s', stem[0]['t']) else ' '.join(s['t'] for s in stem)
        q = dict(t='q', n=n, q=re.sub(r'^\d{1,2}\s*[|｜]?\s*', '', stxt), o=got, a=KEY.get(n), _l=stem + [l]); qs.append(q)
        continue
    buf.append(l)
def region(ls):
    segs = {}
    for l in ls:
        s = segs.setdefault(l['p'], [l['y0'], l['y1'], l['W'], l['H']])
        s[0] = min(s[0], l['y0']); s[1] = max(s[1], l['y1'])
    return [[p, max(0, a - 20), min(H, b + 20), W, H] for p, (a, b, W, H) in segs.items()]
secs = [dict(no=k + 1, name=SECNAME[k], instr='', blocks=[]) for k in range(13)]
def sec_of(n): return next(k for k, (a, b) in enumerate(RANGES) if n <= b)
ti = 0
for q in qs:
    while ti < len(texts) and texts[ti][0] < q['n']:
        k = sec_of(texts[ti][0] + 1)
        if k >= 6: secs[k]['blocks'].append(dict(t='text', text='\n'.join(x['t'] for x in texts[ti][1]), img=region(texts[ti][1])))
        ti += 1
    q['img'] = region(q.pop('_l')); q['o'] = [o.strip() for o in q['o']]
    secs[sec_of(q['n'])]['blocks'].append(q)
secs = [s for s in secs if s['blocks']]
bad = [q['n'] for q in qs if len(q['o']) != 4 or not q['a']]
E = dict(id=eid, title=title, set='Đề thi JLPT N1 2019 (bản đánh máy, OCR)', level='N1', nq=len(qs), sections=secs, scan=True)
json.dump(E, open(outf, 'w'), ensure_ascii=False)
print(title, 'q', len(qs), 'key', len(KEY), 'bad', bad, [(s['no'], sum(b['t'] == 'q' for b in s['blocks'])) for s in secs], file=sys.stderr)
