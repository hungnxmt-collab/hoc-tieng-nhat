# Bổ sung: Từ vựng N1 FULL 10.2024 (Dũng Mori, 1.157 từ, 46 mục) + lộ trình học 27 tuần (SCHEDULE N1-05).
# Cách chạy: python3 tools/tvfull.py <TỪ VỰNG N1 FULL.pdf> tvfull.json ; python3 tools/add_2026_11_01b.py tvfull.json <SCHEDULE.xlsx>
import json, sys, re, datetime, openpyxl
tv = json.load(open(sys.argv[1], encoding='utf-8'))
CH = {'1': 'Động từ 動詞', '2': 'Động từ phức 複合動詞', '3': 'Danh từ 名詞', '4': 'Tính từ 形容詞', '5': 'Phó từ 副詞', '6': 'Katakana カタカナ'}
V = json.load(open('data/vocab.json', encoding='utf-8'))
V = [d for d in V if not d['id'].startswith('dm')]
secs = {}
for x in tv:
    secs.setdefault(x['sec'], []).append(x)
new = []
for sec, items in secs.items():
    ch = sec.split('.')[0]
    new.append(dict(id='dm' + sec.replace('.', '_'), group='Từ vựng N1 FULL (Dũng Mori)', sec=sec,
                    name=f'{sec} · {CH[ch]}',
                    items=[dict(id=f'dm{x["n"]}', w=x['w'], r=x['r'], hv='', m=x['m'], ex=x['ex'], exvi=x['exvi']) for x in items]))
V = new + V   # đặt bộ mới lên đầu
json.dump(V, open('data/vocab.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('vocab decks', len(V), 'new words', len(tv))

wb = openpyxl.load_workbook(sys.argv[2], data_only=True); ws = wb.active
rows = [[c for c in r] for r in ws.iter_rows(values_only=True)]
weeks = []; cur = None
for r in rows:
    a = str(r[0] or '').strip()
    if a.startswith('TUẦN'):
        cur = dict(title=a.title().replace('Tuần', 'Tuần'), days=[]); weeks.append(cur); continue
    if cur is None: continue
    cells = r[1:8]
    if any(isinstance(c, datetime.datetime) for c in r[:8]):
        ds = [c for c in r[:8] if isinstance(c, datetime.datetime)][:7]
        cur['dates'] = [d.strftime('%Y-%m-%d') for d in ds]
    elif a.startswith('NỘI DUNG') or (not a and any(cells)):
        cur['days'] = [re.sub(r'\n{2,}', '\n', str(c or '').strip()) for c in cells]
note = next((str(r[0]).strip() for r in rows if r[0] and str(r[0]).startswith('Note')), '')
title = str(rows[0][0]).split('\n')[0].strip()
plan = dict(title=title, info=str(rows[1][0] or '').strip(), note=note, start=weeks[0]['dates'][0], weeks=[])
for i, w in enumerate(weeks):
    plan['weeks'].append(dict(n=i + 1, days=[dict(id=f'w{i+1}d{j+1}', text=t) for j, t in enumerate(w['days'][:7])]))
json.dump(plan, open('data/plan.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('plan weeks', len(plan['weeks']), plan['start'])
