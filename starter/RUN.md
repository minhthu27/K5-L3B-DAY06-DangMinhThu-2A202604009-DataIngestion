# Cách chạy pipeline (Bước 3)

Từ thư mục `starter/` (đã tạo `.venv`, copy `.env.example` -> `.env`):

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt     # lần đầu: tải torch, có thể mất vài phút
docker compose -p day6_student_starter up -d --wait
python scripts/check_setup.py                 # kỳ vọng: Setup OK
$env:PYTHONIOENCODING="utf-8"; python -m src.run
```

- Model embedding `BAAI/bge-small-en-v1.5` được tải từ Hugging Face ở lần chạy đầu (cần mạng), chạy CPU, chi phí 0.
- Dữ liệu: `../data/manifest.json`, `data/sociology-3e_ch1-2.pdf` (đã cắt từ PDF gốc, xem manifest). Benchmark: `../benchmark/questions.json`.
- Kiểm chứng benchmark: `python ../benchmark/verify_evidence.py` (cần PDF gốc trong `data/raw/`).
- Nạp lại: `python -m src.run` chạy lại ingest hai lần và dừng nếu số dòng thay đổi (upsert theo `(strategy, chunk_id)`, xóa chunk cũ không còn).

## Kết quả ghi vào `results/`

`traces.jsonl` (top-3 đầy đủ), `metrics.json`, `selection_dev.json` (chọn chỉ dựa trên dev), `config.json` (model, phiên bản, thời điểm), `ingest_stats.json` (số chunk, độ dài, thời gian), `audit_*.csv` (mẫu chấm tay; cột nhãn để trống, tác giả tự điền).
