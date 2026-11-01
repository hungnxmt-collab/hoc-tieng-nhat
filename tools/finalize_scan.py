# Thêm biên ngang (x0,x1) cho mỗi vùng ảnh, sửa ghi chú, ghi vào data/exams + index.
import json, glob, re, cv2, numpy as np
OUT = '/home/claude/raw/ocr/out'; REPO = '/home/claude/hoc-tieng-nhat'
cache = {}
def page(p):
    if p not in cache: cache.clear(); cache[p] = cv2.imread(f'/home/claude/raw/ocr/pg/p{p:03d}.png', cv2.IMREAD_GRAYSCALE)
    return cache[p]
def xb(r):
    p, y0, y1, W, H = r[:5]; g = page(p)[y0:y1]
    cols = np.where((g < 150).sum(0) > 1)[0]
    if not len(cols): return r[:5] + [0, W]
    return r[:5] + [max(0, int(cols[0]) - 24), min(W, int(cols[-1]) + 24)]
I = [x for x in json.load(open(f'{REPO}/data/exams/index.json')) if not x['id'].startswith('jr')]
new = []
for f in sorted(glob.glob(f'{OUT}/20*.json')):
    E = json.load(open(f)); E['set'] = 'Đề thi JLPT N1 chính thức 2010–2018 (bản scan)'
    for s in E['sections']:
        s['instr'] = re.sub(r'\s*[\(（][^)）]*\*\s*\d+\s*[)）]\s*$', '', s['instr'])
        for b in s['blocks']:
            b['img'] = [xb(r) for r in sorted(b['img'])]
            if E['id'] == 'jr201807' and b.get('n') == 2 and b['t'] == 'q':
                b['a'] = 3; b['note'] = 'Bảng đáp án gốc ghi 4, nhưng bản đề scan này xếp lựa chọn khác: 偏り đọc là かたより (phương án 3).'
    json.dump(E, open(f"{REPO}/data/exams/{E['id']}.json", 'w'), ensure_ascii=False, separators=(',', ':'))
    new.append(dict(id=E['id'], title=E['title'], set=E['set'], level='N1', nq=E['nq'],
                    secs=[[s['no'], sum(1 for b in s['blocks'] if b['t'] == 'q')] for s in E['sections']], fmt='jlpt', min=110, scan=True))
new.sort(key=lambda x: x['id'])
json.dump(new + I, open(f'{REPO}/data/exams/index.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print(len(new), sum(x['nq'] for x in new))
