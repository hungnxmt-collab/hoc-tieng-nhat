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
    if not re.match(r'^\s*⟦?\s*(Đ\.A|Câu|Đáp án)', l):
        l = re.sub(r'\s{6,}[\d ]{1,7}$', '', l.rstrip())
    l = re.sub(r'(^\s*|\s{3,})⟦\s*\d{1,3}\s*⟧\s*$', '', l)
    if re.fullmatch(r'\s*[\d ]{1,7}\s*', l):
        l = ''
    lines.append(l)

# chia đề
exams = []
cur = dict(title=SINGLE, lines=[]) if SINGLE else None
if cur: exams.append(cur)
for l in lines:
    m = None if SINGLE else (re.match(r'^@@EXAM (.+)$', l) or HEAD.match(l))
    if m:
        title = re.sub(r'\s+', ' ', m.group(1).strip())
        if l.startswith('@@EXAM'):
            cur = dict(title=title, lines=[]); exams.append(cur); continue
        cur = dict(title=title.title().replace('Đề Thi Thử Số', 'Đề thi thử số').replace('Đề Test Đầu Vào', 'Đề test đầu vào'), lines=[])
        exams.append(cur)
        continue
    if cur is not None:
        cur['lines'].append(l)

OPT = re.compile(r'(?:^|\s)([１-４])[．.]?\s*(.+?)(?=\s+[１-４][．.]?\s*\S|\s*$)')
OPT2 = re.compile(r'(?:^|\s)([1-4])[．.]?\s+(.+?)(?=\s+[1-4][．.]?\s+\S|\s*$)')


MK = re.compile(r'(?:(?<=\s)|^)([１-４1-4])(?:[．.、]\s*|\s+)(?=\S)')
MKS = re.compile(r'(?:(?<=\s)|^)([１-４1-4])(?:[．.、]\s*|\s{2,}|\s(?=[^\s0-9０-９年月日]))(?=\S)')
def _split(t, it, start):
    want = start; pos = []
    for m in it:
        if int(m.group(1).translate(FW)) == want and want <= 4:
            pos.append((m.start(), m.end())); want += 1
    if not pos or pos[0][0] != 0:
        return []
    return [t[b:(pos[i + 1][0] if i + 1 < len(pos) else len(t))].strip() for i, (a, b) in enumerate(pos)]


def split_opts(t, start):
    """Tách các phương án theo thứ tự start, start+1… (chấp nhận cả chữ số toàn góc/bán góc)."""
    t = t.strip()
    st = _split(t, MKS.finditer(t), start)
    lo = _split(t, MK.finditer(t), start)
    return st if len(st) >= len(lo) else lo


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
            if nums != list(range(nums[0], nums[0] + len(nums))) or len(nums) != len(vals):
                nums = list(range(nums[0], nums[0] + len(vals)))
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
        t = re.sub(r'^\d{1,3}\s{3,}(?=[１-４][\s．.])', '', t)
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
        if q is not None and not q['options'] and state == 'stem' and len(OPT.findall(t)) == 4 and len(split_opts(t, 1)) < 4:
            q['options'] = [sq(v) for _, v in OPT.findall(t)]; state = 'opt'; continue
        if q is not None and len(q['options']) < 4 and (q['options'] or state == 'stem'):
            got = split_opts(t, len(q['options']) + 1)
            if got:
                q['options'] += [sq(x) for x in got]
                state = 'opt'
                continue
        if q is not None and not q['options']:
            o4 = OPT.findall(t)
            if len(o4) == 4:
                q['options'] = [sq(v) for _, v in o4]; state = 'opt'; continue
        t = re.sub(r'^⟦\s*([0-9０-９]{1,2})\s*⟧\s*⟦?\s*([．.])\s*⟧?', r'\1\2', t)
        t = re.sub(r'^⟦\s*([0-9０-９]{1,2})\s*([．.])', r'\1\2⟦', t)
        tq = re.sub(r'^[０-９]+', lambda m: m.group(0).translate(FW), t)
        mq = re.match(r'^(\d{1,2})(?:\s*[．.。]|\s{2,})\s*(.*)$', tq)
        if mq and (int(mq.group(1)) == expect or (not mq.group(2).strip() and (q is None or len(q['options']) == 4)) or ((q is None or len(q['options']) == 4) and 0 < abs(int(mq.group(1)) - expect) <= 8 and state != 'text')):
            q = dict(n=expect, q=sq(mq.group(2)), options=[])
            sec['blocks'].append(dict(t='q', **{'q': q}))
            expect += 1
            state = 'stem'
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
