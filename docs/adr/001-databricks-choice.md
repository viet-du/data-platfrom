# ADR-001: Databricks Choice

## ADR-001: Choose Databricks Community Edition as Primary Processing Platform

**Status:** Accepted  
**Date:** 2024-01-15  
**Deciders:** Data Platform Team

---

## Context

Cần chọn một nền tảng xử lý dữ liệu cho Data Platform với các yêu cầu:
- Miễn phí hoặc chi phí thấp
- Hỗ trợ Python và SQL
- Có khả năng mở rộng
- Dễ sử dụng cho người mới
- Tương thích với Mac

## Decision Drivers

1. **Budget constraint** - Cần giải pháp miễn phí hoặc chi phí thấp
2. **Technical capability** - Cần xử lý ETL, transformation, analytics
3. **Learning curve** - Team cần học nhanh
4. **Mac compatibility** - Developer dùng Mac
5. **Cloud storage** - Cần kết nối với cloud storage (Google Drive)

## Options Considered

### Option 1: Databricks Community Edition (Chosen)

**Pros:**
- ✅ Miễn phí vĩnh viễn
- ✅ Tích hợp sẵn Spark, Delta Lake, MLflow
- ✅ SQL Editor tốt
- ✅ Có Databricks Connect cho local development
- ✅ Dễ học, có nhiều tutorials

**Cons:**
- ❌ Giới hạn compute (1 cluster, 14 ngày)
- ❌ Giới hạn storage (20GB)
- ❌ Chỉ có 1 cluster tại một thời điểm

**Cost:** $0

### Option 2: AWS EMR

**Pros:**
- ✅ Miễn phí tier (tạm thời)
- ✅ Highly scalable

**Cons:**
- ❌ Phức tạp để setup
- ❌ Tốn thời gian học
- ❌ Cần quản lý infrastructure

**Cost:** $0.015-0.05/GBprocessed

### Option 3: Google Cloud Dataproc

**Pros:**
- ✅ Pay-per-use
- ✅ Tích hợp GCP

**Cons:**
- ❌ Cần GCP account
- ❌ Phức tạp hơn Databricks

**Cost:** $0.01-0.05/GBprocessed

### Option 4: Local Spark

**Pros:**
- ✅ Hoàn toàn miễn phí
- ✅ Không cần internet

**Cons:**
- ❌ Khó setup
- ❌ Không scale được
- ❌ Khó troubleshoot

**Cost:** $0 (nhưng tốn effort)

## Decision

**Chosen: Databricks Community Edition**

## Rationale

1. **Free forever** - Không phát sinh chi phí
2. **Easy to start** - Đăng ký, bắt đầu trong 5 phút
3. **Good for learning** - Nhiều tài liệu, tutorials
4. **Python native** - Dễ dàng sử dụng với existing Python code
5. **Delta Lake** - Native support cho modern data lakehouse
6. **MLflow built-in** - Sẵn sàng cho ML nếu cần

## Consequences

### Positive

- Team có thể bắt đầu ngay với $0
- Ít infrastructure để quản lý
- Dễ dàng chia sẻ notebooks với team

### Negative

- Giới hạn về storage và compute
- Khi scale lên production, cần upgrade lên paid plan
- Dependency vào cloud provider

## Implementation

1. Đăng ký Databricks Community Edition
2. Setup Databricks Connect cho local development
3. Tạo notebooks cho ingestion và transformation
4. Configure dbt-databricks cho transformations

## Notes

- Nếu storage > 20GB, có thể dùng Google Drive làm raw storage
- Nếu compute không đủ, có thể dùng Databricks Jobs thay vì notebooks
- Khi scale production, xem xét upgrade lên Databricks Pro hoặc Enterprise
