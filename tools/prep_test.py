# Chuyển sách "Test từ vựng-ngữ pháp" (BÀI n / TỪ VỰNG / NGỮ PHÁP, đáp án dồn cuối) sang dạng @@EXAM cho exam_parse.py
import re, sys
src, dst, name = sys.argv[1:4]
L = open(src, encoding='utf-8').read().split('\n')
# vị trí phần đáp án: dòng 'ĐÁP ÁN' đứng riêng (không phải mục lục)
first_da = next(i for i, l in enumerate(L) if re.match(r'^\s*⟦?\s*Đ\.A', l))
kpos = max(i for i in range(first_da) if re.fullmatch(r'\s*⟦?\s*BÀI\s*1\s*⟧?\s*', L[i]))
body, key = L[:kpos], L[kpos:]
def units(lines, start_pat):
    out = []; cur = None; bai = None
    for l in lines:
        t = re.sub(r'\s+', ' ', re.sub('[⟦⟧]', '', l)).strip()
        m = re.fullmatch(r'(?:BÀI\s*(\d+)|第\s*(\d+)\s*回)', t)
        if m: bai = int(m.group(1) or m.group(2)); continue
        kind = 'Từ vựng' if t in ('TỪ VỰNG', '文字語彙', '文字・語彙') else 'Ngữ pháp' if t in ('NGỮ PHÁP', '文法') else None
        if bai and kind:
            cur = [f'Bài {bai} – {kind}', []]; out.append(cur); continue
        if cur: cur[1].append(l)
    return out
B = units(body, None); K = units(key, None)
kd = {t: ls for t, ls in K}
with open(dst, 'w', encoding='utf-8') as f:
    for t, ls in B:
        f.write(f'@@EXAM {t}\n' + '\n'.join(ls) + '\nĐáp án:\n' + '\n'.join(kd.get(t, [])) + '\n')
print(name, len(B), 'units', len(K), 'keys', file=sys.stderr)
