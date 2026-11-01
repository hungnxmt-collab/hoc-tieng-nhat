import pdfplumber,re,json,sys,unicodedata
pdf=pdfplumber.open(sys.argv[1])
JP=re.compile(r'[ぁ-んァ-ン一-龥]')
LAT=re.compile(r'[A-Za-zÀ-ỹĐđ]')
out=[];sec='';chap=''
def clean(s): return re.sub(r'(?<=[ぁ-んァ-ン一-龥ー々])\s+(?=[ぁ-んァ-ン一-龥ー々])','',s.replace('\n',' ')).strip()
for pi,page in enumerate(pdf.pages):
    p=page.filter(lambda o: o.get('object_type')!='char' or o['size']>=7)
    tabs=p.find_tables()
    if not tabs: continue
    prevb=0
    for t in tabs:
        rows=t.rows
        head=p.crop((0,prevb,p.width,max(prevb+1,t.bbox[1]))).extract_text() or ''
        prevb=t.bbox[3]
        for l in head.split('\n'):
            l=unicodedata.normalize('NFKC',l)
            m=re.match(r'^\s*(\d+)\s*章',l)
            if m: chap=m[1]
            m=re.search(r'(?:^|\s)(\d+\.\d+)\s*$',l)
            if m and not l.startswith('番号'): sec=m[1]
        xs=None
        _d={}
        for r in rows:
            for c in r.cells:
                if c and c[2]-c[0]>15: _d.setdefault((round(c[0]),round(c[2])),(c[0],c[2]))
        prs=sorted(_d.values())
        prs=[p_ for p_ in prs if not any(q[0]<=p_[0]+1 and q[1]>=p_[1]-1 and (q[1]-q[0])>(p_[1]-p_[0])+2 for q in prs)]
        if len(prs)==5: xs=[a for a,b in prs]+[prs[-1][1]]
        elif len(prs)==4: xs=[prs[0][0],prs[1][0],prs[2][0],prs[2][0],prs[3][0],prs[3][1]]
        if not xs or len(xs)<6: continue
        # entries: spans of non-None cell in column 0
        hs=sorted(e['top'] for e in p.edges if e['orientation']=='h' and e['x0']<=xs[0]+2 and e['x1']>=xs[1]-2)
        hs=[h for i,h in enumerate(hs) if i==0 or h-hs[i-1]>2]
        if t.bbox[3]-hs[-1]>3: hs.append(t.bbox[3])
        spans=list(zip(hs,hs[1:]))
        for top,bot in spans:
            if bot-top<4: continue
            def col(i):
                if xs[i+1]-xs[i]<2: return ''
                return p.crop((xs[i]+0.5,top+0.5,xs[i+1]-0.5,bot-0.5)).extract_text(x_tolerance=1.5,y_tolerance=3) or ''
            num=col(0).strip()
            if not re.fullmatch(r'\d+',num): continue
            w=clean(col(1)); r_=clean(col(2)); m=' '.join(col(3).split()); exs=col(4).split('\n')
            pairs=[];
            for l in exs:
                l=l.strip()
                if not l: continue
                if l.startswith('・'): pairs.append([l[1:].strip(),''])
                elif pairs and LAT.search(l) and not JP.search(l[:3]): pairs[-1][1]=(pairs[-1][1]+' '+l).strip()
                elif pairs and not pairs[-1][1]: pairs[-1][0]+=l
                elif pairs: pairs[-1][1]+=' '+l
            out.append(dict(n=int(num),w=unicodedata.normalize('NFKC',w),r=r_,m=m,ex=[unicodedata.normalize('NFKC',clean(a)) for a,b in pairs],exvi=[b for a,b in pairs],sec=sec,ch=unicodedata.normalize('NFKC',chap),page=pi+1))
best={}
for x in out:
    k=x['n']; sc=len(x['ex'])*10+len(x['m'])+len(x['r'])
    if k not in best or sc>best[k][0]: best[k]=(sc,x)
out=[best[k][1] for k in sorted(best)]
print(len(out),file=sys.stderr)
json.dump(out,open(sys.argv[2],'w'),ensure_ascii=False)
