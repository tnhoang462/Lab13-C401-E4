# Day 13 Observability Lab Report

> **Instruction**: Fill in all sections below. This report is designed to be parsed by an automated grading assistant. Ensure all tags (e.g., `[GROUP_NAME]`) are preserved.

## 1. Team Metadata
- [GROUP_NAME]: 
- [REPO_URL]: 
- [MEMBERS]:
  - Member A: [Name] | Role: Logging & PII
  - Member B: [Name] | Role: Tracing & Enrichment
  - Member C: [Name] | Role: SLO & Alerts
  - Member D: [Name] | Role: Load Test & Dashboard
  - Member E: [Name] | Role: Demo & Report

---

## 2. Group Performance (Auto-Verified)
- [VALIDATE_LOGS_FINAL_SCORE]: /100
- [TOTAL_TRACES_COUNT]: 
- [PII_LEAKS_FOUND]: 

---

## 3. Technical Evidence (Group)

### 3.1 Logging & Tracing
- [EVIDENCE_CORRELATION_ID_SCREENSHOT]: [Path to image]
- [EVIDENCE_PII_REDACTION_SCREENSHOT]: [Path to image]
- [EVIDENCE_TRACE_WATERFALL_SCREENSHOT]: [Path to image]
- [TRACE_WATERFALL_EXPLANATION]: (Briefly explain one interesting span in your trace)

### 3.2 Dashboard & SLOs
- [DASHBOARD_6_PANELS_SCREENSHOT]: [Path to image]
- [SLO_TABLE]:
| SLI | Target | Window | Current Value |
|---|---:|---|---:|
| SLI | Target | Window | Current Value |
|---|---:|---|---:|
| Latency P95 | < 3000ms | 28d | **13311ms** (During Incident) |
| Error Rate | < 2% | 28d | **100%** (During Tool Fail) |
| Cost Budget | < $2.5/day | 1d | **~$5.0** (Projected during cost_spike) |

### 3.3 Alerts & Runbook
- [ALERT_RULES_SCREENSHOT]: [Path to image]
- [SAMPLE_RUNBOOK_LINK]: [docs/alerts.md#L3-L15]

---

## 4. Incident Response (Group)
- [SCENARIO_NAME]: rag_slow (Simulated Performance Degradation)
- [SYMPTOMS_OBSERVED]: Hệ thống vẫn trả về kết quả thành công (HTTP 200) nhưng độ trễ (Latency) tăng vọt từ 160ms lên hơn 13,000ms khi có tải nhẹ (concurrency=5).
- [ROOT_CAUSE_PROVED_BY]: Log ghi nhận `latency_ms` cực cao tập trung tại khâu `retrieve` (RAG), chứng minh sự cố nằm ở layer truy xuất dữ liệu chứ không phải ở LLM.
- [FIX_ACTION]: Tạm thời tắt incident toggle bằng `inject_incident.py --disable`. Trong thực tế sẽ cần tối ưu lại Vector DB hoặc scale-up dịch vụ retrieval.
- [PREVENTIVE_MEASURE]: Cài đặt Alert dựa trên P95 Latency (>2s) để phát hiện sớm các hiện tượng "nghẽn cổ chai" trước khi người dùng phàn nàn.

---

## 5. Individual Contributions & Evidence

### [MEMBER_A_NAME]
- [TASKS_COMPLETED]: 
- [EVIDENCE_LINK]: (Link to specific commit or PR)

### [MEMBER_B_NAME]
- [TASKS_COMPLETED]: 
- [EVIDENCE_LINK]: 

### [MEMBER_C_NAME]
- [TASKS_COMPLETED]: 
- [EVIDENCE_LINK]: 

### [Nguyễn Xuân Mong - Member D]
- [TASKS_COMPLETED]: 
  1. Xác lập Baseline hiệu năng hệ thống (Latency P50 ~160ms).
  2. Thực hiện Chaos Engineering: Giả lập thành công 3 sự cố (`rag_slow`, `cost_spike`, `tool_fail`) để kiểm thử hệ thống giám sát.
  3. Phân tích Stress Test: Đo lường tác động của tải cao (concurrency=5) lên độ trễ hệ thống (tăng vọt lên 13.3s).
  4. Enrich Test Data: Bổ sung dữ liệu PII và Edge cases vào `sample_queries.jsonl` để kiểm tra khả năng Sanitization (lọc dữ liệu nhạy cảm).
- [EVIDENCE_LINK]: Đã thực hiện commit thay đổi file `data/sample_queries.jsonl` và lưu trữ log thực thi các kịch bản load test.

### [MEMBER_E_NAME]
- [TASKS_COMPLETED]: 
- [EVIDENCE_LINK]: 

---

## 6. Bonus Items (Optional)
- [BONUS_COST_OPTIMIZATION]: (Description + Evidence)
- [BONUS_AUDIT_LOGS]: (Description + Evidence)
- [BONUS_CUSTOM_METRIC]: (Description + Evidence)
