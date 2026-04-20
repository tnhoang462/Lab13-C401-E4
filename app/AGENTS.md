# Yêu cầu Dashboard

- dashboard có thể monitoring được các thông tin trong file metrics.py
- có hiển thị alert theo config/alert_rules.yaml và slo theo config/slo.yaml
- dashboard làm với streamlit
- dashboard có thể tương tác với api của app để lấy dữ liệu
- có chức năng set up được thời gian refresh data
- có biểu đồ hiển thị p95, p99 của latency, error rate, cost, quality score
- có biểu đồ hiển thị số lượng request theo thời gian

---

# Implementation Plan — Streamlit Dashboard

Xây dựng dashboard Streamlit tại `app/dashboard.py` để monitoring chatbot RAG, lấy dữ liệu qua API `GET /metrics` và `GET /health`, hiển thị SLO từ `config/slo.yaml` và alerts từ `config/alert_rules.yaml`.

## File thay đổi

| File | Hành động |
|------|-----------|
| `app/dashboard.py` | Viết toàn bộ (hiện đang rỗng) |
| `requirements.txt` | Thêm `streamlit`, `pyyaml`, `plotly`, `streamlit-autorefresh` |

## Nguồn dữ liệu

| Nguồn | Dùng cho |
|-------|----------|
| `GET /metrics` (FastAPI) | Tất cả 6 panels |
| `GET /health` (FastAPI) | Incident status |
| `config/alert_rules.yaml` | Alert status badges |
| `config/slo.yaml` | SLO table |

## Layout tổng thể

```
┌────────────────────────────────────────────────┐
│  🧠 Lab13 Observability Dashboard              │
│  [Auto refresh: 5s / 15s / 30s / 60s]         │
├──────────────────┬─────────────────────────────┤
│  🚦 Alert Status │  📋 SLO Status Table        │
│  (4 badges)      │  (4 SLIs vs current values) │
├──────────────────┴─────────────────────────────┤
│  Panel 1: Latency P50/P95/P99 (bar chart)      │
│  Panel 2: Error Rate + Breakdown (pie)         │
├────────────────────────────────────────────────┤
│  Panel 3: Cost avg + total (metric cards)      │
│  Panel 4: Quality Score avg (gauge)            │
├────────────────────────────────────────────────┤
│  Panel 5: Traffic — Total requests (metric)    │
│  Panel 6: Tokens In / Out (bar chart)          │
└────────────────────────────────────────────────┘
```

## Chi tiết từng section

### Alert Status (từ `alert_rules.yaml`)
- Đọc 4 alert rules: `high_latency_p95`, `high_error_rate`, `cost_budget_spike`, `low_quality_score`
- So sánh với giá trị hiện tại từ `/metrics`
- Badge màu: 🔴 FIRING / 🟢 OK
- Thresholds: latency_p95 > 5000ms | error_rate > 5% | cost spike | quality_avg < 0.70

### SLO Status Table (từ `slo.yaml`)
- 4 SLIs: latency_p95_ms | error_rate_pct | daily_cost_usd | quality_score_avg
- Cột: SLI | Target | Current | Status (✅/❌)

### Panel 1 — Latency P50/P95/P99
- Source: `latency_p50`, `latency_p95`, `latency_p99`
- Dạng: Bar chart ngang, SLO line = 3000ms tại P95

### Panel 2 — Error Rate + Breakdown
- Source: `error_breakdown` (dict), `traffic`
- Dạng: Metric number + Pie chart breakdown
- SLO line: 2%

### Panel 3 — Cost
- Source: `avg_cost_usd`, `total_cost_usd`
- Dạng: 2 metric cards, reference SLO = $2.5/day

### Panel 4 — Quality Score
- Source: `quality_avg`
- Dạng: Gauge 0–1, SLO line = 0.75

### Panel 5 — Traffic
- Source: `traffic`
- Dạng: Metric card lớn (total requests)

### Panel 6 — Tokens In/Out
- Source: `tokens_in_total`, `tokens_out_total`
- Dạng: Bar chart ngang (2 bars)

### Auto-refresh
- Sidebar: chọn interval 5 / 15 / 30 / 60 giây
- Dùng `streamlit-autorefresh` hoặc `st.rerun()`

## Cách chạy

```powershell
# Terminal 1
uvicorn app.main:app --reload

# Terminal 2
streamlit run app/dashboard.py
```

## Verification

1. Gửi request qua Postman → Traffic tăng → Dashboard cập nhật
2. Enable incident `rag_slow` → Latency spike → Alert 🔴 FIRING
3. Kiểm tra SLO table hiển thị đúng current values


