# Ghép dữ liệu sách TRY! N1 vào app: bộ ngữ pháp 'try', 10 đề まとめの問題 (làm trên trang gốc, có audio), data/try.json (mục lục).
import json, sys, re
sys.path.insert(0, '/home/claude/raw/try'); sys.path.insert(0, '/home/claude/scripts')
from toc import ITEMS, PLUS, CHAPTERS
from matome import MATOME, SCRIPT_PAGES
REPO = '/home/claude/hoc-tieng-nhat'
G = json.load(open('/home/claude/raw/try/grammar.json'))
A = json.load(open(f'{REPO}/data/audio.json')); tracks = {t['f']: t for g in A for t in g['tracks']}
chap_of = lambda page: max((c for c in CHAPTERS if c[3] <= page), key=lambda c: c[3])
# 1) ngữ pháp
gram = [g for g in json.load(open(f'{REPO}/data/grammar.json')) if g['set'] != 'try']
for it in G:
    c = chap_of(it['page'])
    use = []
    if it.get('expl'): use.append('Giải thích trong sách (OCR): ' + it['expl'])
    if it['n'] in PLUS: use.append('Mở rộng (Plus): ' + PLUS[it['n']])
    gram.append(dict(id=f'try{it["n"]}', set='try', ch=c[0], grp=f'{c[1]}「{c[2]}」', title='～' + it['pat'], form=[it['ex']], mean=it['vi'],
                     use=use, ex=it.get('exs', []), pg=it['page'], src='TRY! N1'))
json.dump(gram, open(f'{REPO}/data/grammar.json', 'w'), ensure_ascii=False, separators=(',', ':'))
# 2) đề まとめの問題
I = [x for x in json.load(open(f'{REPO}/data/exams/index.json')) if not x['id'].startswith('trym')]
new = []
for ch, m in MATOME.items():
    secs = []; n = 0
    for k, (name, key, tr) in enumerate(m['probs']):
        blocks = []
        for d in key:
            n += 1; blocks.append(dict(t='q', n=n, a=int(d), o=[], pq=1, lab=len(blocks) + 1))
        sec = dict(no=k + 1, name=name, instr='', blocks=blocks)
        if tr: sec['au'] = [f'audio/try/track{t:02d}.mp3' for t in tr]
        secs.append(sec)
    c = next(c for c in CHAPTERS if c[0] == ch and c[4])
    E = dict(id=f'trym{ch}', title=f'TRY! N1 · Chương {ch} — まとめの問題', set='TRY! N1 — まとめの問題 (bài ôn tập cuối chương)', level='N1', nq=n,
             paper=[f'img/try/p{p:03d}.webp' for p in range(m['pages'][0], m['pages'][1] + 1)], sections=secs,
             note='Số câu trong phiếu trả lời đánh theo thứ tự từng 問題 trong sách. Phần nghe có nút phát audio ngay trong phiếu.',
             script=[f'img/try/p{p:03d}.webp' for p in SCRIPT_PAGES])
    json.dump(E, open(f'{REPO}/data/exams/trym{ch}.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    new.append(dict(id=E['id'], title=E['title'], set=E['set'], level='N1', nq=n, secs=[[s['no'], len(s['blocks'])] for s in secs], fmt='practice', min=max(10, n), paper=True))
json.dump(I + new, open(f'{REPO}/data/exams/index.json', 'w'), ensure_ascii=False, separators=(',', ':'))
# 3) mục lục sách
book = dict(pages=208, chapters=[])
for c in CHAPTERS:
    nxt = [x[3] for x in CHAPTERS if x[3] > c[3]]
    end = (min(nxt) - 1) if nxt else 172
    its = [dict(n=i['n'], pat=i['pat'], ex=i['ex'], vi=i['vi'], page=i['page']) for i in ITEMS if c[3] <= i['page'] <= end and chap_of(i['page']) == c]
    trk = [t for t in tracks.values() if t.get('ch') == c[0] and ('まとめ' not in t['t']) and c[2].split('（')[0] in t['t']]
    if '（' in c[2]:
        sfx = re.search(r'（(\d)）', c[2]).group(1); trk = [t for t in trk if t['t'].endswith(f'({sfx})')] or trk
    book['chapters'].append(dict(no=c[0], kind=c[1], title=c[2], page=c[3], end=end, matome=c[4], items=its, tracks=[t['f'] for t in trk]))
book['extra'] = [dict(title='付録 · 文型索引 (chỉ mục mẫu câu)', page=174), dict(title='似ている文型リスト (mẫu câu dễ nhầm)', page=178), dict(title='N1「できること」リスト', page=188),
                 dict(title='別冊 · Đáp án やってみよう!・Check', page=193), dict(title='別冊 · まとめの問題: đáp án + script nghe', page=200)]
json.dump(book, open(f'{REPO}/data/try.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('grammar', len(G), 'matome', len(new), 'chapters', len(book['chapters']), [len(c['tracks']) for c in book['chapters']], file=sys.stderr)
