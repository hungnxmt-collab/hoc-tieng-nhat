# Sửa lỗi OCR trong câu ví dụ 単語3000 bằng bản chép lời audio (chỉ khi bản audio tạo thành từ có trong JMdict còn bản OCR thì không)
import json,re,pickle,difflib,sys
jm=pickle.load(open('/home/claude/dict/jm.pkl','rb')); k2r=jm['k2r']; kana=jm['kana']
ASR=json.load(open('/home/claude/raw/cd/asr.json'))
V=json.load(open(sys.argv[1]))
KJ=re.compile(r'^[一-龥々]+$'); KN=re.compile(r'^[ぁ-んァ-ンー]+$'); HASK=re.compile(r'[一-龥々]')
isword=lambda s: s in k2r or s in kana
def cover(s,i,j):
    for a in range(max(0,i-3),i+1):
        for b in range(j,min(len(s),j+3)+1):
            if b-a>=2 and isword(s[a:b]): return s[a:b]
SKIP={('A','英'),('B','米'),('速','早'),('閥','刺'),('導','刺'),('(つ','はむ')}
def ok(a,b):
    if (a,b) in SKIP or re.search(r'[0-9０-９]',a): return False
    if re.search(r'[、。！？!?「」]',a+b): return False
    if HASK.search(b) and not HASK.search(a) and KN.match(a): return False
    if KJ.match(a) and KN.match(b): return False
    if KJ.match(a) and KJ.match(b) and len(a)==1 and set(k2r.get(a,()))&set(k2r.get(b,())): return False
    return True
n=0; log=[]
for d in V:
  if not d['id'].startswith('h3k'): continue
  for w in d['items']:
    m=re.search(r'(\d{4})',w.get('au3','') or '')
    if not m or not w.get('ex'): continue
    raw=re.sub(r'\s','',ASR[m.group(1)]['t'])
    for k,e in enumerate(w['ex']):
        ops=difflib.SequenceMatcher(None,e,raw,autojunk=False).get_opcodes()
        out=e
        for op,i1,i2,j1,j2 in reversed(ops):
            if op=='replace' and i2-i1==j2-j1 and i2-i1<=2:
                a,b=e[i1:i2],raw[j1:j2]
                cand=e[:i1]+b+e[i2:]
                if ok(a,b) and cover(cand,i1,i2) and not cover(e,i1,i2):
                    out=out[:i1]+b+out[i2:]
        if out!=e: w['ex'][k]=out; n+=1; log.append((w['id'],e,out))
json.dump(V,open(sys.argv[2],'w'),ensure_ascii=False,separators=(',',':'))
json.dump(log,open('/tmp/claude-0/sc/exlog.json','w'),ensure_ascii=False,indent=0)
print('sửa',n,'câu')
