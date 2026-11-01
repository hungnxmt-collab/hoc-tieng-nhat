# Học N1 — ứng dụng học & luyện thi JLPT N1

Web app chạy trên máy tính và điện thoại (cài được lên màn hình chính, dùng được khi offline).

## Tính năng
- **Ôn tập thẻ lặp lại ngắt quãng (SRS)**: từ vựng, kanji, ngữ pháp — tự tính ngày ôn tiếp theo.
- **Từ vựng**: 1.157 từ N1 FULL 10.2024 (Dũng Mori, 46 mục, câu ví dụ có dịch), 1.169 từ N1 tổng hợp (24 bài), 714 từ N1 Trainingbook (theo ngày), từ vựng tiếp khách nhà hàng, và từ bạn tự thêm.
- **Kanji N1**: 315 chữ / 21 chương, có âm Hán Việt, On/Kun, ví dụ, mẹo nhớ.
- **Ngữ pháp**: 106 mẫu theo giáo trình + 30 mẫu hay xuất hiện, kèm bài giảng Mizuna cho một số mẫu.
- **Lộ trình 28 tuần** (lớp N1 Dũng Mori): đánh dấu từng buổi, liên kết thẳng đến bài từ vựng / kanji / ngữ pháp / đọc hiểu.
- **Hiragana / Katakana**: bảng chữ và trắc nghiệm, ưu tiên chữ hay sai.
- **Đọc hiểu**: 56 bài (短文, 中文, 長文, 比較, 検索) với 145 câu hỏi có đáp án, xem kèm bản gốc.
- **Đề thi thử N1**: tự sinh đề (đọc kanji, từ vựng, ngữ pháp, đọc hiểu) có tính giờ, chấm điểm theo phần.
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
