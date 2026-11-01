import re,json,unicodedata
T=open('/home/claude/out/npfull.txt',encoding='utf-8').read()
pages=re.split(r'<<<PAGE \d+>>>\n',T)[5:]  # skip toc pages (content starts page 4)
lines=[]
for p in pages:
    ls=p.split('\n')
    while ls and (not ls[-1].strip() or re.fullmatch(r'\d+',ls[-1].strip())): ls.pop()
    lines+=ls
out=[];cur=None;field=None
hdr=re.compile(r'^(\d+)\.(\d+)\s*\)\s*[～〜~]?\s*(.+)$')
for l in lines:
    l=l.strip()
    if not l: continue
    m=hdr.match(l)
    if m and '接続' not in l:
        cur=dict(ch=int(m[1]),no=int(m[2]),title='～'+m[3].strip(),form=[],mean='',use=[],ex=[])
        out.append(cur);field='h';continue
    if cur is None: continue
    if re.match(r'^第.+章$',l) or re.match(r'^\d+\.\d+）',l): field='skip';continue
    if l.startswith('接続'): field='form';continue
    if l.startswith('使い方'): field='use';continue
    if l.startswith('例文'): field='ex';continue
    if field=='form':
        m=re.search(r'[（(](?=[^)）]*[a-zA-ZĐđà-ỹÀ-Ỹ]{2})',l)
        if m and not cur['mean']:
            before=l[:m.start()].strip(); after=l[m.end():].strip()
            after=re.sub(r'\s*[)）]\s*$','',after)
            if before: cur['form'].append(before)
            cur['mean']=after; field='form2'
        else: cur['form'].append(l)
    elif field=='form2':
        if re.search(r'[a-zà-ỹ]',l) and not re.search(r'[ぁ-んァ-ン一-龥]',l): cur['mean']=re.sub(r'\s*[)）]\s*$','',cur['mean']+' '+l)
        else: cur['form'].append(l)
    elif field=='use':
        if l.startswith('•') or l.startswith('・') or l.startswith('-'): cur['use'].append(l.lstrip('•・- ').strip())
        elif cur['use']: cur['use'][-1]+=' '+l
        else: cur['use'].append(l)
    elif field=='ex':
        if re.match(r'^[①-⑳○〇×✕]|^\d+\s',l) or not cur['ex']: cur['ex'].append(l)
        else: cur['ex'][-1]+=l
for c in out:
    c['ex']=[re.sub(r'^[①-⑳]\s*','',e) for e in c['ex']]
    c['id']=f"g{c['ch']}_{c['no']}"
print(len(out))
for c in out[:2]+out[50:51]+out[-2:]: print(json.dumps(c,ensure_ascii=False))
print([c['title'] for c in out if not c['mean'] or not c['ex']])
json.dump(out,open('/home/claude/out/grammar.json','w'),ensure_ascii=False)
