import json,sys
src,dst=sys.argv[1],sys.argv[2]
F={
'cp10_9':('心細い','こころぼそい','Cảm thấy cô đơn, trơ trọi một mình'),
'cp65_14':('案の定','あんのじょう','Quả nhiên, quả đúng như dự đoán'),
'cp69_2':('無頓着','むとんちゃく','Thờ ơ, không quan tâm ＝ 平気なこと'),
'cp69_14':('頭が上がらない','あたまがあがらない','Biết ơn, nể phục, không dám ngẩng cao đầu'),
'cp69_15':('頭が下がる','あたまがさがる','Thán phục, ngưỡng mộ'),
'cp73_8':('躊躇','ちゅうちょ','Do dự'),
'cp77_3':('昔風','むかしふう','(Mang phong cách) xưa'),
'cp83_19':('挿入','そうにゅう','Lồng, chèn vào'),
'cp84_17':('拝借','はいしゃく','Mượn (khiêm nhường ngữ của động từ 借りる)'),
'cp86_11':('合流','ごうりゅう',None),
'cp88_11':('短縮','たんしゅく','Thu ngắn, rút ngắn'),
'cp89_3':('文脈','ぶんみゃく','Mạch văn, ngữ cảnh'),
'cp90_8':('早急','さっきゅう','Khẩn cấp, ngay lập tức, nhanh chóng'),
'cp90_16':('噴出','ふんしゅつ','Phun trào, bùng nổ, nổ ra'),
'cp93_10':('火の車','ひのくるま','(Kinh doanh, kinh tế gia đình...) khó khăn'),
'cp93_11':('福袋','ふくぶくろ','Túi may mắn'),
'cp95_20':('一蹴','いっしゅう',None),
'cp106_19':('働き盛り','はたらきざかり','Thời kì đỉnh cao của cuộc đời'),
'cp111_6':('すずめの涙','すずめのなみだ','Một chút ít, ít ỏi'),
'cp111_7':('耳寄りな話','みみよりなはなし',None),
'cp34_19':('免れる','まぬかれる','Thoát, tránh'),
'cp93_19':('徒に','いたずらに',None),
'cp1_15':('姑','しゅうとめ',None),'cp2_10':('懐','ふところ',None),
'cp66_15':('先立って','さきだって',None),
'ct11':(None,'とうめん',None),'ct29':(None,'つかのま',None),'ct56':(None,'こいに',None),'ct76':(None,'おてあげ',None),
'kd114':(None,'ゆいしょ',None),'kd148':(None,'ゆいしょ',None),'ti13':(None,'いくとおり',None),
'ha568':(None,'じんぞうせき',None),'ha717':(None,'きゃっかんてき',None),
'kn301':('年俸','ねんぽう',None),'kn388':(None,'すうがく',None),'kn423':(None,'ちゅうしん',None),
'v470':(None,'ひきさがる',None),'v605':(None,'ほうび',None),'v679':(None,'わざ',None),'v711':(None,'おこたる',None),
'v714':(None,'おもむく',None),'v769':(None,'とおざかる',None),'v855':(None,'そっけない',None),
'v964':(None,'いきちがい／ゆきちがい',None),'v998':(None,'きょうぞん／きょうそん',None),'v1004':(None,'じょうちょ／じょうしょ',None),
'v1074':(None,'はかる',None),'v1152':(None,'おって',None),
't13_10':(None,'あわただしい',None),'t14_4':(None,'かがやかしい',None),
'cp1_14':(None,'しゅうちゃく',None),'cp11_19':(None,'むらさき',None),'cp23_15':(None,'じゅうぎょういん',None),
'cp30_12':(None,'きゅうきょく',None),'cp35_5':(None,'めざましい',None),'cp46_14':(None,'しょくりょう',None),
'cp58_16':(None,'じゅうしょう',None),'cp68_20':(None,'まえぶれ',None),'cp70_11':(None,'くちがすべる',None),
'cp70_12':(None,'くちをきる',None),'cp75_20':(None,'うぬぼれる',None),'cp95_14':(None,'まのあたり',None),
'cp98_20':(None,'じょうじょう',None),'cp100_16':(None,'ことわざ',None),'cp104_5':(None,'きょしょくしょう',None),
'cp105_2':(None,'とうにょうびょう',None),'kn248':(None,'ぼくじょう／まきば',None),'kn478':(None,'えんでん／しおだ',None),
}
V=json.load(open(src)); seen=set()
for d in V:
    for w in d['items']:
        if w['id'] in F:
            W,R,M=F[w['id']]; seen.add(w['id'])
            if W: w['w']=W
            if R: w['r']=R
            if M: w['m']=M
            elif w['m'][:1] in '流蹴' : w['m']=w['m'][1:].strip()
print(set(F)-seen)
json.dump(V,open(dst,'w'),ensure_ascii=False,separators=(',',':'))
