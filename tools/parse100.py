# Tách "100 bài đọc hiểu N1" thành các bài đọc + câu hỏi 4 lựa chọn + đáp án (bảng 正解 cuối sách)
import re, sys, json
src, dst = sys.argv[1:3]
FW = str.maketrans('１２３４５６７８９０', '1234567890')
L = []
for l in open(src, encoding='utf-8').read().split('\n'):
    if l.startswith('<<<PAGE') or 'Thaolejp' in l: continue
    if re.fullmatch(r'\s*\d{1,3}\s*', l): continue
    if '正解' not in l: l = re.sub(r'\s{6,}\d{1,3}$', '', l.rstrip())
    L.append(l)
kpos = max(i for i, l in enumerate(L) if re.fullmatch(r'\s*⟦?\s*解答\s*⟧?\s*', l))
body, key = L[:kpos], L[kpos + 1:]
akey = {}
rows = [re.sub('[⟦⟧]', '', l) for l in key]
setsrow = qrow = None
for t in rows:
    if re.search(r'問題', t):
        setsrow = [int(x) for x in re.findall(r'(\d+)\.', t.translate(FW))]; qrow = None
    elif re.match(r'^\s*問\s', t):
        qrow = [int(x) for x in re.findall(r'(\d+)\.', t.translate(FW))]
    elif '正解' in t and setsrow:
        vals = [int(x) for x in re.findall(r'\d', t[t.index('正解') + 2:].translate(FW))]
        if qrow:
            si = -1
            for qn, v in zip(qrow, vals):
                if qn == 1: si += 1
                akey.setdefault(setsrow[si], []).append(v)
        else:
            for sn, v in zip(setsrow, vals): akey.setdefault(sn, []).append(v)
answers = [v for k in sorted(akey) for v in akey[k]]
sets = []; cur = None
for l in body:
    t = re.sub(r'\s+', ' ', l).strip()
    m = re.fullmatch(r'⟦?問題\s*(\d{1,3})⟧?', t)
    if m and (not sets or int(m.group(1)) == sets[-1]['no'] + 1) and int(m.group(1)) <= 100:
        cur = dict(no=int(m.group(1)), lines=[]); sets.append(cur); continue
    t = re.sub(r'⟦\s*\d+\s*⟧', '', t).strip()
    if cur is not None and t: cur['lines'].append(t)
OPT = re.compile(r'^([１-４1-4])[．.]\s*(.*)$')
out = []; qi = 0; bad = []
for s in sets:
    ls = s['lines']; qs = []; passage = []; i = 0
    # tìm các khối lựa chọn
    starts = [k for k, l in enumerate(ls) if OPT.match(l) and OPT.match(l).group(1).translate(FW) == '1']
    prev_end = 0
    for k in starts:
        # câu hỏi: lùi từ k-1
        j = k - 1; stem = []
        while j >= prev_end:
            l = ls[j]
            if re.match(r'^問\s*[0-9０-９]', l):
                stem.insert(0, l); break
            if stem and re.search(r'[。」]$', l): break
            stem.insert(0, l); j -= 1
        pre = ls[prev_end:j if stem and not re.match(r'^問\s*[0-9０-９]', ls[j]) else j]
        if re.match(r'^問\s*[0-9０-９]', ls[j]) if j >= prev_end else False:
            pre = ls[prev_end:j]
        passage += pre
        opts = []; e = k
        while e < len(ls) and len(opts) < 4:
            m = OPT.match(ls[e])
            if m and (int(m.group(1).translate(FW)) == len(opts) + 1 or (len(opts) == 3 and m.group(1).translate(FW) == '3')):
                opts.append(m.group(2)); e += 1; continue
            if opts and not OPT.match(ls[e]) and not re.match(r'^問\s*[0-9０-９]', ls[e]) and len(opts) < 4:
                opts[-1] += ls[e]; e += 1; continue
            break
        q = re.sub(r'^問\s*[0-9０-９]+\s*[：:.．]?\s*', '', ''.join(stem))
        ka = akey.get(s['no'], []); ans = ka[len(qs)] if len(qs) < len(ka) else None; qi += 1
        if len(opts) != 4 or not ans: bad.append((s['no'], q[:20]))
        qs.append(dict(q=q, options=opts, answer=ans))
        prev_end = e
    passage += ls[prev_end:]
    if len(qs) != len(akey.get(s['no'], [])): print('MISMATCH', s['no'], len(qs), len(akey.get(s['no'], [])), [x['q'][:25] for x in qs], file=sys.stderr)
    # ghép đoạn: dòng bắt đầu bằng khoảng trắng đầu dòng (đã mất) -> dùng độ dài
    paras = []; mx = max((len(x) for x in passage), default=1); prev = ''
    for l in passage:
        if paras and len(prev) >= mx * 0.85 and not re.match(r'^(…|（注|＊|※)', l): paras[-1] += l
        else: paras.append(l)
        prev = l
    out.append(dict(id=f'r100_{s["no"]}', title=f'問題{s["no"]}', pages=[], img=[], passage=paras, questions=qs))
print('sets', len(out), 'questions', qi, 'answers', len(answers), 'bad', bad[:10], file=sys.stderr)
json.dump(dict(id='r100', label='問題', title='Thaolejp – 100 bài đọc hiểu N1', sets=out), open(dst, 'w', encoding='utf-8'), ensure_ascii=False)
