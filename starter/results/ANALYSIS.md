# Phân tích Bước 4 — năm khía cạnh

Nguồn số liệu: `metrics.json`, `audit_summary.json`, `traces.jsonl`, `audit_*.csv`. Corpus: 40 trang (ch1 = 19–37, ch2 = 47–67) của *Introduction to Sociology 3e*. Embedding `BAAI/bge-small-en-v1.5`, pgvector, cosine, exact scan.

**Người chấm.** Nhãn coherence và grounding do tác giả chấm thủ công khi đọc từng chunk, lý do ghi trong `audit_*.csv`; metadata được kiểm tra tự động bằng đối chiếu với trang PDF gốc. Nhãn nằm trong `src/audit.py` (sửa rồi chạy lại `python -m src.audit`). Nguy cơ thiên lệch: người chấm cũng là người xây pipeline và biết cấu hình nào sinh ra chunk nào.

## 1. Retrieval accuracy (tử/mẫu)

| Cấu hình | Dev Hit@1 | Dev Hit@3 | Test Hit@1 | Test Hit@3 |
|---|---|---|---|---|
| A (fixed 500/50) | 10/15 | 13/15 | 4/5 | 5/5 |
| B (theo đoạn ≤800) | 11/15 | 14/15 | 4/5 | 5/5 |
| C (B + filter chapter) | 11/15 | 14/15 | 4/5 | 5/5 |

Theo tiêu chí chốt trước (chỉ xét dev: Hit@3 → Hit@1 → số chunk), **B được chọn**. Sai khác giữa các cấu hình là 1 câu trên 15, nằm trong sai số của mẫu nhỏ.

**Ví dụ lỗi (top-3 trượt):**
- **A, d01** ("How do sociologists define sociology?"): câu định nghĩa bị cắt ngang ranh giới chunk (top-3 chỉ có `A:p020:04` với phần sau của câu; script đánh dấu `evidence_possibly_split`), không chunk nào chứa trọn evidence. Đây là lỗi do cắt cố định.
- **A, d07** ("How many steps does the scientific method have?"): top-3 là các chunk trang 49 và 52 có nhắc "6 steps", còn gold là trang 48 ("six prescribed steps"). Lưu ý: trang 49 và 52 cũng chứa bằng chứng hợp lệ nhưng benchmark chỉ ghi trang 48, nên đây có thể là âm tính giả do gold chưa liệt kê hết nguồn hợp lệ. Tác giả cần xác nhận khi chấm lại.
- **B/C, d08** (biến độc lập/phụ thuộc): top-3 là bảng ví dụ biến ở trang 50–51; chunk chứa định nghĩa "cause of the change / effect" không lọt top-3 (evidence nằm ở chunk khác cùng trang). Đây là lỗi xếp hạng, không phải cắt chunk.
- **Hit@1 hụt nhưng Hit@3 đúng (A: d02, d08, d13, t02; B/C: d05, d07, d09, t02):** chunk đúng xếp hạng 2–3; thường do chunk lân cận cùng chủ đề có điểm cao hơn.

## 2. Chunk coherence (10 vị trí cố định = giữa 10 trang đầu 019–028, thang 0–2)

| Cấu hình | Số chunk 0 / 1 / 2 | Trung bình /2 |
|---|---|---|
| A | 1 / 9 / 0 | 0.90 |
| B | 0 / 3 / 7 | 1.70 |
| C | 0 / 3 / 7 | 1.70 (cùng chunk với B) |

- A luôn cắt giữa câu hoặc giữa từ (ví dụ `p020`: bắt đầu bằng mảnh "r family relationships", thiếu chủ ngữ); chỉ chunk 1 điểm khi ý chính vẫn suy ra được.
- B giữ trọn câu và thường đi kèm tiêu đề mục, nhưng 3/10 vị trí được 1 điểm vì **thiếu tiền đề** ("This understanding…", "It also presents…") hoặc vì tiêu đề cuối chunk treo (`p020`).
- Mẫu chỉ gồm 10 trang đầu (đều chương 1), không đại diện chương 2.

## 3. Metadata usefulness

- **Đúng và đủ** (`source`, `page`, `chapter` khớp manifest; nội dung chunk tìm thấy ở trang PDF gốc): A 15/15, B 15/15, C 15/15 (5 câu test × top-3). Không có lỗi.
- **Tuân thủ filter:** C 1/1 (chỉ `t03` có filter ở tập test); A, B: N/A vì không lọc.
- **Hữu ích:** `page` cho phép truy ngược chính xác về trang PDF và chấm hit; `chapter` cho phép giới hạn phạm vi theo chương.
- **Hạn chế:** `source` chỉ là tiêu đề sách (không có URL/tên file); `chapter` chỉ có 2 giá trị nên lọc thô; ở `t03` top-3 của B đã toàn chương 2 nên filter không đổi kết quả. 15/15 cũng chỉ kiểm tra tính đúng của metadata, chưa chứng minh filter cải thiện truy xuất.

## 4. Grounding quality (5 câu test, top-3, thang 0–2)

| Cấu hình | Số câu 0 / 1 / 2 | Trung bình /2 |
|---|---|---|
| A | 0 / 0 / 5 | 2.0 |
| B | 0 / 0 / 5 | 2.0 |
| C | 0 / 0 / 5 | 2.0 |

Đây chỉ đánh giá độ đủ của bằng chứng truy xuất, **không phải độ chính xác của câu trả lời LLM**. Cả 3 đều đạt trần ở 5 câu test nên thang này không phân biệt được cấu hình; các câu test tương đối dễ (Evidence Hit@3 = 5/5 cho cả ba).

## 5. Tác động của chiến lược dữ liệu

| So sánh | Thay đổi | Tác động quan sát được |
|---|---|---|
| A → B | fixed 500/50 → theo đoạn ≤800 | Chunk 287 → 216 (−25%); tổng ký tự 133 946 → 121 488 (A có overlap); embed 7,23 s → 4,73 s; coherence 0,90 → 1,70; Dev Hit@3 13 → 14/15, Dev Hit@1 10 → 11/15; test không đổi |
| B → C | thêm filter `chapter` | Không đổi chunk, không đổi kết quả (4 câu có filter đều đã đúng chương); không có chi phí thêm đáng kể |

**Đánh đổi:** B chunk dài hơn (trung bình 562 so với 467 ký tự) nên mỗi chunk chứa nhiều ý hơn, tốt cho coherence nhưng có thể làm loãng điểm tương đồng (d08). A đơn giản và đều nhưng cắt ý. Chi phí embedding bằng 0 với model local.

**Kết luận có giới hạn:** trên corpus này, B tốt hơn A rõ ở coherence và nhỉnh hơn ở truy xuất dev; C chưa chứng minh được lợi ích của filter. Mẫu quá nhỏ (15 dev, 5 test, 4 câu filter), một sách duy nhất, nên **không suy rộng** ra corpus khác hay khẳng định chiến lược tốt nhất tổng quát.

## Giới hạn và việc cần tác giả xác nhận

1. Nhãn coherence và grounding là đánh giá chủ quan của một người chấm, mẫu nhỏ.
2. Số liệu test đã được in cùng dev trong lần chạy đầu; cấu hình được chọn chỉ dựa trên dev, không sửa pipeline sau khi thấy test.
3. Gold chỉ ghi một trang cho mỗi câu; một số câu (rõ nhất là d07) có nhiều trang hợp lệ, nên Hit có thể bị đánh giá thấp.
4. Chunk B chưa tách theo heading thật: PDF mất ranh giới đoạn nên ranh giới đoạn được suy ra bằng quy tắc dấu câu và chữ hoa.
