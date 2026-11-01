# Trích đáp án dạng "問題N 1234..." từ file đáp án PDF có lớp chữ. In ra các nhóm theo thứ tự xuất hiện.
import sys, re, subprocess, unicodedata, json
f = sys.argv[1]
t = unicodedata.normalize('NFKC', subprocess.run(['pdftotext', '-layout', f, '-'], capture_output=True, text=True).stdout)
groups = []
for m in re.finditer(r'問題\s*(\d{1,2})\s*[:：]?\s*((?:[1-4]\s*){1,14})(?=\s|$)', t):
    groups.append((int(m.group(1)), re.sub(r'\s', '', m.group(2))))
print(json.dumps(groups, ensure_ascii=False))
