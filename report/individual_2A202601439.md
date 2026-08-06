# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Thế Khôi |
| MSSV | 2A202601439 |
| Khóa/Lớp | K3 |
| Tên nhóm | Nhóm K3 — Data Pipeline & Data Observability |
| Vai trò chính | Vai trò 1 — Điều phối pipeline |
| Repository | `K3_Day10_Data-Pipeline-Data-Observability_A53` |
| Ngày cập nhật | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Cấu hình dùng chung | `src/core/config.py`, `.env.example` | Biến môi trường và cấu trúc thư mục | `Settings`/`Paths` thống nhất, không chứa secret | Hoàn thành, đã dùng khi chạy |
| Baseline orchestration | `src/pipelines/phase1.py::main` | Raw records, clean DataFrame, index, test set | Baseline artifacts, metrics, quality/freshness và report | Hoàn thành |
| Corruption orchestration | `src/pipelines/corruption_flow.py::main` | Baseline artifacts, clean/raw data | Corrupted/repaired artifacts và comparison report | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Chốt data contract và artifact path | Toàn nhóm | Dùng đúng các path trong `Settings.paths`; không tạo path hard-code mới. |
| Kiểm tra handoff | Vai trò 2, 3, 4 | Xác định chuỗi raw → clean → index → evaluate → report trước khi tích hợp. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Rà soát contract điều phối | `src/core/config.py` | Danh sách artifact baseline/corrupted/repaired đã được chốt | Đối chiếu các thuộc tính `Settings.paths` |
| Chốt thứ tự pha 1 | `src/pipelines/phase1.py` | Fetch/load → clean → save → build index → test set → evaluate → quality/freshness → report | Chạy `python script/run_phase1.py` sau khi các module phụ thuộc hoàn tất |
| Chốt thứ tự pha 2 | `src/pipelines/corruption_flow.py` | Corrupt → save/re-index/evaluate → quality/freshness → repair từ raw → re-index/evaluate → report | Chạy `python script/run_corruption_flow.py` sau baseline |

Đã tạo đủ artifact tích hợp: ba metrics/answers JSON trong `data/results/`, ba embedding manifests, quality/freshness JSON và `data/reports/phase1_report.md`, `data/reports/corruption_report.md`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Điều phối các module độc lập thành hai pipeline tái hiện được, bảo đảm output của bước trước đúng là input của bước sau và mọi trạng thái dùng chung evaluation set.

### Cách triển khai

`load_settings()` là điểm vào chung. Pha baseline ưu tiên load snapshot raw khi có, hoặc gọi source khi cần; sau đó persist clean dataset trước khi build Chroma index. Pha corruption chỉ bắt đầu khi baseline artifacts tồn tại. Repair phải tạo lại clean dataset từ raw records thay vì chỉnh sửa dữ liệu corrupted. Mọi output dùng path đã khai báo trong `Settings.paths`.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `Settings`, raw records, clean DataFrame, index, evaluation set và baseline metrics |
| Output | CSV/JSON, embedding manifests, metrics/answers JSON, quality/freshness JSON và Markdown reports |
| Module phụ thuộc | `ingestion`, `retrieval`, `evaluation`, `observability` |
| Module sử dụng output | Scripts `run_phase1.py` và `run_corruption_flow.py` |
| Điều kiện lỗi cần xử lý | Thiếu `.env`/credential, thiếu baseline artifact, raw/clean schema sai, lỗi source hoặc index |

### Cách xác minh

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** hai lệnh hoàn tất và tạo đúng artifact paths trong config.
- **Kết quả thực tế:** baseline hoàn tất với 24 clean records; corruption/repair flow hoàn tất trên cùng 8 câu hỏi.
- **Artifact/log:** `data/results/baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json` và hai report Markdown.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** cần đặt tên và đường dẫn artifact để bốn người phát triển song song.
- **Các phương án đã cân nhắc:** tự đặt path theo từng module; hoặc dùng duy nhất `Settings.paths` đã có.
- **Phương án đã chọn:** dùng `Settings.paths` làm source of truth.
- **Lý do:** tránh lệch tên file giữa build, load, evaluation và report; dễ tái hiện trên máy khác.
- **Bằng chứng quyết định phù hợp:** `LocalEmbeddingIndex._derive_collection_name()` và hai pipeline đều được thiết kế dựa trên các path này.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `NotImplementedError: Student task: implement phase 1 pipeline.`
- **Lệnh hoặc bước tái hiện:** gọi `main()` trong `src/pipelines/phase1.py`.
- **Nguyên nhân gốc:** đây là starter code; orchestration và các module đầu vào chưa được nhóm implement.
- **Cách xử lý:** phân công module theo role, chốt contract/path và chỉ tích hợp sau khi owner bàn giao artifact hợp lệ.
- **Cách xác minh sau khi sửa:** chạy hai script pipeline và đối chiếu `data/results/`, `data/quality/`, `data/reports/`.
- **Điều học được:** orchestration không thể được xác minh chỉ bằng import; cần artifact thật từ toàn bộ dependency chain.

## 7. Hiểu biết về luồng end-to-end

Crossref response được lưu raw rồi parse thành `PaperRecord`; cleaning tạo DataFrame và `text_for_embedding`; MiniLM đưa document vào Chroma. Test set lấy `paper_id` từ clean data làm ground truth để đo retrieval hit rate và chất lượng câu trả lời. Quality checks đo completeness/uniqueness/validity, còn freshness đo độ mới qua `published` và `age_days`. Cùng test set phải được giữ nguyên để chênh lệch metrics phản ánh dữ liệu, không phản ánh câu hỏi khác. Repair thành công khi clean/index được dựng lại từ raw, quality/freshness phục hồi và metrics được đối chiếu với baseline.

## 8. Phân tích kết quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | 0.250 | 1.000 | Sáu documents đầu test set bị drop, repair phục hồi hoàn toàn. |
| `mean_token_f1` | 1.000 | 0.408 | 1.000 | Câu trả lời corrupted giảm mạnh rồi về baseline. |
| `judge_accuracy` | 1.000 | 0.375 | 1.000 | Gemini judge chấm đúng 3/8 sau corruption. |
| `mean_judge_score` | 5.000 | 2.625 | 5.000 | Repair phục hồi điểm trung bình. |
| Ragas: precision/recall/faithfulness | 0.750/0.750/0.750 | 0.125/0.125/0.262 | 0.750/0.750/0.750 | Grounding và retrieval giảm rồi phục hồi. |
| Quality checks | PASS | FAIL | PASS | Corrupted fail duplicate, summary length và freshness. |
| Freshness status | Fresh | Stale | Fresh | 0 → 1 → 0 stale row. |

Corruption giảm corpus từ 24 xuống 19 rows, có 1 duplicate, 2 blank summary và 1 stale row; đồng thời retrieval hit rate giảm 0.75. Repair rerun cleaning từ raw records khôi phục 24 rows, quality/freshness PASS và toàn bộ bốn metrics về baseline.

## 9. Điều học được và hướng cải thiện

1. Contract artifact là một phần của pipeline, không chỉ là chi tiết lưu file.
2. Tích hợp cần chạy theo dependency order thay vì ghép code ở cuối.
3. Đánh giá ba trạng thái phải dùng cùng corpus contract và test set.

Nếu có thêm thời gian, bổ sung CLI validation kiểm tra tồn tại/schema artifact trước từng stage.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo thành viên khác.

**Họ và tên:** Nguyễn Thế Khôi
**Ngày xác nhận:** 2026-08-06
