# Capacity Model: Local Laptop MVP

## 1. Executive Summary
This document defines the capacity planning strategy for the **Finance Data Engineering Platform** during its **Phase 1 (Local MVP)** lifecycle. Unlike cloud-native architectures that scale horizontally via auto-scaling groups, this system is constrained by the physical limits of a single developer laptop.

**Primary Constraint:** Hardware resources (RAM, CPU cores, Disk I/O) of the host machine.
**Scaling Strategy:** Vertical optimization (query tuning, partitioning) and batch size management, not horizontal scaling.
**Target Horizon:** 12 months of operation on local hardware before requiring migration to cloud infrastructure.

---

## 2. Current Baseline (Month 0)
**Hardware Assumptions (Typical Developer Laptop):**
- **CPU:** 8-12 Cores (e.g., M2/M3 Pro or Intel i7/i9)
- **RAM:** 16GB - 32GB Unified Memory
- **Storage:** 512GB - 1TB NVMe SSD (Shared with OS and other apps)
- **Network:** Standard Broadband (Asymmetric upload/download)

**Workload Profile:**
- **Sources:** 1 Primary Source (FRED API) + 1 Secondary (Eurostat - Phase 2).
- **Frequency:** Daily batches (T+1).
- **Data Volume:** ~50MB - 200MB raw JSON per day.
- **Processed Volume:** ~500MB - 2GB Parquet/Iceberg per year.

**Resource Utilization (Estimated):**
| Component | Idle | Peak (Pipeline Run) | Limit |
| :--- | :--- | :--- | :--- |
| **RAM** | 4 GB | 10-12 GB | 16 GB (Critical) |
| **CPU** | 5% | 60-80% (Multi-core parallelism) | 100% |
| **Disk** | 200 GB Used | +2 GB/day | 512 GB Total |
| **Docker** | 1 GB | 4-6 GB (Overhead) | Shared with RAM |

---

## 3. Growth Projections & Bottlenecks

### 3.1 Month 6: The "Data Accumulation" Phase
- **Volume:** ~500MB raw data accumulated. Processed history ~10GB.
- **Risk:** Query latency in DuckDB/Parquet may increase as file counts grow without partitioning.
- **Bottleneck:** **Disk I/O**. Reading thousands of small files slows down validation.
- **Mitigation:**
  - Enforce strict partitioning strategy (`year=/month=/day=`).
  - Implement "Compaction" jobs in dbt to merge small files weekly.

### 3.2 Month 12: The "Memory Wall" Phase
- **Volume:** ~1GB raw data accumulated. Processed history ~25GB+.
- **Risk:** Loading full historical datasets for re-validation exceeds available RAM (OOM Kill).
- **Bottleneck:** **RAM**. Dagster assets attempting to load too much data into Pandas/DataFrames.
- **Mitigation:**
  - Switch to streaming iterators where possible (do not load full DFs).
  - Increase swap space (virtual memory) on host OS (performance trade-off).
  - Prune "Dev/Test" data regularly; keep only production-grade snapshots.

### 3.3 Month 18+: The "Migration Trigger"
- **Trigger Event:** Pipeline runtime exceeds 4 hours OR frequent OOM crashes.
- **Decision Point:** Migrate to Cloud (AWS/GCP) or dedicated On-Prem server.
- **Action:** Activate Phase 2 (Cloud-Native) architecture plan.

---

## 4. Scaling Strategies (Local Context)

Since we cannot add more servers, we must optimize the existing node:

### 4.1 Vertical Optimization (Software Level)
1. **Columnar Storage:** Strict enforcement of Parquet format (never CSV for storage).
2. **Predicate Pushdown:** Ensure DuckDB/dbt filters data *before* loading into memory.
3. **Parallelism Limits:** Configure Dagster `max_concurrent` runs to match CPU core count minus 2 (reserve for OS).
   ```yaml
   # dagster.yaml snippet
   run_launcher:
     module: dagster.core.launcher
     class: DefaultRunLauncher
   # Limit concurrent execution to prevent thrashing
