"""Đọc và chuẩn hóa corpus theo data/manifest.json.

Giữ liên kết trang: `page` = số trang PDF của FILE GỐC (không phải số in trong sách).
File đã cắt (sociology-3e_ch1-2.pdf) có trang thứ i tương ứng manifest["pages"][i].
"""
import json
import logging
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader

from .models import DocumentPage

log = logging.getLogger(__name__)

# Dòng chân trang lặp lại của OpenStax, vd "8 1 • An Introduction to Sociology Access for free at openstax.org"
_FOOTER = re.compile(r"(Access for free at openstax\.org)")


def normalize_text(text: str) -> str:
    """NFC, bỏ ký tự điều khiển, nối từ bị ngắt dòng bằng gạch nối, gộp khoảng trắng.

    Giữ lại ranh giới đoạn (dòng trống) để chunk theo đoạn còn dùng được.
    """
    text = unicodedata.normalize("NFC", text)
    text = text.replace(" ", " ").replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = _FOOTER.sub("", text)
    # bỏ dòng chân/đầu trang OpenStax: "8 1 • An Introduction..." và "1.1 • What Is Sociology? 9"
    text = re.sub(r"(?m)^\s*\d+ \d+ • .*$", "", text)
    text = re.sub(r"(?m)^\s*\d+\.\d+ • .* \d+\s*$", "", text)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)          # nối từ ngắt dòng
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_manifest(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))[0]


def load_pdf(path: Path, document_id: str, source: str, page_map: list[dict]) -> list[DocumentPage]:
    """Trích từng trang của file đã cắt; page/chapter lấy từ manifest.

    Trang rỗng hoặc lỗi được ghi log và bỏ qua (không âm thầm bỏ).
    """
    reader = PdfReader(str(path))
    if len(reader.pages) != len(page_map):
        raise ValueError(f"PDF có {len(reader.pages)} trang nhưng manifest có {len(page_map)}")
    pages: list[DocumentPage] = []
    for idx, info in enumerate(page_map):
        try:
            raw = reader.pages[idx].extract_text() or ""
        except Exception as exc:  # ghi lỗi, không dừng cả pipeline
            log.error("Lỗi đọc trang pdf_page=%s: %s", info["pdf_page"], exc)
            continue
        text = normalize_text(raw)
        if not text:
            log.warning("Trang rỗng pdf_page=%s", info["pdf_page"])
            continue
        pages.append(DocumentPage(
            document_id=document_id,
            source=source,
            page=info["pdf_page"],
            text=text,
            metadata={"chapter": info["chapter"], "page_id": info["page_id"]},
        ))
    return pages
