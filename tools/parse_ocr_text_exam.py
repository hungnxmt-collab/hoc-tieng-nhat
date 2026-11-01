# Đề scan không có ô số câu (vd. 12/2018 Chengdu): câu "N." đầu dòng, mỗi lựa chọn 1 dòng.
# python3 parse_ocr_text_exam.py PGDIR first last key.json out.json ID "title"
import sys, re, csv, json, unicodedata
pgdir, first, last, keyf, outf, eid, title = sys.argv[1:8]
first, last = int(first), int(last)
KEY = {int(k): v for k, v in json.load(open(keyf)).items()}
SECNAME = {1: '漢字読み', 2: '文脈規定', 3: '言い換え類義', 4: '用法', 5: '文法形式の判断', 6: '文の組み立て', 7: '文章の文法',
           8: '内容理解（短文）', 9: '内容理解（中文）', 10: '内容理解（長文）', 11: '統合理解', 12: '主張理解（長文）', 13: '情報検索'}
L = []
for p in range(first, last + 1):
    rows = {}
    H = W = 0
    for r in csv.DictReader(open(f'{pgdir}/p{p:03d}.tsv', encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE):
        if r['level'] == '1': W, H = int(r['width']), int(r['height'])
        if r['level'] != '5' or not (r['text'] or '').strip(): continue
        rows.setdefault((r['block_num'], r['par_num'], r['line_num']), []).append(r)
    for ws in rows.values():
        ws.sort(key=lambda r: int(r['left']))
        t = ''
        for i, w in enumerate(ws):
            if i and int(w['left']) - (int(ws[i-1]['left']) + int(ws[i-1]['width'])) > 25: t += ' '
            t += w['text']
        t = unicodedata.normalize('NFKC', t).strip()
        y0 = min(int(w['top']) for w in ws); y1 = max(int(w['top']) + int(w['height']) for w in ws)
        if re.search(r'(成都|帝京|内部資料|^\*比|cdteikyo|YuuKi|日本語能力試験|第[一二三]部分)', t) or y0 > H - 150: continue
        L.append(dict(p=p, y0=y0, y1=y1, t=t, W=W, H=H))
    L.sort(key=lambda l: (l['p'], l['y0']))

def region(ls):
    segs = {}
    for l in ls:
        s = segs.setdefault(l['p'], [l['y0'], l['y1'], l['W'], l['H']])
        s[0] = min(s[0], l['y0']); s[1] = max(s[1], l['y1'])
    return [[p, max(0, a - 18), min(H, b + 18), W, H] for p, (a, b, W, H) in segs.items()]

sections = []; sec = None; q = None; qn = 0; cur = None
OPT = re.compile(r'^([1-4|lI])\s*[.、]?\s*(?=\S)(.*)$')
def multi(t, start):
    # nhiều lựa chọn trên 1 dòng: "1 むしろ   2 一方で"
    pos = []; want = start
    for m in re.finditer(r'(?:^|\s)([1-4|])\s*[.、]?\s*(?=\S)', t):
        d = 1 if m.group(1) == '|' else int(m.group(1))
        if d == want: pos.append((m.start(), m.end())); want += 1
    if not pos or pos[0][0] > 1: return []
    return [t[b:(pos[k + 1][0] if k + 1 < len(pos) else len(t))].strip() for k, (a, b) in enumerate(pos)]
for i, l in enumerate(L):
    t = l['t']
    if re.fullmatch(r'[\d| ]{1,5}', t): t = t.replace('|', '1').replace(' ', '')
    t = re.sub(r'^([1-7])\|(?=\s)', r'\g<1>1', t)
    ctx = t + ''.join(x['t'] for x in L[i + 1:i + 3])
    if re.match(r'^問題\s*[\d|lI]{1,2}(?!\d)', t) and re.search(r'(なさい|読んで|選び|答えとして)', ctx) and not re.match(r'^問題\s*[\d|]{1,2}\s*では', t):
        sec = dict(no=len(sections) + 1, instr=re.sub(r'^問題\s*[\d|lI]{1,2}\s*', '', t), blocks=[], _l=[l]); sec['name'] = SECNAME.get(sec['no'], '')
        sections.append(sec); q = None; cur = None; continue
    if sec is None: continue
    m = re.match(r'^(\d{1,2})\s*[.．]?\s*(.*)$', t)
    nxt = [x['t'] for x in L[i + 1:i + 5]]
    if m and int(m.group(1)) == qn + 1 and (q is None or len(q['o']) == 4) and any(OPT.match(x) and OPT.match(x).group(1) in '1|lI' for x in nxt):
        qn += 1; q = dict(t='q', n=qn, q=m.group(2), o=[], a=KEY.get(qn), _l=[l]); sec['blocks'].append(q); cur = None; continue
    if q is not None and len(q['o']) < 4:
        got = multi(t, len(q['o']) + 1)
        if len(got) < 2:
            om = OPT.match(t); got = []
            if om:
                d = om.group(1); d = 1 if d in '|lI' else int(d)
                if d == len(q['o']) + 1: got = [om.group(2)]
        if got:
            q['o'] += got; q['_l'].append(l); continue
    if q is not None and len(q['o']) == 0:
        q['q'] += t; q['_l'].append(l); continue
    if q is not None and 0 < len(q['o']) < 4:
        q['o'][-1] += t; q['_l'].append(l); continue
    if cur is None:
        cur = dict(t='text', text='', _l=[]); sec['blocks'].append(cur); q = None
    cur['text'] += ('\n' if cur['text'] else '') + t; cur['_l'].append(l)
bad = []; nq = 0
for s in sections:
    s.pop('_l')
    for b in s['blocks']:
        b['img'] = region(b.pop('_l'))
        if b['t'] == 'q':
            nq += 1
            if len(b['o']) != 4: bad.append(b['n'])
E = dict(id=eid, title=title, set='Đề thi JLPT N1 chính thức 2010–2018 (bản scan, OCR)', level='N1', nq=nq, sections=sections, scan=True)
json.dump(E, open(outf, 'w', encoding='utf-8'), ensure_ascii=False)
print(f'{title}: sections={len(sections)} q={nq} bad={bad}', [(s['no'], sum(1 for b in s['blocks'] if b['t'] == 'q')) for s in sections], file=sys.stderr)
