# Từ vựng / mẫu ngữ pháp ĐÃ ĐƯỢC HỎI TRỰC TIẾP trong đề thật JLPT N1 (bản có chữ: 2010–2018 + 12/2021)
#  - Từ vựng: 問題1 (từ gạch chân), 問題2 (4 lựa chọn), 問題3 (từ gạch chân + lựa chọn), 問題4 (từ được hỏi)
#  - Ngữ pháp: lựa chọn của 問題5, 6, 7
# → data/freq.json  {n, src, v: {id: [số lần, [mã đề]]}, g: {...}}
import json, re, os
R = os.path.join(os.path.dirname(__file__), '..')
I = json.load(open(f'{R}/data/exams/index.json'))
ids = [x['id'] for x in I if re.match(r'^(jr\d{6}|de12210)$', x['id'])]
KJ = re.compile(r'[一-龥々]')
ul = lambda q: re.findall(r'⟦(.+?)⟧', q or '')
vstr, gstr = [], []          # (chuỗi, mã đề)
for i in ids:
    E = json.load(open(f'{R}/data/exams/{i}.json'))
    for s in E['sections']:
        for b in s['blocks']:
            if b.get('t') != 'q': continue
            n, q, o = s['no'], b.get('q') or '', [x for x in (b.get('o') or []) if x]
            if n == 1: vstr += [(x, i) for x in ul(q)]
            elif n == 2: vstr += [(x, i) for x in o]
            elif n == 3: vstr += [(x, i) for x in ul(q) + o]
            elif n == 4: vstr += [(re.sub(r'[⟦⟧]', '', q), i)]
            elif n in (5, 6, 7): gstr += [(x, i) for x in o]
vstr = [(re.sub(r'[\s　]', '', a), i) for a, i in vstr if a.strip()]
ROW = {'う': 'わいうえおっ', 'く': 'かきくけこい', 'ぐ': 'がぎぐげごい', 'す': 'さしすせそ', 'つ': 'たちつてとっ', 'ぬ': 'なにぬねのん',
       'ぶ': 'ばびぶべぼん', 'む': 'まみむめもん', 'る': 'らりるれろったてなまよさずば'}
def pat(w):
    w = re.split(r'[〈［\[（(／/・]', w)[0].strip()
    if KJ.search(w) and len(w) > 2: w = re.sub(r'な$', '', w)
    if len(w) > 3: w = re.sub(r'する$', '', w)
    if len(w) < 2 and not KJ.search(w): return None
    if len(w) < 2: return None
    last = w[-1]
    if KJ.search(w[:-1]) and last in ROW: return re.compile('^' + re.escape(w[:-1]) + '[' + ROW[last] + ']'), len(w)
    if KJ.search(w[:-1]) and last == 'い': return re.compile('^' + re.escape(w[:-1]) + '[いかくけさ]'), len(w)
    return re.compile('^' + re.escape(w) + '(?:な|に|する|した|して|と|だ|の)?$' if not KJ.search(w) else '^' + re.escape(w)), len(w)
def hits(p, L, pool):
    rx, n = p
    return [i for s, i in pool if rx.search(s) and len(s) <= n + 4]
VSTOP = {'言う', '思う', '見る', '引く', 'する', 'ある', 'なる', 'いる', '行く', '来る'}
V = json.load(open(f'{R}/data/vocab.json')); vf = {}; cache = {}
for d in V:
    for it in d['items']:
        w = it['w']
        if w not in cache:
            p = None if re.split(r'[〈［]', w)[0] in VSTOP else pat(w); cache[w] = hits(p, 0, vstr) if p else []
        if cache[w]: vf[it['id']] = [len(cache[w]), sorted(set(cache[w]))]
G = json.load(open(f'{R}/data/grammar.json'))
def gcore(t): return re.sub(r'[A-Z]', '', re.split(r'[／/・〜～（(]', re.sub(r'^[～〜~]', '', t))[0]).strip()
GSTOP = {'という', 'だろう', 'でしょう', 'ところ', 'ながら', 'から', 'まで', 'までに', 'だけ', 'まま', 'ものだ', 'はずだ', 'てください', 'てくれる', 'いただく', 'ては', 'とする', 'ではないか', 'だろうか', 'でしょうか', 'として', 'とは', 'もの', 'なり'}
gf = {}
for g in G:
    c = gcore(g['title'])
    if len(c) < 2 or c in GSTOP: continue
    h = [i for s, i in gstr if s == c or (len(c) >= 3 and c in s)]
    if h: gf[g['id']] = [len(h), sorted(set(h))]
json.dump({'n': len(ids), 'src': ids, 'v': vf, 'g': gf}, open(f'{R}/data/freq.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print(len(ids), 'đề;', len(vstr), 'chuỗi từ vựng,', len(gstr), 'lựa chọn ngữ pháp;', len(vf), 'mục từ;', len(gf), 'mẫu ngữ pháp')
