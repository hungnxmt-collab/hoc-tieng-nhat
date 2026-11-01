import re, json, sys, unicodedata

FILES = [
    ('r_20678c65.txt', 'tanbun', '短文', 'Đoạn văn ngắn (短文)'),
    ('r_9751c4a5.txt', 'chuubun', '中文', 'Đoạn văn vừa (中文)'),
    ('r_aa56b568.txt', 'choubun', '長文', 'Đoạn văn dài (長文)'),
    ('r_2793ab3b.txt', 'hikaku', '比較', 'Đọc so sánh (統合理解)'),
    ('r_64b64aaf.txt', 'kensaku', '検索', 'Tìm kiếm thông tin (情報検索)'),
]

def nz(s):
    return unicodedata.normalize('NFKC', s)

def parse(fn, key, label, title):
    raw = open('/home/claude/out/' + fn, encoding='utf-8').read()
    pages = re.split(r'<<<PAGE (\d+)>>>\n', raw)[1:]
    pages = [(int(pages[i]), pages[i + 1]) for i in range(0, len(pages), 2)]
    keypage = pages[-1][1]
    body_pages = pages[:-1]
    # build line stream with page numbers
    lines = []
    for pno, txt in body_pages:
        ls = txt.split('\n')
        # drop trailing page number
        while ls and re.fullmatch(r'\s*\d+\s*', ls[-1] or ''):
            ls.pop()
        while ls and not ls[-1].strip():
            ls.pop()
        for l in ls:
            lines.append((pno, l.rstrip()))
    head_re = re.compile(r'^\s*' + label + r'\s*([0-9０-９]+)\s*$')
    sets = []
    cur = None
    for pno, l in lines:
        m = head_re.match(l)
        if m:
            cur = {'no': int(nz(m.group(1))), 'lines': [], 'pages': []}
            sets.append(cur)
        if cur is None:
            continue
        if pno not in cur['pages']:
            cur['pages'].append(pno)
        if not m:
            cur['lines'].append(l)
    out = []
    for s in sets:
        passage, qs = [], []
        q = None
        state = 'p'
        for l in s['lines']:
            t = l.strip()
            if not t or re.fullmatch(r'\d+', t):
                continue
            t = re.sub(r'^([1-4１-４])\s+(.+?)\s+([2-4２-４])\s+(.+)$', lambda m: m.group(0), t)
            mq = re.match(r'^問(?:\s*([0-9０-９]+)|\s)\s*(.*)$', t)
            multi = re.findall(r'(?:^|\s)([1-4１-４])\s+(\S+?)(?=\s+[1-4１-４]\s|$)', t)
            mo = re.match(r'^([1-4１-４])\s+(.*)$', t)
            if q is not None and len(multi) >= 2 and [int(nz(a)) for a, _ in multi] == list(range(len(q['options']) + 1, len(q['options']) + 1 + len(multi))):
                q['options'] += [b for _, b in multi]
                state = 'o'
            elif mq:
                q = {'q': mq.group(2).strip(), 'options': []}
                qs.append(q)
                state = 'q'
            elif q is not None and mo and len(q['options']) < 4 and int(nz(mo.group(1))) == len(q['options']) + 1:
                q['options'].append(mo.group(2).strip())
                state = 'o'
            elif q is not None and state == 'q':
                q['q'] += t
            elif q is not None and state == 'o' and len(q['options']) < 4:
                q['options'][-1] += t
            elif q is not None and state == 'o' and len(q['options']) == 4:
                # passage continues after questions (検索 layout: questions first, then doc)
                passage.append(t)
                state = 'p2'
            else:
                passage.append(t)
        out.append({'id': f'{key}{s["no"]}', 'title': f'{label}{s["no"]}', 'pages': s['pages'],
                    'passage': passage, 'questions': qs})
    # answer key
    left, right = [], []
    for l in keypage.split('\n'):
        l = nz(l)
        toks = re.findall(r'(?:問\s*\d|' + label + r'\s*\d+)\s+(\d)', l)
        if len(toks) == 2:
            left.append(int(toks[0])); right.append(int(toks[1]))
        elif len(toks) == 1:
            left.append(int(toks[0]))
    answers = left + right
    allq = [q for s in out for q in s['questions']]
    if len(answers) < len(allq):
        print('WARN answers', fn, len(answers), len(allq), file=sys.stderr)
    for q, a in zip(allq, answers):
        q['answer'] = a
    bad = [(s['id'], len(q['options'])) for s in out for q in s['questions'] if len(q['options']) != 4]
    print(title, 'sets', len(out), 'questions', len(allq), 'answers', len(answers), 'bad', bad, file=sys.stderr)
    return {'id': key, 'label': label, 'title': title, 'sets': out}

res = [parse(*f) for f in FILES]
json.dump(res, open('/home/claude/out/reading.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
