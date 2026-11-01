import openpyxl,re,json
wb=openpyxl.load_workbook('/home/claude/raw/87849251-N1_Trainingbook-1.xlsx',data_only=True)
KANA=re.compile(r'^[ぁ-ゖァ-ヺー・／/ 　　（）()]+$')
JP=re.compile(r'[ぁ-んァ-ン一-龥]')
VI=re.compile(r'[a-zA-ZĐđà-ỹÀ-Ỹ]{2,}')
def is_ex(s):
    return s.startswith('・') or (JP.search(s) and not VI.search(s) and len(s)>8 and re.search(r'[。！？]$',s))
decks=[]
for ws in wb.worksheets:
    if ws.title in ('Link','Ngữ pháp hay xuất hiện N1') or ws.max_row<3: continue
    rows=[[('' if c is None else str(c).strip()) for c in r] for r in ws.iter_rows(values_only=True)]
    rows=[r+['']*(6-len(r)) for r in rows]
    # reading column detection
    starts=[r for r in rows if re.fullmatch(r'\d+',r[0])]
    if not starts: 
        starts=[r for r in rows if r[1] and r[2]]  # sheets without numbers
    kana_c=sum(1 for r in starts if r[2] and KANA.match(r[2].replace('　','')))
    has_read = kana_c >= len(starts)*0.5
    ents=[];cur=None
    for r in rows:
        if r[1] in ('語彙','Từ vựng','彙') or r[0]=='STT': continue
        new = re.fullmatch(r'\d+',r[0]) or (not r[0] and r[1] and not cur) or (not r[0] and r[1] and JP.search(r[1]) and not is_ex(r[1]) and len(r[1])<12 and (r[2] and not is_ex(r[2])) and ws.title=='day6')
        if new and r[1]:
            w=r[1]; rd=''; rest=r[2:]
            if has_read: rd=r[2].replace('　','').strip(); rest=r[3:]
            cur=dict(w=w,r=rd if rd!=w else '',m=[],ex=[]); ents.append(cur)
            cells=rest
        elif cur:
            cells=r[1:]
        else: continue
        for c in cells:
            if not c: continue
            c=c.replace('#NAME?','').strip()
            if not c: continue
            (cur['ex'] if is_ex(c) else cur['m']).append(c.lstrip('・') if is_ex(c) else c)
    for e in ents:
        # format "とうめん: Trước mắt" in meaning -> reading
        if not e['r'] and e['m']:
            m=re.match(r'^([ぁ-ゖー]+)\s*[:：]\s*(.+)$',e['m'][0])
            if m: e['r']=m[1]; e['m'][0]=m[2]
        e['m']=' • '.join(e['m'])
    decks.append(dict(name=ws.title,items=ents))
    print(ws.title,len(ents),has_read)
json.dump(decks,open('/home/claude/out/vocab_xlsx.json','w'),ensure_ascii=False)
d=decks
for i in (0,3,6,12): print(d[i]['name'],d[i]['items'][:3])
