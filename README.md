# Học N1 — ứng dụng học & luyện thi JLPT N1

Web app chạy trên máy tính và điện thoại (cài được lên màn hình chính, dùng được khi offline).

## Tính năng
- **Ôn tập thẻ lặp lại ngắt quãng (SRS)**: từ vựng, kanji, ngữ pháp — tự tính ngày ôn tiếp theo.
- **Từ vựng** (hơn 8.000 thẻ): Chinh phục từ vựng N1 (2.218 từ / 111 bài, có dịch câu ví dụ), 8 chuyên đề Thaolejp (phó từ, từ nối, cụm từ thay thế trong đề, động từ ghép, kanji đọc đặc biệt, 130 kanji khó, tiền tố, hậu tố, kanji dễ nhầm), 1.157 từ N1 FULL 10.2024 (Dũng Mori, 46 mục, câu ví dụ có dịch), 1.169 từ N1 tổng hợp (24 bài), 714 từ N1 Trainingbook (theo ngày), từ vựng tiếp khách nhà hàng, và từ bạn tự thêm.
- **Kanji N1**: 315 chữ / 21 chương, có âm Hán Việt, On/Kun, ví dụ, mẹo nhớ.
- **Ngữ pháp** (683 mục): 106 mẫu theo giáo trình + 30 mẫu hay xuất hiện + Tổng hợp ngữ pháp N1 (201 mẫu) + Cẩm nang ngữ pháp N1 (346 mục), kèm bài giảng Mizuna cho một số mẫu.
- **Lộ trình 28 tuần** (lớp N1 Dũng Mori): đánh dấu từng buổi, liên kết thẳng đến bài từ vựng / kanji / ngữ pháp / đọc hiểu.
- **Hiragana / Katakana**: bảng chữ và trắc nghiệm, ưu tiên chữ hay sai.
- **Đọc hiểu**: 156 bài (gồm 100 bài đọc hiểu N1 Thaolejp) (短文, 中文, 長文, 比較, 検索) với 145 câu hỏi có đáp án, xem kèm bản gốc.
- **Đề thi đầy đủ**: 37 đề Thaolejp (36 đề thi thử + đề test đầu vào) và đề JLPT N1 12/2021 — 2.665 câu có đáp án; thi có giờ 110 phút hoặc luyện tập từng câu.
- **Bài tập có đáp án**: 2 bộ Test từ vựng-ngữ pháp (60 bài), 25 bài tập Cẩm nang ngữ pháp, 2 tài liệu bổ trợ đọc hiểu.
- **Luyện theo dạng câu**: 13 dạng 問題 (漢字読み, 文脈規定, ★, đọc hiểu…) gom từ tất cả các đề.
- **Kính ngữ**: bảng 34 động từ 尊敬語・謙譲語・丁寧語, quy tắc, lỗi hay gặp, trắc nghiệm.
- **Đề tự sinh**: tự sinh đề (đọc kanji, từ vựng, ngữ pháp, đọc hiểu) có tính giờ, chấm điểm theo phần.
- **Tiến độ**: chuỗi ngày học, lịch học, số từ đã thuộc, biểu đồ điểm thi.
- **Phát âm** bằng giọng đọc tiếng Nhật của trình duyệt.

## Dữ liệu lưu ở đâu
- Nội dung học: thư mục `data/` (JSON) và `img/reading/` (ảnh trang đề gốc) trên nhánh `main`.
- Tiến độ học: file `progress.json` trên nhánh `userdata` (ứng dụng tự tạo nhánh này khi đồng bộ lần đầu), ghi qua GitHub API bằng token của bạn.
  Tách nhánh để mỗi lần lưu tiến độ không làm GitHub Pages build lại trang.

## Kết nối đồng bộ
1. GitHub → Settings → Developer settings → **Fine-grained tokens** → Generate new token.
2. Repository access: chỉ chọn `hoc-tieng-nhat`. Permissions → **Contents: Read and write**.
3. Mở ứng dụng → **Đồng bộ** → dán token → *Lưu & đồng bộ*. Làm tương tự trên điện thoại.

## Thêm / sửa nội dung
Sửa trực tiếp các file trong `data/` rồi commit. Các script trích xuất từ tài liệu PDF/Excel gốc nằm ở `tools/`.
