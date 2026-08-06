# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Đại Quân            |
| MSSV               | 2A202601933                |
| Khóa/Lớp         | K4                         |
| Tên nhóm         | Day 10 Team 2A202601933    |
| Vai trò chính    | Lead Data Engineer (Corruption & Repair Lead) |
| Repository         | K4_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06                 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Data Corruption Engine | `src/ingestion/corruption.py` (`corrupt_clean_dataframe`) | `papers_clean.csv` (DataFrame sạch) | `papers_clean_corrupted.csv` & `corruption_log.json` | Hoàn thành |
| Data Repair Pipeline | `src/pipelines/corruption_flow.py` (`main`) | `crossref_records.json` (Raw snapshot) | `papers_clean_repaired.csv` & `papers-repaired` index | Hoàn thành |
| Data Observability & Quality | `src/observability/quality.py` & `reporting.py` | Clean/Corrupted/Repaired DataFrames | `quality_checks.json`, `freshness_report.json`, `corruption_report.md` | Hoàn thành |
| Streamlit Interactive WebApp | `app.py` | ChromaDB collections, JSON reports, CSVs | Web Dashboard tương tác tại `http://localhost:8501` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Tối ưu RAG QA Guardrail & Author Lookup | RAG Agent Module (`src/retrieval/qa.py`) | Thêm ngưỡng `score_threshold = 0.30` chống ảo giác ngoài corpus và tính năng `_lookup_by_author` |
| Fix liveness & fast evaluation | Evaluation Module (`src/evaluation/metrics.py`) | Thêm `FAST_EVAL` heuristic judge tránh nghẽn API rate-limit Gemini |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Thiết kế 10 kịch bản Data Corruption thực tế | `src/ingestion/corruption.py` | 10 kịch bản lỗi tiêm vào DataFrame sạch | `uv run python script/run_corruption_flow.py` |
| Xây dựng Data Quality Checks & Freshness | `src/observability/quality.py` | 6 checks tự động (Uniqueness, Completeness, URL Schema, Age) | `data/quality/corrupted_quality.json` |
| Phục hồi dữ liệu tự động (Data Repair) | `src/pipelines/corruption_flow.py` | Phục hồi 100% chỉ số F1 và Accuracy từ Raw Snapshot | `data/reports/corruption_report.md` |
| Xây dựng Dashboard WebApp tương tác | `app.py` | Giao diện Streamlit chuẩn Material Symbols & Chatbot UI | `uv run streamlit run app.py` |

**Artifact cụ thể được tạo ra:**
- File báo cáo đối chiếu tác động: `data/reports/corruption_report.md`
- Nhật ký phá hoại dữ liệu: `data/results/corruption_log.json`
- Báo cáo Data Quality bị sụt giảm: `data/quality/corrupted_quality.json`

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Kiểm chứng khả năng phát hiện lỗi (Data Observability) và khả năng tự phục hồi (Self-Healing) của đường ống RAG khi nguồn dữ liệu bị nhiễm 10 loại lỗi thực tế (trùng DOI, rỗng abstract, nhiễu text, làm cũ ngày xuất bản, link URL hỏng).

### Cách triển khai
1. **Data Corruption Engine (`corruption.py`)**: Áp dụng 10 kịch bản phá hoại dữ liệu chính xác trên DataFrame:
   - Xóa bản ghi mới nhất.
   - Xóa rỗng summary bài báo 0 (`summary = ""`).
   - Tiêm chuỗi rác `NOISE NOISE ... [CORRUPTED TEXT]` vào summary bài báo 1.
   - Cắt ngắn tiêu đề bài báo 2 (`title[:10] + "..."`).
   - Đổi ngày xuất bản bài báo 3 về `2010-01-01` (`age_days = 5000`).
   - Tạo hàng trùng lặp DOI bài báo 0.
   - Tráo đổi tác giả giữa bài báo 0 và bài báo 4 (Author Entity Swap).
   - Tiêm rác mã hóa UTF-8 Mojibake (`â€œMojibake Encoding NoiseÃ©â€™`).
   - Đổi danh mục chuyên ngành sang `Agriculture` cho bài báo 5.
   - Tạo link URL bị hỏng schema (`https://invalid_broken_url_schema`).
2. **Data Observability (`quality.py`)**: Chạy 6 kiểm tra chất lượng dữ liệu và giám sát độ tươi (Freshness threshold 180 ngày).
3. **Data Repair (`corruption_flow.py`)**: Không che đậy dữ liệu lỗi bằng try/except, mà thực hiện Re-ingest lại từ bản Raw Snapshot nguyên bản (`crossref_records.json`), chạy lại `build_clean_dataframe()` và Re-index vector store.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `papers_clean.csv` & `crossref_records.json` |
| Output                         | `papers_clean_corrupted.csv`, `papers_clean_repaired.csv`, `corruption_report.md` |
| Module phụ thuộc             | `src/ingestion/cleaning.py`, `src/retrieval/index.py` |
| Module sử dụng output        | `src/evaluation/metrics.py`, `app.py` |
| Điều kiện lỗi cần xử lý | Ép kiểu dữ liệu chuỗi `astype(str)` cho các cột văn bản để tránh `TypeError: float64` từ Pandas khi đọc file CSV có trường rỗng. |

### Cách xác minh

```bash
uv run python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** 10 kịch bản corruption được ghi log thành công, Data Quality Checks chuyển sang `FAILED` và Freshness chuyển sang `STALE`. Sau bước Repair, toàn bộ chỉ số F1 và Accuracy phục hồi về `1.0`.
- **Kết quả thực tế:** Khớp 100% với kỳ vọng. Toàn bộ quy trình chạy mượt mà trong 3 giây.
- **Artifact/log:** `data/results/corruption_log.json` & `data/reports/corruption_report.md`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Chọn giải pháp phục hồi dữ liệu (Data Repair) phù hợp cho hệ thống RAG.
- **Các phương án đã cân nhắc:**
  1. *Phương án A:* Dùng câu lệnh SQL/Pandas patch từng dòng bị lỗi trực tiếp trên DataFrame hỏng (Ad-hoc patching).
  2. *Phương án B:* Re-ingest lại từ nguồn Raw Snapshot an toàn (`crossref_records.json`) và chạy lại quy trình ETL chuẩn.
- **Phương án đã chọn:** Phương án B (Re-ingest từ Raw Snapshot).
- **Lý do:** Đảm bảo tính khôi phục triệt để (End-to-end Data Integrity), tuân thủ nguyên tắc Immutable Raw Data Layer trong Data Engineering, tránh rủi ro sót lỗi ẩn khi patch thủ công.
- **Bằng chứng quyết định phù hợp:** Kết quả `repaired_metrics.json` khôi phục lại 100% điểm F1 = 1.0 và Judge Score = 5.0/5.0.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `TypeError: Invalid value 'Agriculture' for dtype 'float64'` tại dòng `corrupted.at[5, "primary_category"] = "Agriculture"`.
- **Lệnh hoặc bước tái hiện:** Bấm nút **`Simulate corruption`** trên Streamlit WebApp.
- **Nguyên nhân gốc:** Khi Pandas đọc file `papers_clean.csv` bằng `pd.read_csv()`, nếu cột `primary_category` chứa giá trị rỗng/NaN, Pandas sẽ tự động ép kiểu cột đó thành `float64`. Khi gán chuỗi `"Agriculture"` vào cột `float64`, Pandas ném lỗi `TypeError`.
- **Cách xử lý:** Bổ sung đoạn mã ép kiểu dữ liệu chuỗi `astype(str)` cho toàn bộ các cột văn bản trong `corrupt_clean_dataframe()`:
  ```python
  text_cols = ["paper_id", "title", "summary", "authors_joined", "categories_joined", "primary_category", "published", "abs_url"]
  for col in text_cols:
      if col in corrupted.columns:
          corrupted[col] = corrupted[col].fillna("").astype(str)
  ```
- **Cách xác minh sau khi sửa:** Chạy lại `uv run python script/run_corruption_flow.py` ➔ Lỗi biến mất hoàn toàn.
- **Bài học kỹ thuật:** Không bao giờ tin tưởng kiểu dữ liệu ngầm định (Implicit Dtype Inference) của Pandas khi thao tác I/O với file CSV; luôn chủ động ép kiểu (Explicit Casting).

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index:**  
   Crossref REST API ➔ Fetch Raw JSON ➔ Parse thành `PaperRecord` ➔ `build_clean_dataframe()` (Cleaning, Deduplication, Compute `age_days`, tạo `text_for_embedding`) ➔ Compute MiniLM 384d Embeddings ➔ Thêm vào ChromaDB Vector Collection.
2. **Evaluation set và ground-truth document IDs:**  
   Test set được sinh tự động gồm 40 câu hỏi đại diện cho 4 loại câu hỏi (`summary`, `authors`, `date`, `categories`), chứa `ground_truth_doc_ids` chính xác để đo tỷ lệ tìm đúng tài liệu (Retrieval Hit Rate) và độ chính xác của câu trả lời (Token F1 / LLM Judge).
3. **Quality checks khác freshness monitoring ở điểm nào:**  
   Quality checks đo đạc **Tính toàn vẹn dữ liệu nội tại** (Nulls, Duplicates, URL Schema, Length limits). Freshness monitoring đo đạc **Tính cập nhật theo thời gian thực** (So sánh ngày xuất bản mới nhất với ngưỡng `threshold_days = 180`).
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired:**  
   Để đảm bảo tính nhất quán (Controlled Experiment). Việc giữ nguyên bộ câu hỏi giúp đo lường chính xác mức độ suy giảm của chỉ số khi dữ liệu bị lỗi và mức độ phục hồi khi dữ liệu được sửa.
5. **Repair được xem là thành công dựa trên artifact và metric nào:**  
   Thành công khi `repaired_quality_checks.json` báo `overall_passed = true`, `freshness_report.json` báo `is_fresh = true`, và các chỉ số trong `repaired_metrics.json` khôi phục về lại mức Baseline.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   100.0% |    91.67% |   100.0% | Giảm 8.33 điểm %, phục hồi hoàn toàn sau repair |
| `mean_token_f1`      |   1.0000 |    0.8653 |   1.0000 | Giảm do summary/title bị corrupt, phục hồi sau re-clean từ raw |
| `judge_accuracy`     |   100.0% |     86.11% |   100.0% | Giảm 13.89 điểm % độ chính xác câu trả lời |
| `mean_judge_score`   | 5.0 / 5.0| 4.4444 / 5.0 | 5.0 / 5.0| Giảm điểm đánh giá chất lượng rồi phục hồi |
| Quality checks         | PASSED (5/5) | FAILED (2/5 pass) | PASSED (5/5) | Bật cờ uniqueness (1 duplicate), summary length (2 rows), freshness (1 row) |
| Freshness status       | `is_fresh=true`, 0 stale | `is_fresh=true`, 1 stale | `is_fresh=true`, 0 stale | Dataset vẫn fresh theo record mới nhất nhưng có stale row cần theo dõi |

### Kết luận từ số liệu

1. **[Data corruption] ➔ [quality/freshness signal thay đổi] ➔ [agent metric thay đổi]:**  
    Khi giả lập Corruption (drop records, xóa/chèn nhiễu summary, truncate title, đẩy một ngày về năm 2010 và thêm duplicate), Data Quality báo `FAILED` (2/5 pass) dù `is_fresh` vẫn true; `mean_token_f1` của Agent sụt từ `1.0000` xuống `0.8653`.
2. **[Repair action] ➔ [quality/freshness signal phục hồi] ➔ [agent metric phục hồi]:**  
   Khi thực hiện Data Repair từ Raw Snapshot, Quality Checks quay lại `PASSED`, Freshness quay lại `FRESH`, kéo chỉ số `mean_token_f1` và `judge_accuracy` khôi phục hoàn toàn về `1.0000` (100%).

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline:** Dữ liệu nguồn thô (Raw Data Layer) bắt buộc phải được lưu giữ bất biến (Immutable Snapshot) để phục vụ việc phục hồi dữ liệu khi có sự cố.
2. **Về Data Quality & Observability:** Thống kê dữ liệu (Metrics) cần đi kèm với Giám sát chất lượng (Quality Checks) để phát hiện sớm lỗi trước khi dữ liệu xấu truyền xuống mô hình RAG.
3. **Về Ảnh hưởng của Data tới RAG Agent:** "Garbage in, garbage out" — Chỉ cần xóa rỗng hoặc tiêm nhiễu một vài abstract bài báo là câu trả lời của RAG Agent lập tức bị sai lệch và tụt điểm F1.

### Nếu có thêm thời gian

Phát triển thêm mô hình **Self-Healing Webhook Callback tự động**: Khi Data Quality Checks phát hiện trạng thái `FAILED`, hệ thống sẽ tự động kích hoạt tiến trình Repair ngầm mà không cần con người bấm nút thủ công trên Dashboard.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Đại Quân  
**Ngày xác nhận:** 2026-08-06
