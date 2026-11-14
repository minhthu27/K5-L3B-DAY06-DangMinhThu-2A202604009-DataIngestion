# Báo cáo cá nhân — Day 6: Data Ingestion Engineering

Học viên: Đặng Minh Thu · MSSV 2A202604009 · Lớp L3B

## Dữ liệu và pipeline
- **Chủ đề, nguồn/quyền, số trang, quy tắc tính trang:** *Introduction to Sociology 3e* (OpenStax), chương 1–2. Nguồn: https://openstax.org/details/books/introduction-sociology-3e, truy cập 2026-11-14. Giấy phép theo trang bản quyền của PDF (trang PDF 4): Creative Commons Attribution Non-Commercial ShareAlike 4.0 (CC BY-NC-SA 4.0), chỉ dùng phi thương mại, phải ghi nguồn. Bài này dùng cho mục đích học tập. Có 40 trang nội dung: chương 1 là trang PDF 19–37, chương 2 là trang PDF 47–67. `page` là số trang PDF của file gốc, không phải số in trong sách. Đã loại bìa, mục lục, Key Terms, Summary, Quiz và References. PDF gốc 664 trang, 48 MB, không commit; bản cắt `starter/data/sociology-3e_ch1-2.pdf` có commit.
- **Chuẩn hóa, lỗi, giới hạn:** Trích văn bản bằng pypdf, rồi chuẩn hóa Unicode NFC, bỏ ký tự điều khiển, bỏ dòng đầu/chân trang OpenStax, nối từ bị ngắt dòng bằng gạch nối và gộp khoảng trắng. 40/40 trang nạp thành công, 0 trang bị bỏ. `manifest.json` ghi `char_count` = 124 398 là số ký tự thô pypdf trích ra (đã kiểm tra lại, khớp đúng). Sau chuẩn hóa còn 121 664 ký tự; chênh 2 734 ký tự là phần đầu/chân trang, gạch nối ngắt dòng và khoảng trắng thừa bị loại. PDF mất ranh giới đoạn nên ranh giới đoạn của chiến lược B được suy ra bằng quy tắc dấu câu và chữ hoa, chưa tách theo heading thật.
- **Embedding, vector store, lệnh chạy, chi phí:** `BAAI/bge-small-en-v1.5` chạy local bằng sentence-transformers 6.3.0 (torch 2.15.0 CPU), 384 chiều, vector chuẩn hóa. Truy vấn có tiền tố BGE "Represent this sentence for searching relevant passages: ", tài liệu không có tiền tố. Vector store là PostgreSQL 16.16 với pgvector 0.8.7, metric cosine (`<=>`), quét chính xác (không dùng chỉ mục ANN). Lệnh chạy: `docker compose -p day6_student_starter up -d --wait`, rồi `python -m src.run` (xem `starter/RUN.md`). Chi phí 0 USD.
- **Metadata:** Bắt buộc có `document_id`, `source`, `page`, `chapter`. Trường lọc bổ sung là `chapter` (`ch1|ch2`), lấy từ ranh giới chương trong sách. Lý do chọn: có thể xác minh khách quan và dùng được cho truy vấn chỉ thuộc một chương.

## Cấu hình và benchmark
- **A / B / C:**
  - A: fixed-size 500 ký tự, overlap 50, không filter.
  - B: tách theo đoạn/câu, gộp đến tối đa 800 ký tự, overlap 0, không filter.
  - C: dùng lại index B, thêm filter `chapter` cho 4 câu có filter.
  - A→B chỉ đổi chiến lược chunking. B→C khác nhau duy nhất ở filter chapter. Cả ba dùng cùng model, corpus và benchmark.
- **Benchmark:** 20 câu, gồm 15 dev (d01–d15) và 5 test (t01–t05). Có 4 câu metadata filter (d08, d14, d15, t03). Mỗi câu có `evidence_quote`. `benchmark/verify_evidence.py` kiểm tra quote có trong trang gold (sau NFC) và filter khớp chương của trang gold. Kết quả: `total=20 dev=15 test=5 filter=4 test_filter=1 fail=0`. Các câu test hỏi chủ đề và trang không trùng với câu dev (trang 34, 35, 50, 64, 65).
- **Tiêu chí chọn chiến lược (chốt trước khi chạy test):** Chỉ xét dev: Evidence Hit@3 cao nhất, nếu hòa thì Hit@1, nếu vẫn hòa thì ít chunk/thời gian hơn. Kết quả lưu ở `starter/results/selection_dev.json`.

## Kết quả
| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian embed | Chi phí |
|---|---|---|---|---|---|---|
| A | dev | 10/15 | 13/15 | 287 | 7,23 s | 0 |
| A | test | 4/5 | 5/5 | 287 | 7,23 s | 0 |
| B | dev | 11/15 | 14/15 | 216 | 4,73 s | 0 |
| B | test | 4/5 | 5/5 | 216 | 4,73 s | 0 |
| C | dev | 11/15 | 14/15 | 216 (dùng lại B) | 4,73 s | 0 |
| C | test | 4/5 | 5/5 | 216 (dùng lại B) | 4,73 s | 0 |

| Strategy | Coherence TB /2 (n=10) | Metadata đủ và đúng | Filter tuân thủ | Grounding 0/1/2 và TB /2 (n=5) |
|---|---|---|---|---|
| A | 0,90 | 15/15 | N/A | 0/0/5, 2,0 |
| B | 1,70 | 15/15 | N/A | 0/0/5, 2,0 |
| C | 1,70 | 15/15 | 1/1 (t03) | 0/0/5, 2,0 |

Trace, nhãn thủ công và cách chọn mẫu:
- Trace top-3 đầy đủ nằm ở `starter/results/traces.jsonl`.
- Nhãn nằm ở `starter/results/audit_coherence.csv`, `audit_grounding.csv`, `audit_metadata.csv`.
- Coherence: 10 vị trí cố định, là giữa 10 trang đầu (019–028).
- Grounding: 5 câu test, top-3.
- Metadata: 5 câu test × top-3, đối chiếu tự động với PDF gốc.
- Chi tiết ở `starter/results/ANALYSIS.md`.

## Phân tích và kết luận
- **A→B:** Số chunk giảm từ 287 xuống 216 (−25%), thời gian embed từ 7,23 s xuống 4,73 s. Coherence tăng từ 0,90 lên 1,70. Dev Hit@3 tăng từ 13/15 lên 14/15 và Hit@1 từ 10/15 lên 11/15. Test không đổi. **B→C:** Kết quả giống hệt B ở cả 4 câu có filter vì top-3 của B đã đúng chương, nên chưa chứng minh được lợi ích của filter.
- **Hai ví dụ sai:**
  1. **d01** ("How do sociologists define sociology?"), cấu hình A, nguồn *Introduction to Sociology 3e*, trang gold 20. Câu định nghĩa bị cắt ngang ranh giới chunk. Top-3 chỉ có `A:p020:04` chứa phần sau, không chunk nào chứa trọn evidence. Đây là lỗi do cắt cố định.
  2. **d08** ("In the research process, what separates the independent variable from the dependent variable?"), cấu hình B và C, trang gold 50. Top-3 là các bảng ví dụ biến ở trang 50–51, còn chunk chứa định nghĩa "cause of the change / effect" nằm ở chunk khác cùng trang và không lọt top-3. Đây là lỗi xếp hạng, không phải lỗi cắt chunk.
- **Chiến lược chọn:** Chọn B. Đánh đổi: chunk dài hơn (trung bình 562 ký tự, so với 467 của A) nên giữ trọn ý nhưng có thể làm loãng điểm tương đồng (d08). Điều kiện áp dụng: văn bản có cấu trúc đoạn rõ và cần giữ trọn câu. Filter chỉ nên dùng khi truy vấn thật sự giới hạn theo chương.
- **Hạn chế:**
  - Mẫu nhỏ: 15 dev, 5 test, 4 câu filter. Sai khác giữa các cấu hình chỉ là 1 câu, nằm trong sai số.
  - Chỉ một sách nên dev và test cùng giọng văn, và rò rỉ chỉ giảm chứ không bị loại bỏ.
  - Test không phân biệt được cấu hình: cả ba đều 5/5 và grounding đạt trần 2,0.
  - Dev và test được in cùng một lần chạy. Cấu hình chỉ được chọn dựa trên dev và pipeline không sửa sau khi thấy test.
  - Gold chỉ ghi một trang mỗi câu. d07 (gold trang 48) còn có evidence hợp lệ ở trang 49 và 52, nên Hit bị đánh giá thấp.
  - Nhãn coherence và grounding do một người chấm, cũng là người xây pipeline.
  - Grounding chỉ đo độ đủ của bằng chứng, không đo độ chính xác câu trả lời LLM.
  - Thời gian chỉ là thời gian embed trên CPU, một lần chạy, chưa lặp lại. Chi phí bằng 0 vì dùng model local.
- **Nếu làm lại:**
  - Thêm nhiều sách hoặc nhiều chương để filter có tác dụng thật.
  - Tách đoạn theo heading thật.
  - Ghi nhiều trang gold hợp lệ cho mỗi câu.
  - Thêm một người chấm độc lập.
  - Thử reranker hoặc hybrid BM25.
  - Lặp lại phép đo thời gian nhiều lần.
