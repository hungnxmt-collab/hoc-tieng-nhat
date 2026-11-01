# "Cẩm nang ngữ pháp N1": tách các BÀI TẬP thành @@EXAM cho exam_parse.py.
# Đáp án cuối sách: hàng số câu "1. 2. …" + hàng đáp án; ghép theo vị trí cột. Đánh lại số câu liên tục trong mỗi bài tập.
import re, sys
src, dst = sys.argv[1:3]
L = open(src, encoding='utf-8').read().split('\n')
clean = lambda l: l.replace('⟦', ' ').replace('⟧', ' ')
head = re.compile(r'^\s*BÀI TẬP\s*([\d.]+)(?:\s*\((\d+)\s*câu\))?\s*(?:\d+)?\s*$')
kstart = max(i for i, l in enumerate(L) if re.fullmatch(r'\s*⟦?\s*ĐÁP\s+ÁN\s*⟧?\s*', l))
# --- đáp án
keys = {}; cur = None; numrow = None
for l in L[kstart + 1:]:
    c = clean(l)
    m = head.match(c)
    if m: cur = m.group(1); keys[cur] = []; numrow = None; continue
    if cur is None: continue
    c = re.sub(r'問題\s*\d', lambda m: ' ' * len(m.group(0)), c)
    c = re.sub(r'\(\d{4}\)', lambda m: ' ' * len(m.group(0)), c)
    toks = [(m.start(), m.group(1)) for m in re.finditer(r'(\d+)\.', c)]
    if toks and len(toks) >= 2 or (toks and not re.search(r'\d(?!\d*\.)', re.sub(r'\d+\.', '', c))):
        numrow = [[p, None] for p, _ in toks]; keys[cur].append(numrow); continue
    vals = [(m.start(), int(m.group(1))) for m in re.finditer(r'(?<![\d(])([1-4])(?![\d.)])', c)]
    if numrow and vals:
        for p, v in vals:
            k = min(range(len(numrow)), key=lambda i: abs(numrow[i][0] - p))
            if numrow[k][1] is None: numrow[k][1] = v
# --- đề
units = []; u = None
for l in L[:kstart]:
    c = clean(l).strip()
    m = head.match(clean(l))
    if m and '....' not in l:
        u = dict(id=m.group(1), lines=[], n=int(m.group(2) or 99)); units.append(u); off = 0; last = 0; newsec = False; tail = 0; continue
    if u is None: continue
    if last >= u['n']:
        tail += 1
        isopt = bool(re.match(r'^([1-4１-４][\s．.]|\d{1,3}\s{3,}[1-4１-４])', c))
        seen = u.setdefault('seen', 0)
        if isopt: u['seen'] += 1
        if c and (tail > 16 or (u['seen'] and not isopt and not c.startswith('⟦'))):
            u = None; continue
    if re.match(r'^\s*(BÀI\s*\d+|CHẶNG)\s*', c) and not c.startswith('BÀI TẬP'):
        u = None; continue
    if re.match(r'^問題\s*\d', c): newsec = True
    mq = re.match(r'^(\s*⟦?\s*)(\d{1,2})(\s*[．.])', l)
    if mq:
        n = int(mq.group(2))
        if newsec:
            off = last if n <= last else 0; newsec = False
        n2 = n + off
        if n2 == last + 1:
            l = l[:mq.start(2)] + str(n2) + l[mq.end(2):]; last = n2
    u['lines'].append(l)
with open(dst, 'w', encoding='utf-8') as f:
    for u in units:
        vals = [v for row in keys.get(u['id'], []) for _, v in row]
        f.write(f'@@EXAM Bài tập {u["id"]}\n' + '\n'.join(u['lines']) + '\nĐáp án:\n')
        f.write('Câu ' + ' '.join(str(i + 1) for i in range(len(vals))) + '\nĐ.A ' + ' '.join(str(v or 0) for v in vals) + '\n')
print('units', len(units), 'keys', len(keys), file=sys.stderr)
