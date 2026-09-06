# ADR-002: Google Drive Raw Layer

## ADR-002: Use Google Drive as Raw Data Storage Layer

**Status:** Accepted  
**Date:** 2024-01-15  
**Deciders:** Data Platform Team

---

## Context

Cần chọn giải pháp lưu trữ raw data (CSV, Excel files) trước khi ingest vào Databricks:

- Free storage cho raw data
- Dễ dàng upload files (non-technical users)
- Có thể track file changes
- Tích hợp với Google Workspace
- Mac-friendly

## Decision Drivers

1. **Cost** - Cần giải pháp miễn phí hoặc rẻ
2. **Accessibility** - Non-technical users cần upload files dễ dàng
3. **Integration** - Tích hợp với existing tools
4. **Audit** - Cần track ai upload, khi nào
5. **Mac support** - Developer dùng Mac

## Options Considered

### Option 1: Google Drive (Chosen)

**Pros:**
- ✅ 15GB free per account
- ✅ Google Shared Drive miễn phí (unlimited với business)
- ✅ Easy upload via web UI
- ✅ Có API để automate
- ✅ Version history có sẵn
- ✅ Có thể share với non-technical users

**Cons:**
- ❌ Giới hạn 15GB (cho personal) hoặc cần Shared Drive
- ❌ API rate limits
- ❌ Không phải designed cho data processing

**Cost:** $0-10/month

### Option 2: AWS S3

**Pros:**
- ✅ Designed cho data storage
- ✅ Cheap ($0.023/GB)
- ✅ Highly available
- ✅ Good API

**Cons:**
- ❌ Cần AWS account
- ❌ Không user-friendly cho non-technical
- ❌ Cần setup IAM, buckets

**Cost:** $0.023/GB/month

### Option 3: Dropbox

**Pros:**
- ✅ Easy to use
- ✅ Desktop sync tốt

**Cons:**
- ❌ Giới hạn storage (2GB free)
- ❌ API hạn chế
- ❌ Không có Shared Drive

**Cost:** $0-12/month

### Option 4: Local File System

**Pros:**
- ✅ Hoàn toàn miễn phí
- ✅ Fast

**Cons:**
- ❌ Khó share giữa nhiều users
- ❌ Không có API
- ❌ Không có version control

**Cost:** $0 (nhưng không scalable)

## Decision

**Chosen: Google Shared Drive**

## Rationale

1. **Free tier** - 15GB personal + unlimited Shared Drive (business)
2. **User-friendly** - Non-technical users có thể upload qua web
3. **API access** - Google Drive API cho automation
4. **Version history** - Track changes theo thời gian
5. **Sharing** - Dễ dàng share folders với team
6. **Mac native** - Google Drive app cho Mac

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Google Shared Drive: data-platform                        │
│                                                             │
│  ├── raw/                                                  │
│  │   ├── sources/                                          │
│  │   │   ├── sales/                                        │
│  │   │   ├── customers/                                    │
│  │   │   └── products/                                    │
│  │   ├── api_responses/                                    │
│  │   └── manual_uploads/                                  │
│  └── staging/                                             │
│      └── processed/                                        │
└─────────────────────────────────────────────────────────────┘
           │
           │ Python (Google Drive API)
           ▼
┌─────────────────────────────────────────────────────────────┐
│  Databricks Bronze Layer                                    │
│  ├── /bronze/tables/sales_raw/                            │
│  ├── /bronze/tables/customers_raw/                        │
│  └── /bronze/tables/products_raw/                         │
└─────────────────────────────────────────────────────────────┘
```

## Consequences

### Positive

- Raw data accessible cho tất cả team members
- Non-technical users có thể upload files
- Version history để track changes
- Miễn phí với Google Workspace

### Negative

- Google Drive không designed cho data processing
- Rate limits khi query qua API
- Cần maintain credentials

## Implementation

1. Tạo Google Shared Drive "data-platform"
2. Setup folder structure (raw/sources, etc.)
3. Tạo Service Account cho automation
4. Implement google_drive_sync module
5. Configure Airflow để poll và ingest files

## Security Considerations

- Service Account với read-only permissions
- Không share credentials với end users
- Files trong Shared Drive inherit team permissions
- Audit logs từ Google Admin

## Notes

- Nếu storage > 15GB, consider Google Workspace Business
- Nếu cần real-time ingestion, consider polling thường xuyên
- Khi scale, có thể transition sang S3/Cloud Storage
