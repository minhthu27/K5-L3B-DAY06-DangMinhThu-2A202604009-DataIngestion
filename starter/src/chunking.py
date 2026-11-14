"""Chunking: fixed-size (A) và theo đoạn/heading (B, C)."""
import re

from .models import Chunk, DocumentPage


def _make(page: DocumentPage, strategy: str, idx: int, text: str) -> Chunk:
    # chunk_id ổn định -> nạp lại không nhân đôi
    return Chunk(
        chunk_id=f"{strategy}:{page.document_id}:p{page.page:03d}:{idx:02d}",
        document_id=page.document_id,
        source=page.source,
        page=page.page,
        text=text,
        metadata=dict(page.metadata),
    )


def fixed_size(page: DocumentPage, size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Cửa sổ cố định `size` ký tự, chồng `overlap`; chunk chỉ nằm trong một trang."""
    if overlap >= size:
        raise ValueError("overlap phải nhỏ hơn size")
    text = re.sub(r"\s+", " ", page.text).strip()
    chunks, start, idx = [], 0, 0
    while start < len(text):
        piece = text[start:start + size].strip()
        if piece:
            chunks.append(_make(page, "A", idx, piece))
            idx += 1
        if start + size >= len(text):
            break
        start += size - overlap
    return chunks


_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'“(])")


def _split_long(par: str, max_size: int) -> list[str]:
    """Tách đoạn quá dài theo câu, rồi theo từ nếu một câu vẫn quá dài."""
    out, cur = [], ""
    for sent in _SENT.split(par):
        while len(sent) > max_size:  # câu quá dài: cắt theo từ
            cut = sent.rfind(" ", 0, max_size)
            cut = cut if cut > 0 else max_size
            if cur:
                out.append(cur); cur = ""
            out.append(sent[:cut].strip()); sent = sent[cut:].strip()
        if cur and len(cur) + 1 + len(sent) > max_size:
            out.append(cur); cur = sent
        else:
            cur = f"{cur} {sent}".strip()
    if cur:
        out.append(cur)
    return out


def _paragraphs(text: str) -> list[str]:
    """Tách đoạn: dòng trống; nếu PDF chỉ ngắt dòng đơn thì coi dòng kết thúc bằng
    dấu câu rồi tới dòng viết hoa/heading số (vd '1.3 Theoretical ...') là ranh giới."""
    parts = re.split(r"\n\s*\n", text)
    if len(parts) == 1:
        text = re.sub(r"(?<=[.!?:])\n(?=[A-Z0-9])", "\n\n", text)
        text = re.sub(r"\n(?=\d\.\d [A-Z])", "\n\n", text)  # heading mục "1.3 ..."
        parts = re.split(r"\n\s*\n", text)
    return [re.sub(r"\s+", " ", p).strip() for p in parts if p.strip()]


def by_paragraph(page: DocumentPage, max_size: int = 800) -> list[Chunk]:
    """Gộp các đoạn liền nhau đến `max_size`; đoạn quá dài tách theo câu.

    Không cắt giữa câu trừ khi một câu dài hơn max_size.
    """
    units: list[str] = []
    for p in _paragraphs(page.text):
        units.extend(_split_long(p, max_size) if len(p) > max_size else [p])
    chunks, cur, idx = [], "", 0
    for u in units:
        if cur and len(cur) + 1 + len(u) > max_size:
            chunks.append(_make(page, "B", idx, cur)); idx += 1; cur = u
        else:
            cur = f"{cur} {u}".strip()
    if cur:
        chunks.append(_make(page, "B", idx, cur))
    return chunks
