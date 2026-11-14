# Benchmark — Introduction to Sociology 3e (chương 1–2)

Corpus: `data/manifest.json` (40 trang PDF: ch1 = 19–37, ch2 = 47–67). `gold_page` là **số trang PDF của file gốc** (không phải số in trong sách).

## Tệp

| Tệp | Mục đích |
|---|---|
| `questions.json` | 20 câu: `id, split, type, question, expected_answer, gold_source_id, gold_page, evidence_quote, filter` |
| `build_questions.py` | Nguồn sinh `questions.json` |
| `verify_evidence.py` | Kiểm tra quote có trong trang gold (sau NFC + gộp khoảng trắng) và filter khớp chương của trang gold |

Kiểm chứng (chạy từ thư mục gốc repo, trong `.venv` của starter):

```powershell
starter\.venv\Scripts\python.exe benchmark\verify_evidence.py
```

Kết quả lần chạy: `total=20 dev=15 test=5 filter=4 test_filter=1 fail=0`.

## Cách chia dev/test (chốt trước khi chạy bất kỳ cấu hình nào)

- Dev = `d01–d15`, test = `t01–t05`. Test gồm: `t01` Goffman (ch1), `t02` Clark/Brown v. Board (ch1), `t03` hypothesis (ch2, có filter), `t04` ASA (ch2), `t05` secondary data (ch2).
- Mỗi câu test hỏi một **chủ đề khác** với câu dev, nhưng **không tránh được trùng trang**: test dùng trang 34, 35, 50, 65, 64; trang 50 trùng `d08`, trang 65 trùng `d15`, trang 64 trùng `d13` (xem rò rỉ bên dưới).
- Loại câu: `truc_tiep`, `dien_dat_lai` (paraphrase, hạn chế trùng từ với evidence), `dieu_kien` (phân biệt/điều kiện), `chi_tiet`, `loc_metadata`.
- Filter (trường `chapter`, giá trị `ch1`/`ch2`): 4 câu (`d08`, `d14`, `d15` dev; `t03` test). Giá trị filter là input giả định được cung cấp trước truy xuất; cấu hình C chạy **không filter** với các câu còn lại. Các câu filter chọn chủ đề xuất hiện ở cả hai chương (hypothesis, Weber) để filter có tác dụng thật.

## Tiêu chí chọn cấu hình (định nghĩa trước khi xem test)

Chọn trên **dev**: (1) Evidence Hit@3 cao nhất; nếu hòa thì (2) Hit@1 cao hơn; nếu vẫn hòa thì (3) ít chunk/thời gian ingest hơn. Cấu hình được chọn chỉ dựa trên dev. Trên thực tế, lần chạy đầu in số liệu dev và test cùng lúc; pipeline và cấu hình không được sửa sau khi xem test. Không sửa `questions.json` sau khi đã xem kết quả test; nếu buộc phải sửa, ghi rõ trong báo cáo.

## Nguy cơ rò rỉ và giới hạn (ghi trung thực)

- Corpus là **một sách**, nên dev và test cùng giọng văn/thuật ngữ; chia theo chủ đề chỉ giảm chứ không loại bỏ rò rỉ.
- Một số khái niệm xuất hiện ở nhiều trang: `d03` (manifest/latent) cũng được nhắc ở trang 31; `t02` Clark chỉ ở trang 35; `d14`/`d15` cùng nhắc Weber nhưng khác chương. Với các câu có nhiều trang hợp lệ, khi chấm cần ghi trang hợp lệ khác nếu gặp; đang ghi **một** trang gold cho mỗi câu.
- Test chỉ có 5 câu: sai số lớn, không dùng để khẳng định chiến lược tốt nhất tổng quát.
- Bộ câu hỏi và evidence do tác giả soạn, sau đó kiểm chứng bằng script ở trên.
