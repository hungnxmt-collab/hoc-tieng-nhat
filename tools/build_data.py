import json,re,openpyxl,unicodedata
O='/home/claude/out/';A='/home/claude/app/data/'
JPc=r'[ぁ-んァ-ン一-龥々ー]'
def jpjoin(s): return re.sub(r'(?<='+JPc+r')\s+(?='+JPc+r')','',s)
# ---------- vocab
decks=[]
flash=json.load(open(O+'flash.json'))
for i in range(0,len(flash),50):
    ch=flash[i:i+50]
    decks.append(dict(id=f'n1v{i//50+1}',group='Từ vựng N1 tổng hợp',name=f'Bài {i//50+1} (#{ch[0]["n"]}–{ch[-1]["n"]})',
      items=[dict(id=f'v{x["n"]}',w=x['w'],r=x['r'] if x['r']!=x['w'] else '',hv=x['hv'],m=x['m'],ex=[]) for x in ch]))
fix={'克明':'Tỉ mỉ, chi tiết, cẩn thận','億劫':'Ngại, lười (làm gì đó vì thấy phiền)','厄介':'Phiền phức, rắc rối','雑踏':'Đám đông chen chúc, ồn ào','ユーモアがある':'Có khiếu hài hước'}
xl=json.load(open(O+'vocab_xlsx.json'))
for di,d in enumerate(xl):
    nm=d['name']; m=re.search(r'(\d+)',nm); num=int(m[1]) if m else di+1
    if nm.startswith('Sheet'): nm=f'Day {num}'
    nm=nm.replace('GOI day','Day ').replace('day','Day ').replace('  ',' ')
    items=[]
    for j,e in enumerate(d['items']):
        items.append(dict(id=f't{num}_{j+1}',w=e['w'],r=e['r'],hv='',m=e['m'] or fix.get(e['w'],''),ex=e['ex']))
    decks.append(dict(id=f'tb{num}',group='N1 Trainingbook (theo ngày)',name=nm,items=items))
# hospitality
wb=openpyxl.load_workbook('/home/claude/raw/295bdcb0-T_-v_ng-ti_p-kh_ch-1.xlsx',data_only=True)
for sh,did in (('Tên món ăn','food'),('Vị','taste')):
    items=[]
    for r in wb[sh].iter_rows(values_only=True):
        r=[str(c).strip() for c in r if c is not None and str(c).strip()]
        if len(r)<3 or not r[0].isdigit(): continue
        w=r[1]
        if len(r)>=4: rom,m=r[2].strip('()'),r[3]
        else: rom,m='',r[2]
        items.append(dict(id=f'{did}{r[0]}',w=w,r='',hv=rom,m=m,ex=r[4:5]))
    decks.append(dict(id=did,group='Tiếp khách nhà hàng',name={'food':'Tên món ăn','taste':'Miêu tả hương vị'}[did],items=items))
txt=list(wb['Câu văn mẫu'].iter_rows(values_only=True))[0][0]
items=[];sec='';pend=None
for l in [x.strip() for x in txt.split('\n') if x.strip()]:
    if l.endswith(':') and not re.search(JPc,l): sec=l[:-1]; continue
    m=re.match(r'^(.*?[。？！])\s*(.+)$',l)
    if m and re.search(r'[a-zà-ỹ]',m[2]): items.append((m[1],m[2],sec)); continue
    if re.search(JPc,l): pend=l
    elif pend: items.append((pend,l,sec)); pend=None
decks.append(dict(id='phrase',group='Tiếp khách nhà hàng',name='Câu văn mẫu',items=[dict(id=f'ph{i+1}',w=a,r='',hv=s,m=b,ex=[]) for i,(a,b,s) in enumerate(items)]))
json.dump(decks,open(A+'vocab.json','w'),ensure_ascii=False,separators=(',',':'))
print('vocab decks',len(decks),'items',sum(len(d['items']) for d in decks),'phrases',len(items))
# ---------- kanji
K=json.load(open(O+'kanji.json'))
json.dump([dict(id='k'+c['k'],k=c['k'],hv=c['hv'],kun=c['kun'],on=c['on'],ex=c['ex'],tip=c['tip'],ch=c['ch'],ls=c['ls']) for c in K],open(A+'kanji.json','w'),ensure_ascii=False,separators=(',',':'))
# ---------- grammar
G=json.load(open(O+'grammar.json'))
gfix={'～ながら':'Trong trạng thái vẫn ~, giữ nguyên ~ (vốn dĩ ~)','～にして':'Ngay cả ~ / Phải đến ~ mới / Vừa ~ vừa ~','～のごとく':'Cứ như là, giống như','～ないではすまない／～ずにはすまない':'Không ... thì không xong / Nhất định phải ...','～といい〜といい':'Cả N1, cả N2 đều... / Dù N1, dù N2 đều...','～ときたら':'(Nói đến) N ấy à, thì...'}
out=[]
for g in G:
    form=[jpjoin(f) for f in g['form'] if f.strip() not in ('+','/','N2','N 2','')]
    form=[f for f in form if not re.match(r'^使\s*い',f)]
    mean=gfix.get(g['title'],g['mean']).strip()
    use=g['use']
    if g['title']=='～といい〜といい': use=[u.strip() for u in g['mean'].split('•')[1:]]+use
    if g['title']=='～ないではすまない／～ずにはすまない': form=['V ない ＋ ではすまない','V ず ＋ にはすまない']
    out.append(dict(id=g['id'],set='book',ch=g['ch'],title=g['title'],form=form,mean=mean,use=[u for u in use if u not in('N2',)],ex=[jpjoin(re.sub(r'^\d+\s+','',e)) for e in g['ex']]))
F=json.load(open(O+'grammar_freq_raw.json'))
for f in F:
    mean=[];ex=[];st=None
    for l in f['lines']:
        if l.startswith('意味'): st='m';continue
        if l.startswith('用例'): st='e';continue
        if st=='e' and re.match(r'^\d+\.',l): ex.append(re.sub(r'^\d+\.\s*','',l))
        elif st=='e' and ex and not re.search(r'^A',l): ex[-1]+=l
        elif st=='e': mean.append(l)
        else: mean.append(l)
    out.append(dict(id=f'f{f["n"]}',set='freq',ch=0,title=f['title'],form=[],mean=' • '.join(mean),use=[],ex=ex))
json.dump(out,open(A+'grammar.json','w'),ensure_ascii=False,separators=(',',':'))
print('grammar',len(out))
# ---------- reading
R=json.load(open(O+'reading.json'))
srcmap={'tanbun':'r1','chuubun':'r2','choubun':'r3','hikaku':'r4','kensaku':'r5'}
def paras(lines):
    ls=[l for l in lines if l.strip()]
    if not ls: return []
    mx=max(len(l) for l in ls)
    out=[];buf=''
    for l in ls:
        if buf and len(prev)>=mx*0.82 and not re.match(r'^(（注|\(注|[AB]$|※|●|・)',l): buf+=l
        else:
            if buf: out.append(buf)
            buf=l
        prev=l
    if buf: out.append(buf)
    return [jpjoin(p) if not re.search(r'[a-zA-Z]{2}',p) else p for p in out]
for g in R:
    for s in g['sets']:
        s['passage']=paras(s['passage'])
        s['img']=[f'img/reading/{srcmap[g["id"]]}-{p}.webp' for p in s['pages']]
        for q in s['questions']:
            q['q']=jpjoin(q['q']); q['options']=[jpjoin(o) for o in q['options']]
        if g['id']=='kensaku':
            s['passage']=[]; s['imgOnly']=True
            for q in s['questions']:
                q['q']=re.split(r'(?<=[？?。])',q['q'])[0] if len(q['q'])>150 else q['q']
                if '名前' in q['q'] and len(q['q'])>60: q['q']=q['q'].split('名前')[0]
    if g['id']=='kensaku':
        q=[s for s in g['sets'] if s['id']=='kensaku4'][0]['questions'][0]
        q['q']='次の学生のうち、インターンシップに応募できるのは誰か。（表は原本を参照）'; q['options']=['高橋さん','山下さん','佐々木さん','リーさん']
json.dump(R,open(A+'reading.json','w'),ensure_ascii=False,separators=(',',':'))
print('reading sets',sum(len(g['sets']) for g in R))
