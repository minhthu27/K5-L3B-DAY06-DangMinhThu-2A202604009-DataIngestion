"""Kiểm chứng evidence_quote nằm đúng ở gold_page (chạy từ thư mục gốc repo).
Chuẩn hóa: Unicode NFC, gộp khoảng trắng. Thoát mã 1 nếu có câu sai.
"""
import json
import re
import sys
import unicodedata

from pypdf import PdfReader

SRC = "starter/data/raw/introduction-sociology-3e_-_WEB.pdf"


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


man = json.load(open("data/manifest.json", encoding="utf-8"))[0]
chap = {p["pdf_page"]: p["chapter"] for p in man["pages"]}
reader = PdfReader(SRC)
qs = json.load(open("benchmark/questions.json", encoding="utf-8"))
bad = 0
for q in qs:
    pg = q["gold_page"]
    ok_page = pg in chap
    ok_quote = ok_page and norm(q["evidence_quote"]) in norm(reader.pages[pg - 1].extract_text() or "")
    ok_filter = q["filter"] is None or (ok_page and chap[pg] == q["filter"]["chapter"])
    ok = ok_quote and ok_filter
    bad += not ok
    print(q["id"], q["split"], pg, chap.get(pg), "OK" if ok else
          f"FAIL page_in_corpus={ok_page} quote={ok_quote} filter={ok_filter}")
d = sum(q["split"] == "dev" for q in qs)
f = [q for q in qs if q["filter"]]
tf = sum(q["split"] == "test" for q in f)
print(f"total={len(qs)} dev={d} test={len(qs) - d} filter={len(f)} test_filter={tf} fail={bad}")
sys.exit(1 if bad else 0)
