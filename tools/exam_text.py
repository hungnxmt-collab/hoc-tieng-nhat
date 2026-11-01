# Trích chữ từ PDF đề thi: bỏ furigana (cỡ chữ nhỏ), đánh dấu chữ gạch chân bằng ⟦ ⟧, sửa lỗi phông GBK.
# python3 exam_text.py in.pdf out.txt
import sys, unicodedata, re
from multiprocessing import Pool
import pdfplumber
from pdfplumber.utils import extract_text

FIX = {'实': '実', '尐': '少', '忚': '応', '为': '主', '卖': '単', '审': '室', '朩': '未', '单': '南', '雤': '雨', '筊': '筋',
       '亓': '五', '务': '劣', '刉': '刊', '旪': '旬', '变': '叙', '枞': '枠', '宠': '宣', '泤': '泥', '泋': '泌', '敶': '敷',
       '炋': '炎', '穁': '穂', '粙': '粛'}
KEEP_MATSU = ['週末', '年末', '期末', '結末', '始末', '粗末', '末っ子', '末尾', '末端', '末期', '月末', '幕末', '末裔', '末日',
              '場末', '末路', '末席', '末筆', '末永', '末梢', '本末', '行く末', '末広']
SRC = None


def fixtext(t, matsu):
    for a, b in FIX.items():
        t = t.replace(a, b)
    if matsu:  # phông lỗi 本→末: đổi lại trừ các từ thật sự có chữ 末
        keep = {}
        for i, w in enumerate(KEEP_MATSU):
            t = t.replace(w.replace('本', '末'), f'{i}') if '本' in w else t.replace(w, f'{i}')
        t = t.replace('末', '本')
        t = re.sub('(\\d+)', lambda m: KEEP_MATSU[int(m[1])], t)
    return t


def page_text(i):
    with pdfplumber.open(SRC) as pdf:
        p = pdf.pages[i]
        chars = [dict(c) for c in p.chars if c['size'] >= 8]
        ul = [o for o in p.lines + p.rects if (o['bottom'] - o['top']) < 2.5 and 8 < (o['x1'] - o['x0']) < 400]
        flags = []
        for c in chars:
            u = any(c['x0'] >= o['x0'] - 1.5 and c['x1'] <= o['x1'] + 1.5 and -1.5 <= o['top'] - c['bottom'] <= 3 for o in ul)
            flags.append(u)
        # đánh dấu đầu/cuối mỗi đoạn gạch chân (theo thứ tự đọc)
        order = sorted(range(len(chars)), key=lambda k: (round(chars[k]['top']), chars[k]['x0']))
        prev = False
        for idx, k in enumerate(order):
            if flags[k] and not prev:
                chars[k]['text'] = '⟦' + chars[k]['text']
            nxt = order[idx + 1] if idx + 1 < len(order) else None
            if flags[k] and (nxt is None or not flags[nxt] or round(chars[nxt]['top']) != round(chars[k]['top'])):
                chars[k]['text'] = chars[k]['text'] + '⟧'
                prev = False
            else:
                prev = flags[k]
        return extract_text(chars, layout=True, x_density=6.5, y_density=13, x_tolerance=2, y_tolerance=3)


if __name__ == '__main__':
    SRC = sys.argv[1]
    matsu = '--matsu' in sys.argv
    with pdfplumber.open(SRC) as pdf:
        n = len(pdf.pages)
    with Pool(8, initializer=lambda s: globals().__setitem__('SRC', s), initargs=(SRC,)) as pool:
        pages = pool.map(page_text, range(n), chunksize=4)
    out = []
    for i, t in enumerate(pages):
        t = unicodedata.normalize('NFC', fixtext(t, matsu))
        out.append(f'<<<PAGE {i + 1}>>>\n' + '\n'.join(l.rstrip() for l in t.split('\n')))
    open(sys.argv[2], 'w', encoding='utf-8').write('\n'.join(out))
    print('pages', n)
