"""Bước 4: điền nhãn audit và tổng hợp 5 tiêu chí. Chạy từ starter/: python -m src.audit

Nhãn coherence và grounding được chấm thủ công bằng cách đọc từng chunk thật trong
results/audit_*.csv; nhãn nằm trong các dict bên dưới (sửa rồi chạy lại). Metadata được
kiểm tra tự động bằng đối chiếu với trang PDF gốc (không dùng nhãn chủ quan).
"""
import csv
import json
import re
import statistics
import unicodedata
from pathlib import Path

from pypdf import PdfReader

STARTER = Path(__file__).resolve().parents[1]
ROOT = STARTER.parent
RES = STARTER / "results"
RAW_PDF = STARTER / "data" / "raw" / "introduction-sociology-3e_-_WEB.pdf"


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


# ---- Coherence (0/1/2) cho 10 vị trí; C dùng đúng chunk của B nên nhãn C = nhãn B ----
COH = {
    ("p019", "A"): (1, "Bắt đầu và kết thúc giữa câu ('...take one leg of the'), nhưng vẫn hiểu là mô tả đám đông ga tàu."),
    ("p020", "A"): (0, "Mở đầu bằng mảnh từ 'r family relationships', thiếu chủ ngữ của 'They may study'; kết thúc bằng số trang '1' lạc vào văn bản."),
    ("p021", "A"): (1, "Bắt đầu giữa câu, kết thúc cắt giữa từ ('past decade'); ý chính về 'tìm mẫu hình' vẫn hiểu được."),
    ("p022", "A"): (1, "Mở đầu giữa câu, kết thúc cắt giữa từ ('Otherwi'); câu chuyện Ashley hiểu một phần."),
    ("p023", "A"): (1, "Từ đầu bị cắt ('ly subjective'), kết thúc 'nomadic an'; nội dung Ma Tuan-Lin và Khaldun vẫn rõ."),
    ("p024", "A"): (1, "Bắt đầu bằng mảnh chú thích ảnh; phần Comte đầy đủ nhưng kèm nhiễu."),
    ("p025", "A"): (1, "Bắt đầu giữa câu ('d from what Comte proposed'), kết thúc 'had dev'; ý Marx vẫn hiểu được."),
    ("p026", "A"): (1, "Mở đầu 'is still controversial' thiếu chủ ngữ (lý thuyết nào), nhưng câu sau tự giải thích."),
    ("p027", "A"): (1, "Mở đầu bằng '(2005), the challenge...' thiếu chủ thể; kết thúc 'Columbia Universi'."),
    ("p028", "A"): (1, "Mở đầu giữa câu; kết thúc cắt 'looking-glass self' khi vừa sang nhân vật Cooley."),
    ("p019", "B"): (2, "Trọn đoạn mở đầu, bắt đầu và kết thúc ở ranh giới câu, đủ ngữ cảnh (ga tàu đông người)."),
    ("p020", "B"): (1, "'This understanding' thiếu tiền đề ở chunk trước; cuối chunk treo tiêu đề 'What Are Society and Culture?' mà nội dung ở chunk sau."),
    ("p021", "B"): (2, "Tiêu đề + đoạn trọn vẹn về cách nhà xã hội học nhìn các mẫu hình."),
    ("p022", "B"): (2, "Tiêu đề + mở đầu câu chuyện Ashley, tự đứng được dù câu chuyện còn tiếp ở chunk sau."),
    ("p023", "B"): (1, "Bắt đầu giữa đoạn (thiếu bối cảnh quyền lực của Giáo hội) và chuyển chủ đề sang Ma Tuan-Lin ở cuối."),
    ("p024", "B"): (2, "Chú thích + mục Comte; ý trọn vẹn tới hết câu về Saint-Simon (chú thích ảnh là nhiễu nhỏ)."),
    ("p025", "B"): (1, "'It also presents Marx's theory' thiếu tiền đề (Communist Manifesto ở chunk trước); phần còn lại rõ."),
    ("p026", "B"): (2, "Tiêu đề Weber + đoạn trọn vẹn về The Protestant Ethic."),
    ("p027", "B"): (2, "Tiêu đề + mở đầu mục nhà xã hội học Mỹ, ý trọn vẹn."),
    ("p028", "B"): (2, "Mục Jane Addams trọn vẹn từ tên tới kết luận."),
}
for k in [k for k in list(COH) if k[1] == "B"]:
    COH[(k[0], "C")] = COH[k]

# ---- Grounding (0/1/2) cho 5 câu test x 3 cấu hình ----
GRD = {
    ("A", "t01"): (2, "Top-1 có định nghĩa dramaturgical analysis, Goffman, ví dụ diễn viên và kịch bản; chunk cắt cuối câu nhưng đủ trả lời."),
    ("A", "t02"): (2, "Top-3 chứa tên Kenneth và Mamie Clark; top-1/2 bổ sung bối cảnh Brown v. Board và doll test."),
    ("A", "t03"): (2, "Top-1 chứa trọn định nghĩa hypothesis kèm ví dụ biến độc lập/phụ thuộc."),
    ("A", "t04"): (2, "Top-1 chứa định nghĩa ASA và mô tả bộ quy tắc đạo đức."),
    ("A", "t05"): (2, "Top-1 chứa lý do 'không tiếp xúc trực tiếp với đối tượng, không làm thay đổi hành vi'."),
    ("B", "t01"): (2, "Top-1 trọn đoạn Goffman, có cả ví dụ và nguồn trích."),
    ("B", "t02"): (2, "Top-2 chứa câu trả lời Clark kèm doll test; top-1/3 bổ sung bối cảnh và hệ quả."),
    ("B", "t03"): (2, "Top-1 có tiêu đề bước 3, định nghĩa, ví dụ if-then và biến IV/DV."),
    ("B", "t04"): (2, "Top-1 có định nghĩa ASA và danh sách nguyên tắc đạo đức."),
    ("B", "t05"): (2, "Top-1 có định nghĩa nonreactive/unobtrusive và lợi ích kèm."),
}
for q in ("t01", "t02", "t03", "t04", "t05"):
    GRD[("C", q)] = GRD[("B", q)]


def read_csv(p):
    return list(csv.DictReader(open(p, encoding="utf-8-sig")))


def write_csv(p, rows):
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    man = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))[0]
    chapter_of = {p["pdf_page"]: p["chapter"] for p in man["pages"]}
    raw = PdfReader(str(RAW_PDF))

    # ---- coherence ----
    rows = read_csv(RES / "audit_coherence.csv")
    for r in rows:
        lab, why = COH[(r["position"], r["config"])]
        r["coherence_0_2"], r["reason"] = lab, why
    write_csv(RES / "audit_coherence.csv", rows)
    coh = {}
    for c in "ABC":
        v = [int(r["coherence_0_2"]) for r in rows if r["config"] == c]
        coh[c] = {"n": len(v), "scores": v, "mean_of_2": round(statistics.mean(v), 2),
                  "count_0_1_2": [v.count(0), v.count(1), v.count(2)]}

    # ---- grounding ----
    rows = read_csv(RES / "audit_grounding.csv")
    for r in rows:
        lab, why = GRD[(r["config"], r["question_id"])]
        r["grounding_0_2"], r["reason"] = lab, why
    write_csv(RES / "audit_grounding.csv", rows)
    grd = {}
    for c in "ABC":
        v = [int(r["grounding_0_2"]) for r in rows if r["config"] == c]
        grd[c] = {"n": len(v), "count_0_1_2": [v.count(0), v.count(1), v.count(2)],
                  "mean_of_2": round(statistics.mean(v), 2)}

    # ---- metadata: đối chiếu tự động với trang PDF gốc ----
    rows = read_csv(RES / "audit_metadata.csv")
    traces = [json.loads(l) for l in open(RES / "traces.jsonl", encoding="utf-8")]
    full = {(t["strategy"], t["question_id"], i + 1): h for t in traces for i, h in enumerate(t["top3"])}
    for r in rows:
        h = full[(r["config"], r["question_id"], int(r["rank"]))]
        page = int(r["page"])
        raw_page = norm(raw.pages[page - 1].extract_text() or "") if page in chapter_of else ""
        t = norm(h["text"])
        probes = [t[:50], t[len(t) // 2: len(t) // 2 + 50]]
        errs = []
        if h["source"] != man["title"]:
            errs.append("source khác manifest")
        if page not in chapter_of:
            errs.append("page ngoài corpus")
        elif h["chapter"] != chapter_of[page]:
            errs.append(f"chapter={h['chapter']} nhưng manifest={chapter_of[page]}")
        if not all(p in raw_page for p in probes):
            errs.append("nội dung chunk không tìm thấy ở trang PDF gốc đã ghi")
        r["metadata_correct_yes_no"] = "no" if errs else "yes"
        r["error_note"] = "; ".join(errs)
    write_csv(RES / "audit_metadata.csv", rows)
    meta = {}
    for c in "ABC":
        rs = [r for r in rows if r["config"] == c]
        ok = sum(r["metadata_correct_yes_no"] == "yes" for r in rs)
        meta[c] = {"correct_over_checked": f"{ok}/{len(rs)}", "errors": [r["error_note"] for r in rs if r["error_note"]]}
    # tuân thủ filter: chỉ cấu hình C có filter trong lần chạy; A/B ghi N/A
    fq = [t for t in traces if t["split"] == "test" and t["strategy"] == "C" and t["filter_applied"]]
    comply = sum(all(h["chapter"] == t["filter_applied"]["chapter"] for h in t["top3"]) for t in fq)
    meta["C"]["filter_compliance_test"] = f"{comply}/{len(fq)}"
    meta["A"]["filter_compliance_test"] = meta["B"]["filter_compliance_test"] = "N/A (không lọc)"

    metrics = json.loads((RES / "metrics.json").read_text(encoding="utf-8"))
    stats = json.loads((RES / "ingest_stats.json").read_text(encoding="utf-8"))
    summary = {"labeler_note": "coherence và grounding: chấm thủ công bởi tác giả; metadata: kiểm tra tự động với PDF gốc",
               "retrieval": metrics, "coherence": coh, "grounding": grd, "metadata": meta,
               "resources": {"A": {k: stats["A"][k] for k in ("n_chunks", "total_chars", "mean", "median", "embed_seconds")},
                             "B": {k: stats["B"][k] for k in ("n_chunks", "total_chars", "mean", "median", "embed_seconds")}}}
    (RES / "audit_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("coherence", "grounding", "metadata")}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
