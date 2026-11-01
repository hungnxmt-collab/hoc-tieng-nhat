# "Tổng hợp ngữ pháp N1" (Thaolejp): n．tiêu đề / nghĩa (VI) / cấu trúc / ví dụ JP + dịch VI / ghi chú
import sys, re, json
sys.path.insert(0, '/home/claude/scripts')
from furi import read_lines
src, dst, setid = sys.argv[1:4]
MODE = sys.argv[4] if len(sys.argv) > 4 else 'th'
lines = read_lines(src)
VI = re.compile(r'[A-Za-zÀ-ỹĐđ]{2,}')
JP = re.compile(r'[ぁ-んァ-ヶ一-龥]')
def jj(s): return re.sub(r'(?<=[ぁ-んァ-ヶー一-龥々、。「」（）])\s+(?=[ぁ-んァ-ヶー一-龥々、。「」（）])', '', s)
out = []; cur = None; started = False; skip = False; bai = '0'; chang = 1
for ln in lines:
    t = re.sub(r'\s+', ' ', ln['text']).strip()
    if not t or 'Thaolejp' in t or re.fullmatch(r'\d+', t) or '.....' in t: continue
    if MODE == 'cn':
        if re.match(r'^ĐÁP ÁN$', t) and out: break
        if t.startswith('BÀI TẬP'): skip = True; cur = None; continue
        mb = re.fullmatch(r'BÀI\s*(\d+)', t); mc = re.match(r'^CHẶNG\s*(\d)', t)
        if mc: chang = int(mc.group(1)); skip = False; cur = None; continue
        if mb: bai = mb.group(1); skip = False; cur = None; continue
        if skip and t.isupper() and not JP.search(t): skip = False; bai = t.title(); cur = None; continue
        if skip: continue
        if not skip and t.isupper() and not JP.search(t) and len(t) > 3 and not re.match(r'^[A-Z]{1,3}[：:]', t): bai = t.title(); continue
        m = re.match(r'^(\d{1,2})\s*[．.]\s*(.+)$', t)
        if m and JP.search(m.group(2)) and not VI.search(m.group(2)) and not re.search(r'[。]$', m.group(2)):
            cur = dict(no=len(out) + 1, title=jj(m.group(2)), mean=[], form=[], ex=[], exvi=[], use=[], grp=(f'Chặng {chang} · ' + (f'Bài {bai}' if bai.isdigit() else bai))); out.append(cur); continue
    m = re.match(r'^(\d{1,3})\s*[．.]\s*(.+)$', t)
    if m and (not out and m.group(1) == '1' or out and int(m.group(1)) == out[-1]['no'] + 1) and JP.search(m.group(2)) and not VI.search(m.group(2)):
        cur = dict(no=int(m.group(1)), title=jj(m.group(2)), mean=[], form=[], ex=[], exvi=[], use=[]); out.append(cur); continue
    if cur is None: continue
    isvi = bool(VI.search(t)) and not (JP.search(t) and len(JP.findall(t)) > len(VI.findall(t)) * 2)
    isform = ('＋' in t or '+' in t or re.match(r'^(N|V|A|ナ|イ|普通形|①|②|（1）|\(1\))', t)) and not t.endswith('。') and not t.startswith('・')
    last = cur.get('last')
    if isvi:
        if last == 'ex': cur['exvi'][-1] = t; cur['last'] = 'exvi'
        elif last == 'exvi' and not re.search(r'[.!?…”"]$', cur['exvi'][-1]): cur['exvi'][-1] += ' ' + t
        elif last == 'mean' and not re.search(r'[.!?)…]$', cur['mean'][-1]): cur['mean'][-1] += ' ' + t
        elif not cur['mean'] and not cur['ex']: cur['mean'].append(t); cur['last'] = 'mean'
        elif last == 'use' and not re.search(r'[.!?)…:]$', cur['use'][-1]): cur['use'][-1] += ' ' + t
        else: cur['use'].append(t); cur['last'] = 'use'
    elif isform and last in (None, 'mean', 'form'):
        cur['form'].append(jj(t)); cur['last'] = 'form'
    else:
        t = jj(t.lstrip('・'))
        if last == 'ex' and not re.search(r'[。？！」）]$', cur['ex'][-1]): cur['ex'][-1] += t
        else: cur['ex'].append(t); cur['exvi'].append(''); cur['last'] = 'ex'
res = []
for x in out:
    res.append(dict(id=f'{setid}{x["no"]}', set=setid, ch=0, grp=x.get('grp', ''), title=('～' + x['title'].lstrip('～〜')) if not re.match(r'^[（(ぁ-ん一-龥]', x['title'].lstrip('～〜')) or x['title'].startswith(('～', '〜')) else x['title'],
                    form=x['form'], mean=' '.join(x['mean']), use=x['use'], ex=x['ex'], exvi=x['exvi']))
print(len(res), 'nomean', sum(1 for r in res if not r['mean']), 'noex', sum(1 for r in res if not r['ex']), file=sys.stderr)
json.dump(res, open(dst, 'w', encoding='utf-8'), ensure_ascii=False)
