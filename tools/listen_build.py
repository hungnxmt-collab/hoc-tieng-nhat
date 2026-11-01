# Dựng đề nghe hiểu (聴解) cho các đề JLPT N1 thật + đề đọc dạng "làm trên đề gốc" cho các đề 2020–2025.
# Nguồn: catalog.json (file đề/script), classify.json (OCR nhanh từng trang), listen_keys.txt, reading_keys.json,
#        txt/<ym>.txt (chép lời audio, dùng để tìm mốc 問題1..5).
import json, re, os, subprocess, sys
from PIL import Image
B = '/home/claude/raw/exb'; REPO = '/home/claude/hoc-tieng-nhat'
CAT = json.load(open(f'{B}/catalog.json')); CL = json.load(open(f'{B}/classify.json'))
RK = json.load(open(f'{B}/reading_keys.json'))
LK = {}
for l in open('/home/claude/raw/ex/listen_keys.txt'):
    p = l.split()
    if p: LK[p[0]] = p[1:]
PNAME = ['問題1 課題理解', '問題2 ポイント理解', '問題3 概要理解', '問題4 即時応答', '問題5 統合理解']
RNAME = ['漢字読み', '文脈規定', '言い換え類義', '用法', '文法形式の判断', '文の組み立て', '文章の文法', '内容理解（短文）', '内容理解（中文）', '内容理解（長文）', '統合理解', '主張理解（長文）', '情報検索']
KN = dict(zip('一二三四五', range(1, 6)))
LIS = {'2010-07': (13, 14), '2010-12': (13, 14), '2011-07': (13, 14), '2011-12': (13, 14), '2012-07': (12, 14), '2012-12': (13, 14),
       '2013-07': (13, 13), '2013-12': (13, 14), '2014-07': (13, 14), '2014-12': (12, 14), '2015-07': (12, 14), '2015-12': (12, 13),
       '2016-07': (12, 14), '2016-12': (14, 15), '2017-07': (14, 15), '2017-12': (13, 15), '2018-07': (16, 17), '2018-12': (22, 25),
       '2019-07': (16, 19), '2019-12': (30, 36), '2020-12': (23, 25), '2021-07': (36, 48), '2021-12': (18, 22), '2022-07': (17, 20),
       '2022-12': (20, 22), '2023-07': (32, 35), '2023-12': (39, 51), '2024-07': (34, 36), '2024-12': (37, 39)}
REND = {'2020-12': 22, '2021-07': 33, '2021-12': 17, '2022-07': 16, '2022-12': 19, '2023-07': 30, '2023-12': 33, '2024-07': 32, '2024-12': 35, '2025-07': 30}

def render(pdf, pages, out, w=1240):
    os.makedirs(os.path.dirname(out), exist_ok=True); names = []
    for p in pages:
        f = f'{out}_{p:02d}.webp'
        if not os.path.exists(f):
            tmp = f'/tmp/claude-0/r_{os.getpid()}'
            subprocess.run(['pdftoppm', '-r', '130', '-gray', '-f', str(p), '-l', str(p), '-png', pdf, tmp], capture_output=True)
            src = [x for x in os.listdir('/tmp/claude-0') if x.startswith(f'r_{os.getpid()}')][0]
            im = Image.open('/tmp/claude-0/' + src).convert('L'); os.remove('/tmp/claude-0/' + src)
            im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS); im.save(f, 'WEBP', quality=55, method=6)
        names.append(f.replace(REPO + '/', ''))
    return names

def markers(ym, sizes=None):
    """Thời điểm bắt đầu 問題1..5 trong audio (theo chép lời)."""
    f = f'/home/claude/raw/exa/txt/{ym}.txt'
    if not os.path.exists(f): return None
    segs = []
    for l in open(f, encoding='utf-8'):
        m = re.match(r'([\d.]+) -- ([\d.]+): (.*)', l.strip())
        if m: segs.append((float(m.group(1)), m.group(3)))
    ts = {}
    for t, s in segs:
        m = re.match(r'^\s*問題\s*([1-5一二三四五])[^0-9]', s + ' ')
        if m:
            k = int(m.group(1)) if m.group(1).isdigit() else KN[m.group(1)]
            if k not in ts and all(ts.get(j, -1) < t for j in range(1, k)): ts[k] = t
    end = segs[-1][0] + 5 if segs else None
    if len(ts) < 5:   # dự phòng: nhóm theo "1番" lặp lại
        NUM = dict(zip('一二三四五六七八九', range(1, 10))); NUM.update({'十': 10})
        def num(x):
            x = x.strip()
            if x.isdigit(): return int(x)
            if x in NUM: return NUM[x]
            m = re.fullmatch(r'十([一二三四五六七八九])', x)
            return 10 + NUM[m.group(1)] if m else None
        hits = []
        for t, s in segs:
            m = re.match(r'^\s*([0-9一二三四五六七八九十]{1,3})\s*番\s*[？?。]?\s*$', s)
            if m and num(m.group(1)): hits.append((t, num(m.group(1))))
        starts = [t for k, (t, n) in enumerate(hits) if n == 1 and (k == 0 or hits[k - 1][1] > 1)]
        if len(starts) == 4 and sizes:   # thiếu mốc 問題5: lấy câu tiếp theo sau đủ số câu của 問題4
            after = [t for t, n in hits if t >= starts[3]]
            starts = starts + [after[sizes[3]] if len(after) > sizes[3] else after[-1] + 30]
        if len(starts) >= 5:
            if len(starts) > 5 and sizes:
                import itertools
                def cost(c):
                    tot = 0
                    for k, a in enumerate(c):
                        b = c[k + 1] if k + 1 < 5 else 1e9
                        tot += abs(sum(1 for t, n in hits if a <= t < b) - sizes[k])
                    return tot
                starts = min((c for c in itertools.combinations(starts, 5) if c[0] == starts[0]), key=cost)
            ts = {k + 1: max(0, t - 2) for k, t in enumerate(starts[:5])}
    return ts, end

idx = [x for x in json.load(open(f'{REPO}/data/exams/index.json')) if not x['id'].startswith(('ls', 'jn'))]
new = []
for ym in sorted(CAT):
    c = CAT[ym]
    if not c['book'] or ym not in CL: continue
    bp = CL[ym]['book']; sp = CL[ym].get('script', [])
    pdf = '/home/claude/raw/ex/' + c['book']
    # trang đề nghe: trang có ≥3 chữ 番 (phần câu hỏi nghe) — lấy dải liên tục cuối cùng
    lis = list(range(LIS[ym][0], LIS[ym][1] + 1)) if ym in LIS else []
    tag = ym.replace('-', '')
    # --- đề nghe
    if ym in LK and lis:
        mk = markers(ym, [len(g) for g in LK[ym]])
        secs = []; n = 0
        for k, grp in enumerate(LK[ym]):
            blocks = []
            for j, d in enumerate(grp):
                n += 1; blocks.append(dict(t='q', n=n, a=int(d), o=[], pq=1, lab=j + 1))
            sec = dict(no=k + 1, name=PNAME[k], instr='', blocks=blocks)
            if mk and (k + 1) in mk[0]:
                a = mk[0][k + 1]; b = next((mk[0][j] for j in range(k + 2, 6) if j in mk[0]), mk[1])
                sec['au'] = [dict(f=f'audio/exam/{ym}.mp3', a=round(max(0, a - 1), 1), b=round(b, 1) if b else None)]
            secs.append(sec)
        aud = os.path.exists(f'{REPO}/audio/exam/{ym}.mp3')
        sc_pages = []
        if c['script']:
            spdf = '/home/claude/raw/ex/' + c['script']
            if 'Đáp án+Script' in c['script'] or 'Đáp Án+Script' in c['script']:
                st = next((i + 1 for i, p in enumerate(sp) if i >= 3 and (p['ban'] >= 1 or p['cho'])), max(2, len(sp) - 5))
                sc_pages = [1] + list(range(st, len(sp) + 1))
            else:
                sc_pages = list(range(1, len(sp) + 1))
            sc_pages = render(spdf, sc_pages, f'{REPO}/img/exam/{tag}/s')
        E = dict(id=f'ls{tag}', title=f'JLPT N1 tháng {int(ym[5:])}/{ym[:4]} — Nghe hiểu (聴解)', set='Đề thi JLPT N1 thật — Nghe hiểu (có audio)', level='N1',
                 nq=n, paper=render(pdf, lis, f'{REPO}/img/exam/{tag}/l'), sections=secs, script=sc_pages,
                 audio=f'audio/exam/{ym}.mp3' if aud else None,
                 note='Mỗi 問題 có trình phát audio riêng (tự tua đến đúng phần). Phần 問題3–5 không in câu hỏi trong đề: nghe rồi chọn 1–4 trong phiếu.' if aud else 'Đề này không có file nghe.')
        json.dump(E, open(f'{REPO}/data/exams/{E["id"]}.json', 'w'), ensure_ascii=False, separators=(',', ':'))
        new.append(dict(id=E['id'], title=E['title'], set=E['set'], level='N1', nq=n, secs=[[s['no'], len(s['blocks'])] for s in secs], fmt='practice', min=60, paper=True, listen=True))
    # --- đề đọc dạng làm trên đề gốc (đề chưa có trong app)
    if ym in RK and not os.path.exists(f'{REPO}/data/exams/jr{tag}.json') and not os.path.exists(f'{REPO}/data/exams/jl{tag}.json'):
        key = RK[ym]; N = len(key)
        sizes = {'2020-12': [6, 7, 6, 6, 10, 5, 4, 4, 9, 3, 2, 4, 2], '2021-07': [6, 7, 6, 6, 10, 5, 4, 4, 9, 4, 2, 4, 2],
                 '2021-12': [6, 7, 6, 6, 10, 5, 4, 4, 9, 4, 3, 3, 2]}.get(ym, [6, 7, 6, 6, 10, 5, 4, 4, 8, 3, 2, 3, 2])
        assert sum(sizes) == N, (ym, N)
        rpages = [i + 1 for i in range(REND[ym]) if bp[i]['n'] > 150]
        secs = []; n = 0
        for k, sz in enumerate(sizes):
            blocks = [dict(t='q', n=n + j + 1, a=int(key[n + j]), o=[], pq=1) for j in range(sz)]; n += sz
            secs.append(dict(no=k + 1, name=RNAME[k], instr='', blocks=blocks))
        E = dict(id=f'jn{tag}', title=f'JLPT N1 tháng {int(ym[5:])}/{ym[:4]}', set='Đề thi JLPT N1 2019–2025 (làm trên đề gốc)', level='N1', nq=N,
                 paper=render(pdf, rpages, f'{REPO}/img/exam/{tag}/r'), sections=secs, note='Đáp án do các nhóm luyện thi tổng hợp (JLPT không công bố đáp án chính thức).')
        json.dump(E, open(f'{REPO}/data/exams/{E["id"]}.json', 'w'), ensure_ascii=False, separators=(',', ':'))
        new.append(dict(id=E['id'], title=E['title'], set=E['set'], level='N1', nq=N, secs=[[s['no'], len(s['blocks'])] for s in secs], fmt='jlpt', min=110, paper=True))
    print(ym, 'listen pages', lis, 'markers', markers(ym, [len(g) for g in LK[ym]] if ym in LK else None)[0] if markers(ym) else None, file=sys.stderr)
json.dump(idx + new, open(f'{REPO}/data/exams/index.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('new', len(new), file=sys.stderr)
