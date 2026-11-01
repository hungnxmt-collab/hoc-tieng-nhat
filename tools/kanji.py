import re,json,unicodedata
T=open('/home/claude/out/kanji.txt',encoding='utf-8').read()
T=re.sub(r'\n(\d+)\n([A-ZĐÀ-ỸÂĂÊÔƠƯ][^\n]*)\n(\S)\n',r'\n\1 \2\n\3\n',T)
lines=[l.strip() for l in T.split('\n')]
out=[];cur=None;field=None;lesson=None
hdr=re.compile(r'^(\d+)\s+([A-ZĐÀ-ỸÂĂÊÔƠƯ][A-ZĐÀ-ỸÂĂÊÔƠƯa-zà-ỹ /,\-]*)$')
i=0
chap=0
while i<len(lines):
    l=lines[i]; i+=1
    if not l or l.startswith('<<<') or re.fullmatch(r'\d+\s*(장|章)',l): continue
    m=re.match(r'^(\d+)\s*章$',l)
    if m: chap=int(m[1]); continue
    m=hdr.match(l)
    if m and i<len(lines) and len(lines[i])==1:
        cur=dict(n=int(m[1]),hv=m[2].strip(),k=lines[i],ex=[],kun='',on='',tip='',ch=chap)
        out.append(cur); i+=1; field='ex'; continue
    if cur is None or l.startswith('第'): continue
    if len(l)==1: continue
    l=unicodedata.normalize('NFKC',l)
    m=re.match(r'^覚.?え方\s*[:：]\s*(.*)$',l)
    if m: cur['tip']=m[1]; field='tip'; continue
    parts=re.split(r'(KUN:|ON:|\d+\.\s*)',l)
    for p in parts:
        if not p.strip(): continue
        if p=='KUN:': field='kun'; continue
        if p=='ON:': field='on'; continue
        if re.fullmatch(r'\d+\.\s*',p): field='ex'; cur['ex'].append(''); continue
        p=p.strip()
        if field=='ex':
            if cur['ex']: cur['ex'][-1]+=p
        elif field in('kun','on'): cur[field]=(cur[field]+' '+p).strip()
        elif field=='tip': cur['tip']+=p
for c in out:
    c['tip']=re.sub(r'\s+','',c['tip']); c['ex']=[e.replace(' ','') for e in c['ex'] if e]
    c['kun']=c['kun'].replace('ー','-'); 
print(len(out))
import collections
print(collections.Counter(len(c['ex']) for c in out))
for c in out[:6]+out[300:303]+out[-3:]: print(c)
json.dump(out,open('/home/claude/out/kanji.json','w'),ensure_ascii=False)
