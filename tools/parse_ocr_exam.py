# Tách 1 đề JLPT scan (đã OCR: pXXX.png + pXXX.tsv) thành JSON giống các đề khác, kèm toạ độ vùng ảnh gốc cho từng câu/đoạn.
# python3 parse_ocr_exam.py PGDIR first last key.json out.json ID "Tiêu đề"
import sys, re, csv, json, unicodedata
sys.path.insert(0, '/home/claude/scripts')
from ocr_geom import load, boxes, underlines, boxes_v
import subprocess, tempfile, os, cv2
def boxnum(im, b):
    x, y, w, h = b
    crop = im[y + 5:y + h - 5, x + 5:x + w - 5]
    crop = cv2.copyMakeBorder(cv2.resize(crop, None, fx=2, fy=2), 25, 25, 25, 25, cv2.BORDER_CONSTANT, value=255)
    fd, p = tempfile.mkstemp(suffix='.png'); os.close(fd); cv2.imwrite(p, crop)
    r = subprocess.run(['tesseract', p, '-', '-l', 'eng', '--psm', '7', '-c', 'tessedit_char_whitelist=0123456789'], capture_output=True, text=True).stdout.strip()
    os.remove(p)
    return int(r) if r.isdigit() else None
pgdir, first, last, keyf, outf, eid, title = sys.argv[1:8]
first, last = int(first), int(last)
KEY = {int(k): v for k, v in json.load(open(keyf)).items()}
FW = str.maketrans('１２３４５６７８９０', '1234567890')
MK = re.compile(r'(?:(?<=\s)|(?<=[。、」）)])|^)([1-4１-４])(?:[．.、]\s*|\s*)(?=[^\s0-9０-９年月日時分回歳%])')
SECNAME = {1: '漢字読み', 2: '文脈規定', 3: '言い換え類義', 4: '用法', 5: '文法形式の判断', 6: '文の組み立て', 7: '文章の文法',
           8: '内容理解（短文）', 9: '内容理解（中文）', 10: '内容理解（長文）', 11: '統合理解', 12: '主張理解（長文）', 13: '情報検索'}


MKR = re.compile(r'([1-4１-４])(?=[^\s0-9０-９年月日時分回歳%])')
def split_opts(t, start):
    a = _split(t, start, MK)
    m0 = re.match(r'^\s*([1-4１-４])[．.]?\s+(?=\S)', t)
    if not a and m0 and int(m0.group(1).translate(FW)) == start:   # "1 時代…": chữ sau số bị loại nhầm
        rest = t[m0.end():]; more = _split(rest, start + 1, MK)
        if more:
            k = re.search(r'(?:(?<=\s)|^)' + str(start + 1), rest)
            return [rest[:k.start()].strip() if k else rest.strip()] + more
        return [rest.strip()]
    if len(a) + start - 1 < 4:
        b = _split(t, start, MKR)
        if len(b) + start - 1 == 4 and len(b) > len(a): return b
    return a
def _split(t, start, RX):
    t = t.strip(); want = start; pos = []
    for m in RX.finditer(t):
        if int(m.group(1).translate(FW)) == want and want <= 4:
            pos.append((m.start(), m.end())); want += 1
    if not pos or pos[0][0] > 2:
        return []
    return [t[b:(pos[i + 1][0] if i + 1 < len(pos) else len(t))].strip() for i, (a, b) in enumerate(pos)]


def page_lines(p):
    png = f'{pgdir}/p{p:03d}.png'; tsv = f'{pgdir}/p{p:03d}.tsv'
    im, bw = load(png)
    H, W = bw.shape
    bx = [b for b in boxes(bw) if 150 <= b[0] <= 330 and b[2] < 130 and b[3] < 90]
    xl = bx[0][0] + 1 if bx else 213
    for b in boxes_v(bw, xl):
        if not any(abs(b[1] - c[1]) < 20 for c in bx): bx.append(b)
    bx.sort(key=lambda b: b[1])
    bnum = {b: boxnum(im, b) for b in bx}
    ul = underlines(bw)
    words = []
    with open(tsv, encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE):
            if r['level'] != '5' or not (r['text'] or '').strip(): continue
            words.append(dict(x=int(r['left']), y=int(r['top']), w=int(r['width']), h=int(r['height']), t=r['text'].strip(),
                              k=(r['block_num'], r['par_num'], r['line_num'])))
    lines = {}
    for wd in words: lines.setdefault(wd['k'], []).append(wd)
    out = []
    for k, ws in lines.items():
        ws.sort(key=lambda w: w['x'])
        y0 = min(w['y'] for w in ws); y1 = max(w['y'] + w['h'] for w in ws)
        raw = ''.join(w['t'] for w in ws)
        if y0 > H - 260 and not re.search(r'[問間閂門][題超頭].*(なさい|選び)', raw): continue                                   # số trang dưới cùng
        if y1 < 300 and not re.search(r'[問間閂門][題超頭]', raw) and (re.search(r'(秘|通[赴辻直]|真[題惑剖题恩]|能力|N\s*1|YuuKi|考)', raw) or len(raw) < 6): continue   # watermark / tiêu đề đầu trang
        box = next((b for b in bx if b[1] - 25 < (y0 + y1) / 2 < b[1] + b[3] + 25), None)
        text = ''; prev = None
        for w in ws:
            chars = list(w['t']); n = len(chars); cw = w['w'] / max(n, 1)
            for i, ch in enumerate(chars):
                cx = w['x'] + (i + .5) * cw
                if box and cx < box[0] + box[2] + 12: continue
                und = any(u[0] - 6 <= cx <= u[0] + u[2] + 6 and -6 <= u[1] - (w['y'] + w['h']) <= 22 for u in ul)
                if prev is not None and cx - prev > cw * 1.6 + 8: text += ' '
                text += ('⟦' + ch + '⟧') if und else ch
                prev = cx
        text = re.sub('⟧⟦', '', text)
        text = unicodedata.normalize('NFKC', text).replace('⟦ ⟧', ' ')
        x0 = min(w['x'] for w in ws)
        if box and x0 < box[0] + box[2] + 12: x0 = box[0] + box[2] + 12
        out.append(dict(p=p, y0=y0, y1=y1, x0=x0, t=text.strip(), box=box, bn=bnum.get(box) if box else None, W=W, H=H))
    # ô số câu không dính dòng nào (dòng trống) -> thêm dòng rỗng
    for b in bx:
        if not any(l['box'] == b for l in out):
            out.append(dict(p=p, y0=b[1], y1=b[1] + b[3], x0=b[0] + b[2], t='', box=b, bn=bnum.get(b), W=W, H=H))
    out.sort(key=lambda l: l['y0'])
    return out


L = []
for p in range(first, last + 1):
    L += page_lines(p)
# bỏ tiêu đề đề thi / tên phần
if os.environ.get('DBG'):
    for l in L: print(l['p'], l['y0'], l['x0'], l['box'] and 'B', l['bn'], l['t'][:60], file=sys.stderr)
L = [l for l in L if not re.search(r'(真[題题]|能力考|^第.部分|^言語知識|^読解|^[\(（]?文字|^文法\s*$|^言語知識)', l['t'].replace(' ', '')) or l['box']]

sections = []; sec = None; q = None; qn = 0; state = None; bad = []
def region(lines):
    segs = {}
    for l in lines:
        s = segs.setdefault(l['p'], [l['y0'], l['y1'], l['W'], l['H']])
        s[0] = min(s[0], l['y0']); s[1] = max(s[1], l['y1'])
    return [[p, max(0, a - 18), min(H, b + 18), W, H] for p, (a, b, W, H) in segs.items()]
cur_text = None
def near(q, l, t):  # dòng tiếp nối liền ngay dưới lựa chọn (không phải mở đầu đoạn văn mới)
    p = q['_l'][-1]
    if re.match(r'^[（(]\s*[0-9０-９]\s*[)）]', t.replace('⟦', '')): return False
    return p['p'] == l['p'] and l['y0'] - p['y1'] < 0.9 * (p['y1'] - p['y0'])
for li, l in enumerate(L):
    t = l['t']; tc = t.replace(' ', '').replace('⟦', '').replace('⟧', '')
    if qn >= max(KEY) and q is not None and len(q['o']) == 4 and re.match(r'^(\d+番|聴解|例$)', tc): break
    m = re.match(r'^[問間閂門][題超頭題]?\s*([0-9０-９]{1,2})', tc) or (re.match(r'^[問間閂門][題超頭]\D', tc) and 'なさい' in tc and re.match(r'^..(.)', tc))
    if m and not l['box'] and ('なさい' in tc or '選び' in tc or '読んで' in tc or len(tc) > 12):
        no = int(m.group(1).translate(FW)) if m.group(1).translate(FW).isdigit() else (sections[-1]['no'] + 1 if sections else 1)
        if sections and no != sections[-1]['no'] + 1: no = sections[-1]['no'] + 1
        sec = dict(no=no, instr=re.sub(r'^[問間閂門][題超頭題]?\s*[0-9０-９]{1,2}\s*', '', t).replace('⟦', '').replace('⟧', ''), name=SECNAME.get(no, ''), blocks=[], _l=[l])
        sections.append(sec); q = None; state = 'instr'; cur_text = None; continue
    if sec is None: continue
    if state == 'instr' and not l['box'] and not split_opts(t, 1) and not sec['instr'].endswith('。'):
        sec['instr'] += t.replace('⟦', '').replace('⟧', ''); continue
    nxt = L[li + 1]['t'] if li + 1 < len(L) else ''
    implicit = (not l['box'] and t and sec['no'] not in (6, 7) and len(split_opts(t, 1)) < 2 and (q is None or len(q['o']) == 4) and state != 'instr'
                and re.match(r'^[1１][．.\s]', nxt) and len(split_opts(nxt, 1)) >= (1 if os.environ.get('LOOSE') else 2) and qn < max(KEY))
    inline = (l['box'] and sec is not None and sec['no'] == 7 and state in ('text', 'stem') and not split_opts(t, 1)
              and (not (re.match(r'^[1１][．.\s]', nxt) and len(split_opts(nxt, 1)) >= 2) or (li + 1 < len(L) and L[li + 1]['box'] and L[li + 1]['p'] == l['p'])))
    if os.environ.get('DBG2') and l['box'] and sec and sec['no'] == 7: print('DBG', state, len(t), bool(split_opts(t, 1)), repr(nxt[:30]), file=sys.stderr)
    if inline:
        l = dict(l, t=f"（{l['bn'] or ''}）" + t, box=None)
        t = l['t']
    if (l['box'] or implicit) and not inline:
        bn = l.get('bn')
        qn = bn if bn and qn < bn <= qn + 4 else qn + 1
        q = dict(t='q', n=qn, q=t, o=[], a=KEY.get(qn), _l=[l]); sec['blocks'].append(q); state = 'stem'; cur_text = None
        got = split_opts(t, 1)
        if len(got) >= 2: q['o'] = got; q['q'] = ''; state = 'opt'
        continue
    if q is not None and len(q['o']) < 4:
        got = split_opts(t, len(q['o']) + 1)
        if got:
            q['o'] += got; q['_l'].append(l); state = 'opt'; continue
        if state == 'stem':
            q['q'] += t; q['_l'].append(l); continue
        if state == 'opt' and near(q, l, t):
            q['o'][-1] += t; q['_l'].append(l); continue
    if q is not None and state == 'opt' and len(q['o']) == 4 and near(q, l, t) and l['x0'] > q['_l'][-1]['x0'] + 30 and not re.search(r'[。」]$', q['o'][-1].replace('⟧', '')):
        q['o'][-1] += t; q['_l'].append(l); continue
    # đoạn văn
    if cur_text is None:
        cur_text = dict(t='text', text='', _l=[]); sec['blocks'].append(cur_text); q = None; state = 'text'
    cur_text['text'] += ('\n' if cur_text['text'] else '') + t; cur_text['_l'].append(l)

out_secs = []; nq = 0
for s in sections:
    blocks = []
    for b in s['blocks']:
        b['img'] = region(b.pop('_l'))
        if b['t'] == 'q':
            b['o'] = [re.sub(r'\s+', ' ', o).strip() for o in b['o']]; b['q'] = re.sub(r'\s+', ' ', b['q']).strip()
            if len(b['o']) != 4 or not b['a']: bad.append(b['n'])
            nq += 1
        blocks.append(b)
    s.pop('_l', None); s['blocks'] = blocks; out_secs.append(s)
E = dict(id=eid, title=title, set='Đề thi JLPT N1 chính thức 2010–2018 (bản scan, OCR)', level='N1', nq=nq, sections=out_secs, scan=True)
json.dump(E, open(outf, 'w', encoding='utf-8'), ensure_ascii=False)
print(f'{title}: sections={len(out_secs)} q={nq} key={len(KEY)} bad={bad}', [(s['no'], sum(1 for b in s['blocks'] if b['t'] == "q")) for s in out_secs], file=sys.stderr)
