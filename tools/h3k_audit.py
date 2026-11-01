import json,re,pickle,sys
k2r=pickle.load(open('/home/claude/dict/jm.pkl','rb'))['k2r']
ASR=json.load(open('/home/claude/raw/cd/asr.json'))
V=json.load(open(sys.argv[1]))
core=lambda w: re.split(r'[〈［\[]',w)[0].strip()
def stem(w):
    w=core(w)
    if re.search(r'[うくぐすつぬぶむるい]$',w) and len(w)>1 and re.search(r'[一-龥々]',w): return w[:-1]
    if w.endswith('な'): return w[:-1]
    return w
def hw(n):
    v=ASR.get(n); 
    if not v: return '',''
    tok,ts=v['tok'],v['ts']; cut=None
    for i in range(1,len(tok)):
        if ts[i]-ts[i-1]>.45 and ''.join(tok[:i]).strip(): cut=i;break
    h=re.sub(r'[\s。、？?！!]','',''.join(tok[:cut])) if cut else ''
    return h, re.sub(r'\s+','',v['t'])
out=[]
for d in V:
    if not d['id'].startswith('h3k'): continue
    for w in d['items']:
        n=re.search(r'(\d{4})',w.get('au3','') or '')
        n=n.group(1) if n else None
        h,raw=hw(n) if n else ('','')
        W=core(w['w']); s=stem(w['w'])
        ex=''.join(w.get('ex',[]))
        inex = s and (s in ex or s in raw)
        asr_ok = h and (W==h or s in h or h in W)
        dict_ok = W in k2r or not re.search(r'[一-龥]',W)
        if not (inex and (asr_ok or not h)) :
            out.append(dict(deck=d['id'],id=w['id'],w=w['w'],r=w['r'],m=w['m'][:40],asr=h,ex=ex[:50],raw=raw[:50],chk=w.get('chk',0)))
json.dump(out,open('/tmp/claude-0/sc/h3k_flag.json','w'),ensure_ascii=False,indent=0)
print(len(out))
