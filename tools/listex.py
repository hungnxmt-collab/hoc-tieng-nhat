# Danh sách "n．tiêu đề" + các câu "・ví dụ" (Từ nối, Text nghe kính ngữ)
import re, sys, json
src, dst = sys.argv[1:3]
out = []; cur = None; sec = ''
for l in open(src, encoding='utf-8').read().split('\n'):
    t = re.sub(r'\s+', ' ', l).strip()
    if not t or t.startswith('<<<') or 'Thaolejp' in t or 'MÙA LUYỆN' in t or 'Website' in t or 'Youtube' in t or 'Fanpage' in t or 'Học tiếng Nhật' in t or re.fullmatch(r'\d+', t): continue
    if t.isupper() and not re.search(r'[ぁ-んァ-ヶ一-龥]', t): sec = t.title(); continue
    m = re.match(r'^(\d{1,2})\s*[．.]\s*(.+)$', t)
    if m and not t.startswith('・'):
        cur = dict(sec=sec, title=m.group(2).strip(), ex=[]); out.append(cur); continue
    if cur is None: continue
    if t.startswith('・'): cur['ex'].append(t[1:].strip())
    elif cur['ex']: cur['ex'][-1] += (' ' if re.match(r'^[A-Z]', t) else '') + t
json.dump(out, open(dst, 'w', encoding='utf-8'), ensure_ascii=False)
print(len(out), [ (x['sec'], x['title'], len(x['ex'])) for x in out][:6], file=sys.stderr)
