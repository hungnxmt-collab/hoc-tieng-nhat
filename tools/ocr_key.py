# Đọc bảng đáp án (正答表): tách lưới ô bằng OpenCV, OCR từng ô; trả về {số câu: đáp án} cho phần 言語知識・読解 và 聴解
import cv2, numpy as np, subprocess, re, sys, json, os, tempfile
def cells(png):
    im = cv2.imread(png, 0)
    bw = cv2.threshold(im, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    H = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (60, 1)))
    V = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40)))
    grid = cv2.dilate(H | V, np.ones((3, 3), np.uint8))
    cnts, hier = cv2.findContours(grid, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for i, c in enumerate(cnts):
        x, y, w, h = cv2.boundingRect(c)
        if hier[0][i][3] >= 0 and 40 <= w <= 400 and 40 <= h <= 200:
            out.append((x, y, w, h))
    return im, out
def ocr(img, digits=True):
    fd, p = tempfile.mkstemp(suffix='.png'); os.close(fd); cv2.imwrite(p, img)
    cfg = ['--psm', '7'] + (['-c', 'tessedit_char_whitelist=0123456789()'] if digits else [])
    r = subprocess.run(['tesseract', p, '-', '-l', 'eng'] + cfg, capture_output=True, text=True).stdout.strip()
    os.remove(p); return r
def read(png):
    im, cs = cells(png)
    global IM; IM = im
    rows = {}
    for x, y, w, h in cs:
        crop = im[y + 6:y + h - 6, x + 6:x + w - 6]
        if crop.size == 0: continue
        crop = cv2.copyMakeBorder(cv2.resize(crop, None, fx=1.5, fy=1.5), 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)
        t = ocr(crop)
        rows.setdefault(round(y / 25), []).append((x, y, w, h, t))
    flat = sorted([c for r in rows.values() for c in r], key=lambda c: (c[1], c[0]))
    hs = sorted(c[3] for c in flat); med = hs[len(hs) // 2] if hs else 60
    grid = [c for c in flat if c[3] < med * 1.5]          # bỏ ô nhãn 問題 (cao gấp đôi)
    rowsY = []
    for c in grid:
        for r in rowsY:
            if abs(r[0][1] - c[1]) < 15: r.append(c); break
        else: rowsY.append([c])
    rowsY.sort(key=lambda r: r[0][1])
    ans = {}; maxn = 0; done = False
    for i, r in enumerate(rowsY):
        r.sort(key=lambda c: c[0])
        if not any('(' in c[4] or ')' in c[4] for c in r): continue
        # hàng giá trị ngay bên dưới

        nums = []
        for c in r:
            m = re.search(r'(\d{1,3})', c[4]); nums.append(int(m.group(1)) if m else None)
        # điền số bị đọc sót theo quy luật liên tiếp
        for k in range(len(nums)):
            if nums[k] is None and k and nums[k - 1] is not None: nums[k] = nums[k - 1] + 1
        for k in range(len(nums) - 1, -1, -1):
            if nums[k] is None and k + 1 < len(nums) and nums[k + 1] is not None: nums[k] = nums[k + 1] - 1
        if nums and nums[0] is not None and nums[0] <= maxn - 5: break   # bảng 聴解 (đánh số lại)
        for c, n in zip(r, nums):
            if n is None: continue
            x, y, w, h = c[:4]
            crop = IM[y + h + 6:y + h + med - 6, x + 8:x + w - 8]
            if crop.size:
                t = ocr(cv2.copyMakeBorder(cv2.resize(crop, None, fx=1.5, fy=1.5), 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255))
                t = t.strip('()')
                if re.fullmatch(r'[1-4]', t): ans[n] = int(t)
            maxn = max(maxn, n)
    return ans, flat
if __name__ == '__main__':
    a, flat = read(sys.argv[1])
    print(json.dumps({k: v for k, v in sorted(a.items())}))
