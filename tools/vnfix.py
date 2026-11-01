# Khôi phục dấu thanh tiếng Việt bị OCR làm rơi (thường ở â/ê/ô/ă/ơ/ư): chọn biến thể tốt nhất theo
# phiếu bầu OCR + tần suất từ (OpenSubtitles) + từ ghép có trong Viet74K. Quy hoạch động trên cả câu.
import re, math, unicodedata, functools
D = '/home/claude/dict'
FREQ = {}
for l in open(f'{D}/fw/content/2018/vi/vi_50k.txt', encoding='utf-8'):
    w, c = l.split(); w = unicodedata.normalize('NFC', w); FREQ[w] = FREQ.get(w, 0) + int(c)
TOT = sum(FREQ.values())
WORDS = set()
for l in open(f'{D}/vwl/Viet74K.txt', encoding='utf-8'):
    l = unicodedata.normalize('NFC', l.strip().lower())
    if ' ' in l: WORDS.add(l)
TONES = ['́', '̀', '̉', '̃', '̣']
def split_tone(s):
    d = unicodedata.normalize('NFD', s); t = ''.join(c for c in d if c in TONES)
    return unicodedata.normalize('NFC', ''.join(c for c in d if c not in TONES)), t
def tone_pos(base):
    # vị trí nguyên âm mang dấu (quy tắc đơn giản hoá)
    v = [i for i, c in enumerate(base) if c in 'aăâeêioôơuưy']
    if not v: return None
    for i in v:
        if base[i] in 'ăâêôơư': return i
    if len(v) >= 2 and base[v[-1]] != base[-1] or (len(v) >= 2 and base.endswith(('oa', 'oe', 'uy'))): return v[-1]
    if len(v) >= 2 and v[-1] == len(base) - 1: return v[-2]
    return v[-1] if len(v) == 1 else v[-2] if v[-1] == len(base) - 1 else v[-1]
def variants(tok):
    low = tok.lower(); base, t = split_tone(low)
    out = {low}
    if re.search('[ăâêôơư]', base) or t:
        i = tone_pos(base)
        if i is not None:
            for m in TONES + ['']:
                if m == t: continue
                out.add(unicodedata.normalize('NFC', base[:i + 1] + m + base[i + 1:]))
    return out
def lp(w): return math.log((FREQ.get(w, 0) + .5) / TOT)
def fix_line(text, cands=()):
    toks = text.split()
    if not toks: return text
    core = [re.sub(r'^\W+|\W+$', '', t) for t in toks]
    opts = []
    for k, c in enumerate(core):
        if not c or not re.search('[a-zA-ZÀ-ỹ]', c) or re.search(r'\d', c): opts.append([(c, 0.)]); continue
        vs = variants(c)
        o = []
        for v in vs:
            seen = sum(1 for cl in cands if k < len(cl) and re.sub(r'^\W+|\W+$', '', cl[k]).lower() == v)
            had = bool(split_tone(c.lower())[1])
            o.append((v, lp(v) + 0.1 * seen - (0 if v == c.lower() else 3.5 if had else 1.5)))
        opts.append(o)
    # DP: thưởng khi 2 âm tiết liền nhau thành từ ghép
    best = [{v: (s, None) for v, s in opts[0]}]
    for k in range(1, len(opts)):
        cur = {}
        for v, s in opts[k]:
            cur[v] = max(((ps + s + (6 if f'{pv} {v}' in WORDS else 0), pv) for pv, (ps, _) in best[-1].items()), key=lambda x: x[0])
        best.append(cur)
    v = max(best[-1], key=lambda x: best[-1][x][0]); seq = [v]
    for k in range(len(opts) - 1, 0, -1):
        v = best[k][v][1]; seq.append(v)
    seq.reverse()
    out = []
    for t, c, s in zip(toks, core, seq):
        if c and s != c.lower():
            s2 = s[0].upper() + s[1:] if c[0].isupper() else s
            t = t.replace(c, s2)
        out.append(t)
    return ' '.join(out)

if __name__ == '__main__':
    for s in ['cô phiêu', 'kiêu này hay kiêu khác', 'Không cân sông sang chảnh mà chỉ cân có cuộc sông như người bình thường là hạnh phúc rồi.',
              'Lân đâu tiên tôi mua thử cô phiêu, và y như răng tôi bị lô.', 'Do chậm thanh toán thuê nên tôi bị ủy ban quận gửi thông báo.',
              'Tôi muôn mình trở nên giàu tới mức có thê mua được bât cứ thứ gì.', 'bât kê là gì, bất cứ thứ gì', 'Tôi ráng xoay sở sao cho không bị cạn kiệt nguôn tiên tiệt kiệm.']:
        print(fix_line(s))
