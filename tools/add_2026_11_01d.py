# Bổ sung đợt Thaolejp: Chinh phục từ vựng N1, 8 bảng chuyên đề + Từ nối, Tổng hợp NP N1, Cẩm nang NP N1 (lý thuyết + bài tập),
# 2 bộ Test từ vựng-ngữ pháp, 2 tài liệu bổ trợ đọc hiểu, 100 bài đọc hiểu, text nghe kính ngữ.
# Đầu vào: thư mục chứa các JSON trung gian do tools/*.py tạo ra (xem README).
import json, re, sys, os
D = sys.argv[1]
J = lambda f: json.load(open(os.path.join(D, f), encoding='utf-8'))
JP = r'[ぁ-んァ-ヶー一-龥々〆〇（）「」『』、。・…？！]'
def jj(s): return re.sub(r'(?<=' + JP + r')[ 　]+(?=' + JP + r')', '', s) if isinstance(s, str) else s

# ---------- từ vựng
V = [d for d in json.load(open('data/vocab.json', encoding='utf-8')) if not d['id'].startswith(('cp', 'tc_'))]
cp = J('cptv.json'); bais = sorted({x['bai'] for x in cp})
for b in bais:
    its = [x for x in cp if x['bai'] == b]
    V.append(dict(id=f'cp{b}', group='Chinh phục từ vựng N1 (Thaolejp)', name=f'Bài {b}',
                  items=[dict(id=f'cp{b}_{x["n"]}', w=x['w'], r=x['r'], hv='', m=x['m'], ex=[jj(e) for e in x['ex']], exvi=x['exvi']) for x in its]))
for d in J('topical.json'):
    its = [x for x in d['items'] if x['m'].strip() and len(x['w']) <= 25]
    for x in its: x['ex'] = [jj(e) for e in x['ex']]
    V.append(dict(id='tc_' + d['id'], group=d['group'], name=d['name'], items=its))
tn = J('tunoi.json')
V.append(dict(id='tc_tu_noi', group='Chuyên đề N1 (Thaolejp)', name='Từ nối (接続詞)', items=[dict(id=f'tn{i+1}', w=x['title'], r='', hv='', m='Từ nối — xem ví dụ', ex=[jj(e) for e in x['ex']]) for i, x in enumerate(tn)]))
json.dump(V, open('data/vocab.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('vocab decks', len(V), 'words', sum(len(d['items']) for d in V))

# ---------- ngữ pháp
G = [g for g in json.load(open('data/grammar.json', encoding='utf-8')) if g['set'] not in ('th', 'cn')]
for f in ('thnp.json', 'cnnp.json'):
    for g in J(f):
        g['ex'] = [jj(e) for e in g['ex']]; g['form'] = [jj(x) for x in g['form']]
        if not g['mean'] and g['use']: g['mean'] = g['use'].pop(0)
        G.append(g)
json.dump(G, open('data/grammar.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('grammar', len(G))

# ---------- đề / bài tập
index = json.load(open('data/exams/index.json', encoding='utf-8'))
for x in index:
    x.setdefault('fmt', 'jlpt'); x.setdefault('min', 110)
index = [x for x in index if x['fmt'] == 'jlpt']
SETS = [('test1.json', 'tv1_', 'Thaolejp – Test từ vựng-ngữ pháp N1'), ('test2.json', 'tv2_', 'Thaolejp – Test từ vựng-ngữ pháp N1 (bổ trợ)'),
        ('cn.json', 'cn_', 'Thaolejp – Bài tập Cẩm nang ngữ pháp N1'), ('bt1.json', 'bt1_', 'Thaolejp – Tài liệu bổ trợ đọc hiểu'), ('bt2.json', 'bt2_', 'Thaolejp – Tài liệu bổ trợ đọc hiểu')]
dropped = 0
for f, pre, label in SETS:
    for i, e in enumerate(J(f)):
        e['id'] = f'{pre}{i}'; e['set'] = label; nq = 0
        for s in e['sections']:
            s['instr'] = jj(s['instr']); s['name'] = ''; nb = []
            for b in s['blocks']:
                if b['t'] == 'q':
                    if len(b['o']) != 4 or not b['a']: dropped += 1; continue
                    b['q'] = re.sub(r'（\s*）', '（　　）', jj(b['q'])); b['o'] = [jj(o) for o in b['o']]; nq += 1
                elif b['t'] == 'text': b['text'] = '\n'.join(jj(l) for l in b['text'].split('\n'))
                nb.append(b)
            s['blocks'] = nb
        e['sections'] = [s for s in e['sections'] if any(b['t'] == 'q' for b in s['blocks'])]
        e['nq'] = nq
        if not nq: continue
        json.dump(e, open(f'data/exams/{e["id"]}.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        index.append(dict(id=e['id'], title=e['title'], set=label, level='N1', nq=nq, fmt='practice', min=max(10, round(nq * 1.5)),
                          secs=[[s['no'], sum(1 for b in s['blocks'] if b['t'] == 'q')] for s in e['sections']]))
json.dump(index, open('data/exams/index.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('exams', len(index), 'questions', sum(x['nq'] for x in index), 'dropped', dropped)

# ---------- đọc hiểu
R = [g for g in json.load(open('data/reading.json', encoding='utf-8')) if g['id'] != 'r100']
r = J('r100.json')
for s in r['sets']:
    s['passage'] = [jj(p) for p in s['passage']]
    for q in s['questions']: q['q'] = jj(q['q']); q['options'] = [jj(o) for o in q['options']]
R.append(r)
json.dump(R, open('data/reading.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('reading sets', sum(len(g['sets']) for g in R))

# ---------- kính ngữ: câu mẫu (text nghe)
K = json.load(open('data/keigo.json', encoding='utf-8'))
K['phrases'] = [dict(sec=x['sec'], title=jj(x['title']), ex=[jj(e) for e in x['ex']]) for x in J('kgtext.json')]
json.dump(K, open('data/keigo.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('keigo phrases', len(K['phrases']))
