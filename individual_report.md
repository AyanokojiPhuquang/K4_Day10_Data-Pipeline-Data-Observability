# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Phú Quang             |
| MSSV               | 2A202602017                     |
| Khóa/Lớp         | K4              |
| Tên nhóm         | TrickLord     |
| Vai trò chính    | Source Ingestion                 |
| Repository         | https://github.com/AyanokojiPhuquang/K4_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ------------ |
| Source Ingestion | `src/ingestion/crossref.py` — `fetch_source_records()`, `parse_crossref_payload()`, `load_raw_records()` | Settings (query, filter, max_results) | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàn thành |
| Data class PaperRecord | `src/ingestion/crossref.py` — `PaperRecord` | Raw Crossref API items | Typed dataclass dùng cho toàn pipeline | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------ | -------- |
| Tích hợp pipeline end-to-end | Trần Kiên (phase1.py, corruption_flow.py) | Pipeline chạy thành công từ ingestion đến evaluation |
| Hỗ trợ cleaning contract | Nguyễn Hữu Huy (cleaning.py) | Đảm bảo PaperRecord schema tương thích với cleaning module |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------- | --------------- |
| Gọi Crossref API với retry logic | `src/ingestion/crossref.py::fetch_source_records` | 24 records fetched thành công | `uv run python script/run_phase1.py` — log hiển thị "[crossref] Fetched 24 records" |
| Parse response thành PaperRecord | `src/ingestion/crossref.py::parse_crossref_payload` | Trích xuất DOI, title, abstract, authors, subject, dates, URLs | Kiểm tra `data/raw/crossref_records.json` — 24 records đầy đủ fields |
| Lưu raw response và records | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | 2 artifact files | `ls data/raw/` — cả 2 file tồn tại |
| Load cached records | `src/ingestion/crossref.py::load_raw_records` | Đọc lại records từ JSON khi không cần re-fetch | Pipeline chạy lần 2 dùng cached data thành công |

Output cụ thể: File `data/raw/crossref_records.json` chứa 24 bản ghi học thuật từ Crossref API với schema nhất quán (paper_id, title, summary, authors, categories, published, updated, abs_url, pdf_url, comment). Đây là đầu vào cho module cleaning của Nguyễn Hữu Huy.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Module ingestion cần lấy metadata bài báo học thuật từ Crossref REST API — một nguồn công khai cung cấp DOI, tiêu đề, abstract, tác giả, chủ đề và ngày xuất bản. Dữ liệu này là đầu vào cho toàn bộ RAG pipeline: cleaning → embedding → retrieval → evaluation.

### Cách triển khai

1. **Gọi API với retry**: Dùng `requests.get()` với exponential backoff (2s, 4s, 8s) cho status 429/503. Thêm header `User-Agent` theo yêu cầu của Crossref. Timeout 30s cho mỗi request.

2. **Parse response**: Crossref trả về JSON có cấu trúc `payload["message"]["items"]`. Mỗi item cần trích xuất:
   - DOI → `paper_id`
   - `title[0]` → `title` (normalized whitespace)
   - `abstract` → `summary` (loại bỏ JATS XML tags bằng regex)
   - `author[].given + family` → `authors` list
   - `subject[]` → `categories`
   - `published-print/published-online/created` date-parts → `published` (ISO format)
   - `deposited/indexed` → `updated`
   - DOI → `abs_url` (https://doi.org/{DOI})
   - `link[]` với content-type PDF → `pdf_url`

3. **Validate**: Skip record nếu thiếu DOI hoặc title — đây là hai trường bắt buộc.

4. **Lưu trữ**: Raw API response lưu nguyên dạng JSON; parsed records lưu dạng list of dicts để `load_raw_records()` có thể đọc lại mà không cần gọi API lần nữa.

### Input, output và contract

| Thành phần | Mô tả |
| ------------ | ------- |
| Input | `Settings` chứa `source_query="agentic retrieval augmented generation large language model"`, `source_filter="from-pub-date:2026-02-07,has-abstract:true"`, `max_results=24` |
| Output | `list[PaperRecord]` — 24 records, mỗi record có 11 fields typed |
| Module phụ thuộc | `src/core/config.py` (Settings, Paths), `src/core/utils.py` (write_json, read_json) |
| Module sử dụng output | `src/ingestion/cleaning.py` (build_clean_dataframe nhận list[PaperRecord]) |
| Điều kiện lỗi cần xử lý | API timeout, rate limit 429, server error 503, response thiếu items, record thiếu DOI/title |

### Cách xác minh

```bash
uv run python script/run_phase1.py
```

- **Kết quả mong đợi:** Fetch 24 records, lưu 2 file JSON vào `data/raw/`.
- **Kết quả thực tế:** "[crossref] Fetched 24 records from Crossref API." — 2 files tạo thành công.
- **Artifact/log:** `data/raw/crossref_response.json` (full API response), `data/raw/crossref_records.json` (24 parsed records).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Crossref date-parts có thể thiếu month hoặc day (ví dụ `[[2026, 7]]` thay vì `[[2026, 7, 15]]`). Cần quyết định xử lý thế nào.
- **Các phương án đã cân nhắc:**
  1. Bỏ qua record nếu date không đầy đủ.
  2. Mặc định month=1, day=1 khi thiếu để vẫn giữ record.
- **Phương án đã chọn:** Phương án 2 — mặc định month=1, day=1.
- **Lý do:** Giữ được nhiều record hơn (tăng completeness). Đối với RAG pipeline, việc có approximate date vẫn tốt hơn là mất record hoàn toàn. Trade-off là `age_days` có thể sai lệch vài ngày đối với một số record, nhưng không ảnh hưởng đáng kể đến freshness monitoring (threshold là 180 ngày).
- **Bằng chứng quyết định phù hợp:** 24/24 records đều có `published` field hợp lệ; baseline freshness report cho thấy 0 stale rows, quality checks all passed.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `TypeError: can't subtract offset-naive and offset-aware datetimes`
- **Lệnh hoặc bước tái hiện:** `uv run python script/run_phase1.py` — lỗi xảy ra tại `cleaning.py` khi tính `age_days`.
- **Nguyên nhân gốc:** Hàm `now_utc()` trong `utils.py` trả về `datetime.now(UTC)` (timezone-aware), trong khi `datetime.strptime()` parse ngày từ string trả về naive datetime. Python không cho phép trừ hai kiểu này trực tiếp.
- **Cách xử lý:** Trong `build_clean_dataframe`, trước khi tính `age_days`, convert `run_date` thành naive bằng `run_date.replace(tzinfo=None)`.
- **Cách xác minh sau khi sửa:** Chạy lại `uv run python script/run_phase1.py` — pipeline hoàn thành thành công, `age_days` được tính đúng cho tất cả 24 records.
- **Điều học được:** Khi làm việc với datetime trong Python, luôn kiểm tra consistency giữa timezone-aware và naive datetimes trước khi thực hiện phép tính. Nên thống nhất dùng một loại trong toàn bộ codebase.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Crossref API được gọi với query và filter → raw JSON response lưu vào `data/raw/` → parse thành `PaperRecord` → cleaning module chuẩn hóa text, tính `age_days`, tạo `text_for_embedding` (kết hợp title + abstract + authors + categories) → `LocalEmbeddingIndex.build()` dùng `sentence-transformers/all-MiniLM-L6-v2` để encode text thành vectors → vectors được lưu vào ChromaDB collection với metadata.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Test set được tạo từ cleaned dataset: mỗi paper sinh ra 3-4 câu hỏi (summary, authors, date, categories). Mỗi câu hỏi có `ground_truth` (đáp án đúng) và `ground_truth_doc_ids` (DOI của paper chứa đáp án). Khi evaluate, system trả lời câu hỏi rồi so sánh: (a) `retrieval_hit_rate` — retrieved docs có chứa ground_truth_doc_id không, (b) `token_f1` — overlap giữa answer và ground_truth, (c) LLM judge chấm score 1-5 và correct/incorrect.

3. **Quality checks khác freshness monitoring ở điểm nào?**
   Quality checks kiểm tra tính đúng đắn cấu trúc dữ liệu (completeness: không null, uniqueness: không trùng paper_id, validity: summary có nội dung). Freshness monitoring kiểm tra tính cập nhật theo thời gian — so sánh `age_days` với threshold 180 ngày để xác định data có stale hay không. Quality checks là static validation; freshness là temporal validation.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để đảm bảo so sánh công bằng (controlled experiment). Nếu dùng test set khác, sự thay đổi metrics có thể do câu hỏi khác nhau chứ không phải do data quality. Cùng test set cho phép kết luận nhân quả: sự giảm/tăng metrics trực tiếp do dữ liệu bị corrupt/repair.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Repair thành công khi: (a) quality checks all passed (từ failed → passed), (b) freshness status trở lại FRESH, (c) retrieval và answer metrics phục hồi về mức baseline. Cụ thể trong bài lab: repaired `retrieval_hit_rate`=1.0, `mean_token_f1`=1.0, `judge_accuracy`=1.0, `mean_judge_score`=5.0 — tất cả bằng baseline, chứng minh repair thành công hoàn toàn.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ---------------------- |
| `retrieval_hit_rate` |     1.00 |      0.875 |     1.00 | Corruption làm mất 3 latest records → 12.5% câu hỏi không tìm được đúng doc |
| `mean_token_f1`      |     1.00 |      0.697 |     1.00 | Blank summary và noise injection làm answer sai lệch đáng kể |
| `judge_accuracy`     |     1.00 |      0.681 |     1.00 | ~32% câu trả lời bị đánh giá incorrect do corrupted content |
| `mean_judge_score`   |     5.00 |      3.72 |     5.00 | Score giảm từ 5 xuống 3.72 — chất lượng câu trả lời bị ảnh hưởng rõ rệt |
| Quality checks         | All Pass |  1 Failed |  All Pass | Corrupted: paper_id uniqueness failed do duplicate rows |
| Freshness status       |    FRESH |     FRESH |    FRESH | Stale dates (4 rows → 2020-01-01) nhưng chưa quá 50% threshold |

### Kết luận từ số liệu

1. **[Drop latest + Blank summary]** → **[paper_id bị mất khỏi index, summary trống]** → **[retrieval_hit_rate giảm từ 1.0 → 0.875, token_f1 giảm từ 1.0 → 0.697]**. Khi 3 paper bị xóa và 4 paper mất summary, agent không thể retrieve đúng document và không thể trả lời chính xác từ nội dung rỗng.

2. **[Repair từ raw source]** → **[quality checks all passed, data trở về trạng thái sạch]** → **[tất cả metrics phục hồi về 1.0/5.0]**. Repair bằng cách re-clean từ raw records gốc đảm bảo dữ liệu được phục hồi hoàn toàn từ nguồn đáng tin cậy.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**

`blank_summary` ảnh hưởng rõ nhất vì: (1) nó tác động trực tiếp đến `text_for_embedding` — khi summary trống, embedding vector mất phần thông tin quan trọng nhất, (2) câu hỏi loại "summary" chiếm 1/3 test set — ground_truth dựa trên summary nên khi summary rỗng, token_f1 = 0 cho những câu đó, (3) `drop_latest` cũng ảnh hưởng mạnh nhưng scope hẹp hơn (chỉ 3 records so với 4 records bị blank).

**Kết quả nào khác với kỳ vọng ban đầu?**

Freshness status vẫn FRESH ngay cả khi 4 records bị đặt ngày 2020-01-01. Nguyên nhân: threshold là ≥50% fresh, mà chỉ có 4/24 = 16.7% bị stale → vẫn pass. Nếu muốn phát hiện corruption kiểu stale date tốt hơn, cần thắt chặt threshold (ví dụ ≥90% fresh) hoặc thêm check riêng cho oldest_published date.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline cần idempotent và reproducible:** Lưu raw response cho phép re-run pipeline mà không cần gọi API lại. Điều này quan trọng khi debug hoặc khi API có rate limit.

2. **Data quality checks phải được thiết kế để phát hiện corruption pattern cụ thể:** Check "summary_not_empty ≥ 80%" quá lỏng — cần thêm check về content quality (ví dụ không chứa noise patterns) và stricter uniqueness checks.

3. **Chất lượng embedding phụ thuộc trực tiếp vào chất lượng text đầu vào:** Khi `text_for_embedding` bị corrupt (blank summary, noise injection), retrieval quality giảm ngay lập tức. Điều này cho thấy data observability phải giám sát ở layer ingestion/cleaning chứ không chỉ ở output metrics.

### Nếu có thêm thời gian

Thêm **content anomaly detection** trong quality checks: so sánh distribution của `summary_chars` với baseline (z-score), phát hiện sudden drop hoặc outlier. Đo bằng: chạy corruption lại với anomaly check mới → check phải fail khi summary bị blank hoặc noise, giảm false negative rate từ hiện tại (chỉ phát hiện khi ≥20% bị blank) xuống phát hiện ngay khi ≥1 record bất thường.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Phú Quang
**Ngày xác nhận:** 2026-08-06
