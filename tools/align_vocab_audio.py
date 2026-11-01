# Căn file nghe từ vựng (đã chép lời bằng SenseVoice) với bộ "Chinh phục từ vựng N1":
# mỗi bài bắt đầu bằng "第N", mỗi từ: [số] [từ] [câu ví dụ]. Dùng câu ví dụ trong bộ thẻ làm mốc.
# Kết quả: {item_id: [part, start, end, wstart, wend]}  (đoạn đầy đủ: số+từ+ví dụ; đoạn chỉ có từ)
import re, json, glob, difflib, sys
VOC = '/home/claude/hoc-tieng-nhat/data/vocab.json'
KN = dict(zip('〇一二三四五六七八九', range(10)))
def kanum(s):
    s = s.strip()
    if s.isdigit(): return int(s)
    if not s or any(c not in '〇一二三四五六七八九十百' for c in s): return None
    n = 0; cur = 0
    for c in s:
        if c == '百': n += (cur or 1) * 100; cur = 0
        elif c == '十': n += (cur or 1) * 10; cur = 0
        else: cur = cur * 10 + KN[c]
    return n + cur
segs = []
for f in sorted(glob.glob('/home/claude/asr/out/vocab/part*.txt')):
    part = int(re.search(r'part(\d+)', f).group(1))
    for l in open(f, encoding='utf-8'):
        m = re.match(r'([\d.]+) -- ([\d.]+): (.*)', l.strip())
        if m: segs.append(dict(p=part, a=float(m.group(1)), b=float(m.group(2)), t=m.group(3)))
clean = lambda t: re.sub(r'[。、？?！!「」\s]', '', t)
# mốc bài
lessons = {}
for i, s in enumerate(segs):
    m = re.match(r'^第\s*([〇一二三四五六七八九十百\d]+)\s*[？?。]?$', s['t'])
    if m and kanum(m.group(1)): lessons.setdefault(kanum(m.group(1)), i)
V = json.load(open(VOC)); decks = {int(d['id'][2:]): d for d in V if re.fullmatch(r'cp\d+', d['id'])}
out = {}; miss = []
ls = sorted(lessons); cursor = 0
for L in sorted(decks):
    j0 = lessons[L] + 1 if L in lessons and lessons[L] >= cursor - 2 else cursor
    nxt = [lessons[x] for x in ls if lessons[x] > j0 + 5]
    j1 = min(nxt) if nxt else len(segs)
    cur = j0
    for it in decks[L]['items']:
        exv = it.get('ex') or ''
        if isinstance(exv, list): exv = exv[0] if exv else ''
        if isinstance(exv, dict): exv = exv.get('jp') or exv.get('t') or ''
        ex = clean(exv)
        if not ex: miss.append(it['id']); continue
        best = None
        for j in range(cur, min(j1, cur + 14)):
            acc = '';
            for e in range(j, min(j1, j + 3)):
                if segs[e]['p'] != segs[j]['p']: break
                acc += clean(segs[e]['t']); r = difflib.SequenceMatcher(None, acc, ex).ratio()
                if best is None or r > best[0] + .01: best = (r, j, e)
        if not best or best[0] < .45: miss.append(it['id']); continue
        r, j, e = best
        # đoạn từ + số ở trước câu ví dụ
        w = j - 1; n = j - 2
        ws = segs[w] if w >= cur and segs[w]['p'] == segs[j]['p'] and kanum(re.sub(r'[？?。]', '', segs[w]['t'])) is None else None
        start = segs[w]['a'] if ws else segs[j]['a']
        if ws and n >= cur and segs[n]['p'] == segs[j]['p'] and kanum(re.sub(r'[？?。]', '', segs[n]['t'])) is not None: start = segs[n]['a']
        out[it['id']] = [segs[j]['p'], round(max(0, start - .15), 2), round(segs[e]['b'] + .25, 2),
                         round(ws['a'] - .1, 2) if ws else None, round(ws['b'] + .2, 2) if ws else None]
        cur = e + 1; cursor = cur
tot = sum(len(d['items']) for d in decks.values())
print(f'lessons={len(lessons)} aligned={len(out)}/{tot} miss={len(miss)}', file=sys.stderr)
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else '/home/claude/raw/vocab_audio_align.json', 'w'))
