# Sửa cách đọc / okurigana bị OCR cắt trong data/vocab.json
import json,re,pickle,sys
src,dst=sys.argv[1],sys.argv[2]
k2r=pickle.load(open('/home/claude/dict/jm.pkl','rb'))['k2r']
V=json.load(open(src))
KJ=r'[一-鿿々]'
manual={
'dm117':dict(r='おもいきる'),
'dm478':dict(r='じゅうじつ'),'dm479':dict(r='じりつ'),'dm622':dict(r='わく'),
'dm821':dict(r='ちゅうじつな',m='Trung thành, chân thực'),
'dm822':dict(r='てぢかな',m='Gần, quen thuộc, có sẵn'),
'dm823':dict(r='しぶい',m='Chát, (màu) trầm/ cau có'),
'dm824':dict(r='こうばしい',m='Thơm'),
'dm912':dict(r='なまぬるい',m='Âm ấm, nửa vời'),
'dm914':dict(r='きはくな',m='Mỏng, loãng/ nông cạn, hời hợt'),
'dm915':dict(r='てもちぶさたな',m='Không có gì để làm, buồn tẻ'),
'dm918':dict(r='いちじるしい',m='Rõ rệt, đáng kể'),
'dm919':dict(r='けんちょな',m='Nổi bật, rõ ràng'),
'dm910':dict(w='巧妙な',r='こうみょうな',m='Khéo léo, tinh vi'),
'dm911':dict(w='紛らわしい',r='まぎらわしい',m='Dễ nhầm lẫn'),
't4_31':dict(m='Mặt dày, trơ trẽn, không biết xấu hổ (＝厚かましい)'),
'dg13':dict(w='苛立てる',r='いらだてる',m='Làm bực bội, làm khó chịu',ex=['ささいなことに神経を苛立てる。/ Tức giận vì những chuyện nhỏ nhặt.']),
'cp7_14':dict(w='蘇る',r='よみがえる'),'cp79_10':dict(w='蘇る',r='よみがえる'),
'cp7_16':dict(w='潔い',r='いさぎよい'),'cp7_18':dict(w='快い',r='こころよい'),
'cp9_11':dict(w='憤る',r='いきどおる'),'cp27_4':dict(w='承る',r='うけたまわる'),
'cp32_12':dict(w='覆す',r='くつがえす'),
}
log=[]
for d in V:
    for w in d['items']:
        old=(w['w'],w.get('r',''),w.get('m',''))
        m=w.get('m',''); W=w['w']; R=w.get('r','')
        mA=re.match(r'^([ぁ-ん]{1,4})[\s　]+(\S.*)$',m)
        if mA and R and re.search(KJ+'$',W):
            k=mA.group(1); w['w']=W+k; w['r']=R+k; w['m']=mA.group(2).strip()
        elif not R and not d['id'].startswith('tc') and re.search(KJ,W):
            mB=re.match(r'^([ぁ-ん]{2,})\s*(?:•|・)?\s*(\S.*)$',m)
            if mB: w['r']=mB.group(1); w['m']=mB.group(2).strip()
        mP=re.match(r'^(.*?'+KJ+r'.*?)\s*[（(]([ぁ-ん]+)[)）]$',w['w'])
        if mP and not w.get('r'): w['w'],w['r']=mP.group(1).strip(),mP.group(2)
        if w['id'] in manual: w.update(manual[w['id']])
        if old!=(w['w'],w.get('r',''),w.get('m','')): log.append((d['id'],w['id'],old[0],old[1],'→',w['w'],w['r'],w['m'][:30]))
json.dump(V,open(dst,'w'),ensure_ascii=False,separators=(',',':'))
for l in log: print(*l)
print(len(log),'changed',file=sys.stderr)
