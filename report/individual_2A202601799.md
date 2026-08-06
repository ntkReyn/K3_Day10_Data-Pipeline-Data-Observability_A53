# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Bùi Đặng Quốc An |
| MSSV | 2A202601799 |
| Khóa/Lớp | K3 |
| Tên nhóm | Nhóm K3 — Data Pipeline & Data Observability |
| Vai trò chính | Vai trò 4 — Evaluation & observability |
| Repository | `K3_Day10_Data-Pipeline-Data-Observability_A53` |
| Ngày cập nhật | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Evaluation set | `src/evaluation/testset.py::build_test_set` | Clean DataFrame | `data/eval/test_set.json` | Hoàn thành |
| Scoring integration | `src/evaluation/metrics.py` | Index và test set | Metrics/answers JSON | Hoàn thành |
| Quality/freshness | `src/observability/quality.py` | Clean/corrupted/repaired DataFrame | Quality và freshness JSON | Hoàn thành |
| Reporting | `src/observability/reporting.py` | Metrics, quality, freshness | Phase 1 và comparison Markdown report | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Chốt question contract | Vai trò 2 và 3 | `ground_truth_doc_ids` lấy từ clean `paper_id`, không tự bịa ID. |
| Chốt evidence matrix | Vai trò 1 | Liệt kê metrics và artifacts phải có cho ba trạng thái. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Thiết kế test set | `testset.py` | Bốn question type: summary, authors, date, categories | Đối chiếu schema từng sample |
| Rà soát metrics | `metrics.py::evaluate_pipeline` | Retrieval hit rate, token F1, judge accuracy/score, answers artifacts | Đối chiếu baseline/corrupted/repaired JSON |
| Chốt monitoring signals | `quality.py` | Row count, null, duplicate, summary length, `age_days`, freshness dates | Đối chiếu quality/freshness JSON |
| Chốt report evidence | `reporting.py` | Bảng so sánh ba trạng thái | Đối chiếu artifacts trước khi viết kết luận |

Các artifact evaluation/quality/report chưa tồn tại ở thời điểm cập nhật.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Biến corpus và câu trả lời RAG thành bằng chứng định lượng, đồng thời phát hiện lỗi dữ liệu trước khi lỗi biến thành câu trả lời sai.

### Cách triển khai

Test set được tạo từ rows clean thật, mỗi câu có `id`, `question_type`, `question`, `ground_truth` và `ground_truth_doc_ids=[paper_id]`. Câu authors/date/categories dùng exact title trong dấu nháy đơn để QA hỗ trợ lookup ổn định. `evaluate_pipeline()` lưu cả summary và answers nên có thể trace metric về từng question. Quality checks phải kiểm tra row count, null/unique `paper_id`, title, độ dài summary và `age_days`; freshness report tổng hợp newest/oldest date, stale rows và `is_fresh`. Báo cáo chỉ kết luận từ JSON artifacts của cùng test set.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Clean/corrupted/repaired DataFrame, Chroma index, `paper_id`, settings threshold |
| Output | `data/eval/test_set.json`, `data/results/*_metrics.json`, `*_answers.json`, quality/freshness JSON, reports Markdown |
| Module phụ thuộc | `ingestion.cleaning`, `retrieval.index`, `retrieval.qa`, `evaluation.metrics` |
| Module sử dụng output | Pipelines, group/individual reports và người chấm |
| Điều kiện lỗi cần xử lý | Dataset quá ít, ID không tồn tại trong index, null date, metric không có samples, LLM judge unavailable |

### Cách xác minh

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** ba trạng thái dùng cùng `data/eval/test_set.json`; mỗi trạng thái có metrics, answers, quality/freshness; hai report có bảng comparison.
- **Kết quả thực tế:** tạo 8 samples từ clean corpus và dùng nguyên file đó cho ba trạng thái; đã tạo đủ metrics/answers, quality/freshness và Markdown reports.
- **Artifact/log:** `data/eval/test_set.json`, `data/results/*_metrics.json`, `data/results/*_answers.json`, `data/quality/*.json`, `data/reports/*.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** cần biết việc metrics thay đổi là do data corruption, không do thay câu hỏi.
- **Các phương án đã cân nhắc:** tạo test set mới ở mỗi trạng thái; dùng lại một test set từ clean baseline.
- **Phương án đã chọn:** giữ nguyên `data/eval/test_set.json` cho baseline, corrupted và repaired.
- **Lý do:** cùng câu hỏi, ground truth và document IDs tạo phép so sánh kiểm soát được.
- **Bằng chứng quyết định phù hợp:** `evaluate_pipeline()` nhận `test_set_path` tường minh; các metrics được tính từ các samples tương ứng.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `NotImplementedError: Student task: implement test set builder.`
- **Lệnh hoặc bước tái hiện:** gọi `build_test_set(df, output_path)`.
- **Nguyên nhân gốc:** starter chưa tạo evaluation data/observability reports.
- **Cách xử lý:** xác định schema test set và signals/report fields trước khi implement để không làm metrics lệch contract.
- **Cách xác minh sau khi sửa:** mọi `ground_truth_doc_ids` phải xuất hiện trong clean `paper_id`; kiểm tra metrics/answers reports sau cả hai script.
- **Điều học được:** metrics aggregate không đủ; answers artifact cần thiết để truy nguyên từng retrieval/answer failure.

## 7. Hiểu biết về luồng end-to-end

Crossref raw được làm sạch rồi index; test set lấy nội dung và ID từ clean corpus. Retrieval hit rate đo top-k có chứa đúng paper ID, token F1/judge đo answer. Quality kiểm tra tính đầy đủ/đúng/unique của dataset, freshness giám sát thời gian xuất bản và stale rows. Giữ nguyên test set giữa ba trạng thái mới chứng minh được corruption là nguyên nhân thay đổi. Repair thành công khi quality/freshness khôi phục và metrics được so sánh với baseline trên cùng questions.

## 8. Phân tích kết quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | 0.250 | 1.000 | `retrieved_doc_ids` mất sáu ground-truth IDs sau drop. |
| `mean_token_f1` | 1.000 | 0.408 | 1.000 | Answers corrupted lệch ground truth. |
| `judge_accuracy` | 1.000 | 0.375 | 1.000 | Gemini judge chấm đúng 3/8 sau corruption. |
| `mean_judge_score` | 5.000 | 2.625 | 5.000 | Recovery kiểm chứng bằng cùng test set. |
| Ragas: precision/recall/faithfulness | 0.750/0.750/0.750 | 0.125/0.125/0.262 | 0.750/0.750/0.750 | Ba Ragas metrics dùng chung 8 samples. |
| Quality checks | PASS | FAIL | PASS | Three checks fail ở corrupted state. |
| Freshness status | Fresh | Stale | Fresh | Threshold 180 ngày, stale rows 0/1/0. |

Corruption ảnh hưởng rõ nhất là drop sáu latest records: chúng khớp với sáu ground-truth IDs đầu của test set và làm retrieval hit rate giảm 75 điểm phần trăm. Duplicate, blank summary và stale date bị quality/freshness phát hiện; repair từ raw trả metrics và signals về baseline.

## 9. Điều học được và hướng cải thiện

1. Ground truth phải xuất phát từ data contract, không được tạo ID thủ công.
2. Quality và freshness là hai lớp tín hiệu khác nhau nhưng cùng cảnh báo risk cho RAG.
3. Reports tốt phải liên kết quality signal với answer-level evidence và metric aggregate.

Nếu có thêm thời gian, thêm trend/history freshness và visual chart so sánh ba trạng thái từ các JSON metrics.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo thành viên khác.

**Họ và tên:** Bùi Đặng Quốc An
**Ngày xác nhận:** 2026-08-06
