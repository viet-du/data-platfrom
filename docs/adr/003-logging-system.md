# ADR-003: Logging System

## ADR-003: Choose Logging System for Data Platform

**Status:** Accepted  
**Date:** 2024-01-15  
**Deciders:** Data Platform Team

---

## Context

Cần một hệ thống logging để:
- Debug khi agent chạy
- Track pipeline execution
- Monitor system health
- Alert on errors
- Audit for compliance

## Decision Drivers

1. **Ease of use** - Dễ dàng implement và sử dụng
2. **Mac compatibility** - Development trên Mac
3. **Agent support** - Hỗ trợ debug khi agent chạy
4. **Scalability** - Có thể scale lên production
5. **Cost** - Miễn phí hoặc chi phí thấp

## Options Considered

### Option 1: Loguru + Loki (Chosen)

**Pros:**
- ✅ Loguru: Zero-config, beautiful output
- ✅ Loki: Lightweight, integrates with Grafana
- ✅ JSON output for production
- ✅ Easy to setup
- ✅ Free (self-hosted)

**Cons:**
- ❌ Loki requires separate setup
- ❌ Less enterprise features than ELK

**Cost:** $0 (self-hosted)

### Option 2: ELK Stack

**Pros:**
- ✅ Full-featured
- ✅ Great search
- ✅ Kibana dashboards

**Cons:**
- ❌ Heavy (Elasticsearch là resource-intensive)
- ❌ Complex setup
- ❌ Tốn RAM

**Cost:** $0 (self-hosted) nhưng tốn infrastructure

### Option 3: Python logging (built-in)

**Pros:**
- ✅ No extra dependencies
- ✅ Built-in

**Cons:**
- ❌ Verbose configuration
- ❌ Not structured by default
- ❌ Less features

**Cost:** $0

### Option 4: CloudWatch (AWS)

**Pros:**
- ✅ Native AWS integration
- ✅ Managed service

**Cons:**
- ❌ Vendor lock-in
- ❌ Chỉ work với AWS
- ❌ Tốn chi phí

**Cost:** Pay-per-use

### Option 5: Datadog

**Pros:**
- ✅ APM + Logs + Metrics
- ✅ Great UX

**Cons:**
- ❌ Đắt ($15/host/month)
- ❌ Overkill cho small setup

**Cost:** $15/host/month

## Decision

**Chosen: Loguru for application logging + Loki for log aggregation**

## Rationale

1. **Loguru simplicity** - Zero-config, great developer experience
2. **Loki lightweight** - Ít resource hơn Elasticsearch
3. **Grafana integration** - Centralized monitoring
4. **JSON output** - Sẵn sàng cho ELK/Logstash nếu cần
5. **Free** - Không tốn chi phí
6. **Mac-friendly** - Works trên Mac

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Application (Loguru)                                      │
│                                                             │
│  logger.info("Message", extra={"key": "value"})           │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  Transport Layer                                           │
│  ├── Console (colorized, for development)                  │
│  ├── File (rotated, for production)                        │
│  └── Loki (via Promtail, for aggregation)                  │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  Storage & Visualization                                   │
│  ├── Loki (log storage)                                    │
│  └── Grafana (log viewer + dashboards)                     │
└─────────────────────────────────────────────────────────────┘
```

## Log Format

### Development (Human-readable)

```
2024-01-15 10:30:00 | INFO     | ingestion.google_drive | Downloaded file | file_name=sales.csv duration_ms=1234
```

### Production (JSON)

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "logger": "ingestion.google_drive",
  "message": "Downloaded file",
  "context": {
    "file_name": "sales.csv",
    "duration_ms": 1234
  }
}
```

## Implementation

1. Install dependencies
2. Create `logging_config.py` with Loguru
3. Configure handlers (console, file, Loki)
4. Setup Loki + Grafana via Docker
5. Add structured logging throughout codebase
6. Create log analysis scripts

## Consequences

### Positive

- Easy to add logging anywhere (`logger.info("message")`)
- Beautiful output in development
- JSON format for production
- Scaled well with Loki
- Free to use

### Negative

- Loki setup requires Docker
- Additional infrastructure to maintain
- Need to monitor log storage growth

## Monitoring & Alerting

```python
# Setup alerts in Grafana
# Alert when:
# - ERROR rate > threshold
# - Pipeline duration > SLA
# - Missing data (no logs for > expected interval)
```

## Related Decisions

- ADR-001: Databricks Choice
- ADR-002: Google Drive Raw Layer
