# Xoá trắng các dòng chữ chứa tên Thaolejp / Dũng Mori / Yuuki Bùi trên ảnh trang.
# python3 wipe_names.py img1 img2 ...   (in ra: tên file + số dòng đã xoá)
import sys, subprocess, csv, io, re, os, tempfile
from PIL import Image, ImageDraw
PAT = re.compile(r'(yuu ?ki|yuuk|thaole|thaolejp|d[ũu]ng ?mori|tôi ?yêu ?ngo|toiyeungoai|yeungoaingu|bui\.yuuki|facebook\.com/groups/toiyeu)', re.I)
def ocr(path, psm):
    r = subprocess.run(['tesseract', path, '-', '-l', 'eng+vie', '--psm', str(psm), 'tsv'], capture_output=True, text=True).stdout
    lines = {}
    for w in csv.DictReader(io.StringIO(r), delimiter='\t', quoting=csv.QUOTE_NONE):
        if w.get('level') != '5' or not (w['text'] or '').strip(): continue
        lines.setdefault((w['block_num'], w['par_num'], w['line_num']), []).append(w)
    return lines.values()
for f in sys.argv[1:]:
    im = Image.open(f); mode = im.mode; g = im.convert('L')
    fd, tmp = tempfile.mkstemp(suffix='.png'); os.close(fd); g.save(tmp)
    W, H = g.size; boxes = []
    for psm in (3, 11):
        for ws in ocr(tmp, psm):
            txt = ' '.join(w['text'] for w in ws)
            if not PAT.search(txt.replace(' ', '') if psm == 11 else txt) and not PAT.search(txt): continue
            if psm == 11:   # chỉ những từ khớp + từ lân cận cùng hàng
                ws = [w for w in ws if PAT.search(w['text']) or re.search(r'(b[ùu]i|yuu|ki)$', w['text'], re.I)] or ws
            x0 = min(int(w['left']) for w in ws); y0 = min(int(w['top']) for w in ws)
            x1 = max(int(w['left']) + int(w['width']) for w in ws); y1 = max(int(w['top']) + int(w['height']) for w in ws)
            if y1 - y0 > H * .08: continue   # bỏ qua khối quá cao (nhận nhầm)
            boxes.append((x0, y0, x1, y1))
    os.remove(tmp)
    if boxes:
        d = ImageDraw.Draw(im)
        for x0, y0, x1, y1 in boxes:
            pad = max(6, (y1 - y0) // 2)
            # chân/đầu trang: xoá cả dải ngang từ khối đó tới mép phải (số trang ở lề trái giữ lại)
            if y0 > H * .9 or y1 < H * .08: x1 = W - 1
            d.rectangle([max(0, x0 - pad), max(0, y0 - pad), min(W - 1, x1 + pad), min(H - 1, y1 + pad)], fill=255 if im.mode == 'L' else (255,) * len(im.getbands()))
        im.save(f, quality=60, method=6) if f.endswith('.webp') else im.save(f)
    print(f, len(boxes), flush=True)
