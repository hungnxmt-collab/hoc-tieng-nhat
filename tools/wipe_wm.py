# Xoá dấu chìm nhạt (xám nhạt) trên ảnh trang: điểm ảnh sáng hơn ngưỡng -> trắng
import sys, numpy as np
from PIL import Image
for f in sys.argv[1:]:
    im = Image.open(f).convert('L'); a = np.array(im)
    a = np.where(a >= 200, 255, a).astype('uint8')
    Image.fromarray(a).save(f, quality=60, method=6)
