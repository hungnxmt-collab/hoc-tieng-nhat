# Hình học trang scan: ô số câu (□), đường gạch chân
import cv2, numpy as np
def load(png):
    im = cv2.imread(png, cv2.IMREAD_GRAYSCALE)
    bw = cv2.threshold(im, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    return im, bw
def boxes(bw):
    """Ô vuông viền mảnh chứa số câu: trả về [(x,y,w,h)]"""
    cnts, hier = cv2.findContours(bw, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for i, c in enumerate(cnts):
        x, y, w, h = cv2.boundingRect(c)
        if not (38 <= h <= 75 and 38 <= w <= 140): continue
        if hier[0][i][2] < 0: continue  # phải có lỗ bên trong
        roi = bw[y:y + h, x:x + w]
        side = lambda a: max(np.mean(a[i]) for i in range(a.shape[0])) > 150
        edge = side(roi[:4, :]) and side(roi[-4:, :]) and side(roi[:, :4].T) and side(roi[:, -4:].T)
        inner = roi[6:-6, 6:-6]
        if edge and inner.size and 0.03 < np.mean(inner) / 255 < 0.45:
            out.append((x, y, w, h))
    # gộp trùng
    out.sort(key=lambda b: (b[1], b[0])); res = []
    for b in out:
        if not any(abs(b[0] - r[0]) < 10 and abs(b[1] - r[1]) < 10 for r in res): res.append(b)
    return res
def underlines(bw):
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (45, 1))
    h = cv2.morphologyEx(bw, cv2.MORPH_OPEN, k)
    cnts, _ = cv2.findContours(h, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in cnts:
        x, y, w, hh = cv2.boundingRect(c)
        if hh <= 7 and 45 <= w <= 1700: out.append((x, y, w, hh))
    return out
def boxes_v(bw, xl=213, w=43):
    """Dò ô số bằng nét dọc bên phải (dài 34–62px) + nét trên/dưới + nét trái — bền khi ô dính khung khác."""
    import numpy as np
    H = bw.shape[0]; res = []
    for dx in (w - 1, w, w + 1, w + 2):
        xr = xl + dx
        col = np.any(bw[:, xr - 2:xr + 2] > 0, axis=1)
        y = 0
        while y < H:
            if col[y]:
                s0 = y
                while y < H and col[y]: y += 1
                e = y
                if 34 <= e - s0 <= 62:
                    lft = bw[s0 + 4:e - 4, xl - 3:xl + 4]
                    top = bw[max(0, s0 - 2):s0 + 4, xl + 2:xr - 2]; bot = bw[e - 4:e + 2, xl + 2:xr - 2]
                    if lft.size and np.mean(np.any(lft > 0, axis=1)) > .9 and np.mean(np.any(top > 0, axis=0)) > .8 and np.mean(np.any(bot > 0, axis=0)) > .8:
                        if not any(abs(r[1] - s0) < 15 for r in res): res.append((xl - 1, s0, dx + 2, e - s0))
            y += 1
    return res
