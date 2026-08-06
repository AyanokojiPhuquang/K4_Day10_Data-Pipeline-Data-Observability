# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Trần Tuấn Linh              |
| MSSV               | 2A202601612                 |
| Khóa/Lớp         | K4 – Lớp E402              |
| Tên nhóm         | TrickLord                  |
| Vai trò chính    | Observability               |
| Repository         | https://github.com/AyanokojiPhuquang/K4_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06                  |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------- |
| Data quality checks | `src/observability/quality.py::run_data_quality_checks` | Cleaned DataFrame (`paper_id`, `title`, `summary`, `age_days`...) + `Settings` + `report_name` | `data/quality/{report_name}.json` (5 check: row_count, paper_id_not_null_unique, title_not_null, summary_min_length, freshness_age_days) | Hoàn thành |
| Freshness monitoring | `src/observability/quality.py::build_freshness_report` | Cleaned DataFrame + `Settings` + `report_path` | JSON freshness report (`latest_published`, `oldest_published`, `stale_rows`, `is_fresh`) | Hoàn thành |
| Markdown reporting | `src/observability/reporting.py::generate_phase1_report`, `generate_corruption_report` | `metrics`/`quality`/`freshness` dict (baseline, corrupted, repaired) | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Đối chiếu `Settings`/`Paths` (`quality_dir`, `freshness_report`, `baseline_report`, `comparison_report`) trước khi code, để không tự đoán sai đường dẫn output | Toàn nhóm (đặc biệt Trần Kiên — Integration) | `quality.py`/`reporting.py` ghi đúng file, đúng thư mục mà `phase1.py`/`corruption_flow.py` kỳ vọng, không cần sửa lại đường dẫn khi ghép |
| Kiểm tra tương thích schema cleaned DataFrame giữa `cleaning.py` (Nguyễn Hữu Huy) và code của tôi | Nguyễn Hữu Huy | Xác nhận tên cột thật (`paper_id`, `title`, `summary`, `published`, `age_days`) khớp 100% với cột mà `quality.py` của tôi đọc, không cần đổi tên cột ở đâu cả |
| Phát hiện và xử lý xung đột với bản `quality.py`/`reporting.py` tạm thời mà Nguyễn Phú Quang đã commit trước để chạy thử pipeline | Nguyễn Phú Quang, Trần Kiên | Xác minh `phase1.py`/`corruption_flow.py` chỉ gọi hàm theo signature (không đọc cứng field JSON bên trong), nên thay thế bằng bản chính thức của tôi an toàn, không phá pipeline (chi tiết ở mục 6) |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Viết `run_data_quality_checks`: 5 check (row count, `paper_id` not-null + unique, `title` not-null, `summary` đủ độ dài tối thiểu 40 ký tự, freshness theo `age_days` so với ngưỡng 180 ngày) | `src/observability/quality.py` | `data/quality/baseline_quality.json`, `corrupted_quality.json`, `repaired_quality.json` | Chạy hàm trên 3 DataFrame thật (`papers_clean.csv`, `papers_clean_corrupted.csv`, `papers_clean_repaired.csv`) đang có trong repo, đối chiếu số check pass/fail với corruption log |
| Viết `build_freshness_report`: tìm `latest_published`/`oldest_published`, đếm `stale_rows`, xác định `is_fresh` dựa trên tuổi của record mới nhất so với ngưỡng | `src/observability/quality.py` | `data/quality/freshness_report.json`, `corrupted_freshness_report.json`, `repaired_freshness_report.json` | Chạy hàm trên cùng 3 DataFrame thật, so `stale_rows` với các record bị corruption `stale_date` (4 record) trong `corruption_log.json` |
| Viết `generate_phase1_report`, `generate_corruption_report`: gộp metrics + quality + freshness thành báo cáo markdown, có bảng so sánh baseline/corrupted/repaired kèm diễn giải impact/recovery | `src/observability/reporting.py` | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Chạy hai hàm với `baseline_metrics.json`/`corrupted_metrics.json`/`repaired_metrics.json` thật, mở file `.md` sinh ra kiểm tra đọc được, số liệu khớp input |

Output cụ thể: `data/quality/*.json` và `data/reports/*.md` là bằng chứng bắt buộc theo Rubric mục 7 (Data observability) và một phần mục 8 (Corruption và comparison) — nếu thiếu các file này, nhóm không có căn cứ để chứng minh corruption làm giảm chất lượng agent và repair phục hồi được chất lượng.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Sau khi `cleaning.py` (Huy) tạo ra cleaned DataFrame, không có gì đảm bảo dữ liệu đó vẫn "sạch" ở các bước tiếp theo, đặc biệt là sau khi bị corrupt có chủ đích ở Pha 2. Phần của tôi phải (1) tự động phát hiện các vấn đề dữ liệu — thiếu, trùng, rỗng, cũ — bằng số liệu thay vì cảm tính, và (2) trình bày kết quả cùng metrics của agent thành báo cáo markdown mà người không đọc code cũng hiểu được, để chứng minh quan hệ nhân quả giữa chất lượng dữ liệu và chất lượng agent.

### Cách triển khai

- **`quality.py`**: mỗi check trả về `{name, dimension, passed, details}` độc lập, không dừng sớm khi một check fail, để báo cáo được đầy đủ tất cả vấn đề trong một lần chạy. `row_count` chỉ cần > 0. `paper_id_not_null_unique` check cả null và duplicate cùng lúc. `title_not_null` check cả null và chuỗi rỗng sau khi strip. `summary_min_length` dùng ngưỡng tuyệt đối 40 ký tự thay vì tỷ lệ phần trăm, vì mục tiêu là bắt được từng record cụ thể bị hỏng (ví dụ do corruption `blank_summary`), không chỉ nhìn tổng quan. `freshness_age_days` so `age_days` của từng dòng với `settings.freshness_threshold_days` (180 ngày). `build_freshness_report` tách biệt hai khái niệm: `stale_rows` (đếm số dòng vượt ngưỡng, mang tính thống kê) và `is_fresh` (đánh giá dựa trên tuổi của record mới nhất — dataset vẫn coi là "fresh" nếu vẫn đang được cập nhật đều, dù có một số record cũ).
- **`reporting.py`**: tách các hàm helper `_metrics_table`, `_quality_table`, `_freshness_table` để dùng chung giữa `generate_phase1_report` và `generate_corruption_report`, tránh lặp code. `generate_corruption_report` tự tính cột "Change (Corrupted)" và "Recovery (Repaired)" bằng hiệu số so với baseline, để người đọc không phải tự trừ số trong đầu.

### Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
| Input | Cleaned DataFrame (`paper_id`, `title`, `summary`, `published`, `age_days`...) + `Settings`; `metrics`/`quality`/`freshness` dict cho `reporting.py` |
| Output | `data/quality/{report_name}.json`, freshness JSON tại `report_path` được truyền vào, `data/reports/phase1_report.md`, `data/reports/corruption_report.md` |
| Module phụ thuộc | `src/core/config.py` (`Settings.paths.quality_dir`, `freshness_threshold_days`), `src/core/utils.py` (`write_json`, `write_text`) |
| Module gọi đến output của tôi | `src/pipelines/phase1.py` (gọi cả 3 hàm cho baseline), `src/pipelines/corruption_flow.py` (gọi lại cho corrupted và repaired) |
| Điều kiện lỗi cần xử lý | DataFrame rỗng hoặc thiếu cột `published` → freshness report trả `is_fresh=False` thay vì crash; thiếu cột kỳ vọng (`paper_id`, `title`, `summary`, `age_days`) → check tương ứng trả `passed=False` kèm lý do trong `details`, không raise exception làm dừng cả pipeline |

### Cách xác minh

```bash
python -c "
import ast, pandas as pd
from core.config import load_settings
from core.utils import read_json
from observability.quality import run_data_quality_checks, build_freshness_report

settings = load_settings()
df = pd.read_csv(settings.paths.clean_csv)
quality = run_data_quality_checks(df, settings, 'baseline_quality')
freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
print(quality['passed_checks'], '/', quality['total_checks'])
print(freshness['is_fresh'], freshness['stale_rows'])
"
```

- **Kết quả mong đợi:** trên dữ liệu baseline sạch, cả 5 check pass, `is_fresh=True`, `stale_rows=0`.
- **Kết quả thực tế:** chạy trên `data/clean/papers_clean.csv` thật (24 record), 5/5 check pass, `is_fresh=True`, `stale_rows=0` — khớp với `data/quality/freshness_report.json` đang có trong repo.
- **Artifact/log:** `data/quality/baseline_quality.json`, `data/quality/freshness_report.json`, `data/reports/phase1_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Check "summary có hợp lệ không" có thể triển khai theo hai hướng: (1) tính tỷ lệ phần trăm record có summary không rỗng trên toàn dataset, pass nếu tỷ lệ đủ cao (ví dụ ≥ 80%); (2) đặt ngưỡng độ dài tối thiểu tuyệt đối cho từng dòng, pass toàn bộ check chỉ khi không còn dòng nào dưới ngưỡng.
- **Các phương án đã cân nhắc:** (1) Check theo tỷ lệ phần trăm toàn dataset — đây cũng là cách một bản `quality.py` tạm thời khác trong nhóm đã làm trước khi tôi hoàn thành phần của mình. (2) Check theo ngưỡng tuyệt đối trên từng dòng.
- **Phương án đã chọn:** (2).
- **Lý do:** Mục tiêu của observability là phát hiện sớm và chỉ đích danh vấn đề, không chỉ báo cáo sức khỏe tổng quan. Lần chạy cuối tạo 2 rows có summary ngắn hơn 40 ký tự sau corruption; check tuyệt đối theo từng dòng làm `summary_min_length` fail thay vì để lỗi nội dung bị che bởi một tỷ lệ tổng thể.
- **Bằng chứng quyết định phù hợp:** Lần chạy mới tạo `data/clean/papers_clean_corrupted.csv` với 23 rows. `summary_min_length` trả `too_short_count=2`, `passed=False`; dữ liệu hỏng được gắn cờ rõ ràng thay vì bị tỷ lệ tổng thể che khuất. Tương tự, `freshness_age_days` fail với `stale_count=1` vì corruption đưa một record về năm 2010; check có thể chỉ đích danh lỗi ở artifact thực tế.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Sau khi `git pull`, phát hiện `src/observability/quality.py` và `reporting.py` trên repo **đã có code** (không còn là `TODO(student)`/`NotImplementedError` như bản starter ban đầu), và `data/quality/*.json` đã có artifact thật.
- **Lệnh hoặc bước tái hiện:** `git log --oneline -- src/observability/quality.py` cho thấy commit `"Quang task + report"` đã sửa cả hai file này.
- **Nguyên nhân gốc:** Bạn Nguyễn Phú Quang (Source Ingestion) cần chạy thử `phase1.py`/`corruption_flow.py` để kiểm tra phần `crossref.py` của mình trước khi tôi hoàn thành phần Observability, nên đã tự viết một bản `quality.py`/`reporting.py` tạm để pipeline không bị chặn ở bước gọi hàm của tôi.
- **Cách xử lý:** Đọc kỹ `src/pipelines/phase1.py` và `corruption_flow.py` để xác nhận cả hai file chỉ gọi hàm của tôi theo đúng chữ ký (`run_data_quality_checks(df, settings, report_name)`, `build_freshness_report(df, settings, report_path)`, `generate_phase1_report(...)`, `generate_corruption_report(...)`) và chỉ truyền tiếp `dict` trả về cho hàm khác, không có module nào đọc cứng tên field bên trong JSON. Vì vậy tôi thay thế toàn bộ nội dung hai file bằng bản chính thức của mình mà không phá vỡ phần tích hợp đã có, chỉ cần giữ đúng tên hàm và tham số.
- **Cách xác minh sau khi sửa:** Chạy lại `run_data_quality_checks`/`build_freshness_report`/`generate_phase1_report`/`generate_corruption_report` trên baseline/corrupted/repaired data vừa sinh. `corrupted_quality.json` ghi `duplicate_count=1`, `too_short_count=2`, `stale_count=1`; các giá trị này khớp corruption log và report mới, xác nhận implementation hoạt động trên dữ liệu thật của nhóm.

**Điều học được:** Trong dự án nhóm chạy song song nhiều nhánh, một thành viên có thể tạm thời "che" một phần việc chưa xong của người khác để không bị chặn tiến độ — trước khi thay thế bằng bản chính thức, cần kiểm tra hợp đồng giao tiếp giữa các module (ở đây là chữ ký hàm) thay vì chỉ giả định bản của mình luôn an toàn để ghi đè.

## 7. Hiểu biết về luồng end-to-end

1. **Vì sao Observability phải chạy sau Embedding/Evaluation trong luồng, không chạy song song hoàn toàn độc lập?** `run_data_quality_checks`/`build_freshness_report` chỉ cần cleaned DataFrame nên có thể chạy ngay sau `cleaning.py`, nhưng `generate_phase1_report`/`generate_corruption_report` cần `metrics` từ `evaluate_pipeline` (metrics.py) để ghép vào report, nên về mặt orchestration trong `phase1.py`, quality/freshness và report vẫn phải đợi bước evaluate chạy xong trước.
2. **Data quality và freshness đo hai trục khác nhau như thế nào?** Quality đo tính toàn vẹn/cấu trúc tại một thời điểm (`paper_id` unique, `title`/`summary` không rỗng). Freshness chỉ đo trục thời gian (`age_days`/`published` so với ngưỡng 180 ngày). Một dataset có thể pass hết quality nhưng fail freshness (toàn bài cũ nhưng sạch), hoặc ngược lại — cần đọc cả hai báo cáo, không chỉ nhìn một cờ tổng.
3. **Vì sao `is_fresh` và `stale_rows` trong `build_freshness_report` không phải lúc nào cũng "đi cùng chiều"?** `stale_rows` đếm số dòng cụ thể vượt ngưỡng — mang tính thống kê chi tiết. `is_fresh` chỉ nhìn vào record mới nhất — trả lời câu hỏi "dataset có đang được cập nhật không". Trên dữ liệu corrupted vừa chạy, `stale_rows=1` nhưng `is_fresh=True`, vì record mới nhất (`2026-08-01`) vẫn còn trong ngưỡng 180 ngày dù một record bị corruption đẩy về `2010-01-01`.
4. **Report markdown của tôi dùng để làm gì trong việc chứng minh corruption có tác động?** `generate_corruption_report` không tự kết luận corruption "có tác động", nó chỉ trình bày đúng số liệu baseline/corrupted/repaired cạnh nhau kèm cột chênh lệch, để người đọc (hoặc giảng viên) tự đối chiếu — trách nhiệm diễn giải nhân quả vẫn thuộc về phần phân tích trong report cá nhân/nhóm, không phải do code tự "phán".
5. **Vì sao repair phải chạy lại `run_data_quality_checks`/`build_freshness_report` thay vì chỉ tin baseline?** Vì repair trong `corruption_flow.py` build lại DataFrame từ `raw_records_json` gốc bằng `build_clean_dataframe`, không phải phục hồi thủ công từ dữ liệu corrupted — nên cần chạy lại quality/freshness độc lập để có bằng chứng khách quan rằng dữ liệu đã thực sự sạch trở lại, không chỉ giả định "repair thì chắc chắn ổn".

## 8. Phân tích kết quả

### Metrics chính

(Nguồn: `data/results/baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json` — artifact có sẵn trong repo; `data/quality/*.json`, `data/quality/*freshness_report.json` — do tôi chạy lại trực tiếp bằng code chính thức của mình trên `data/clean/papers_clean*.csv` thật để xác nhận số liệu, trên 24 paper Crossref thật, 72 câu hỏi.)

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 1.0 | 0.9167 | 1.0 | Giảm 8.33 điểm % khi corrupt, phục hồi hoàn toàn sau repair. |
| `mean_token_f1` | 1.0 | 0.8653 | 1.0 | Giảm khi summary/title bị corruption; `summary_min_length` bắt được 2 rows ngắn hơn 40 ký tự. |
| `judge_accuracy` | 1.0 | 0.8611 | 1.0 | 10/72 câu hỏi bị heuristic judge chấm không đúng sau corrupt, sau repair quay về baseline. |
| `mean_judge_score` | 5.0 | 4.4444 | 5.0 | Giảm ~0.56/5 điểm trung bình, phục hồi hoàn toàn sau repair. |
| Quality checks (của tôi) | 5/5 pass, `all_passed=true` | 2/5 pass, `all_passed=false` (`duplicate_count=1`; `summary_min_length` fail với `too_short_count=2`; `freshness_age_days` fail với `stale_count=1`) | 5/5 pass, `all_passed=true` | Check fail đúng 3/5 tiêu chí trên corrupted, khớp các corruption tác động trực tiếp lên uniqueness, summary và freshness. |
| Freshness status (của tôi) | `is_fresh=true`, `stale_rows=0/24` | `is_fresh=true`, `stale_rows=1/23` | `is_fresh=true`, `stale_rows=0/24` | `stale_date` đẩy 1 record về `2010-01-01`; `is_fresh` vẫn true vì record mới nhất (`2026-08-01`) chưa vượt ngưỡng. |

### Kết luận từ số liệu

1. **[Corruption: duplicate row, blank/noisy summary và stale date]** → **[Quality checks của tôi tụt từ 5/5 xuống 2/5 pass, với `duplicate_count=1`, `too_short_count=2`, `stale_count=1`]** → **[Đồng thời `mean_token_f1` giảm 1.0→0.8653 và `judge_accuracy` giảm 1.0→0.8611]**.
2. **[Repair: `corruption_flow.py` build lại DataFrame từ `raw_records_json` gốc bằng `build_clean_dataframe`, không sửa tay]** → **[Quality checks của tôi quay lại 5/5 pass, freshness quay lại `stale_rows=0/24`, đúng bằng baseline]** → **[4 metric agent quay lại đúng giá trị baseline: 1.0/1.0/1.0/5.0]**.

**Corruption nào ảnh hưởng rõ nhất và vì sao?** `blank_summary`/noise injection ảnh hưởng rõ nhất, vì chúng làm `summary_min_length` fail ở 2 rows và trực tiếp phá nội dung mà `qa.py` dùng để trả lời. Ngược lại, `stale_date` bị `freshness_age_days` bắt được (`stale_count=1`) nhưng không phải nguyên nhân chính kéo retrieval xuống, vì semantic search dựa trên nội dung text chứ không dựa vào ngày xuất bản.

**Kết quả nào khác kỳ vọng ban đầu?** `is_fresh` vẫn `true` dù `stale_rows` tăng từ 0 lên 1/23, vì tôi thiết kế `is_fresh` dựa trên tuổi của record mới nhất chứ không phải số record stale. Đây là lý do report phải trình bày cả `stale_rows` lẫn `is_fresh` cạnh nhau.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Cách chọn ngưỡng cho một quality check (theo tỷ lệ phần trăm hay theo từng dòng tuyệt đối) quyết định trực tiếp việc check đó có "nhìn thấy" một corruption cụ thể hay không — ngưỡng lỏng có thể khiến report báo "ổn" trong khi dữ liệu đã hỏng thật.
2. Freshness không phải một khái niệm duy nhất: "tổng thể có đang được cập nhật không" (`is_fresh`) và "có bao nhiêu record cụ thể đã cũ" (`stale_rows`) là hai câu hỏi khác nhau, cần báo cáo cả hai để tránh gây hiểu lầm.
3. Khi làm việc nhóm song song, cần kiểm tra hợp đồng giao tiếp (chữ ký hàm, không phải nội dung code) trước khi thay thế một bản code tạm thời của người khác, để không phá phần tích hợp mà nhóm đã dựa vào để chạy thử các phần khác.

### Nếu có thêm thời gian

Tôi sẽ thêm một check "duplicate content" dựa trên `text_for_embedding` (không chỉ `paper_id`), vì hiện tại nếu một corruption tạo ra hai `paper_id` khác nhau nhưng nội dung giống hệt nhau, check `paper_id_not_null_unique` của tôi sẽ không phát hiện được — đo cải thiện bằng cách tạo thêm một corruption giả lập "duplicate nội dung nhưng đổi ID" và xác nhận check mới bắt được trường hợp này.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Tuấn Linh
**Ngày xác nhận:** 2026-08-06
