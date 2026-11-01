import json,runpy,sys,re
src,dst=sys.argv[1],sys.argv[2]
V=json.load(open(src)); T={}
for b in 'abc': T.update({k:(*v,None) for k,v in runpy.run_path(f'/home/claude/raw/h3k_fix_{b}.py')['T'].items()})
T.update(runpy.run_path('/home/claude/raw/h3k_fix_d.py')['T'])
seen=set()
for d in V:
    if not d['id'].startswith('h3k'): continue
    for w in d['items']:
        if w['id'] not in T: continue
        W,R,M,EX=T[w['id']]; seen.add(w['id'])
        w['w']=W; w['r']=R
        if M: w['m']=M
        if EX is not None:
            w['ex']=EX
            if len(w.get('exvi') or [])!=len(EX): w['exvi']=[]
print('missing',set(T)-seen, 'applied',len(seen))
json.dump(V,open(dst,'w'),ensure_ascii=False,separators=(',',':'))
