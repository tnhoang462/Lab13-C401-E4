# Lab13-C401-E4 — Technical Handoff

## 📦 Repository Overview

**Path**: `E:\AI-in-Action\Lab13-C401-E4`
**Mục tiêu**: Xây dựng 1 chatbot FastAPI có đầy đủ instrumentation: Logging, Tracing, Dashboard, Alerts, Incident Debug.
**Framework chính**: FastAPI + structlog + Langfuse + Pydantic
**Điều kiện đạt**: `validate_logs.py` ≥ 80/100 · ≥ 10 traces · Dashboard 6 panels · ≥ 3 alert rules

---

## 🗺️ Architecture

```
Client ──────────▶ FastAPI App ───▶ CorrelationIdMiddleware
                           │
                     POST /chat
                           │
                   ┌───────▼────────┐
                   │   LabAgent     │
                   ├─ retrieve()   │  (mock RAG)
                   ├─ llm.generate()│  (mock LLM)
                   ├─ metrics       │  (in-memory)
                   └────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼                         ▼
       structlog                    Langfuse
       data/logs.jsonl              cloud.langfuse.com
```

---

## 📁 Cấu trúc file

```
Lab13-C401-E4/
├── app/
│   ├── main.py              # FastAPI app, endpoint /chat, /health, /metrics
│   ├── agent.py             # LabAgent, @observe() decorator cho Langfuse
│   ├── middleware.py         # CorrelationIdMiddleware — inject x-request-id
│   ├── logging_config.py     # structlog pipeline + PII scrub processor
│   ├── pii.py               # Regex patterns + scrub_text() + hash_user_id()
│   ├── tracing.py           # langfuse_context wrapper + tracing_enabled()
│   ├── metrics.py           # In-memory metrics (P50/P95/P99, cost, tokens)
│   ├── incidents.py          # Toggle incident (rag_slow, tool_fail, cost_spike)
│   ├── schemas.py           # Pydantic models
│   ├── mock_llm.py          # Fake LLM (deterministic)
│   └── mock_rag.py          # Fake RAG retrieval (deterministic)
├── config/
│   ├── logging_schema.json  # Expected log schema (validate_logs.py dùng)
│   ├── alert_rules.yaml     # 3 alert rules + runbook link
│   └── slo.yaml            # SLO targets
├── scripts/
│   ├── validate_logs.py    # Chấm điểm tự động → score/100
│   ├── load_test.py        # Generate requests, concurrency test
│   └── inject_incident.py  # Flip incident toggles live
├── data/
│   ├── logs.jsonl          # Log output (structlog ghi vào)
│   ├── audit.jsonl         # Audit log (bonus)
│   ├── incidents.json      # Mô tả các scenario incident
│   └── sample_queries.jsonl
├── docs/
│   ├── blueprint-template.md  # Báo cáo nhóm — điền thông tin vào đây
│   ├── alerts.md              # Runbook chi tiết cho 3 alerts
│   ├── dashboard-spec.md      # Spec 6-panel dashboard
│   └── grading-evidence.md    # Checklist ảnh cần thu thập
└── requirements.txt
```

---

## ⚙️ Dependencies

```txt
fastapi==0.118.0
uvicorn[standard]==0.37.0
pydantic==2.11.4
structlog==25.4.0
python-dotenv==1.1.0
httpx==0.28.1
langfuse==3.2.1
pytest==8.3.5
```

---

## 🔑 Environment Variables (.env)

```bash
APP_ENV=dev
APP_NAME=day13-observability-lab
LOG_LEVEL=INFO
LOG_PATH=data/logs.jsonl
AUDIT_LOG_PATH=data/audit.jsonl
LANGFUSE_PUBLIC_KEY=          # ⚠️ Cần điền → enable tracing
LANGFUSE_SECRET_KEY=          # ⚠️ Cần điền → enable tracing
LANGFUSE_HOST=https://cloud.langfuse.com
```

---

## 🚀 Cách chạy

```bash
# 1. Setup
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt

# 2. Cấu hình
cp .env.example .env
# Điền LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY vào .env

# 3. Chạy app
uvicorn app.main:app --reload

# 4. Gửi request test
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "x-request-id: test-req-001" \
  -d '{"user_id": "u_team_01", "session_id": "s_demo_01", "feature": "qa", "message": "How do I reset my password?"}'

# 5. Load test
python scripts/load_test.py --concurrency 5

# 6. Validate logs
python scripts/validate_logs.py

# 7. Inject incident
python scripts/inject_incident.py --scenario rag_slow
```

---

## 🔍 Chi tiết từng component

### `middleware.py` — Correlation ID

- Chạy trên **mọi request**
- `clear_contextvars()` — tránh leak giữa các request
- Extract `x-request-id` từ header, fallback: `req-<8-char-hex>`
- `bind_contextvars(correlation_id=correlation_id)` → structlog tự động gắn vào mọi log
- Response headers: `x-request-id` + `x-response-time-ms`

### `logging_config.py` — Structured Logging

Pipeline structlog (thứ tự xử lý):
```
merge_contextvars
  → add_log_level
    → TimeStamper(fmt="iso", utc=True)
      → scrub_event (PII scrubbing)
        → StackInfoRenderer
          → format_exc_info
            → JsonlFileProcessor()  ← ghi vào data/logs.jsonl
              → JSONRenderer()
```

Output: `data/logs.jsonl` — mỗi dòng 1 JSON object.

**Schema mong đợi** (`config/logging_schema.json`):
```json
{
  "ts", "level", "service", "event", "correlation_id",
  "env", "user_id_hash", "session_id", "feature", "model",
  "latency_ms", "tokens_in", "tokens_out", "cost_usd",
  "error_type", "tool_name", "payload"
}
```

### `pii.py` — PII Scrubbing

Regex patterns:
| Type | Pattern | Redacted Output |
|------|---------|----------------|
| `email` | `[\w\.-]+@[\w\.-]+\.\w+` | `[REDACTED_EMAIL]` |
| `phone_vn` | `(?:\+84\|0)[ \.-]?\d{3}[ \.-]?\d{3}[ \.-]?\d{3,4}` | `[REDACTED_PHONE_VN]` |
| `cccd` | `\b\d{12}\b` | `[REDACTED_CCCD]` |
| `credit_card` | `\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b` | `[REDACTED_CREDIT_CARD]` |
| `passport` | `\b[A-Z][0-9]{7}\b` | `[REDACTED_PASSPORT]` |
| `address_vn` | Complex pattern (số nhà, đường, quận,...) | `[REDACTED_ADDRESS_VN]` |

Functions:
- `scrub_text(text)` → thay PII bằng `[REDACTED_TYPE]`
- `summarize_text(text, max_len=80)` → cắt ngắn + scrub
- `hash_user_id(user_id)` → SHA256 → lấy 12 ký tự đầu

### `tracing.py` — Langfuse Integration

- `@observe()` decorator bọc `LabAgent.run()` → gửi trace lên Langfuse
- `langfuse_context.update_current_trace(user_id, session_id, tags)`
- `langfuse_context.update_current_observation(metadata, usage_details)`
- `tracing_enabled()` → check xem LANGFUSE keys có giá trị không

### `agent.py` — Core Agent Pipeline

```
run(user_id, feature, session_id, message)
  ├─ @observe() decorator  ← Langfuse trace bắt đầu
  ├─ retrieve(message)   → mock RAG
  ├─ llm.generate(prompt)→ mock LLM
  ├─ _heuristic_quality() → quality_score 0-1
  ├─ metrics.record_request()
  ├─ langfuse_context.update_current_trace()
  ├─ langfuse_context.update_current_observation()
  └─ return AgentResult
```

### `metrics.py` — In-Memory Metrics

Global state tracking:
- `REQUEST_LATENCIES[]` → P50, P95, P99
- `REQUEST_COSTS[]` → avg, total
- `REQUEST_TOKENS_IN/OUT[]` → sum
- `ERRORS` (Counter by error_type)
- `QUALITY_SCORES[]` → avg

Endpoint: `GET /metrics` → trả snapshot dạng dict.

### `incidents.py` — Incident Injection

3 scenarios:
- `rag_slow` → làm RAG retrieval chậm
- `tool_fail` → làm tool fail
- `cost_spike` → tăng chi phí

Toggle qua API:
```
POST /incidents/{name}/enable
POST /incidents/{name}/disable
GET /health → "incidents": {...}
```

### `validate_logs.py` — Grading Script

Đọc `data/logs.jsonl`, kiểm tra và trừ điểm:

| Check | Trừ điểm |
|-------|---------|
| Missing required fields (ts, level, event) | −30 |
| Correlation ID < 2 unique IDs | −20 |
| Missing enrichment fields (user_id_hash, session_id, feature, model) | −20 |
| PII leak (`@` hoặc `4111` trong raw JSON) | −30 |

**Passing: ≥ 80/100**

---

## 👥 Phân công Role — Chi tiết công việc

> Mỗi thành viên đảm nhận 1 phần độc lập. Khi hoàn thành, mỗi người cần commit vào Git để có **Git Evidence (20đ)**.

---

### 👤 Member A — Logging + PII
**Trách nhiệm**: Đảm bảo log có đúng schema + PII không bị leak ra ngoài.

#### File cần làm việc
| File | Việc cần làm |
|------|-------------|
| `app/logging_config.py` | Đăng ký PII scrubber vào structlog pipeline (đã có `scrub_event`, check lại) |
| `app/pii.py` | Thêm regex patterns nếu cần (hiện có: email, phone_vn, cccd, credit_card, passport, address_vn) |
| `app/middleware.py` | Verify middleware gắn `correlation_id` vào contextvars đúng cách |
| `config/logging_schema.json` | Verify schema khớp với `validate_logs.py` |

#### Công việc chi tiết

1. **Verify structlog pipeline** — đảm bảo thứ tự processor đúng, `scrub_event` chạy trước `JSONRenderer`
2. **Test PII redaction**:
   ```bash
   # Gửi message chứa PII
   curl -X POST http://localhost:8000/chat \
     -d '{"user_id": "u_test", "session_id": "s1", "feature": "qa", "message": "My email is nguyen@gmail.com and phone 0901234567"}'
   # Check logs.jsonl — phải thấy [REDACTED_EMAIL], [REDACTED_PHONE_VN]
   ```
3. **Verify correlation ID propagation**:
   ```bash
   # Gửi request với x-request-id cố định
   curl -H "x-request-id: manual-req-001" http://localhost:8000/chat ...
   # Log phải có "correlation_id": "manual-req-001"
   ```
4. **Chạy validate_logs.py** — đảm bảo PII score = PASS

#### Điền vào blueprint-template.md (phần Member A)
```
### [MEMBER_A_NAME]
- [TASKS_COMPLETED]: Mô tả chi tiết những gì đã làm với logging và PII
- [EVIDENCE_LINK]: Link commit hoặc PR cụ thể
```

#### Checkpoint để verify đã xong
- [ ] `python scripts/validate_logs.py` → PII score = PASS (không trừ 30đ)
- [ ] `python scripts/validate_logs.py` → enrichment score = PASS (không trừ 20đ)
- [ ] Logs trong `logs.jsonl` có đủ 14 fields theo schema
- [ ] Correlation ID xuất hiện trong mọi API log entry

---

### 👤 Member B — Tracing + Tags
**Trách nhiệm**: Đảm bảo traces lên Langfuse đầy đủ metadata, có ≥ 10 traces.

#### File cần làm việc
| File | Việc cần làm |
|------|-------------|
| `.env` | Điền LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY |
| `app/tracing.py` | Verify fallback khi Langfuse không available |
| `app/agent.py` | Verify `@observe()` decorator + metadata enrichment |

#### Công việc chi tiết

1. **Setup Langfuse credentials**:
   - Tạo project trên [cloud.langfuse.com](https://cloud.langfuse.com)
   - Copy Public Key + Secret Key vào `.env`
   - Verify: `GET /health` → `"tracing_enabled": true`

2. **Enrich trace metadata**:
   Hiện tại `agent.py` đã gắn:
   - Trace-level: `user_id` (hashed), `session_id`, `tags: ["lab", feature, model]`
   - Observation-level: `doc_count`, `query_preview`, `usage_details`

   Có thể thêm span metadata cho từng operation:
   ```python
   @observe(as_type="generation")
   def llm_span(self, prompt):
       ...
   ```

3. **Verify traces lên Langfuse**:
   ```bash
   # Gửi 15 requests
   python scripts/load_test.py --concurrency 3
   # Check Langfuse dashboard → phải thấy ≥ 15 traces
   ```

4. **Explain trace waterfall** (cho phần Báo cáo):
   - Chọn 1 trace có latency cao bất thường
   - Giải thích: RAG span vs LLM span, token usage, thời gian mỗi span

#### Điền vào blueprint-template.md (phần Member B)
```
### [MEMBER_B_NAME]
- [TASKS_COMPLETED]: Mô tả việc setup Langfuse + enrich metadata
- [TRACE_WATERFALL_EXPLANATION]: Giải thích 1 span thú vị trong trace
- [EVIDENCE_LINK]: Link commit hoặc PR cụ thể
```

#### Checkpoint để verify đã xong
- [ ] `GET /health` → `"tracing_enabled": true`
- [ ] Langfuse dashboard có ≥ 10 traces
- [ ] Mỗi trace có đủ tags: `["lab", feature, model]`
- [ ] Mỗi trace có user_id hash + session_id

---

### 👤 Member C — SLO + Alerts
**Trách nhiệm**: Xây dựng SLO table + viết alert rules + runbooks.

#### File cần làm việc
| File | Việc cần làm |
|------|-------------|
| `config/slo.yaml` | Điền SLO targets thực tế (hiện có sẵn) |
| `config/alert_rules.yaml` | Verify 3 alert rules đúng + runbook link đúng |
| `docs/alerts.md` | Viết runbook chi tiết cho từng alert |

#### Công việc chi tiết

1. **SLO targets** (trong `config/slo.yaml`):
   | SLI | Objective | Target | Window |
   |-----|-----------|--------|--------|
   | Latency P95 | < 3000ms | 99.5% | 28d |
   | Error Rate | < 2% | 99.0% | 28d |
   | Daily Cost | < $2.5/day | 100% | 1d |
   | Quality Avg | > 0.75 | 95% | 28d |

2. **Alert Rules** (trong `config/alert_rules.yaml`):
   Hiện có 3 rules:
   ```yaml
   # 1. High latency P95 — P2
   name: high_latency_p95
   condition: latency_p95_ms > 5000 for 30m
   runbook: docs/alerts.md#1-high-latency-p95

   # 2. High error rate — P1
   name: high_error_rate
   condition: error_rate_pct > 5 for 5m
   runbook: docs/alerts.md#2-high-error-rate

   # 3. Cost budget spike — P2
   name: cost_budget_spike
   condition: hourly_cost_usd > 2x_baseline for 15m
   runbook: docs/alerts.md#3-cost-budget-spike
   ```

3. **Viết Runbooks** (`docs/alerts.md`):
   Mỗi runbook cần có:
   - Severity + Trigger condition
   - Impact description
   - First checks (3-5 bước kiểm tra cụ thể)
   - Mitigation actions
   - Preventive measures

   Template runbook:
   ```markdown
   ## N. [Alert Name]
   - Severity: P1/P2
   - Trigger: `condition`
   - Impact: mô tả
   - First checks:
     1. [Bước 1]
     2. [Bước 2]
   - Mitigation:
     - [Hành động 1]
     - [Hành động 2]
   - Preventive measure: [Làm gì để không tái diễn]
   ```

4. **Test alert firing**:
   ```bash
   # Enable rag_slow incident → latency tăng
   curl -X POST http://localhost:8000/incidents/rag_slow/enable
   python scripts/load_test.py --concurrency 5
   # Check /metrics → latency_p95 phải > threshold
   ```

#### Điền vào blueprint-template.md (phần Member C)
```
### [MEMBER_C_NAME]
- [TASKS_COMPLETED]: Mô tả việc xây dựng SLO + alerts + runbooks
- [EVIDENCE_LINK]: Link commit hoặc PR cụ thể
```

#### Checkpoint để verify đã xong
- [ ] `config/alert_rules.yaml` có ≥ 3 rules
- [ ] Mỗi rule có `runbook` link đúng format `docs/alerts.md#anchor`
- [ ] `docs/alerts.md` có đầy đủ runbook cho 3 alerts
- [ ] `docs/alerts.md` có anchor links đúng với `alert_rules.yaml`

---

### 👤 Member D — Load Test + Incident Injection
**Trách nhiệm**: Xây dựng script load test + inject incidents + hướng dẫn incident response.

#### File cần làm việc
| File | Việc cần làm |
|------|-------------|
| `scripts/load_test.py` | Verify load test script hoạt động |
| `scripts/inject_incident.py` | Verify inject incident hoạt động |
| `app/incidents.py` | Hiểu cách toggle incidents hoạt động |
| `data/incidents.json` | Mô tả chi tiết 3 scenario incident |

#### Công việc chi tiết

1. **Load Test Script** (`scripts/load_test.py`):
   ```bash
   # Test cơ bản (10 requests)
   python scripts/load_test.py

   # Test concurrency (5 parallel workers)
   python scripts/load_test.py --concurrency 5

   # Test nhiều requests
   python scripts/load_test.py --requests 100 --concurrency 10
   ```

2. **Incident Injection** (`scripts/inject_incident.py`):
   ```bash
   # Enable incident
   python scripts/inject_incident.py --scenario rag_slow
   # Hoặc qua API:
   curl -X POST http://localhost:8000/incidents/rag_slow/enable

   # Disable incident
   curl -X POST http://localhost:8000/incidents/rag_slow/disable
   ```

3. **Scenario incidents**:
   | Scenario | Tác động | Cách detect |
   |----------|---------|------------|
   | `rag_slow` | RAG retrieval latency tăng | Trace waterfall: RAG span dài bất thường |
   | `tool_fail` | Tool call thất bại | Error logs + error_rate spike |
   | `cost_spike` | Token usage tăng đột ngột | Cost metric tăng, trace có nhiều tokens |

4. **Incident Debug Flow**:
   ```
   Inject incident (rag_slow)
     → Latency tăng (metrics)
       → Check traces (Langfuse) → RAG span dài
         → Check logs (logs.jsonl) → tìm pattern
           → Root cause: retrieve() chậm
             → Fix: disable incident hoặc optimize RAG
   ```

5. **Viết debug guide** cho team (để Member E đưa vào report):
   - Ghi lại root cause của từng scenario
   - Ghi lại trace IDs + log lines dùng làm bằng chứng
   - Đề xuất preventive measures

#### Điền vào blueprint-template.md (phần Member D)
```
### [MEMBER_D_NAME]
- [TASKS_COMPLETED]: Mô tả việc setup load test + incident injection
- [EVIDENCE_LINK]: Link commit hoặc PR cụ thể
```

#### Checkpoint để verify đã xong
- [ ] `python scripts/load_test.py --concurrency 5` chạy thành công
- [ ] Incident toggle hoạt động qua cả script lẫn API
- [ ] `GET /metrics` → thấy traffic tăng sau load test
- [ ] `GET /health` → incidents status hiển thị đúng

---

### 👤 Member E — Dashboard + Evidence
**Trách nhiệm**: Xây dựng 6-panel dashboard + thu thập screenshots evidence.

#### File cần làm việc
| File | Việc cần làm |
|------|-------------|
| `docs/dashboard-spec.md` | Đọc spec (đã có sẵn) |
| Dashboard tool (Grafana/Langfuse built-in) | Build 6 panels |

#### Công việc chi tiết

1. **Dashboard Spec** — 6 panels bắt buộc:
   | # | Panel | Metrics | Unit | Threshold/SLO |
   |---|-------|--------|------|---------------|
   | 1 | Latency P50/P95/P99 | `latency_p50/p95/p99` | ms | SLO line: 3000ms (P95) |
   | 2 | Traffic / QPS | `traffic` | req/s | — |
   | 3 | Error Rate + Breakdown | `error_breakdown` | % | SLO line: 2% |
   | 4 | Cost over Time | `avg_cost_usd`, `total_cost_usd` | USD | SLO line: $2.5/day |
   | 5 | Tokens In/Out | `tokens_in_total`, `tokens_out_total` | tokens | — |
   | 6 | Quality Proxy | `quality_avg` | score 0-1 | SLO line: 0.75 |

2. **Dashboard quality bar**:
   - Default time range: 1 giờ
   - Auto refresh: 15-30 giây
   - Visible SLO threshold line
   - Units rõ ràng
   - ≤ 6-8 panels trên main layer

3. **Evidence collection** — Screenshots cần thu thập (`docs/grading-evidence.md`):
   ```
   ✅ BẮT BUỘC:
   - Langfuse trace list ≥ 10 traces
   - Một full trace waterfall
   - JSON log có correlation_id
   - Log line thể hiện PII redaction
   - Dashboard ≥ 6 panels
   - Alert rules với runbook link

   ✅ TÙY CHỌN (bonus):
   - Incident before/after fix
   - Cost comparison before/after optimization
   - Auto-instrumentation proof
   ```

4. **Thu thập screenshots**:
   - Lưu vào thư mục `evidence/` hoặc `screenshots/`
   - Đặt tên file rõ ràng: `trace-list-10-items.png`, `log-correlation-id.png`
   - Update `blueprint-template.md` với đường dẫn file

#### Điền vào blueprint-template.md (phần Member E)
```
### [MEMBER_E_NAME]
- [TASKS_COMPLETED]: Mô tả việc xây dựng dashboard + thu thập evidence
- [EVIDENCE_CORRELATION_ID_SCREENSHOT]: [Path]
- [EVIDENCE_PII_REDACTION_SCREENSHOT]: [Path]
- [EVIDENCE_TRACE_WATERFALL_SCREENSHOT]: [Path]
- [DASHBOARD_6_PANELS_SCREENSHOT]: [Path]
- [ALERT_RULES_SCREENSHOT]: [Path]
- [EVIDENCE_LINK]: [Link commit hoặc PR]
```

#### Checkpoint để verify đã xong
- [ ] Dashboard có đủ 6 panels
- [ ] Mỗi panel có đơn vị (ms, %, USD, tokens)
- [ ] Có SLO threshold line trên latency/error/cost panels
- [ ] Auto refresh enable
- [ ] Screenshots được lưu + link trong blueprint-template.md

---

### 👤 Member F — Blueprint + Demo Lead
**Trách nhiệm**: Tổng hợp báo cáo nhóm + dẫn demo + điều phối team.

#### File cần làm việc
| File | Việc cần làm |
|------|-------------|
| `docs/blueprint-template.md` | Điền toàn bộ sections |
| Toàn bộ repo | Review lại tất cả components |

#### Công việc chi tiết

1. **Điền blueprint-template.md** — Phải có đầy đủ:

   **Section 1: Team Metadata**
   ```markdown
   - [GROUP_NAME]: Tên nhóm
   - [REPO_URL]: GitHub URL
   - [MEMBERS]: Danh sách 6 thành viên + role
   ```

   **Section 2: Group Performance**
   ```markdown
   - [VALIDATE_LOGS_FINAL_SCORE]: X/100  ← chạy scripts/validate_logs.py
   - [TOTAL_TRACES_COUNT]: N            ← đếm trên Langfuse
   - [PII_LEAKS_FOUND]: N               ← từ validate_logs.py
   ```

   **Section 3: Technical Evidence**
   - Điền đường dẫn screenshots từ Member E
   - Điền SLO table với current values
   - Điền sample runbook link

   **Section 4: Incident Response**
   ```markdown
   - [SCENARIO_NAME]: rag_slow
   - [SYMPTOMS_OBSERVED]: Latency P95 tăng từ 200ms → 5000ms
   - [ROOT_CAUSE_PROVED_BY]: Trace ID xyz → RAG span 4900ms / total 5000ms
   - [FIX_ACTION]: Disable rag_slow incident
   - [PREVENTIVE_MEASURE]: Add RAG timeout + fallback
   ```

   **Section 5: Individual Contributions**
   - Tổng hợp từ tất cả Members A-E
   - Merge các `[EVIDENCE_LINK]` lại

   **Section 6: Bonus Items**
   - Cost optimization (Member D/ Member A)
   - Audit logs (Member A)
   - Custom metrics (Member B)

2. **Demo script** — Chuẩn bị trước:
   ```
   DEMO FLOW (15-20 phút):

   [0:00-2:00] Giới thiệu nhóm + repo
   [2:00-5:00] Member A: Show logging + PII redaction
     - Run: python scripts/load_test.py
     - Show: data/logs.jsonl (correlation_id, redaction)
     - Show: python scripts/validate_logs.py → ≥80/100

   [5:00-8:00] Member B: Show Langfuse tracing
     - Show: Langfuse dashboard ≥ 10 traces
     - Show: 1 trace waterfall + giải thích spans

   [8:00-10:00] Member C: Show SLO + Alerts
     - Show: SLO table với current values
     - Show: 3 alert rules + runbook links

   [10:00-13:00] Member D: Show incident injection + debug
     - Enable rag_slow: curl -X POST .../incidents/rag_slow/enable
     - Run load test → latency spike
     - Trace → RAG span dài
     - Logs → correlation_id trace được
     - Disable rag_slow

   [13:00-16:00] Member E: Show dashboard + evidence
     - Show: 6-panel dashboard
     - Show: screenshots evidence

   [16:00-20:00] Member F: Tổng kết + Q&A
     - Show: blueprint-template.md hoàn chỉnh
     - Q&A
   ```

3. **Điều phối team**:
   - Gặp team trước 1 ngày → review checklist
   - Đảm bảo mỗi người commit ít nhất 1 lần vào Git
   - Backup: screenshots, Langfuse export, logs.jsonl

4. **Pre-demo checklist**:
   - [ ] App chạy ổn định
   - [ ] Tất cả 6 members đã commit
   - [ ] `validate_logs.py` → ≥ 80/100
   - [ ] Langfuse có ≥ 10 traces
   - [ ] Dashboard 6 panels + screenshots
   - [ ] Alert rules + runbooks
   - [ ] Incident debug đã test thành công
   - [ ] `blueprint-template.md` đầy đủ

#### Điền vào blueprint-template.md (phần Member F)
```
### [MEMBER_F_NAME]
- [TASKS_COMPLETED]: Tổng hợp blueprint + dẫn demo
- [EVIDENCE_LINK]: Link commit/PR tổng hợp
```

---

## 📊 Yêu cầu đạt điểm — Tổng hợp

| Criteria | Điểm | Verifier |
|----------|------|----------|
| `validate_logs.py` score ≥ 80/100 | Group (30đ) | Member A |
| ≥ 10 traces Langfuse | Group (30đ) | Member B |
| PII redact hoàn toàn | Group (30đ) | Member A |
| Dashboard 6 panels + SLO line | Group (30đ) | Member E |
| ≥ 3 alert rules + runbook | Group (30đ) | Member C |
| Incident root cause đúng | Group (10đ) | Member D |
| Live demo mượt mà | Group (20đ) | Member F |
| **Individual report chi tiết** | **Individual (20đ)** | **Mọi member** |
| **Git commits/PRs cụ thể** | **Individual (20đ)** | **Mọi member** |

### Bonus (10đ max)
| Bonus | Điểm | Ai làm |
|-------|------|--------|
| Cost optimization (before/after) | +3đ | Member A/D |
| Dashboard đẹp, chuyên nghiệp | +3đ | Member E |
| Auto-instrumentation | +2đ | Member B |
| Audit logs riêng | +2đ | Member A |

---

## 📋 Global Checklist — Tất cả members

```
SETUP
[ ] Tạo .env từ .env.example
[ ] Điền LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY
[ ] pip install -r requirements.txt
[ ] uvicorn app.main:app --reload ✅ chạy được

LOGGING + PII (Member A)
[ ] structlog pipeline đúng thứ tự
[ ] scrub_event chạy trước JSONRenderer
[ ] PII patterns đầy đủ (email, phone, CCCD, CC, passport, address)
[ ] validate_logs.py → PII score = PASS

TRACING (Member B)
[ ] tracing_enabled() = True
[ ] ≥ 10 traces trên Langfuse
[ ] Trace có tags, user_id hash, session_id

SLO + ALERTS (Member C)
[ ] slo.yaml điền targets thực tế
[ ] alert_rules.yaml có 3 rules
[ ] docs/alerts.md có runbook cho 3 alerts
[ ] Runbook links khớp với alert_rules.yaml

LOAD TEST + INCIDENT (Member D)
[ ] load_test.py chạy --concurrency 5
[ ] inject_incident.py hoạt động
[ ] Incident debug flow đã test

DASHBOARD + EVIDENCE (Member E)
[ ] Dashboard 6 panels đủ
[ ] Mỗi panel có unit + SLO line
[ ] Screenshots evidence lưu đủ
[ ] Đường dẫn trong blueprint-template.md

BLUEPRINT + DEMO (Member F)
[ ] blueprint-template.md đầy đủ
[ ] Tất cả 6 members đã commit
[ ] Demo script chạy thử
[ ] Backup sẵn sàng

FINAL
[ ] python scripts/validate_logs.py → ≥80/100
[ ] Langfuse ≥ 10 traces ✅
[ ] Dashboard 6 panels ✅
[ ] Alert rules ✅
[ ] blueprint-template.md ✅
```

---

## 🛠️ Troubleshooting

| Vấn đề | Nguyên nhân | Fix |
|--------|-------------|-----|
| Trace không lên Langfuse | `.env` thiếu LANGFUSE keys | Thêm vào `.env`, restart app |
| validate_logs score < 80 | Missing correlation_id hoặc enrichment | Check middleware `bind_contextvars` |
| PII vẫn leak | Regex không cover edge case | Thêm pattern vào `pii.py` → commit |
| Logs.jsonl trống | `LOG_PATH` sai hoặc quyền ghi | `data/logs.jsonl` phải tồn tại |
| Alert không fire | Threshold quá cao/thấp | Điều chỉnh `config/alert_rules.yaml` |
| Incident không affect | Toggle chưa enable đúng | Check `GET /health` → incidents status |
| Dashboard panel trống | Metrics chưa có data | Chạy load test trước |
| Langfuse 404 error | Sai LANGFUSE_HOST hoặc credentials | Check `.env` LANGFUSE_* vars |

---

*Generated: 2026-04-20 — Lab13-C401-E4 Technical Handoff v2*
*Nội dung đầy đủ cho 6 members: A(logging+PII) · B(tracing) · C(SLO+alerts) · D(load test+incident) · E(dashboard+evidence) · F(blueprint+demo)*