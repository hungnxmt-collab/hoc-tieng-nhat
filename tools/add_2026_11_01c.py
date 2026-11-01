# Bổ sung: 36 đề thi thử N1 + đề test đầu vào (Thaolejp), đề JLPT N1 12/2021, bảng kính ngữ.
# Tạo JSON đề bằng tools/exam_text.py + tools/exam_parse.py, rồi: python3 tools/add_2026_11_01c.py 36de.json de1221.json keigo.pdf
import json, re, sys, pdfplumber
JP = r'[ぁ-んァ-ヶー一-龥々〆〇（）「」『』、。・…]'
def jj(s):
    return re.sub(r'(?<=' + JP + r')\s+(?=' + JP + r')', '', s) if isinstance(s, str) else s
SECNAME = {1: '漢字読み', 2: '文脈規定', 3: '言い換え類義', 4: '用法', 5: '文法形式の判断', 6: '文の組み立て', 7: '文章の文法',
           8: '内容理解（短文）', 9: '内容理解（中文）', 10: '内容理解（長文）', 11: '統合理解', 12: '主張理解（長文）', 13: '情報検索'}
index = []
for f in sys.argv[1:3]:
    for e in json.load(open(f, encoding='utf-8')):
        for s in e['sections']:
            s['instr'] = jj(s['instr']); s['name'] = SECNAME.get(s['no'], '')
            for b in s['blocks']:
                if b['t'] == 'q':
                    b['q'] = re.sub(r'（\s*）', '（　　）', jj(b['q'])).replace('(　)', '（　　）'); b['o'] = [jj(o) for o in b['o']]
                elif b['t'] == 'text':
                    b['text'] = '\n'.join(jj(l) for l in b['text'].split('\n'))
        json.dump(e, open(f'data/exams/{e["id"]}.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        index.append(dict(id=e['id'], title=e['title'], set=e['set'], level=e['level'], nq=e['nq'],
                          secs=[[s['no'], sum(1 for b in s['blocks'] if b['t'] == 'q')] for s in e['sections']]))
json.dump(index, open('data/exams/index.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('exams', len(index), 'questions', sum(x['nq'] for x in index))

pdf = pdfplumber.open(sys.argv[3])
verbs, rules, mistakes = [], [], []
for i, p in enumerate(pdf.pages):
    for t in p.extract_tables():
        for r in t:
            r = [(c or '').replace('\n', '').strip() for c in r]
            if len(r) == 4 and i < 4 and r[0] and r[0] not in ('基本形', '使用方法', '行為をする人') and r[1]:
                verbs.append(dict(v=r[0], son=r[1], ken=r[2], tei=r[3]))
            elif len(r) == 9 and r[0] != '敬語':
                rules.append([x for x in r if x])
            elif len(r) == 4 and i >= 5 and r[0] and r[2] and not r[0].startswith('❌'):
                mistakes.append(dict(bad=r[0], good=r[2].replace('ご覧いただけますしたでしょうか', 'ご覧いただけましたでしょうか')))
            elif len(r) == 4 and r[0] == '丁寧語':
                rules.append(['丁寧語', r[1]])
usage = dict(son='Dùng với người trên, để tôn vinh đối phương (người thực hiện hành động là đối phương).',
             ken='Dùng khi tự hạ mình để tôn vinh đối phương (người thực hiện hành động là mình).',
             tei='Nói lịch sự với người nghe bằng です・ます・ございます (không phân biệt đối tượng).')
k = next((i for i, m in enumerate(mistakes) if m['good'] == 'ビジネス'), len(mistakes))
formal = [dict(plain=m['bad'], formal=m['good'].replace('さっきほど', '先ほど（さきほど）')) for m in mistakes[k + 1:]]
mistakes = mistakes[:k]
json.dump(dict(verbs=verbs, rules=rules, mistakes=mistakes, formal=formal, usage=usage), open('data/keigo.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
V = json.load(open('data/vocab.json', encoding='utf-8'))
V = [d for d in V if d['id'] != 'keigo']
V.append(dict(id='keigo', group='Kính ngữ', name='Động từ kính ngữ (Thaolejp)', items=[
    dict(id=f'kg{i+1}', w=x['v'], r='', hv='', m=f"尊敬: {x['son']} ／ 謙譲: {x['ken']}", ex=[]) for i, x in enumerate(verbs)]))
json.dump(V, open('data/vocab.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('keigo verbs', len(verbs), 'rules', len(rules), 'mistakes', len(mistakes))
