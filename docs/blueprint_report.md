# Day 13 Observability Lab Report

> **Instruction**: Fill in all sections below. This report is designed to be parsed by an automated grading assistant. Ensure all tags (e.g., `[GROUP_NAME]`) are preserved.

## 1. Team Metadata
- [GROUP_NAME]: C401-E4
- [REPO_URL]: https://github.com/tnhoang462/Lab13-C401-E4
- [MEMBERS]:
  - Member A: [Trần Nhật Hoàng] | Role: Logging & PII
  - Member B: [Trần Minh Toàn] | Role: Tracing & Enrichment
  - Member C: [Phạm Đỗ Ngọc Minh  ] | Role: SLO & Alerts
  - Member D: [Nguyễn Xuân Mong] | Role: Load Test & Incident Injection
  - Member E: [Trương Đặng Gia Huy] | Role: Dashboard & Evidence
  - Member F: [Nguyễn Ngọc Thắng] | Role: Blueprint, Report
  - Member G: [Lê Quý Công] | Role: Blueprint, Demo

---

## 2. Group Performance (Auto-Verified)
- [VALIDATE_LOGS_FINAL_SCORE]: 100/100
- [TOTAL_TRACES_COUNT]: 39
- [PII_LEAKS_FOUND]: 0

---

## 3. Technical Evidence (Group)

### 3.1 Logging & Tracing
- [EVIDENCE_CORRELATION_ID_SCREENSHOT]: [docs\evidence\logs_correlation_id.png]
- [EVIDENCE_PII_REDACTION_SCREENSHOT]: [docs\evidence\logs_pii_redaction.png]
- [EVIDENCE_TRACE_WATERFALL_SCREENSHOT]: [docs\evidence\trace_waterfall.png]
- [TRACE_WATERFALL_EXPLANATION]: The llm_generate span specifically highlights the system's fallback logic, showing how the prompt was dynamically adjusted to provide a general answer after the retrieval step failed to find matching documents. It also captures critical observability metadata in one place, including the 0.15s latency, precise token usage (155 total), and the specific model version used.

### 3.2 Dashboard & SLOs
- [DASHBOARD_6_PANELS_SCREENSHOT]: [docs\evidence\dashboard_6panels.png]
- [SLO_TABLE]:
| SLI | Target | Window | Current Value |
| Latency P95 | < 3000ms | 28d | 150.0ms (base) / 13311.0ms (incident) |
| Error Rate | < 2% | 28d | 0% (base) / **100%** (during tool fail) |
| Cost Budget | < $2.5/day | 1d | $0.0716 (base) / **~$5.0** (Projected during cost_spike) |



### 3.3 Alerts & Runbook
- [ALERT_RULES_SCREENSHOT]: [docs\evidence\alert_rules.png]
- [SAMPLE_RUNBOOK_LINK]: [docs/alerts.md]

---

## 4. Incident Response (Group)
- [SCENARIO_NAME]: rag_slow (Simulated Performance Degradation)
- [SYMPTOMS_OBSERVED]: Hệ thống vẫn trả về kết quả thành công (HTTP 200) nhưng độ trễ (Latency) tăng vọt từ 160ms lên hơn 13,000ms khi có tải nhẹ (concurrency=5).
- [ROOT_CAUSE_PROVED_BY]: Log ghi nhận `latency_ms` cực cao tập trung tại khâu `retrieve` (RAG), chứng minh sự cố nằm ở layer truy xuất dữ liệu chứ không phải ở LLM.
- [FIX_ACTION]: Tạm thời tắt incident toggle bằng `inject_incident.py --disable`. Trong thực tế sẽ cần tối ưu lại Vector DB hoặc scale-up dịch vụ retrieval.
- [PREVENTIVE_MEASURE]: Cài đặt Alert dựa trên P95 Latency (>2s) để phát hiện sớm các hiện tượng "nghẽn cổ chai" trước khi người dùng phàn nàn.

---

## 5. Individual Contributions & Evidence

### [Trần Nhật Hoàng - Member A]
- [TASKS_COMPLETED]: Thiết lập hệ thống Structured Logging cho toàn bộ ứng dụng và triển khai logic nhận diện/che giấu dữ liệu PII (Personal Identifiable Information) để đảm bảo an toàn dữ liệu trong log.
- [EVIDENCE_LINK]: commit [7d59575](https://github.com/tnhoang462/Lab13-C401-E4/commit/7d59575)

### [Trần Minh Toàn - Member B]
- [TASKS_COMPLETED]: Tích hợp Langfuse SDK và triển khai tracing chi tiết cho các bước `rag_retrieve` và `llm_generate`, bổ sung các metadata enrichment (model, tokens) để hỗ trợ monitor hiệu năng AI.
- [EVIDENCE_LINK]: commit [7d724fc](https://github.com/tnhoang462/Lab13-C401-E4/commit/7d724fc)

### [Phạm Đỗ Ngọc Minh - Member C]
- [TASKS_COMPLETED]: Định nghĩa các chỉ số SLIs/SLOs quan trọng (Latency P95, Error Rate, Cost) và cấu hình tệp `alert_rules.yaml` để kích hoạt cảnh báo tự động khi hệ thống gặp sự cố.
- [EVIDENCE_LINK]: commit [fd25c16](https://github.com/tnhoang462/Lab13-C401-E4/commit/fd25c16)

### [Nguyễn Xuân Mong - Member D]
- [TASKS_COMPLETED]: 
  1. Xác lập Baseline hiệu năng hệ thống (Latency P50 ~160ms).
  2. Thực hiện Chaos Engineering: Giả lập thành công 3 sự cố (`rag_slow`, `cost_spike`, `tool_fail`) để kiểm thử hệ thống giám sát.
  3. Phân tích Stress Test: Đo lường tác động của tải cao (concurrency=5) lên độ trễ hệ thống (tăng vọt lên 13.3s).
  4. Enrich Test Data: Bổ sung dữ liệu PII và Edge cases vào `sample_queries.jsonl` để kiểm tra khả năng Sanitization.
- [EVIDENCE_LINK]: commit [8b82114](https://github.com/tnhoang462/Lab13-C401-E4/commit/8b82114) và thay đổi file `data/sample_queries.jsonl`.

### [Trương Đặng Gia Huy - Member E]
- [TASKS_COMPLETED]: Xây dựng giao diện Dashboard quan sát thời gian thực, trực quan hóa các chỉ số từ hệ thống Prometheus/Metrics API để đội ngũ vận hành dễ theo dõi trạng thái hệ thống.
- [EVIDENCE_LINK]: commit [8000833](https://github.com/tnhoang462/Lab13-C401-E4/commit/8000833)

### [Nguyễn Ngọc Thắng - Member F]
- [TASKS_COMPLETED]: Tổng hợp các bằng chứng kỹ thuật (screenshots, logs), hoàn thiện báo cáo Blueprint và đảm bảo tính nhất quán của tài liệu hướng dẫn cho việc chấm điểm tự động.
- [EVIDENCE_LINK]: commit [aaaf29b](https://github.com/tnhoang462/Lab13-C401-E4/commit/aaaf29b)

### [Lê Quý Công - Member G]
- [TASKS_COMPLETED]: Phối hợp hoàn thiện UI Dashboard và tối ưu hóa các mẫu Regex trong module PII để tăng độ chính xác trong việc lọc dữ liệu nhạy cảm. Chịu trách nhiệm Demo dự án.
- [EVIDENCE_LINK]: commit [4767d03](https://github.com/tnhoang462/Lab13-C401-E4/commit/4767d03)
---

## 6. Bonus Items (Optional)
- [BONUS_COST_OPTIMIZATION]: (Description + Evidence)
- [BONUS_AUDIT_LOGS]: (Description + Evidence)
- [BONUS_CUSTOM_METRIC]: (Description + Evidence)
