# Đọc PDF có furigana: trả về các dòng chữ (cỡ lớn) kèm hàm lấy cách đọc cho một đoạn từ (ghép furigana theo vị trí).
import pdfplumber, re, unicodedata
from multiprocessing import Pool

KANJI = re.compile(r'[一-龥々〆ヶ]')
SRC = None


def _page(i):
    with pdfplumber.open(SRC) as pdf:
        p = pdf.pages[i]
        big = [c for c in p.chars if c['size'] >= 8]
        small = [c for c in p.chars if c['size'] < 8 and c['text'].strip()]
        lines = []
        for c in sorted(big, key=lambda c: (round(c['top']), c['x0'])):
            if lines and abs(lines[-1]['top'] - c['top']) <= 2.5:
                lines[-1]['chars'].append(c)
            else:
                lines.append(dict(top=c['top'], chars=[c]))
        out = []
        for ln in lines:
            cs = sorted(ln['chars'], key=lambda c: c['x0'])
            text, pos = '', []
            for k, c in enumerate(cs):
                if k and c['x0'] - cs[k - 1]['x1'] > 2.5 and c['text'] != ' ' and not text.endswith(' '):
                    text += ' '; pos.append(None)
                text += c['text']; pos.append((c['x0'], c['x1']))
            furi = [(s['x0'], s['x1'], s['text']) for s in small if ln['top'] - 12 <= s['top'] <= ln['top'] - 1]
            out.append(dict(text=text, pos=pos, furi=furi, page=i + 1))
        return out


def read_lines(src, procs=2):
    global SRC
    SRC = src
    with pdfplumber.open(src) as pdf:
        n = len(pdf.pages)
    with Pool(procs, initializer=lambda s: globals().__setitem__('SRC', s), initargs=(src,)) as pool:
        pages = pool.map(_page, range(n), chunksize=4)
    return [l for pg in pages for l in pg]


def reading(line, a, b):
    """Cách đọc của line['text'][a:b] (kana giữ nguyên, cụm kanji thay bằng furigana phía trên)."""
    t, pos, furi = line['text'], line['pos'], line['furi']
    out = ''; k = a; ok = True
    while k < b:
        ch = t[k]
        if KANJI.match(ch):
            j = k
            while j < b and KANJI.match(t[j]): j += 1
            xs = [pos[m] for m in range(k, j) if pos[m]]
            x0, x1 = min(p[0] for p in xs), max(p[1] for p in xs)
            fs = sorted((f for f in furi if x0 - 3 <= (f[0] + f[1]) / 2 <= x1 + 3), key=lambda f: f[0])
            if not fs: ok = False
            out += ''.join(f[2] for f in fs); k = j
        else:
            out += ch; k += 1
    return unicodedata.normalize('NFKC', out) if ok else ''
