# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Hữu Huy             |
| MSSV               | 2A202601220                     |
| Khóa/Lớp         | K4 – Lớp E402              |
| Tên nhóm         | TrickLord     |
| Vai trò chính    | Cleaning & Test set                 |
| Repository         | https://github.com/AyanokojiPhuquang/K4_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ------------ |
| Cleaning pipeline | `src/ingestion/cleaning.py` — `build_clean_dataframe()` | `list[PaperRecord]` (raw, từ `crossref.py`) + `run_date` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Hoàn thành |
| Evaluation test set | `src/evaluation/testset.py` — `build_test_set()` | Cleaned DataFrame | `data/eval/test_set.json` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------ | -------- |
| Fix conflict khi `git pull` do làm cùng lúc với commit chung của nhóm, giữ đúng file sở hữu từng người khi merge | Toàn nhóm | Repo hợp nhất sạch, không ghi đè công việc của Quang (`crossref.py`) hay Quân (`corruption.py`) |
| Kiểm tra tương thích schema giữa `cleaning.py` và `crossref.py`/`corruption.py` | Nguyễn Phú Quang, Nguyễn Đại Quân | Xác nhận DataFrame do `cleaning.py` sinh ra dùng đúng tên cột mà `index.py`, `quality.py`, `corruption.py` đang kỳ vọng |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------- | --------------- |
| Chuẩn hóa title/summary (kể cả strip markup), lọc record hỏng, parse `published`, tính `age_days`, dedupe theo `paper_id`, sinh `text_for_embedding` | `src/ingestion/cleaning.py::build_clean_dataframe` | 24/24 record thật giữ lại, `paper_id` unique | Chạy trên 24 raw record thật (`data/raw/crossref_records.json`), assert `paper_id` unique, `age_days >= 0`, không còn ký tự `<`/`>` trong title |
| Sinh câu hỏi loại `summary`/`authors`/`date`/`categories` kèm `ground_truth` lấy trực tiếp từ dữ liệu sạch, bỏ qua loại thiếu ground truth | `src/evaluation/testset.py::build_test_set` | `data/eval/test_set.json` — 72 câu hỏi | Chạy trên cleaned DataFrame thật, đối chiếu số lượng/cấu trúc với `data/eval/test_set.json` đang có trong repo — khớp 100% |

Output cụ thể: File `data/eval/test_set.json` chứa 72 câu hỏi (24 summary + 24 authors + 24 date) sinh trực tiếp từ 24 paper sạch, là input cho `evaluate_pipeline` (metrics.py) — mọi giá trị `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy` trong `data/results/*.json` đều được tính trên chính bộ câu hỏi này.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

`crossref.py` chỉ trả về `PaperRecord` thô (chưa chắc sạch, có thể lẫn record hỏng/markup). Phần của tôi phải biến dữ liệu thô đó thành (1) một DataFrame đáng tin cậy để embed, và (2) một bộ câu hỏi có `ground_truth` kiểm chứng được để đo chất lượng RAG một cách công bằng trên cả ba trạng thái baseline/corrupted/repaired.

### Cách triển khai

1. **Cleaning**: strip markup + chuẩn hóa whitespace cho `title`/`summary`; loại record thiếu `paper_id`/`title` hoặc `summary` < 20 ký tự; parse `published` bằng `datetime.fromisoformat`, loại record không parse được ngày.
2. **Derived fields**: nối `authors`/`categories` thành `authors_joined`/`categories_joined`; tính `age_days = (run_date - published_date).days`; build `text_for_embedding` theo template cố định (`Title/Authors/Categories/Published` + nội dung summary).
3. **Dedupe & sort**: loại trùng theo `paper_id` (giữ bản ghi đầu); sort theo `published` giảm dần để record mới nhất luôn ở đầu (phục vụ bước "drop latest" của corruption sau này).
4. **Test set**: với mỗi record sạch, sinh tối đa 4 loại câu hỏi; câu hỏi luôn chứa `title` trong dấu nháy đơn để khớp cơ chế exact-lookup bằng regex `r"'([^']+)'"` trong `qa.py`; `ground_truth` lấy nguyên văn từ cột tương ứng của chính record đó; nếu ground truth rỗng thì bỏ qua loại câu hỏi đó thay vì tạo câu hỏi không thể trả lời đúng.

### Input, output và contract

| Thành phần | Mô tả |
| ------------ | ------- |
| Input | `list[PaperRecord]` (paper_id, title, summary, authors, categories, published...) + `run_date`; DataFrame sạch cho `testset.py` |
| Output | DataFrame 16 cột (`paper_id`...`text_for_embedding`) ghi ra `data/clean/`; `list[dict]` (`id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`) ghi ra `data/eval/test_set.json` |
| Module phụ thuộc | `src/ingestion/crossref.py` (`PaperRecord`), `src/core/utils.py` (`normalize_whitespace`, `compact_join`, `first_sentence`, `write_json`) |
| Module sử dụng output | `src/retrieval/index.py` (build embedding documents từ `text_for_embedding`/metadata), `src/observability/quality.py` (freshness/quality dựa trên `age_days`/`published`), `src/evaluation/metrics.py` (`evaluate_pipeline` đọc `test_set.json`) |
| Điều kiện lỗi cần xử lý | Record thiếu DOI/title/ngày không parse được → loại khỏi clean dataset thay vì crash toàn pipeline; ground truth rỗng (vd. thiếu `subject`) → bỏ loại câu hỏi đó thay vì sinh câu hỏi không thể trả lời |

### Cách xác minh

```bash
python -c "
from datetime import UTC, datetime
from core.config import load_settings
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
from evaluation.testset import build_test_set

settings = load_settings()
records = load_raw_records(settings.paths.raw_records_json)
df = build_clean_dataframe(records, datetime.now(UTC))
print(len(df), df['paper_id'].is_unique)
samples = build_test_set(df, settings.paths.eval_testset)
print(len(samples))
"
```

- **Kết quả mong đợi:** giữ lại toàn bộ record hợp lệ, `paper_id` unique, sinh được test set có `ground_truth_doc_ids` tồn tại trong chính clean dataset.
- **Kết quả thực tế:** 24/24 record thật giữ lại (không mất record nào), `paper_id` unique; sinh 72 câu hỏi (summary/authors/date — không có categories vì 24/24 record Crossref thật thiếu trường `subject`, đã kiểm tra trực tiếp trên `data/raw/crossref_records.json`).
- **Artifact/log:** `data/clean/papers_clean.csv`, `data/clean/papers_clean.json`, `data/eval/test_set.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** `build_test_set` có thể luôn sinh đủ 4 câu hỏi/paper (kể cả khi `categories_joined` rỗng), hoặc chỉ sinh câu hỏi khi `ground_truth` thực sự tồn tại.
- **Các phương án đã cân nhắc:**
  1. Luôn sinh đủ 4 loại, chấp nhận `ground_truth=""` khi thiếu dữ liệu.
  2. Chỉ sinh câu hỏi khi `ground_truth` khác rỗng, bỏ qua loại thiếu dữ liệu cho record đó.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Nếu để `ground_truth` rỗng, agent bị chấm điểm trên một câu hỏi không thể trả lời đúng một cách chính đáng, làm sai lệch `retrieval_hit_rate`/`token_f1`/`judge_accuracy` — vi phạm nguyên tắc ground truth phải kiểm chứng được từ chính dữ liệu sạch. Đánh đổi là số câu hỏi không đều giữa các loại.
- **Bằng chứng quyết định phù hợp:** Trên 24 record Crossref thật, `categories` rỗng ở 24/24 record (Crossref không trả trường `subject` cho các bài này). Nếu không lọc, sẽ có 24 câu hỏi `ground_truth=""` gây nhiễu metric; sau khi lọc, test set chỉ còn 3 loại hợp lệ, tổng 72 câu — khớp chính xác với `data/eval/test_set.json` đang có trong repo.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Sau khi parse, title của một số paper còn sót thẻ markup ngay trong chuỗi, ví dụ: `Hi‐ <scp>RAG</scp> : A Hierarchical Retrieval‐Augmented Generation Framework...` (DOI `10.1111/exsy.70341`).
- **Lệnh hoặc bước tái hiện:** Chạy `build_clean_dataframe` trên raw records thật rồi in cột `title`, thấy thẻ `<scp>...</scp>` còn nguyên trong chuỗi.
- **Nguyên nhân gốc:** Crossref không chỉ nhúng tag JATS/HTML trong `abstract` mà đôi khi cả trong `title`. `crossref.py` chỉ strip tag cho `abstract`, không strip cho `title`; vì `cleaning.py` (phần của tôi) nhận `PaperRecord` đã parse làm input và trước đó chỉ gọi `normalize_whitespace` (chỉ gộp khoảng trắng, không bóc tag), title bẩn bị lan thẳng vào `text_for_embedding` và vào các câu hỏi trong `testset.py`.
- **Cách xử lý:** Thêm hàm `_strip_markup` (regex bóc tag `<[^>]+>` rồi `normalize_whitespace`) trong `cleaning.py`, áp dụng cho cả `title` và `summary` ngay tại lớp cleaning — không sửa `crossref.py` vì đó là file của Quang, cleaning chỉ nên tự phòng vệ với dữ liệu đầu vào thay vì giả định input đã sạch.
- **Cách xác minh sau khi sửa:** Chạy lại `build_clean_dataframe` trên toàn bộ 24 record thật, kiểm tra không còn ký tự `<`/`>` trong bất kỳ title nào (`df[df['title'].str.contains('<')]` rỗng).
- **Điều học được:** Dữ liệu từ API công khai như Crossref không đồng nhất format giữa các trường dù cùng một nguồn (title vs abstract); một module cleaning không nên tin tưởng hoàn toàn rằng input từ module trước đã sạch, mà phải tự chuẩn hóa lại trong phạm vi trách nhiệm của chính mình.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   `crossref.py` gọi Crossref API, lưu raw response + parse thành `PaperRecord` vào `data/raw/`. `cleaning.py` (phần của tôi) nhận list `PaperRecord`, strip markup, lọc record hỏng, tính `age_days`, build `text_for_embedding`, ghi DataFrame vào `data/clean/`. `retrieval/index.py` đọc DataFrame này, với mỗi dòng tạo một document (`record_id`, `paper_id`, `content=text_for_embedding`, `metadata`), encode `content` bằng `sentence-transformers/all-MiniLM-L6-v2` rồi nạp vào collection ChromaDB persist tại `data/chroma/`.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   `testset.py` (phần của tôi) sinh câu hỏi trực tiếp từ cleaned DataFrame — `ground_truth` lấy nguyên văn từ cột tương ứng của chính paper đó, `ground_truth_doc_ids = [paper_id của chính paper đó]`. Khi evaluate, hệ thống trả lời câu hỏi rồi so `retrieved_doc_ids` với `ground_truth_doc_ids` để tính `retrieval_hit_rate`, so `answer` với `ground_truth` để tính `token_f1` và LLM-judge `score`/`correct`. Vì ground truth sinh trực tiếp từ dữ liệu sạch (không tự bịa), metric phản ánh đúng khả năng thật của hệ thống trên corpus đã index.

3. **Quality checks khác freshness monitoring ở điểm nào?**
   Quality checks đo tính toàn vẹn/cấu trúc tại một thời điểm (row count, `paper_id` unique/not null, `title`/`summary` không rỗng). Freshness monitoring chỉ đo trục thời gian (`age_days`/`published` so với `freshness_threshold_days=180`). Một dataset có thể pass hết quality nhưng vẫn fail freshness (toàn bài cũ), hoặc ngược lại pass freshness nhưng fail quality (có duplicate).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Vì mục tiêu là đo ảnh hưởng của *dữ liệu* lên chất lượng agent, biến duy nhất được phép đổi là dữ liệu, không phải câu hỏi/ground truth. Nếu mỗi trạng thái dùng test set khác nhau, chênh lệch metric có thể đến từ độ khó câu hỏi khác nhau chứ không phải do corruption/repair, làm mất quan hệ nhân quả.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Khi `repaired_metrics.json` (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`) quay lại xấp xỉ/bằng `baseline_metrics.json` trên cùng test set, `repaired_quality.json.all_passed=true`, `repaired_freshness_report.json.status="FRESH"` giống baseline, và repair chạy lại từ raw source thật (`data/raw/`) chứ không sửa tay kết quả.

## 8. Phân tích kết quả

### Metrics chính

(Nguồn: `data/results/baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`, `data/quality/*.json` — artifact hiện có trong repo, chạy trên 24 paper Crossref thật, 72 câu hỏi do `testset.py` sinh ra.)

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ---------------------- |
| `retrieval_hit_rate` |     1.00 |      0.9167 |     1.00 | Giảm 8.33 điểm % khi corrupt (drop 2 records và các lỗi nội dung/metadata), phục hồi hoàn toàn sau repair. |
| `mean_token_f1`      |     1.00 |      0.8653 |     1.00 | Giảm khi summary bị blank/nhiễu và title bị truncate; repair khôi phục hoàn toàn. |
| `judge_accuracy`     |     1.00 |      0.8611 |     1.00 | 10/72 câu hỏi bị heuristic judge chấm không đúng sau corruption; repair đưa về baseline. |
| `mean_judge_score`   |     5.00 |      4.44 |     5.00 | Giảm ~0.56/5 điểm trung bình, phục hồi hoàn toàn sau repair. |
| Quality checks         | 5/5 Pass |  2/5 Pass | 5/5 Pass | Corrupted có 1 duplicate, 2 summary dưới 40 ký tự và 1 stale row; quality check bắt được lỗi độc lập với agent metric. |
| Freshness status       | `is_fresh=true` (0 stale/24) | `is_fresh=true` (1 stale/23) | `is_fresh=true` (0 stale/24) | `stale_date` đẩy 1 record về `2010-01-01`; `is_fresh` vẫn true vì record mới nhất còn trong ngưỡng 180 ngày. |

### Kết luận từ số liệu

1. **[Corruption: drop 2 records, blank/noisy summary, truncate title và metadata faults]** → **[`summary_min_length` fail với 2 rows, uniqueness fail với 1 duplicate, freshness fail với 1 stale row]** → **[`mean_token_f1` giảm 1.0→0.8653 và `judge_accuracy` giảm 1.0→0.8611]**.
2. **[Repair: chạy lại cleaning từ raw records gốc trong `data/raw/`, không sửa tay]** → **[`repaired_quality.json.all_passed=true`, `repaired_freshness_report.json.status="FRESH"` với 0 stale row, đúng bằng baseline]** → **[4 metric agent quay lại đúng giá trị baseline: 1.0/1.0/1.0/5.0]**.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**

`blank_summary` và `noise_injection` ảnh hưởng rõ nhất đến `mean_token_f1`/`judge_accuracy` vì `qa.py` trích câu trả lời trực tiếp từ `summary` cho loại câu hỏi `summary` — hỏng summary là hỏng thẳng câu trả lời. Ngược lại, `stale_date` đổi 1 record về `2010-01-01` nhưng không phải tín hiệu chính kéo retrieval xuống, vì semantic search dựa trên nội dung text chứ không dựa vào ngày xuất bản.

**Kết quả nào khác với kỳ vọng ban đầu?**

`is_fresh` vẫn là `true` dù có 1 stale row vì hàm freshness đánh giá tuổi của record mới nhất, không phải chỉ nhìn số rows cũ. Vì vậy cần đọc cả `stale_rows` lẫn `is_fresh`, thay vì coi cờ tổng thể FRESH là không có bất thường.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** Một hàm cleaning không nên tin tưởng tuyệt đối dữ liệu "đã sạch" từ module trước (`crossref.py`) — lỗi nhỏ như sót tag markup ở một trường có thể âm thầm lan sang mọi module phía sau (embedding, test set, report).
2. **Về data quality/observability:** Quality checks và freshness monitoring đo hai trục khác nhau (cấu trúc vs thời gian) và có thể lệch pha — cần đọc cả hai, không chỉ nhìn cờ pass/fail tổng, vì một dataset có thể pass cái này nhưng fail cái kia.
3. **Về ảnh hưởng của data đến RAG agent:** Không phải corruption nào cũng tác động như nhau lên agent: corruption phá trực tiếp nội dung text (blank/noise summary) ảnh hưởng agent rõ rệt hơn nhiều so với corruption phá metadata phụ (stale date), vì cách hệ thống này trả lời phụ thuộc trực tiếp vào nội dung text đã index.

### Nếu có thêm thời gian

Tôi sẽ thêm cơ chế sinh câu hỏi `categories` không phụ thuộc hoàn toàn vào trường `subject` của Crossref (vốn thường rỗng trong thực tế) — ví dụ để LLM gợi ý category tổng quát từ `summary` cho một tập nhỏ, rồi dùng chính giá trị đó làm `ground_truth`; đo cải thiện bằng số loại câu hỏi tăng từ 3 lên 4 mà vẫn giữ được ground truth kiểm chứng được.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Hữu Huy
**Ngày xác nhận:** 2026-08-06
