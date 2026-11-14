"""Pipeline Day 06: ingest -> chunk -> embed -> pgvector -> top-3 -> metrics + mẫu chấm tay.

Chạy từ thư mục starter/:  python -m src.run
Kết quả ghi vào starter/results/. Thiếu backend/model sẽ báo lỗi, không fallback.

Ba cấu hình (cùng corpus, model, benchmark, cosine, exact scan):
  A: chunk cố định 500 ký tự, overlap 50      | không lọc
  B: chunk theo đoạn, tối đa 800 ký tự         | không lọc
  C: giống B (dùng lại index B)                | lọc chapter CHỈ cho câu có filter
"""
import csv
import json
import logging
import os
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from . import chunking, evaluation
from .embeddings import DEFAULT_MODEL, QUERY_PREFIX, MyEmbedder
from .ingestion import load_manifest, load_pdf
from .store import PgVectorStore

STARTER = Path(__file__).resolve().parents[1]
ROOT = STARTER.parent
RESULTS = STARTER / "results"
FIXED_SIZE, FIXED_OVERLAP, PARA_MAX = 500, 50, 800
TOP_K = 3
# config -> (index/strategy lưu vector, có áp filter hay không)
CONFIGS = {"A": ("A", False), "B": ("B", False), "C": ("B", True)}

log = logging.getLogger("run")


def length_stats(chunks):
    lens = sorted(len(c.text) for c in chunks)
    return {"n_chunks": len(lens), "total_chars": sum(lens), "approx_tokens_chars_div4": sum(lens) // 4,
            "min": lens[0], "median": statistics.median(lens), "mean": round(statistics.mean(lens), 1),
            "p90": lens[int(0.9 * (len(lens) - 1))], "max": lens[-1]}


def ingest(store, embedder, strategy, chunks):
    t0 = time.perf_counter()
    vectors = embedder.embed_documents([c.text for c in chunks])
    t_embed = time.perf_counter() - t0
    t1 = time.perf_counter()
    store.upsert(strategy, chunks, vectors)
    t_store = time.perf_counter() - t1
    return {"embed_seconds": round(t_embed, 2), "store_seconds": round(t_store, 2)}


def coherence_positions(pages, chunks_by_strategy, n=10):
    """10 vị trí cố định TRƯỚC khi xem điểm: giữa trang của 10 page ID đầu (sắp xếp)."""
    rows = []
    for page in sorted(pages, key=lambda p: p.page)[:n]:
        flat = " ".join(page.text.split())
        mid = len(flat) // 2
        probe = None
        for shift in (0, -40, 40, -80, 80, -120, 120):
            cand = flat[mid + shift: mid + shift + 30]
            if all(any(cand in c.text for c in chunks_by_strategy[s] if c.page == page.page)
                   for s in ("A", "B")):
                probe = cand
                break
        if probe is None:
            probe = flat[mid:mid + 30]
        for cfg, (idx, _) in CONFIGS.items():
            hit = next((c for c in chunks_by_strategy[idx] if c.page == page.page and probe in c.text), None)
            rows.append({"position": f"p{page.page:03d}", "probe_30chars": probe, "config": cfg,
                         "chunk_id": hit.chunk_id if hit else "", "chunk_text": hit.text if hit else "NOT_FOUND",
                         "coherence_0_2": "", "reason": ""})
    return rows


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    load_dotenv(STARTER / ".env")
    db_url = os.environ["DATABASE_URL"]
    RESULTS.mkdir(exist_ok=True)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # 1. corpus + benchmark
    man = load_manifest(ROOT / "data" / "manifest.json")
    pages = load_pdf(ROOT / man["local_file"], man["source_id"], man["title"], man["pages"])
    skipped = len(man["pages"]) - len(pages)
    if len(pages) < 30:
        raise SystemExit(f"Chỉ có {len(pages)} trang nội dung đọc được (<30)")
    questions = json.loads((ROOT / "benchmark" / "questions.json").read_text(encoding="utf-8"))
    assert sum(q["split"] == "dev" for q in questions) >= 15 and sum(q["split"] == "test" for q in questions) >= 5
    log.info("Corpus: %d trang (bỏ qua %d), %d câu hỏi", len(pages), skipped, len(questions))

    # 2. chunk
    chunks = {"A": [c for p in pages for c in chunking.fixed_size(p, FIXED_SIZE, FIXED_OVERLAP)],
              "B": [c for p in pages for c in chunking.by_paragraph(p, PARA_MAX)]}

    # 3. embed + store
    embedder = MyEmbedder(DEFAULT_MODEL)
    store = PgVectorStore(db_url, embedder.dimensions)
    store.create_schema()
    stats = {}
    for s in ("A", "B"):
        timing = ingest(store, embedder, s, chunks[s])
        n_first = store.count(s)
        ingest(store, embedder, s, chunks[s])            # nạp lại cùng phiên bản
        n_second = store.count(s)
        assert n_first == n_second == len(chunks[s]), f"Nạp lại làm đổi số dòng ({s}): {n_first}->{n_second}"
        stats[s] = {**length_stats(chunks[s]), **timing, "rows_after_first_ingest": n_first,
                    "rows_after_reingest": n_second, "reingest_duplicates": n_second - n_first}
        log.info("Strategy %s: %s", s, stats[s])
    stats["C"] = {"note": "dùng lại index B; chỉ thêm filter chapter cho câu có filter"}

    # 4. truy xuất top-3 cho mọi câu x mọi cấu hình
    traces, qcache = [], {}
    for q in questions:
        t0 = time.perf_counter()
        qcache[q["id"]] = embedder.embed_query(q["question"])
        qcache[q["id"] + "_ms"] = (time.perf_counter() - t0) * 1000
    for cfg, (idx, use_filter) in CONFIGS.items():
        for q in questions:
            flt = q["filter"] if (use_filter and q["filter"]) else None
            t0 = time.perf_counter()
            hits = store.search(idx, qcache[q["id"]], TOP_K, flt)
            ms = (time.perf_counter() - t0) * 1000
            ev = evaluation.evaluate_query(q, hits)
            traces.append({
                "strategy": cfg, "index": idx, "split": q["split"], "question_id": q["id"], "type": q["type"],
                "question": q["question"], "filter_requested": q["filter"], "filter_applied": flt,
                "gold_source_id": q["gold_source_id"], "gold_page": q["gold_page"],
                "evidence_quote": q["evidence_quote"], "search_ms": round(ms, 2),
                "top3": [{**h, "is_hit": f} for h, f in zip(hits, ev["per_rank_hit"])],
                "eval": ev})
    with open(RESULTS / "traces.jsonl", "w", encoding="utf-8") as f:
        for t in traces:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    # 5. metrics + chọn cấu hình CHỈ dựa trên dev
    metrics = evaluation.summarize(traces)
    dev = {c: metrics[f"{c}|dev"] for c in CONFIGS}
    n_chunks = {"A": stats["A"]["n_chunks"], "B": stats["B"]["n_chunks"], "C": stats["B"]["n_chunks"]}
    simplicity = {"A": 0, "B": 1, "C": 2}   # hòa mọi tiêu chí -> chọn cấu hình đơn giản hơn
    order = sorted(CONFIGS, key=lambda c: (-dev[c]["hit3"], -dev[c]["hit1"], n_chunks[c], simplicity[c]))
    selection = {"criteria": "dev Hit@3 -> dev Hit@1 -> ít chunk hơn -> đơn giản hơn",
                 "ranking_on_dev": order, "selected": order[0], "dev_metrics": dev}
    (RESULTS / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (RESULTS / "selection_dev.json").write_text(json.dumps(selection, indent=2, ensure_ascii=False), encoding="utf-8")

    # 6. thống kê, cấu hình, phiên bản
    import psycopg, pypdf, sentence_transformers, torch
    with psycopg.connect(db_url) as conn:
        pg = conn.execute("SELECT version()").fetchone()[0].split(",")[0]
        pgv = conn.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone()[0]
    config = {"started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "embedding": {"provider": "local sentence-transformers", "model": DEFAULT_MODEL,
                            "dimensions": embedder.dimensions, "normalize": True,
                            "query_prefix": QUERY_PREFIX, "document_prefix": "", "cost_usd": 0},
              "vector_store": {"engine": pg, "pgvector": pgv, "metric": "cosine (<=>)",
                               "search": "exact scan (không index ANN)", "table": "chunks"},
              "strategies": {"A": {"chunk": f"fixed {FIXED_SIZE} ký tự, overlap {FIXED_OVERLAP}", "filter": False},
                             "B": {"chunk": f"theo đoạn/câu, tối đa {PARA_MAX} ký tự", "filter": False},
                             "C": {"chunk": "như B (dùng index B)", "filter": "chapter, chỉ cho câu có filter"}},
              "corpus": {"pages_expected": len(man["pages"]), "pages_loaded": len(pages), "pages_skipped": skipped,
                         "chars_after_normalization": sum(len(p.text) for p in pages)},
              "versions": {"python": platform.python_version(), "sentence_transformers": sentence_transformers.__version__,
                           "torch": torch.__version__, "psycopg": psycopg.__version__, "pypdf": pypdf.__version__}}
    (RESULTS / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    (RESULTS / "ingest_stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    # 7. mẫu chấm thủ công (nhãn để TRỐNG, tác giả tự điền)
    by_cfg = {"A": chunks["A"], "B": chunks["B"]}
    write_csv(RESULTS / "audit_coherence.csv", coherence_positions(pages, by_cfg),
              ["position", "probe_30chars", "config", "chunk_id", "chunk_text", "coherence_0_2", "reason"])
    meta_rows, ground_rows = [], []
    for t in traces:
        if t["split"] != "test":
            continue
        ground_rows.append({"config": t["strategy"], "question_id": t["question_id"], "question": t["question"],
                            "evidence_quote": t["evidence_quote"], "auto_hit_at_3": t["eval"]["hit_at_3"],
                            "grounding_0_2": "", "reason": ""})
        for rank, h in enumerate(t["top3"], 1):
            meta_rows.append({"config": t["strategy"], "question_id": t["question_id"], "rank": rank,
                              "chunk_id": h["chunk_id"], "source": h["source"], "page": h["page"],
                              "chapter": h["chapter"], "filter_applied": json.dumps(t["filter_applied"]),
                              "page_text_preview": h["text"][:120], "metadata_correct_yes_no": "", "error_note": ""})
    write_csv(RESULTS / "audit_grounding.csv", ground_rows,
              ["config", "question_id", "question", "evidence_quote", "auto_hit_at_3", "grounding_0_2", "reason"])
    write_csv(RESULTS / "audit_metadata.csv", meta_rows,
              ["config", "question_id", "rank", "chunk_id", "source", "page", "chapter", "filter_applied",
               "page_text_preview", "metadata_correct_yes_no", "error_note"])

    # 8. in tóm tắt
    print("\n=== Evidence Hit (tử/mẫu) ===")
    for k, v in metrics.items():
        print(f"{k:10s} n={v['n']:2d}  Hit@1={v['hit1']}/{v['n']}  Hit@3={v['hit3']}/{v['n']}")
    print("Chọn trên dev:", selection["selected"], "| xếp hạng:", order)
    print("Đã ghi kết quả vào", RESULTS)


if __name__ == "__main__":
    main()
