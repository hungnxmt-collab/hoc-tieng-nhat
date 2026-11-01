# "Chinh phục từ vựng N1 (kèm dịch nghĩa)": BÀI n → mục "n．TỪ nghĩa" + ví dụ "・…" + dịch
import sys, re, json
sys.path.insert(0, '/home/claude/scripts')
from furi import read_lines, reading
src, dst = sys.argv[1:3]
lines = read_lines(src)
JPW = re.compile(r'^([0-9０-９]+)[．.]\s*([^\sA-Za-zÀ-ỹĐđ（(]+(?:（[^）]*）)?)\s*(.*)$')
out = []; bai = None; cur = None; seen_bai = False
for ln in lines:
    t = ln['text'].strip()
    if not t or 'Thaolejp' in t or re.fullmatch(r'\d+', t): continue
    m = re.fullmatch(r'BÀI\s*(\d+)(?:\s*\(.*\))?', t)
    if m and '---' not in t:
        bai = int(m.group(1)); seen_bai = True; continue
    if not seen_bai or '------' in t: continue
    m = JPW.match(t)
    if m and not t.startswith('・'):
        a = ln['text'].index(m.group(2)); b = a + len(m.group(2))
        w = m.group(2); r = reading(ln, a, b)
        cur = dict(bai=bai, n=int(m.group(1).translate(str.maketrans('０１２３４５６７８９', '0123456789'))), w=w, r=r if r != w else '', m=m.group(3).strip(), ex=[], exvi=[])
        out.append(cur); continue
    if cur is None: continue
    if t.startswith('・'):
        cur['ex'].append(t[1:].strip()); cur['exvi'].append(''); continue
    jp = re.search(r'[ぁ-んァ-ン一-龥]', t) and not re.search(r'[A-Za-zÀ-ỹĐđ]{2}', t)
    if cur['ex']:
        if jp and not cur['exvi'][-1]: cur['ex'][-1] += t
        else: cur['exvi'][-1] = (cur['exvi'][-1] + ' ' + t).strip()
    else:
        cur['m'] = (cur['m'] + ' ' + t).strip()
import collections
c = collections.Counter(x['bai'] for x in out)
print('words', len(out), 'bai', len(c), 'noread', sum(1 for x in out if not x['r'] and re.search(r'[一-龥]', x['w'])), 'noex', sum(1 for x in out if not x['ex']), file=sys.stderr)
json.dump(out, open(dst, 'w', encoding='utf-8'), ensure_ascii=False)
