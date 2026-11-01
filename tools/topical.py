# Bảng chuyên đề Thaolejp → các bộ thẻ từ vựng
import sys, re, json, glob, pdfplumber
sys.path.insert(0, '/home/claude/scripts')
A = '/mnt/user-data/attachments/413ebfd0-e47f-5706-9593-b1c390735ee8/'
JP = re.compile(r'[ぁ-んァ-ヶ一-龥]')
def rows(pre):
    f = glob.glob(A + pre + '*')[0]; out = []
    with pdfplumber.open(f) as pdf:
        for p in pdf.pages:
            p = p.filter(lambda o: o.get('object_type') != 'char' or o['size'] >= 8)
            for t in p.extract_tables():
                for r in t: out.append([(c or '').strip() for c in r])
    return out
one = lambda s: re.sub(r'\s*\n\s*', ' ', s).strip()
decks = []
def deck(id, name, items): decks.append(dict(id=id, group='Chuyên đề N1 (Thaolejp)', name=name, items=items)); print(name, len(items), file=sys.stderr)
# Phó từ
it = []
for r in rows('f69b7e2e'):
    c = [x for x in r if x]
    if len(c) >= 3 and re.match(r'^\d+\.?$', c[0]) and JP.search(c[1]): it.append(dict(id=f'pt{len(it)+1}', w=one(c[1]), r='', hv='', m=one(c[2]), ex=[]))
deck('pho_tu', 'Phó từ N1', it)
# Cụm từ thay thế
it = []; year = ''
for r in rows('4b90ba47'):
    c = [x for x in r if x]
    if len(c) == 1 and re.fullmatch(r'20\d\d', c[0]): year = c[0]; continue
    if len(c) >= 4 and re.match(r'^\d+$', c[0]):
        w, rep, vi = one(c[1]), one(c[2]), one(c[3])
        m = re.match(r'^(.*?)（([ぁ-ん]+)）(.*)$', w)
        it.append(dict(id=f'ct{len(it)+1}', w=(m.group(1) + m.group(3)) if m else w, r=m.group(2) if m else '', hv=f'Đề {year}' if year else '', m=f'≈ {rep} — {vi}', ex=[]))
    elif it and len(c) >= 1 and not re.match(r'^\d+$', c[0]) and len(r) >= 4:
        it[-1]['m'] += ' ' + ' '.join(one(x) for x in c)
deck('thay_the', 'Cụm từ thay thế trong đề thi (言い換え)', it)
# Động từ ghép
it = []
for r in rows('191c7385'):
    if len(r) >= 3 and re.match(r'^\d+$', r[0].strip()) and r[1]:
        parts = [x.strip() for x in r[2].split('\n') if x.strip()]
        mean = parts[0] if parts else ''; ex = []
        for p in parts[1:]:
            if JP.search(p) and not ex or (JP.search(p[:3])): ex.append(p)
            elif ex: ex[-1] += ' ' + p
            else: mean += ' ' + p
        it.append(dict(id=f'dg{len(it)+1}', w=one(r[1]), r='', hv='', m=mean, ex=ex))
    elif it and len(r) >= 3 and not r[0].strip() and r[2]:
        it[-1]['ex'] += [x.strip() for x in r[2].split('\n') if x.strip()]
deck('dt_ghep', 'Động từ ghép N1', it)
# Kanji cách đọc đặc biệt
it = []; k = ''
for r in rows('6eb6d6c1'):
    if len(r) >= 6 and r[2] and r[0] != 'STT':
        if r[1]: k = r[1]
        it.append(dict(id=f'kd{len(it)+1}', w=one(r[2]), r=one(r[4]), hv=one(r[3]), m=one(r[5]) + (f' (chữ {k})' if k else ''), ex=[]))
    elif it and len(r) >= 6 and not r[2] and (r[5] or r[3]):
        it[-1]['m'] = it[-1]['m'] + ' ' + one(r[5]); it[-1]['hv'] += (' ' + one(r[3])) if r[3] else ''
deck('kanji_dacbiet', 'Kanji cách đọc đặc biệt', it)
# 130 kanji khó
it = []
for r in rows('bf9f7f64'):
    if len(r) >= 4 and re.match(r'^\d+$', r[0].strip()):
        it.append(dict(id=f'kk{len(it)+1}', w=one(r[1]), r=one(r[2]), hv='', m=one(r[3]), ex=[]))
    elif it and len(r) >= 4 and not r[0].strip() and r[3]: it[-1]['m'] += ' ' + one(r[3])
deck('kanji_kho', '130 cụm kanji khó', it)
# Tiền tố / Hậu tố
for pre, did, name in [('d80789de', 'tien_to', 'Tiền tố (接頭語)'), ('d22bbc21', 'hau_to', 'Hậu tố (接尾語)')]:
    it = []; g = ''
    for r in rows(pre):
        if len(r) >= 5 and r[0] != 'STT' and r[2]:
            if r[1]: g = one(r[1])
            it.append(dict(id=f'{did[:2]}{len(it)+1}', w=one(r[2]), r=one(r[3]), hv=g, m=one(r[4]), ex=[]))
        elif it and len(r) >= 5 and not r[2] and r[4]: it[-1]['m'] += ' ' + one(r[4])
    deck(did, name, it)
# Kanji dễ nhầm lẫn
it = []; grp = 0
for r in rows('3d61a691'):
    if len(r) >= 8 and r[0] != 'STT' and r[5]:
        if r[0].strip(): grp = r[0].strip()
        hv = one(r[2] or r[3] or r[4])
        it.append(dict(id=f'kn{len(it)+1}', w=one(r[5]), r=one(r[6]), hv=f'{one(r[1])} {hv}'.strip(), m=one(r[7]) + (f' — nhóm {grp}' if grp else ''), ex=[]))
    elif it and len(r) >= 8 and not r[5] and r[7]: it[-1]['m'] = it[-1]['m'].replace(f' — nhóm {grp}', '') + ' ' + one(r[7]) + f' — nhóm {grp}'
deck('kanji_nham', 'Kanji dễ nhầm lẫn', it)
json.dump(decks, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False)
