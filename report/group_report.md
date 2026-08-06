# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K3 |
| Tên nhóm | Nhóm A53|
| Repository | `K3_Day10_Data-Pipeline-Data-Observability_A53` |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Nguyễn Thế Khôi | 2A202601439 | Điều phối pipeline | `config.py`, `phase1.py`, `corruption_flow.py`, tích hợp và demo |
| 2 | Nguyễn Quang Huy | 2A202601165 | Nền tảng dữ liệu & recovery | `crossref.py`, `cleaning.py`, `corruption.py`, raw/clean artifacts |
| 3 | Lê Tiến Đạt | 2A202601263 | RAG & agent | MiniLM/Chroma, search, lookup, agent smoke test |
| 4 | Bùi Đặng Quốc An | 2A202601799 | Evaluation & observability | `testset.py`, `metrics.py`, `quality.py`, `reporting.py` |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thiện hai pha của data pipeline RAG dùng Crossref. Pha baseline gọi Crossref, lưu cả HTTP response nguyên bản và records đã parse, làm sạch thành 24 paper records, tạo embedding bằng `sentence-transformers/all-MiniLM-L6-v2`, xây ChromaDB và đánh giá trên 8 câu hỏi factual sinh từ chính clean dataset. Baseline đạt retrieval hit rate 1.00, token F1 1.00, Gemini judge accuracy 1.00 và mean judge score 5.00.

Pha corruption cố ý xóa sáu latest records, blank hai summary, inject noise, truncate title, làm stale một publication date và thêm duplicate row. Dataset giảm từ 24 xuống 19 rows; quality report phát hiện duplicate, short summary và freshness failure. Trên cùng test set, retrieval hit rate giảm còn 0.25, token F1 còn 0.408, judge accuracy còn 0.375 và mean judge score còn 2.625. Ragas context precision/recall giảm từ 0.75 xuống 0.125, faithfulness giảm từ 0.75 xuống 0.262.

Repair không sửa tay corrupted dataset mà rebuild clean data từ `data/raw/crossref_records.json`, sau đó re-index và re-evaluate. Repaired dataset trở về 24 rows, quality/freshness PASS và tất cả metric retrieval, answer, Ragas trở lại baseline. Giới hạn chính là Ragas `answer_relevancy` không chạy với Gemini 3.5 Flash do metric yêu cầu multiple candidates; nhóm dùng context precision, context recall và faithfulness thay thế.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> data/raw/crossref_response.json
    -> data/raw/crossref_records.json
    -> data/clean/papers_clean.csv + .json
    -> MiniLM embedding + ChromaDB
    -> baseline evaluation, quality/freshness, report
    -> corruption + re-index + re-evaluate
    -> repair từ raw records + re-index + re-evaluate
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref `/works` | Query, retry/backoff 429/503, parse DOI metadata | `data/raw/crossref_response.json`, `crossref_records.json` | Huy |
| Cleaning | `list[PaperRecord]` | Normalize, date parsing, deduplicate, create embedding text | `data/clean/papers_clean.csv/json` | Huy |
| Embedding/index | Clean DataFrame | MiniLM, Chroma cosine collections | `data/chroma/`, embedding manifests | Đạt |
| Evaluation | Index và test set | Retrieval/answer metrics, Gemini judge, Ragas | `data/results/*_metrics.json`, `*_answers.json` | An |
| Observability | Ba DataFrame | Quality checks, freshness reports, Markdown reports | `data/quality/*.json`, `data/reports/*.md` | An |
| Corruption/repair | Baseline clean + raw records | Simulate defects; rebuild from raw records | Corruption log, corrupted/repaired datasets | Huy |
| Orchestration | Settings và các artifacts | Thứ tự stage, precondition, persistence | Two runnable pipeline scripts | Khôi |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | `gemini` |
| `LLM_MODEL` | `gemini-3.5-flash` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày |
| Evaluation samples | 8 |
| Ragas | Bật tạm thời bằng `RUN_RAGAS=1` |

Không đưa API key hoặc nội dung `.env` vào report.

### Lệnh cài đặt

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline:

```bash
python script/run_phase1.py
```

Corruption/repair:

```bash
python script/run_corruption_flow.py
```

Chạy Ragas cho cả ba trạng thái:

```powershell
$env:RUN_RAGAS='1'
python script/run_phase1.py
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| Baseline pipeline | Thành công | 2026-08-06 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow | Thành công | 2026-08-06 | `data/results/corrupted_metrics.json`, `repaired_metrics.json`, `corruption_report.md` |
| Agent smoke test | Thành công | 2026-08-06 | Gemini agent trả lời đúng category `Uncategorized` từ baseline Chroma index |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API `https://api.crossref.org/works` |
| Query | `agentic retrieval augmented generation large language model` |
| Filter | `from-pub-date:2026-02-07,has-abstract:true` |
| Số record parse/clean | 24 / 24 |
| Cơ chế retry/backoff | Tối đa 4 attempts; exponential backoff cho 429/503 và request error |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| `paper_id` | string | Có | DOI normalize lowercase; document identity | Loại record nếu thiếu; deduplicate theo field này |
| `title` | string | Có | Tiêu đề paper | Loại nếu blank |
| `summary` | string | Có | `abstract` hoặc fallback `description` | Loại nếu ngắn hơn 30 ký tự |
| `authors`, `categories` | list[string] | Không | Metadata source | Normalize từng phần tử; dùng placeholder joined khi rỗng |
| `published`, `updated` | ISO date string | `published` có | Date của paper | Loại record có `published` không parse được |
| `authors_joined`, `categories_joined` | string | Có sau cleaning | Metadata cho QA/index | Tạo từ list đã clean |
| `summary_chars`, `age_days` | integer | Có sau cleaning | Completeness và freshness signals | Tính từ summary/date đã clean |
| `text_for_embedding` | string | Có sau cleaning | Input MiniLM | Ghép title, abstract, authors, categories có label |

### Quy tắc cleaning

| Quy tắc | Quality dimension | Số record bị tác động ở baseline | Cách xác minh |
| --- | --- | ---: | --- |
| Normalize whitespace/title/summary/list metadata | Validity, consistency | 24 processed | `papers_clean.json` |
| Loại record không DOI/title/summary/date hợp lệ | Completeness, validity | 0 bị loại trong snapshot | 24 raw = 24 clean |
| Deduplicate theo DOI | Uniqueness | 0 duplicate baseline | `baseline_quality.json` |
| Tạo `text_for_embedding` và `age_days` | Usability, freshness | 24 rows | Clean schema + quality report |

`text_for_embedding` gồm Title, Abstract, Authors và Categories có nhãn rõ ràng. DOI là document ID xuyên suốt raw → clean → Chroma → evaluation. `age_days` được tính bằng run date trừ `published` và baseline có 0 stale row theo threshold 180 ngày.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 8 |
| `question_type` | `summary`, `authors`, `date`, `categories` |
| Ground-truth document ID | `paper_id` thật từ clean DataFrame |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection | Chroma cosine: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k` | 4 |
| LLM provider/model | Gemini / `gemini-3.5-flash` |
| Test set dùng chung | `data/eval/test_set.json` cho cả 3 states |

Test set được giữ nguyên để metric difference chỉ phản ánh thay đổi của corpus/index do corruption hoặc repair, không phải do thay đổi câu hỏi, ground truth hoặc document IDs.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | `data/raw/` | Có | HTTP source và 24 flat records |
| Cleaned dataset | `data/clean/papers_clean.csv/json` | Có | 24 rows |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Có | MiniLM + Chroma |
| Evaluation set | `data/eval/test_set.json` | Có | 8 samples |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Retrieval, answer, judge, Ragas |
| Quality/freshness | `data/quality/baseline_quality.json`, `freshness_report.json` | Có | PASS / Fresh |
| Baseline report | `data/reports/phase1_report.md` | Có | Markdown evidence |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| `retrieval_hit_rate` | 1.000 | Top-4 luôn chứa ground-truth paper ID. |
| `mean_token_f1` | 1.000 | Factual answers match reference text. |
| `judge_accuracy` | 1.000 | Gemini judge xác nhận toàn bộ answer materially correct. |
| `mean_judge_score` | 5.000 | Mean score tối đa trên thang 1–5. |
| Ragas context precision | 0.750 | Context retrieved có độ chính xác tốt. |
| Ragas context recall | 0.750 | Context bao phủ phần lớn reference evidence. |
| Ragas faithfulness | 0.750 | Answer được grounding tốt trong retrieved contexts. |

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| --- | --- | --- | --- | --- |
| `row_count` | Completeness | > 0 | PASS, 24 | `baseline_quality.json` |
| `paper_id_not_null` | Completeness | 0 null/blank | PASS, 0 | `baseline_quality.json` |
| `paper_id_unique` | Uniqueness | 0 duplicate | PASS, 0 | `baseline_quality.json` |
| `title_not_blank` | Completeness | 0 blank | PASS, 0 | `baseline_quality.json` |
| `summary_min_length` | Validity | 0 summary < 30 chars | PASS, 0 | `baseline_quality.json` |
| `embedding_text_not_blank` | Usability | 0 blank | PASS, 0 | `baseline_quality.json` |
| `age_days_valid` | Validity | 0 invalid | PASS, 0 | `baseline_quality.json` |
| `freshness_threshold` | Freshness | 0 stale | PASS, 0 | `baseline_quality.json` |

### Freshness

| Thuộc tính | Giá trị |
| --- | --- |
| Freshness được đo tại | Cleaned baseline dataset |
| Timestamp mới nhất | 2026-08-01 |
| Timestamp cũ nhất | 2026-02-12 |
| Ngưỡng freshness | 180 ngày |
| Trạng thái baseline | Fresh |
| Lý do | 24 rows hợp lệ và không có row nào có `age_days` vượt threshold |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal thực tế | Tác động thực tế | Cách repair |
| --- | --- | ---: | --- | --- | --- |
| Drop latest records | Xóa 6 rows đầu clean set | 6 | Row count 24 → 19; IDs missing | Hit rate 1.00 → 0.25 | Rebuild từ raw records |
| Blank summary | Set summary rỗng | 2 | `summary_min_length` FAIL (2) | Answer grounding giảm | Reclean raw source |
| Summary noise | Append noise token | 1 | Nội dung degraded trong corpus | Context quality giảm | Reclean raw source |
| Truncate title | Cắt title 24 chars | 1 | Metadata fidelity bị hỏng | Exact lookup risk | Reclean raw source |
| Stale date | Set `published=2000-01-01` | 1 | Freshness FAIL; stale rows = 1 | Corpus không còn fresh | Reclean raw source |
| Duplicate row | Append duplicate row | 1 | `paper_id_unique` FAIL (1) | Retrieval corpus có duplicate | Reclean raw source |

Corruption log: `data/results/corruption_log.json` — có đầy đủ type, paper IDs bị tác động và input/output row count. Repair dùng `crossref_records.json` làm trusted source, chạy lại cleaning và build index; không sửa trực tiếp corrupted artifact.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | 0.250 | 1.000 | Drop relevant documents làm hit rate giảm 75 điểm phần trăm; repair phục hồi. |
| `mean_token_f1` | 1.000 | 0.408 | 1.000 | Answer quality suy giảm rồi trở lại baseline. |
| `judge_accuracy` | 1.000 | 0.375 | 1.000 | Gemini judge xác nhận recovery. |
| `mean_judge_score` | 5.000 | 2.625 | 5.000 | Corruption làm chất lượng factual answer giảm mạnh. |
| Ragas context precision | 0.750 | 0.125 | 0.750 | Context relevance bị ảnh hưởng rõ. |
| Ragas context recall | 0.750 | 0.125 | 0.750 | Relevant evidence bị mất do deleted papers. |
| Ragas faithfulness | 0.750 | 0.262 | 0.750 | Answer grounding giảm rồi phục hồi. |
| Quality checks | PASS | FAIL | PASS | Corrupted fail duplicate, short summary, freshness. |
| Freshness status | Fresh | Stale | Fresh | Stale rows: 0 → 1 → 0. |

Hai kết luận có quan hệ nhân quả được hỗ trợ bởi artifact:

1. Xóa sáu records có ground-truth IDs trong test set → IDs không còn trong corrupted index, quality row count giảm → retrieval hit rate 1.00 xuống 0.25, Ragas precision/recall cùng xuống 0.125.
2. Repair bằng cách rerun cleaning từ raw records → 24 rows unique, summary valid và 0 stale row → retrieval, judge và Ragas metrics trở lại baseline.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Gemini API trả 404 khi dùng `gemini-2.5-flash`; evaluation âm thầm dùng fallback heuristic.
- **Nguyên nhân:** model này không còn được cấp cho tài khoản Gemini API mới.
- **Cách xử lý:** đổi `LLM_MODEL` trong `.env`, `.env.example`, README và default `Settings` sang `gemini-3.5-flash`; smoke test gọi Gemini thành công.
- **Cách xác minh:** `baseline_answers.json` ghi reasoning do Gemini sinh ra thay vì fallback; baseline/corruption/repaired metrics được chạy lại.

Một integration issue khác là Ragas 0.4 không tương thích public `model` object trên MiniLM wrapper và Gemini không hỗ trợ multiple candidates cho `answer_relevancy`. Nhóm đổi wrapper sang private transformer attribute và chạy ba metrics tương thích: context precision, context recall, faithfulness.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| Test set chỉ có 8 questions, chủ yếu factual/exact-title | Metric có thể cao hơn use case open-ended thực tế | Mở rộng test set theo categories và paraphrase; báo cáo CI hoặc phân phối score |
| `answer_relevancy` Ragas không chạy với Gemini 3.5 Flash | Thiếu một Ragas signal | Dùng model/provider hỗ trợ multiple candidates hoặc metric Ragas tương thích khác |
| Crossref là live source | Rerun có thể đổi corpus/metric | Lưu và version raw snapshot, ghi timestamp/hash trong report |
| Chroma persist chứa segments từ nhiều lần local run | Tốn dung lượng workspace | Dọn persist directory có kiểm soát trước release và rebuild từ artifact được chọn |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm, vai trò và module rõ ràng.
- [x] Baseline và corruption/repair pipeline đã chạy.
- [x] Ba trạng thái dùng cùng `data/eval/test_set.json`.
- [x] Metrics, answers, quality/freshness và report artifacts đã tạo.
- [x] Data corruption có bằng chứng làm RAG metrics giảm và repair phục hồi.
- [x] Không đưa `.env` hoặc API key vào report.
- [x] Stage/commit các artifacts cần nộp trong `data/` và source/report files.
