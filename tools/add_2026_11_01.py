# Bổ sung dữ liệu ngày 2026-11-01: slide ngữ pháp Mizuna + 1 bài đọc hiểu (ảnh chụp sách).
# Chạy lại an toàn: ghi đè trường "notes" và nhóm đọc hiểu "extra".
import json

G = json.load(open('data/grammar.json', encoding='utf-8'))
byid = {g['id']: g for g in G}
MZ = 'Bài giảng Mizuna'
notes = {
    'g8_4': [dict(src=MZ, mean='Lúc thì V1 lúc thì V2', form='V1ます + つ + V2ます + つ',
                  note='Diễn tả hai hành động hoặc sự việc đan xen nhau bằng cách đặt những cặp động từ trái nghĩa như 「行く、戻る」 hoặc dạng chủ động + bị động 「押す、押される」. Đây là cách nói trang trọng, không dùng nhiều trong giao tiếp và thường chỉ dùng với một số động từ.',
                  img=['img/grammar/mz-tsu-tsu.webp'])],
    'g8_2': [dict(src=MZ, mean='Nghĩa 1: Không chủ định mà V, vô tình V — thực hiện hành động gì đó trong trạng thái không ý thức định làm', form='Vる + ともなく・ともなしに',
                  note='Đi với một số giới hạn những động từ ý chí (見る・聞く・待つ など), nhưng mô tả việc thực hiện hành động đó trong trạng thái vô thức, không mục đích. Thường lặp lại một động từ hai lần.',
                  img=['img/grammar/mz-tomonaku-1.webp']),
             dict(src=MZ, mean='Nghĩa 2: Không biết là… (không rõ ai / ở đâu / khi nào)', form='疑問詞（+ 助詞）+ ともなく・ともなしに',
                  note='Đi với từ để hỏi về người, nơi chốn, thời gian (どこ・いつ・だれ など) hoặc cụm từ để hỏi kèm theo trợ từ.',
                  img=['img/grammar/mz-tomonaku-2.webp'])],
    'g7_1': [dict(src=MZ, mean='Ít nhất cũng, chí ít cũng phải N — tức là nhiều hơn N', form='数詞 + からある・からする・からの + N',
                  note='Nhấn mạnh số lượng lớn. Đằng sau có danh từ tương ứng với số lượng ấy. Không dùng với thời gian hay số lượng ít. Số lượng thì 「〜からある・〜からの」, giá cả thì 「〜からする」, nhân số (số người) thì 「〜からの」.',
                  img=['img/grammar/mz-karaaru.webp'])],
    'g7_2': [dict(src=MZ, mean='Như thể là…, như muốn nói là…', form='発話文 + とばかり（に）',
                  note='Đi với nội dung câu nói y nguyên, có thể có 「」 hoặc không. Nói về trạng thái của người khác chứ không phải về bản thân người nói.',
                  img=['img/grammar/mz-tobakari.webp'])],
    'g7_3': [dict(src=MZ, mean='Đã là N thì… — thực hiện điều gì đó là đúng đắn, là phù hợp', form='N + たるもの（は）',
                  note='Đi với danh từ chỉ những người có địa vị cao hoặc trách nhiệm lớn lao. Phía sau có câu mô tả sự việc nên làm để tương xứng với thân phận ấy, cương vị ấy.',
                  img=['img/grammar/mz-tarumono.webp'])],
    'g8_1': [dict(src=MZ, mean='Dù là N, hay N', form='N + であれ・であろうと・であろうが',
                  note='Đưa ra các ví dụ trong một nhóm cùng ý nghĩa để nhấn mạnh sự việc phía sau đề cập đến mà không liên quan là N1 hay N2.',
                  img=['img/grammar/mz-deare-1.webp', 'img/grammar/mz-deare-2.webp'])],
    'g7_5': [dict(src=MZ, mean='Cùng với N, kết hợp với N', form='N + と相まって・が相まって（có thể ở dạng とが・とも）',
                  note='Diễn đạt sự cộng hưởng một yếu tố hoặc tính chất này với một yếu tố hoặc tính chất khác để tạo nên một hiệu quả tốt hơn hoặc mức độ cao hơn.',
                  img=['img/grammar/mz-aimatte.webp'])],
    'g8_3': [dict(src=MZ, mean='N cũng thế, N cũng thế', form='N + といい',
                  note='Đưa ra các ví dụ trong một nhóm cùng ý nghĩa. Phía sau có câu trình bày trạng thái (thường là câu có tính từ mô tả đánh giá của người nói). Không dùng với câu diễn tả ý hướng, nguyện vọng của người nói hoặc câu tác động.',
                  img=['img/grammar/mz-toii.webp'])],
    'g8_5': [dict(src=MZ, mean='Cứ V1 rồi lại V2', form='V1ては + V2て、V1ては + V2て ／ V1ては + V2ます、V1ては + V2ます',
                  note='Dùng khi muốn diễn tả các động tác cứ lặp đi rồi lặp lại, cứ làm V1 thì V2 xảy ra. Hay dùng với các cặp động từ trái nghĩa nhau.',
                  img=['img/grammar/mz-tewa.webp'])],
}
for gid, n in notes.items():
    byid[gid]['notes'] = n
# sửa lỗi chính tả tiêu đề và bổ sung dạng/ví dụ mới
g = byid['g7_1']; g['title'] = '～からある・～からいる・～からする・～からの'
g['form'] = ['N(数) + からある / からいる / からする / からの + N']
g = byid['g8_2']; g['title'] = '～ともなく・～ともなしに'
if 'Không biết là' not in g['mean']: g['mean'] += ' • Không biết là… (đi với từ để hỏi)'
if '疑問詞' not in ''.join(g['form']): g['form'].append('疑問詞（+助詞）+ ともなく・ともなしに')
g = byid['g8_1']; g['title'] = '～であれ〜であれ・～であろうと'
for e in ['1円であれ、10円であれ、お金なんだから、盗んではいけないよ。', '王様であれ、一般市民であれ、みんなそれぞれ幸せになりたいと思っている。']:
    if e not in g['ex']: g['ex'].append(e)
g = byid['g7_3']; g['title'] = '～たる・～たるもの（は）'
g = byid['g7_2']; g['title'] = '～とばかり（に）'
json.dump(G, open('data/grammar.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

R = json.load(open('data/reading.json', encoding='utf-8'))
R = [x for x in R if x['id'] != 'extra']
R.append(dict(id='extra', label='追加', title='Bài bổ sung (từ ảnh bạn gửi)', sets=[dict(
    id='extra1', title='追加1', pages=[], img=['img/reading/extra-1.webp'],
    passage=['司法試験に合格したからといって裁判官や検察官、弁護士にすぐなれるわけではありません。合格した人は、最高裁判所に属している司法研修所で２年間、司法修習生として法律についてのことなどを勉強するのです。この司法研修所に入所するためにおこなわれるのが司法試験で、この試験を管理しているのが司法試験管理委員会です。',
             '（『図説・日本の政治としくみ　法務省』旺文社より）'],
    questions=[dict(q='司法試験管理委員会の仕事は何か。',
                    options=['司法修習生になるための試験の管理', '司法試験に合格した人の管理', '司法研修所における試験の管理', '最高裁判所に属するための試験の管理'],
                    answer=1,
                    explain='Ảnh không kèm đáp án; đáp án này do Claude xác định: 司法試験 là kỳ thi để vào 司法研修所 và trở thành 司法修習生, còn 委員会 quản lý kỳ thi đó → chọn 1. Phương án 3 sai vì kỳ thi diễn ra để được vào viện, không phải thi trong viện.')])]))
json.dump(R, open('data/reading.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('ok', sum(1 for g in G if g.get('notes')), 'grammar entries with notes;', sum(len(x['sets']) for x in R), 'reading sets')
