# Tách đề thi (dạng Thaolejp) thành JSON: phần 問題, đoạn văn, câu hỏi 4 lựa chọn, đáp án.
# python3 exam_parse.py text.txt out.json PREFIX "Nhãn bộ đề" LEVEL
import re, sys, json, unicodedata

src, dst, prefix, label, level = sys.argv[1:6]
SINGLE = sys.argv[6] if len(sys.argv) > 6 else None
raw = open(src, encoding='utf-8').read()
FW = str.maketrans('１２３４５６７８９０', '1234567890')
HEAD = re.compile(r'^\s*(ĐỀ\s+(?:NGHE\s+)?THI\s+THỬ\s+SỐ\s*(\d+)|ĐỀ\s+TEST\s+ĐẦU\s+VÀO|ĐỀ\s+THI\s+(?:JLPT\s+)?N\d\s+(?:THÁNG\s*)?[\d/.\- ]+)\s*$', re.I)

lines = []
for l in raw.split('\n'):
    if l.startswith('<<<PAGE'):
        continue
    if 'Khóa luyện đề' in l or 'Thaolejp' in l or 'thaolejp' in l or 'Khóa học online' in l:
        continue
    l = re.sub(r'\s{6,}[\d ]{1,7}$', '', l.rstrip())
    if re.fullmatch(r'\s*[\d ]{1,7}\s*', l):
        l = ''
    lines.append(l)

# chia đề
exams = []
cur = dict(title=SINGLE, lines=[]) if SINGLE else None
if cur: exams.append(cur)
for l in lines:
    m = None if SINGLE else HEAD.match(l)
    if m:
        title = re.sub(r'\s+', ' ', m.group(1).strip())
        cur = dict(title=title.title().replace('Đề Thi Thử Số', 'Đề thi thử số').replace('Đề Test Đầu Vào', 'Đề test đầu vào'), lines=[])
        exams.append(cur)
        continue
    if cur is not None:
        cur['lines'].append(l)

OPT = re.compile(r'(?:^|\s)([１-４])[．.]?\s*(.+?)(?=\s+[１-４][．.]?\s*\S|\s*$)')
OPT2 = re.compile(r'(?:^|\s)([1-4])[．.]?\s+(.+?)(?=\s+[1-4][．.]?\s+\S|\s*$)')


def sq(s):
    return re.sub(r'[ 　]{2,}', ' ', s).strip()


def parse_exam(ex):
    body, key = [], []
    inkey = False
    for l in ex['lines']:
        if re.match(r'^\s*⟦?\s*Đáp án\s*:', l):
            inkey = True
            continue
        (key if inkey else body).append(l)
    # đáp án
    ans = {}
    nums = None
    for l in key:
        t = re.sub('[⟦⟧]', '', l).strip()
        if t.startswith('Câu'):
            nums = [int(x) for x in re.findall(r'\d+', t)]
        elif (t.startswith('Đáp án') or t.startswith('Đ.A')) and nums:
            vals = [int(x) for x in re.findall(r'\d+', t.translate(FW))]
            for n, v in zip(nums, vals):
                ans[n] = v
            nums = None
    sections = []
    sec = None
    q = None
    expect = 1
    state = 'text'
    pend_instr = False
    for l in body:
        t = l.strip()
        if not t:
            if state == 'instr':
                state = 'afterinstr'
            continue
        ms = re.match(r'^問題\s*([0-9０-９]+)\s*(.*)$', t)
        if ms:
            sec = dict(no=int(ms.group(1).translate(FW)), instr=sq(ms.group(2)), blocks=[])
            sections.append(sec)
            state = 'instr'
            q = None
            continue
        if sec is None:
            continue
        if state == 'instr' and not re.search(r'[。]$', sec['instr']) and not re.match(r'^\d{1,2}\s*[．.]', t):
            sec['instr'] = sq(sec['instr'] + t)
            continue
        tq = re.sub(r'^[０-９]+', lambda m: m.group(0).translate(FW), t)
        mq = re.match(r'^(\d{1,2})(?:\s*[．.]|\s{2,})\s*(.*)$', tq)
        if mq and (int(mq.group(1)) == expect or ((q is None or len(q['options']) == 4) and 0 < abs(int(mq.group(1)) - expect) <= 8 and state != 'text')):
            q = dict(n=expect, q=sq(mq.group(2)), options=[])
            sec['blocks'].append(dict(t='q', **{'q': q}))
            expect += 1
            state = 'stem'
            continue
        opts = OPT.findall(t)
        if not opts and re.match(r'^[1-4][．.]?\s+\S', t):
            opts = [(k.translate(str.maketrans('1234', '１２３４')), v) for k, v in OPT2.findall(t)]
        if q is not None and len(opts) == 4 and not q['options']:
            q['options'] = [sq(v) for _, v in opts]
            state = 'opt'
            continue
        if q is not None and opts and int(opts[0][0].translate(FW)) == len(q['options']) + 1 and len(q['options']) < 4:
            for k, v in opts:
                if int(k.translate(FW)) == len(q['options']) + 1:
                    q['options'].append(sq(v))
            state = 'opt'
            continue
        if state == 'stem' and q is not None and not q['options']:
            q['q'] = sq(q['q'] + t)
            continue
        if state == 'opt' and q is not None and (len(q['options']) < 4 or (not re.search(r'[。」）)]$', q['options'][-1]) and len(t) <= 30 and not re.match(r'^[（(]\d', t))):
            q['options'][-1] = sq(q['options'][-1] + t)
            continue
        # đoạn văn
        state = 'text'
        if sec['blocks'] and sec['blocks'][-1]['t'] == 'text':
            sec['blocks'][-1]['lines'].append(l)
        else:
            sec['blocks'].append(dict(t='text', lines=[l]))
    # gắn đáp án + dọn đoạn văn
    nq = 0
    bad = []
    for s in sections:
        nb = []
        for b in s['blocks']:
            if b['t'] == 'q':
                qq = b['q']
                qq['answer'] = ans.get(qq['n'])
                nq += 1
                if len(qq['options']) != 4 or not qq['answer']:
                    bad.append(qq['n'])
                nb.append(dict(t='q', n=qq['n'], q=qq['q'], o=qq['options'], a=qq['answer']))
            else:
                ls = [x.rstrip() for x in b['lines']]
                table = sum(1 for x in ls if re.search(r'\S\s{4,}\S', x.strip())) >= max(3, len(ls) * 0.3)
                if table:
                    ind = min((len(x) - len(x.lstrip()) for x in ls if x.strip()), default=0)
                    nb.append(dict(t='pre', text=re.sub('[⟦⟧]', '', '\n'.join(x[ind:] for x in ls))))
                else:
                    nb.append(dict(t='text', text='\n'.join(sq(x) for x in ls)))
        s['blocks'] = nb
    return sections, nq, len(ans), bad


out = []
for i, ex in enumerate(exams):
    secs, nq, na, bad = parse_exam(ex)
    if not nq or 'Nghe' in ex['title'] or 'NGHE' in ex['title']:
        continue
    eid = f'{prefix}{i}'
    out.append(dict(id=eid, title=ex['title'], set=label, level=level, nq=nq, sections=secs))
    print(f'{ex["title"]:28} q={nq:3} keys={na:3} bad={bad[:12]}', file=sys.stderr)
json.dump(out, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('exams', len(out), file=sys.stderr)
