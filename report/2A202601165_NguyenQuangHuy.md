# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Quang Huy |
| MSSV | 2A202601165 |
| Khóa/Lớp | K3 |
| Tên nhóm | Nhóm K3 — Data Pipeline & Data Observability |
| Vai trò chính | Vai trò 2 — Nền tảng dữ liệu & recovery |
| Repository | `K3_Day10_Data-Pipeline-Data-Observability_A53` |
| Ngày cập nhật | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Crossref ingestion | `src/ingestion/crossref.py` | Crossref REST payload, `Settings` | Raw response, raw records `PaperRecord` | Hoàn thành |
| Cleaning/data model | `src/ingestion/cleaning.py` | `list[PaperRecord]`, run date | Clean DataFrame, CSV/JSON và embedding text | Hoàn thành |
| Corruption/repair input | `src/ingestion/corruption.py` | Clean DataFrame | Corrupted DataFrame và corruption log | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Chốt document identity | Vai trò 3 và 4 | `paper_id` lấy từ DOI Crossref, normalize `strip().lower()`. |
| Bàn giao schema clean | Vai trò 1, 3, 4 | Cột bắt buộc cho index, test set, quality đã được xác định. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Phân tích raw contract | `PaperRecord` trong `crossref.py` | 11 trường raw nhất quán | Kiểm tra dataclass và payload `message.items` |
| Chốt clean contract | `cleaning.py` | Cột raw + `authors_joined`, `categories_joined`, `summary_chars`, `age_days`, `text_for_embedding` | Kiểm tra DataFrame trước index |
| Lập kế hoạch recovery | `corruption.py`, raw records JSON | Repair rebuild từ raw thay vì sửa corrupted CSV | So sánh repaired dataset với output cleaning từ raw |

Đã tạo `data/raw/crossref_response.json`, `crossref_records.json`, baseline/corrupted/repaired CSV/JSON. Baseline có 24 records; corruption output có 19 rows và repair khôi phục 24 rows.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Chuyển Crossref payload không đồng nhất thành dữ liệu có định danh ổn định, đủ sạch để retrieval và vẫn có raw evidence phục vụ recovery.

### Cách triển khai

`parse_crossref_payload()` sẽ duyệt `payload["message"]["items"]`, trích DOI, title, abstract, authors, subject, dates và URLs vào `PaperRecord`. DOI là `paper_id` vì ổn định hơn title. `fetch_source_records()` lưu nguyên payload trước parse, dùng params từ `Settings` và retry/backoff cho 429/503. Cleaning chuẩn hóa whitespace, list authors/categories, parse ngày, bỏ record không có DOI/title/summary, deduplicate theo `paper_id`, rồi tạo `text_for_embedding` từ title, summary, authors và categories. `age_days` được tính từ `run_date` và `published`.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Crossref payload, `Settings.source_query`, `source_filter`, `max_results`, `list[PaperRecord]` |
| Output | `data/raw/crossref_response.json`, `data/raw/crossref_records.json`, `data/clean/papers_clean.csv/json` |
| Module phụ thuộc | `core.config`, `core.utils`, Crossref REST API |
| Module sử dụng output | `retrieval.index`, `evaluation.testset`, `observability.quality`, pipelines |
| Điều kiện lỗi cần xử lý | 429/503, DOI/title/abstract thiếu, date không parse được, duplicate DOI |

### Cách xác minh

```bash
python script/run_phase1.py
```

- **Kết quả mong đợi:** raw JSON và cleaned CSV/JSON xuất hiện; `paper_id` unique, `text_for_embedding` không rỗng.
- **Kết quả thực tế:** fetch/parse được 24 records hợp lệ; clean dataset có `paper_id` unique, summary/embedding text không blank và không có stale row.
- **Artifact/log:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json`, `data/clean/papers_clean.*`, `data/results/corruption_log.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** cần chọn ID vừa dùng cho deduplicate vừa làm ground truth retrieval.
- **Các phương án đã cân nhắc:** slug từ title; DOI từ Crossref.
- **Phương án đã chọn:** DOI normalize làm `paper_id`.
- **Lý do:** title có thể trùng/biến thể, còn DOI là identity công bố học thuật và có trong source.
- **Bằng chứng quyết định phù hợp:** `LocalEmbeddingIndex` và evaluation dùng `paper_id` làm document identity.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `NotImplementedError: Student task: implement Crossref payload parsing.`
- **Lệnh hoặc bước tái hiện:** gọi `parse_crossref_payload({})`.
- **Nguyên nhân gốc:** starter cố ý chưa cung cấp parser/fetcher.
- **Cách xử lý:** xác định payload contract, field mapping và validation rules trước khi implement.
- **Cách xác minh sau khi sửa:** kiểm tra hai raw artifacts, số row clean, uniqueness DOI và schema trước build index.
- **Điều học được:** không được làm sạch phá hủy raw evidence vì repair cần tái tạo từ dữ liệu nguồn.

## 7. Hiểu biết về luồng end-to-end

Raw Crossref response là bằng chứng nguồn; parser biến nó thành `PaperRecord`; cleaning tạo document chuẩn cho index. Evaluation lấy `paper_id` sạch làm ground truth, còn Chroma trả lại IDs để tính hit rate. Quality đo các lỗi như null/duplicate; freshness dùng `published`/`age_days` để đo độ mới. Dùng một test set cố định giúp phân biệt tác động của corruption với thay đổi sample. Repair tốt khi rerun cleaning từ raw khôi phục schema/quality và các metrics liên quan.

## 8. Phân tích kết quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | 0.250 | 1.000 | Drop sáu DOI có ground truth làm hit rate giảm. |
| `mean_token_f1` | 1.000 | 0.408 | 1.000 | Blank/noisy content làm answers xấu đi. |
| `judge_accuracy` | 1.000 | 0.375 | 1.000 | Repair từ raw khôi phục factual answers. |
| `mean_judge_score` | 5.000 | 2.625 | 5.000 | Gemini judge xác nhận repair về đúng baseline. |
| Ragas: precision/recall/faithfulness | 0.750/0.750/0.750 | 0.125/0.125/0.286 | 0.750/0.750/0.750 | Data corruption làm grounding giảm rõ rệt. |
| Quality checks | PASS | FAIL | PASS | Fail 1 duplicate, 2 short summaries, 1 stale row. |
| Freshness status | Fresh | Stale | Fresh | Corrupt date 2000-01-01 tạo 1 stale row. |

`corruption_log.json` cho thấy sáu latest records bị xóa, hai summary bị blank, một summary bị noise, một title bị truncate, một date bị làm stale và một row bị duplicate. Các signals này đồng thời đi với sự giảm metrics; rebuild từ raw records phục hồi cả data contract lẫn metrics.

## 9. Điều học được và hướng cải thiện

1. Raw snapshot là điều kiện để data recovery có thể audit được.
2. Stable paper ID liên kết ingestion, index và evaluation.
3. Cleaning phải bảo toàn metadata đồng thời tạo text phù hợp semantic retrieval.

Nếu có thêm thời gian, thêm test fixture Crossref cố định cho parser/date edge cases và một validation schema tự động.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo thành viên khác.

**Họ và tên:** Nguyễn Quang Huy
**Ngày xác nhận:** 2026-08-06
