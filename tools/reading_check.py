import json,pickle,re,sys,functools
k2r=pickle.load(open('/home/claude/dict/jm.pkl','rb'))['k2r']
h=lambda s:''.join(chr(ord(c)-96) if 'ァ'<=c<='ヶ' else c for c in s)
# thêm âm on/kun từ kanji.json
K=json.load(open('data/kanji.json'))
extra={}
for k in K:
    rs=set()
    for x in re.split(r'[、,・\s/()（）]+',h(k.get('on',''))+' '+k.get('kun','')):
        x=x.split('-')[0].strip()
        if x: rs.add(x)
    extra[k['k']]=rs
DAK=dict(zip('かきくけこさしすせそたちつてとはひふへほ','がぎぐげござじずぜぞだぢづでどばびぶべぼ'))
HAN=dict(zip('はひふへほ','ぱぴぷぺぽ'))
def variants(r):
    out={r}
    if r and r[0] in DAK: out.add(DAK[r[0]])  if False else out.add(DAK[r[0]]+r[1:])
    if r and r[0] in HAN: out.add(HAN[r[0]]+r[1:])
    if len(r)>1 and r[-1] in 'つくちき': out|={x[:-1]+'っ' for x in list(out)}
    return out
def readings(seg):
    rs=set(map(h,k2r.get(seg,())))
    if len(seg)==1: rs|=extra.get(seg,set())
    o=set()
    for r in rs: o|=variants(r)
    return o
def ok(w,r):
    w=w.replace('々','々'); 
    @functools.lru_cache(None)
    def f(i,j):
        if i==len(w): return j==len(r)
        c=w[i]
        if re.match(r'[ぁ-んァ-ヶー]',c):
            return j<len(r) and h(c)==r[j] and f(i+1,j+1)
        for L in range(min(8,len(w)-i),0,-1):
            seg=w[i:i+L]
            if L==1 and c=='々' and i>0:
                pass
            for rd in readings(seg):
                if r.startswith(rd,j) and f(i+L,j+len(rd)): return True
        if c=='々' and i>0:
            for rd in readings(w[i-1]):
                for v in variants(rd):
                    if r.startswith(v,j) and f(i+1,j+len(v)): return True
        return False
    return f(0,0)
if __name__=='__main__':
    V=json.load(open(sys.argv[1])); bad=[]
    for d in V:
        for w in d['items']:
            W=w['w'].strip(); R=w.get('r','').strip()
            if not R or not re.search(r'[一-鿿]',W) or re.search(r'[/／、,・（(～〜\s＝=A-Za-z0-9]',W+R): continue
            if W in k2r: continue
            if not ok(W,h(R)): bad.append((d['id'],w['id'],W,R,w['m'][:30]))
    for b in bad: print(*b)
    print(len(bad),file=sys.stderr)
