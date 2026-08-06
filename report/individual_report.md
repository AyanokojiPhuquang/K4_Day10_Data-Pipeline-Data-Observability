# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Hữu Huy             |
| MSSV               | 2A202601220                 |
| Khóa/Lớp         | K4 – Lớp E402              |
| Tên nhóm         | TrickLord                  |
| Vai trò chính    | Cleaning & Test set        |
| Repository         | https://github.com/AyanokojiPhuquang/K4_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06                  |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------- |
| Cleaning pipeline | `src/ingestion/cleaning.py::build_clean_dataframe` | `list[PaperRecord]` (raw, từ `crossref.py`) + `run_date` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` (DataFrame 24 dòng, có `text_for_embedding`, `age_days`) | Hoàn thành |
| Evaluation test set | `src/evaluation/testset.py::build_test_set` | Cleaned DataFrame | `data/eval/test_set.json` (bộ câu hỏi kèm ground truth) | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Cài đặt môi trường Python 3.11 (venv), fix conflict khi `git pull` do làm cùng lúc với commit chung của nhóm | Toàn nhóm | Repo build lại sạch từ `pyproject.toml`; giữ đúng file sở hữu của từng người, không ghi đè công việc của Quang (`crossref.py`) hay Quân (`corruption.py`) |
| Kiểm tra tương thích schema giữa `cleaning.py` và `crossref.py` (Quang) / `corruption.py` (Quân) | Nguyễn Phú Quang, Nguyễn Đại Quân | Xác nhận DataFrame do `cleaning.py` sinh ra dùng đúng tên cột mà `index.py`, `quality.py`, `corruption.py` đang kỳ vọng (`paper_id`, `authors_joined`, `categories_joined`, `text_for_embedding`...) |
| Phát hiện lỗi title dính thẻ markup từ Crossref (`<scp>RAG</scp>`) | Ảnh hưởng chung tới embedding/agent | Thêm bước strip markup phòng vệ trong `cleaning.py` (chi tiết ở mục 6) |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Viết `build_clean_dataframe`: chuẩn hóa title/summary (kể cả strip markup), lọc record hỏng, parse `published`, tính `age_days`, dedupe theo `paper_id`, sinh `text_for_embedding` | `src/ingestion/cleaning.py` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` — 24/24 record thật giữ lại, `paper_id` unique | Chạy `build_clean_dataframe` trên 24 raw record thật (`data/raw/crossref_records.json`), assert `paper_id` unique, `age_days >= 0`, không còn ký tự `<`/`>` trong title |
| Viết `build_test_set`: sinh câu hỏi loại `summary`/`authors`/`date`/`categories` kèm `ground_truth` lấy trực tiếp từ dữ liệu sạch, bỏ qua loại thiếu ground truth | `src/evaluation/testset.py` | `data/eval/test_set.json` — 72 câu hỏi (24 summary + 24 authors + 24 date; không có `categories` vì Crossref thật thiếu trường `subject`) | Chạy `build_test_set` trên cleaned DataFrame thật, đối chiếu số lượng và cấu trúc với `data/eval/test_set.json` đang có trong repo — khớp 100% |

Output cụ thể: `data/eval/test_set.json` là input trực tiếp cho `evaluate_pipeline` (metrics.py) — mọi giá trị `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy` trong `data/results/*.json` đều được tính trên đúng 72 câu hỏi do hàm `build_test_set` của tôi sinh ra.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

`crossref.py` chỉ trả về `PaperRecord` thô (chưa chắc sạch, có thể lẫn record hỏng/markup). Phần của tôi phải biến dữ liệu thô đó thành (1) một DataFrame đáng tin cậy để embed, và (2) một bộ câu hỏi có `ground_truth` kiểm chứng được để đo chất lượng RAG một cách công bằng trên cả ba trạng thái baseline/corrupted/repaired.

### Cách triển khai

- **`cleaning.py`**: strip markup + chuẩn hóa whitespace cho `title`/`summary`; loại record thiếu `paper_id`/`title` hoặc `summary` < 20 ký tự; parse `published` bằng `datetime.fromisoformat`, loại record không parse được ngày; nối `authors`/`categories` thành `authors_joined`/`categories_joined`; tính `age_days = (run_date - published_date).days`; dedupe theo `paper_id` (giữ bản ghi đầu); build `text_for_embedding` theo template cố định (`Title/Authors/Categories/Published` + nội dung summary); sort theo `published` giảm dần (phục vụ bước "drop latest" của corruption sau này).
- **`testset.py`**: với mỗi record sạch, sinh tối đa 4 loại câu hỏi; câu hỏi luôn chứa `title` trong dấu nháy đơn để khớp cơ chế exact-lookup bằng regex `r"'([^']+)'"` trong `qa.py`; `ground_truth` lấy nguyên văn từ cột tương ứng của chính record đó (`first_sentence(summary)`, `authors_joined`, `published`, `categories_joined`); nếu ground truth rỗng thì bỏ qua loại câu hỏi đó thay vì tạo câu hỏi không thể trả lời đúng.

### Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
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
- **Các phương án đã cân nhắc:** (1) Luôn sinh đủ 4 loại, chấp nhận `ground_truth=""` khi thiếu dữ liệu; (2) Chỉ sinh câu hỏi khi `ground_truth` khác rỗng, bỏ qua loại thiếu dữ liệu cho record đó.
- **Phương án đã chọn:** (2).
- **Lý do:** Nếu để `ground_truth` rỗng, agent bị chấm điểm trên một câu hỏi không thể trả lời đúng một cách chính đáng, làm sai lệch `retrieval_hit_rate`/`token_f1`/`judge_accuracy` — vi phạm nguyên tắc ground truth phải kiểm chứng được từ chính dữ liệu sạch. Đánh đổi là số câu hỏi không đều giữa các loại.
- **Bằng chứng quyết định phù hợp:** Trên 24 record Crossref thật, `categories` rỗng ở 24/24 record (Crossref không trả trường `subject` cho các bài này). Nếu không lọc, sẽ có 24 câu hỏi `ground_truth=""` gây nhiễu metric; sau khi lọc, test set chỉ còn 3 loại hợp lệ, tổng 72 câu — khớp chính xác với `data/eval/test_set.json` đang có trong repo.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Sau khi parse, title của một số paper còn sót thẻ markup ngay trong chuỗi, ví dụ: `Hi‐ <scp>RAG</scp> : A Hierarchical Retrieval‐Augmented Generation Framework...` (DOI `10.1111/exsy.70341`).
- **Lệnh hoặc bước tái hiện:** Chạy `build_clean_dataframe` trên raw records thật rồi in cột `title`, thấy thẻ `<scp>...</scp>` còn nguyên trong chuỗi.
- **Nguyên nhân gốc:** Crossref không chỉ nhúng tag JATS/HTML trong `abstract` mà đôi khi cả trong `title`. `crossref.py` chỉ strip tag cho `abstract`, không strip cho `title`; vì `cleaning.py` (phần của tôi) nhận `PaperRecord` đã parse làm input và trước đó chỉ gọi `normalize_whitespace` (chỉ gộp khoảng trắng, không bóc tag), title bẩn bị lan thẳng vào `text_for_embedding` và vào câu hỏi loại `summary`/`authors`/... trong `testset.py`.
- **Cách xử lý:** Thêm hàm `_strip_markup` (regex bóc tag `<[^>]+>` rồi `normalize_whitespace`) trong `cleaning.py`, áp dụng cho cả `title` và `summary` ngay tại lớp cleaning — không sửa `crossref.py` vì đó là file của Quang, cleaning chỉ nên tự phòng vệ với dữ liệu đầu vào thay vì giả định input đã sạch.
- **Cách xác minh sau khi sửa:** Chạy lại `build_clean_dataframe` trên toàn bộ 24 record thật, kiểm tra không còn ký tự `<`/`>` trong bất kỳ title nào (`df[df['title'].str.contains('<')]` rỗng).

**Điều học được:** Dữ liệu từ API công khai như Crossref không đồng nhất format giữa các trường dù cùng một nguồn (title vs abstract); một module cleaning không nên tin tưởng hoàn toàn rằng input từ module trước đã sạch, mà phải tự chuẩn hóa lại trong phạm vi trách nhiệm của chính mình.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** `crossref.py` gọi Crossref API, lưu raw response + parse thành `PaperRecord` vào `data/raw/`. `cleaning.py` (phần của tôi) nhận list `PaperRecord`, strip markup, lọc record hỏng, tính `age_days`, build `text_for_embedding`, ghi DataFrame vào `data/clean/`. `retrieval/index.py` đọc DataFrame này, với mỗi dòng tạo một document (`record_id`, `paper_id`, `content=text_for_embedding`, `metadata`), encode `content` bằng MiniLM rồi nạp vào collection ChromaDB persist tại `data/chroma/`.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?** `testset.py` (phần của tôi) sinh câu hỏi trực tiếp từ cleaned DataFrame — `ground_truth` lấy nguyên văn từ cột tương ứng của chính paper đó, `ground_truth_doc_ids = [paper_id của chính paper đó]`. Khi evaluate, so `retrieved_doc_ids` với `ground_truth_doc_ids` để tính `retrieval_hit_rate`, so `answer` với `ground_truth` để tính `token_f1`/`judge_score`. Vì ground truth sinh trực tiếp từ dữ liệu sạch (không tự bịa), metric phản ánh đúng khả năng thật của hệ thống trên corpus đã index.
3. **Quality checks khác freshness monitoring ở điểm nào?** Quality checks đo tính toàn vẹn/cấu trúc tại một thời điểm (row count, `paper_id` unique/not null, `title`/`summary` không rỗng). Freshness monitoring chỉ đo trục thời gian (`age_days`/`published` so với `freshness_threshold_days=180`). Một dataset có thể pass hết quality nhưng vẫn có thể fail freshness (toàn bài cũ), hoặc ngược lại pass freshness nhưng fail quality (có duplicate).
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Vì mục tiêu là đo ảnh hưởng của *dữ liệu* lên chất lượng agent, biến duy nhất được phép đổi là dữ liệu, không phải câu hỏi/ground truth. Nếu mỗi trạng thái dùng test set khác nhau, chênh lệch metric có thể đến từ độ khó câu hỏi khác nhau chứ không phải do corruption/repair, làm mất quan hệ nhân quả.
5. **Repair được xem là thành công dựa trên artifact và metric nào?** Khi `repaired_metrics.json` (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`) quay lại xấp xỉ/bằng `baseline_metrics.json` trên cùng test set, `repaired_quality.json.all_passed=true`, `repaired_freshness_report.json.status="FRESH"` giống baseline, và repair chạy lại từ raw source thật (`data/raw/`) chứ không sửa tay kết quả.

## 8. Phân tích kết quả

### Metrics chính

(Nguồn: `data/results/baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`, `data/quality/*.json`, `data/quality/*freshness_report.json` — artifact hiện có trong repo, chạy trên 24 paper Crossref thật, 72 câu hỏi.)

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 1.0 | 0.875 | 1.0 | Giảm 12.5 điểm % khi corrupt (drop 3 record mới nhất + 3 duplicate làm nhiễu top-k), phục hồi hoàn toàn sau repair. |
| `mean_token_f1` | 1.0 | 0.6975 | 1.0 | Giảm mạnh nhất — hợp lý vì `blank_summary` (4 record) và `noise_injection` (3 record) phá trực tiếp nội dung mà `qa.py` dùng để trả lời. |
| `judge_accuracy` | 1.0 | 0.6806 | 1.0 | ~32% câu hỏi bị LLM-judge chấm sai sau corrupt, khớp với các record bị hỏng nội dung (blank/noise summary, truncate title). |
| `mean_judge_score` | 5.0 | 3.72 | 5.0 | Giảm ~1.28/5 điểm trung bình, phục hồi hoàn toàn sau repair. |
| Quality checks | `all_passed=true` | `all_passed=false` (`paper_id` unique 21/24) | `all_passed=true` | Corruption `duplicate_row` (3 dòng) làm fail check uniqueness dù agent vẫn trả lời được — quality check bắt được lỗi mà agent metric không lộ rõ. |
| Freshness status | FRESH (0 stale/24) | FRESH nhưng `stale_rows=4/24` | FRESH (0 stale/24) | `stale_date` đẩy 4 record về `2020-01-01`; vẫn qua ngưỡng "≥50% fresh" nên status tổng thể không đổi — ngưỡng hiện tại chưa đủ nhạy với mức corruption này. |

### Kết luận từ số liệu

1. **[Corruption `blank_summary`(4) + `noise_injection`(3) + `truncate_title`(3)]** → **[`summary_not_empty` tụt còn 83.33%, nội dung `text_for_embedding` của các record này bị rỗng/nhiễu]** → **[`mean_token_f1` giảm 1.0→0.6975 và `judge_accuracy` giảm 1.0→0.6806, vì `qa.py` trích câu trả lời trực tiếp từ `summary` đã hỏng]**.
2. **[Repair: chạy lại cleaning từ raw records gốc trong `data/raw/`, không sửa tay]** → **[`repaired_quality.json.all_passed=true`, `repaired_freshness_report.json.status="FRESH"` với 0 stale row, đúng bằng baseline]** → **[4 metric agent quay lại đúng giá trị baseline: 1.0/1.0/1.0/5.0]**.

**Corruption nào ảnh hưởng rõ nhất và vì sao?** `blank_summary` và `noise_injection` ảnh hưởng rõ nhất đến `mean_token_f1`/`judge_accuracy` vì `qa.py` trích câu trả lời trực tiếp từ `summary` cho loại câu hỏi `summary` — hỏng summary là hỏng thẳng câu trả lời. Ngược lại, `stale_date` đổi 4 record về `2020-01-01` nhưng gần như không kéo `retrieval_hit_rate`/`judge_accuracy` xuống, vì semantic search dựa trên nội dung text chứ không dựa vào ngày xuất bản.

**Kết quả nào khác kỳ vọng ban đầu?** Tôi kỳ vọng freshness status sẽ chuyển "STALE" sau khi 4/24 record (~16.7%) bị đẩy về năm 2020, nhưng ngưỡng check trong dataset là "≥50% record trong hạn" nên status vẫn "FRESH". Giả thuyết "freshness sẽ tự phát hiện corruption stale_date" không đúng ở mức độ corruption này — cần đọc kỹ ngưỡng thay vì chỉ nhìn cờ pass/fail tổng, và đây là điểm nhóm có thể cân nhắc siết ngưỡng nếu muốn freshness nhạy hơn.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Một hàm cleaning không nên tin tưởng tuyệt đối dữ liệu "đã sạch" từ module trước (`crossref.py`) — lỗi nhỏ như sót tag markup ở một trường có thể âm thầm lan sang mọi module phía sau (embedding, test set, report).
2. Quality checks và freshness monitoring đo hai trục khác nhau (cấu trúc vs thời gian) và có thể lệch pha — cần đọc cả hai, không chỉ nhìn cờ pass/fail tổng, vì một dataset có thể pass cái này nhưng fail cái kia.
3. Không phải corruption nào cũng tác động như nhau lên agent: corruption phá trực tiếp nội dung text (blank/noise summary) ảnh hưởng agent rõ rệt hơn nhiều so với corruption phá metadata phụ (stale date), vì cách hệ thống này trả lời phụ thuộc trực tiếp vào nội dung text đã index.

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
