# Group Report — Day 10: Data Pipeline & Data Observability

> Báo cáo được cập nhật ngày 2026-08-06 bằng cách đối chiếu source, artifact trong `data/`, Rubric và báo cáo cá nhân của 5 thành viên. Phân biệt rõ **artifact đã có trong repository** với **khả năng chạy lại tại máy hiện tại**.

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4 |
| Tên nhóm | TrickLord |
| Repository | https://github.com/AyanokojiPhuquang/K4_Day10_Data-Pipeline-Data-Observability |
| Ngày cập nhật báo cáo | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu | Trạng thái evidence |
| --: | --- | --- | --- | --- | --- |
| 1 | Nguyễn Phú Quang | 2A202602017 | Source Ingestion | `src/ingestion/crossref.py` | Có source, raw response/records và báo cáo cá nhân |
| 2 | Nguyễn Hữu Huy | 2A202601220 | Cleaning & Test Set | `src/ingestion/cleaning.py`, `src/evaluation/testset.py` | Có source, clean data, 72-question test set và báo cáo cá nhân |
| 3 | Trần Tuấn Linh | 2A202601612 | Observability | `src/observability/quality.py`, `reporting.py` | Có source, quality/freshness/reports và báo cáo cá nhân |
| 4 | Nguyễn Đại Quân | 2A202601933 | Corruption & Repair | `src/ingestion/corruption.py` | Có source, corruption log và corrupted/repaired artifacts |
| 5 | Trần Kiên | 2A202601598 | Integration & Comparison | `src/pipelines/phase1.py`, `corruption_flow.py`, `script/` | Có source, metrics 3 trạng thái và báo cáo cá nhân |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành đầy đủ các khối code theo vai trò: Crossref ingestion, cleaning/data model, MiniLM + ChromaDB retrieval, evaluation, observability, corruption/repair và hai pipeline điều phối. Hai flow đã được chạy end-to-end thành công ngày 2026-08-06. Repository hiện có raw response và 24 raw records, cleaned dataset, ba embedding manifests, một test set 72 câu hỏi, answers/metrics của baseline–corrupted–repaired, quality/freshness JSON và hai Markdown reports. Baseline đạt retrieval hit rate/F1/judge accuracy là 1.0000 và judge score 5.0000; corruption làm các chỉ số lần lượt giảm còn 0.9167/0.8653/0.8611/4.4444; repair từ raw source đưa các chỉ số về đúng baseline.

Quality evidence cũng cùng chiều: baseline và repaired pass 5/5 checks, trong khi corrupted chỉ pass 2/5: duplicate count là 1, có 2 summary ngắn hơn 40 ký tự và 1 stale row. Vì ba metrics files cùng có 72 samples, so sánh là trên cùng evaluation set. Lần chạy mới đã tái sinh `data/quality/`, `data/results/` và `data/reports/` từ source hiện tại, vì vậy artifacts và code observability/corruption hiện đã cùng format.

## 3. Kiến trúc và luồng dữ liệu

```text
Crossref REST API / raw cache
    -> raw response + PaperRecord JSON
    -> cleaning, dedupe, text_for_embedding
    -> MiniLM embeddings + ChromaDB collection
    -> shared evaluation test set + baseline metrics
    -> quality/freshness reports
    -> intentional corruption + re-index + re-evaluate
    -> re-clean from raw source + re-index + re-evaluate
    -> baseline/corrupted/repaired comparison report
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref API/settings | Fetch, retry/backoff, parse thành `PaperRecord` | `data/raw/crossref_response.json`, `crossref_records.json` | Nguyễn Phú Quang |
| Cleaning | `list[PaperRecord]` | Normalize, lọc record lỗi, dedupe, tính `age_days`, build `text_for_embedding` | `data/clean/papers_clean.csv`, `.json` | Nguyễn Hữu Huy |
| Embedding/index | Cleaned DataFrame | `sentence-transformers/all-MiniLM-L6-v2`, Chroma persistent collection | `data/embeddings/*.json`, `data/chroma/` khi chạy | Retrieval module; tích hợp bởi Trần Kiên |
| Evaluation | Shared test set + index | Retrieval, answer extraction, token F1, heuristic/LLM judge | `data/results/*_answers.json`, `*_metrics.json` | Nguyễn Hữu Huy; tích hợp bởi Trần Kiên |
| Observability | Cleaned DataFrame + metrics | Quality checks, freshness, Markdown reporting | `data/quality/`, `data/reports/` | Trần Tuấn Linh |
| Corruption/repair | Cleaned data + raw snapshot | Inject faults; repair bằng re-clean từ raw | Corruption log, corrupted/repaired clean data | Nguyễn Đại Quân |
| Orchestration | Settings + các contract trên | Điều phối baseline và corruption flow | Scripts, metrics, comparison evidence | Trần Kiên |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị |
| --- | --- |
| `LLM_PROVIDER` | `gemini` mặc định; có thể dùng OpenAI, Anthropic, OpenRouter, Ollama hoặc custom endpoint |
| `LLM_MODEL` | `gemini-2.5-flash` mặc định |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Source | Crossref REST API; query `agentic retrieval augmented generation large language model` |
| Số record cấu hình | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày |
| Fast evaluation | `FAST_EVAL=1` dùng heuristic judge, không cần gọi LLM cho mỗi câu hỏi |

Không có API key trong source/report/artifacts đã kiểm tra. Tạo `.env` từ `.env.example` nếu chọn provider cần credential.

### Lệnh cài đặt và chạy

Do thư mục repository nằm sâu trong OneDrive, không tạo `.venv` ở project nếu gặp WinError 206 từ PyTorch. Dùng Python 3.11–3.13 và venv ở đường dẫn ngắn, ví dụ:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe" -m venv C:\venvs\k4d10
C:\venvs\k4d10\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .

$env:PYTHONPATH = "$PWD\src"
$env:FAST_EVAL = "1"
python script\run_phase1.py
python script\run_corruption_flow.py
```

### Trạng thái tái hiện

| Lệnh | Trạng thái hiện tại | Bằng chứng |
| --- | --- | --- |
| Compile source | Đạt | `python -m compileall src script app.py` pass |
| Baseline pipeline | Thành công | Chạy xong `script/run_phase1.py`; `baseline_metrics.json` có timestamp artifact 2026-08-06 10:57 UTC |
| Corruption flow | Thành công | Chạy xong `script/run_corruption_flow.py`; comparison report sinh lúc 2026-08-06 10:58 UTC |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API |
| Query | `agentic retrieval augmented generation large language model` |
| Filter đã ghi trong artifact | `from-pub-date:2026-02-07,has-abstract:true` |
| Records raw / cleaned | 24 / 24 |
| Retry/backoff | Retry cho 429/503 với exponential backoff trong `crossref.py` |

### Raw và clean schema

| Trường | Kiểu | Vai trò | Xử lý lỗi |
| --- | --- | --- | --- |
| `paper_id` | string | DOI/document identity ổn định | Record thiếu DOI bị loại từ ingestion/cleaning |
| `title`, `summary` | string | Nội dung cho retrieval và ground truth | Normalize/strip markup; record thiếu title hoặc summary quá ngắn bị loại |
| `authors`, `categories` | list[string] | Metadata và câu hỏi evaluation | Dùng `authors_joined`/`categories_joined` cho index |
| `published`, `age_days` | ISO date/integer | Freshness và corruption stale-date | Ngày không parse được bị loại |
| `text_for_embedding` | string | Text đầu vào MiniLM | Ghép title, authors, categories, published, summary |

## 6. Evaluation setup

| Thành phần | Cấu hình/evidence |
| --- | --- |
| Số câu hỏi | 72 |
| Question types | 24 summary, 24 authors, 24 publication date |
| Ground truth | Sinh trực tiếp từ cleaned dataset, có `ground_truth_doc_ids` |
| Embedding/vector store | MiniLM + ChromaDB |
| Retrieval | Top 4 |
| Chỉ số | `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score` |
| Test set dùng chung | `data/eval/test_set.json` |

Giữ nguyên test set là điều kiện để metric phản ánh ảnh hưởng của data state, không phản ánh khác biệt câu hỏi. Cả ba metrics files đều có `samples: 72`.

## 7. Kết quả baseline

| Artifact | Đường dẫn | Trạng thái | Evidence |
| --- | --- | --- | --- |
| Raw response/records | `data/raw/` | Có | 2 JSON files, 24 records |
| Cleaned dataset | `data/clean/papers_clean.*` | Có | 24 cleaned records |
| Embedding manifest | `data/embeddings/papers_embeddings.json` | Có | MiniLM/Chroma manifest |
| Evaluation set | `data/eval/test_set.json` | Có | 72 questions |
| Baseline metrics/answers | `data/results/baseline_*` | Có | 72 samples |
| Quality/freshness | `data/quality/baseline_quality.json`, `freshness_report.json` | Có | Quality all passed; stale rows 0 |
| Baseline report | `data/reports/phase1_report.md` | Có | Source, metrics, quality, freshness |

| Metric | Giá trị baseline |
| --- | ---: |
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 1.0000 |
| `judge_accuracy` | 1.0000 |
| `mean_judge_score` | 5.0000 |

## 8. Data quality và freshness

| Check/signal | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| Row count | Pass, 24 | Pass, 23 | Pass, 24 |
| `paper_id` unique/not-null | Pass, 0 duplicate | **Fail**, 1 duplicate | Pass, 0 duplicate |
| Title not null | Pass | Pass | Pass |
| Summary minimum length | Pass, 0 short | **Fail**, 2 short | Pass, 0 short |
| Freshness rows | 0 stale/24 | 1 stale/23 | 0 stale/24 |
| Overall quality | Pass | **Fail** | Pass |
| Dataset freshness status | FRESH | FRESH | FRESH |

`is_fresh=true` của corrupted chỉ phản ánh record mới nhất còn mới; không phủ nhận 4 rows stale. Vì vậy kết luận observability dựa trên cả row-level checks và freshness summary.

## 9. Corruption scenarios và repair

Artifacts hiện có trong `data/results/corruption_log.json` ghi nhận các tác động sau:

| Corruption | Số record tác động | Data-quality impact | Repair |
| --- | ---: | --- | --- |
| Drop latest | 2 | Giảm coverage của corpus | Rebuild từ raw records |
| Blank summary | 1 | Summary dưới ngưỡng 40 ký tự | Re-clean raw snapshot |
| Noise injection + mojibake | 2 | Nội dung embedding bị nhiễu | Re-clean raw snapshot |
| Truncate title | 1 | Metadata/retrieval cue giảm chất lượng | Re-clean raw snapshot |
| Stale date | 1 | 1 stale row | Re-clean raw snapshot |
| Duplicate row | 1 | Fail uniqueness (1 duplicate) | Re-clean raw snapshot |
| Author swap/category misclassification/malformed URL | 4 actions | Factuality và validity metadata bị tác động | Re-clean raw snapshot |

Repair không chỉnh sửa trực tiếp DataFrame lỗi. `corruption_flow.py` nạp `data/raw/crossref_records.json`, chạy lại `build_clean_dataframe`, rồi build index và evaluate lại.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Change do corruption | Recovery so baseline |
| --- | ---: | ---: | ---: | ---: | ---: |
| `retrieval_hit_rate` | 1.0000 | 0.9167 | 1.0000 | -0.0833 | 0.0000 |
| `mean_token_f1` | 1.0000 | 0.8653 | 1.0000 | -0.1347 | 0.0000 |
| `judge_accuracy` | 1.0000 | 0.8611 | 1.0000 | -0.1389 | 0.0000 |
| `mean_judge_score` | 5.0000 | 4.4444 | 5.0000 | -0.5556 | 0.0000 |
| Quality checks | All pass | Fail uniqueness | All pass | Suy giảm | Khôi phục |
| Stale rows | 0 | 1 | 0 | +1 | 0 |

Kết luận có evidence:

1. Blank/noisy summary, missing latest documents và duplicate rows làm quality signal xấu đi; đồng thời retrieval hit rate, F1 và judge metrics đều giảm.
2. Re-clean từ raw source loại lại corruption thay vì che lỗi; data quality trở lại pass và bốn evaluation metrics trở lại baseline trên cùng 72 câu hỏi.

## 11. Kiểm tra mức hoàn thành theo Rubric

| Mục rubric | Evidence hiện có | Đánh giá tự kiểm | Điểm khả năng* |
| --- | --- | --- | ---: |
| 1. Code structure (10) | `src/` chia core, ingestion, retrieval, evaluation, observability, pipelines | Đủ module, naming rõ | 9/10 |
| 2. Raw ingestion (15) | `crossref.py`, raw response/records 24 items | Có fetch, parse, cache, retry | 14/15 |
| 3. Cleaning/modeling (15) | Clean CSV/JSON, schema, `text_for_embedding` | Có normalize, filter, dedupe, derived fields | 14/15 |
| 4. Embedding/vector store (10) | MiniLM/Chroma code và manifests | Có build/search/index evidence | 9/10 |
| 5. Agent/LLM provider (10) | `llm.py`, `qa.py`, provider config | Có abstraction đa provider; baseline/corruption/repaired đã chạy bằng fast evaluator | 8/10 |
| 6. Evaluation/scoring (10) | 72 questions, answers và metrics 3 states | Đủ four metrics + answer artifacts; đã chạy lại | 10/10 |
| 7. Observability (10) | Quality/freshness JSON và Markdown reports | Có checks, freshness, reporting; đã tái sinh | 10/10 |
| 8. Corruption/comparison (10) | Log, corrupted/repaired metrics và repair flow | Impact/recovery rõ; đã chạy lại từ source hiện tại | 10/10 |
| **Tổng cơ bản dự kiến** |  | **Có evidence cho mọi mục 1–8** | **84/90** |

\*Đây không phải điểm giảng viên chấm. Điểm thực tế vẫn do giảng viên chấm; bài đã có một lần chạy end-to-end thành công trên source hiện tại.

### Kết luận về phần việc của thành viên

Theo code, artifacts và 5 báo cáo cá nhân, mỗi role đã có deliverable chính và evidence tương ứng. Vì vậy nhóm **đã phủ đủ task được phân công**; baseline và corruption flow cũng đã chạy thành công trên source hiện tại. Trước khi nộp, còn hai việc khuyến nghị để tăng độ chắc chắn/điểm bonus:

1. Lưu lại environment Python ở đường dẫn ngắn như hướng dẫn để thành viên khác tái hiện không gặp WinError 206.
2. Thêm smoke tests hoặc validation tự động để hướng tới bonus.

## 12. Vấn đề tích hợp quan trọng và giới hạn

- **CSV list contract:** `authors` và `categories` trở thành string khi lưu CSV. `corruption_flow.py` parse lại có kiểm soát bằng `ast.literal_eval` trước khi đưa vào corruption, tránh sai kiểu dữ liệu ở flow sau.
- **Môi trường Windows:** `.venv` trong repository vẫn không nên dùng nếu nằm ở đường dẫn OneDrive dài. Lần chạy thành công dùng virtual environment ở đường dẫn ngắn; ghi lại lựa chọn này trong README trước khi nộp.
- **Artifact/source consistency:** Các output cũ đã được thay bằng output từ lần chạy mới; quality/report/corruption log hiện có format khớp implementation source hiện tại.
- **Validation tự động:** Repository chưa có test suite. Thêm smoke tests cho baseline preconditions, test-set hash và repair equality sẽ tăng reproducibility.

## 13. Checklist trước khi nộp

- [x] Có đủ source modules cho 5 vai trò và không còn `TODO(student)`/`NotImplementedError` trong `src/`/`script/`.
- [x] Có raw, clean, embeddings manifest, eval set, metrics/answers, quality/freshness và reports.
- [x] Có báo cáo cá nhân cho 5 thành viên theo cấu trúc `report/<HoTen>_<MSSV>.md`.
- [x] Không phát hiện API-key-like value trong source/report/artifact đã kiểm tra.
- [x] Bảng baseline/corrupted/repaired dùng metrics 72 samples và có evidence đường dẫn cụ thể.
- [x] Đã chạy lại end-to-end trên environment sạch của source hiện tại.
- [x] Đã xác nhận artifact/report mới sinh khớp với code cuối cùng.
- [ ] Đã thêm smoke tests hoặc validation tự động (khuyến nghị bonus).
