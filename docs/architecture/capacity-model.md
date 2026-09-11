# Capacity Model

## Purpose
This document projects infrastructure capacity requirements at 12, 24, and 36 months to ensure the platform scales cost-effectively while meeting SLOs defined in `nfr.md`.

## Current Baseline (Month 0)

| Metric | Value | Notes |
|--------|-------|-------|
| Data sources | 1 (FRED) | Daily frequency, ~50 series |
| Daily ingestion volume | ~50 KB | Raw JSON payloads |
| Monthly storage (Bronze) | ~1.5 MB | Immutable Parquet with provenance |
| Daily pipeline runs | 1 | FRED connector |
| Peak memory usage | ~256 MB | Dagster + dbt execution |
| Query latency (P95) | <50 ms | Gold layer, local MinIO |

## Growth Assumptions

### Data Source Expansion
- **Month 12**: 5 sources (FRED, Eurostat, ECB, BEA, BLS)
- **Month 24**: 12 sources (add IMF, World Bank, national statistics offices)
- **Month 36**: 25+ sources (comprehensive global coverage)

### Frequency & Volume
- Average series per source: 100 (Month 12), 300 (Month 24), 800 (Month 36)
- Average observations per series: 500 (monthly/quarterly data aggregated)
- Payload overhead: 2x for provenance metadata, 3x for Bronze→Silver→Gold materialization

### Query Load
- Internal analysts: 5 (Month 12), 15 (Month 24), 40 (Month 36)
- Queries per analyst per day: 20
- Dashboard refreshes: 50/day (Month 12), 200/day (Month 24), 500/day (Month 36)

## Projected Capacity Requirements

### Month 12

| Resource | Requirement | Headroom (vs. baseline) | Cost Estimate (Monthly) |
|----------|-------------|-------------------------|-------------------------|
| Storage (Bronze) | 50 MB | 33x | $0.50 (S3 IA) |
| Storage (Silver) | 150 MB | 33x | $1.50 (S3 Standard) |
| Storage (Gold) | 75 MB | 33x | $0.75 (S3 Standard) |
| Compute (ingestion) | 512 MB RAM, 0.5 vCPU | 2x | $5 (spot EC2) |
| Compute (transformation) | 1 GB RAM, 1 vCPU | 4x | $10 (on-demand EC2) |
| Compute (query serving) | 2 GB RAM, 1 vCPU | 8x | $15 (RDS t3.small) |
| Network egress | 5 GB/month | 50x | $0.50 |
| **Total** | | | **~$28/month** |

### Month 24

| Resource | Requirement | Headroom (vs. baseline) | Cost Estimate (Monthly) |
|----------|-------------|-------------------------|-------------------------|
| Storage (Bronze) | 200 MB | 133x | $2.00 (S3 IA) |
| Storage (Silver) | 600 MB | 133x | $6.00 (S3 Standard) |
| Storage (Gold) | 300 MB | 133x | $3.00 (S3 Standard) |
| Compute (ingestion) | 1 GB RAM, 1 vCPU | 4x | $10 (spot EC2) |
| Compute (transformation) | 2 GB RAM, 2 vCPU | 8x | $25 (on-demand EC2) |
| Compute (query serving) | 4 GB RAM, 2 vCPU | 16x | $40 (RDS t3.medium) |
| Network egress | 20 GB/month | 200x | $2.00 |
| **Total** | | | **~$88/month** |

### Month 36

| Resource | Requirement | Headroom (vs. baseline) | Cost Estimate (Monthly) |
|----------|-------------|-------------------------|-------------------------|
| Storage (Bronze) | 800 MB | 533x | $8.00 (S3 IA) |
| Storage (Silver) | 2.4 GB | 533x | $24.00 (S3 Standard) |
| Storage (Gold) | 1.2 GB | 533x | $12.00 (S3 Standard) |
| Compute (ingestion) | 2 GB RAM, 2 vCPU | 8x | $25 (spot EC2) |
| Compute (transformation) | 4 GB RAM, 4 vCPU | 16x | $60 (on-demand EC2) |
| Compute (query serving) | 8 GB RAM, 4 vCPU | 32x | $100 (RDS t3.large) |
| Network egress | 100 GB/month | 1000x | $9.00 |
| **Total** | | | **~$218/month** |

## Scaling Triggers & Actions

| Metric | Threshold | Action | Automation Level |
|--------|-----------|--------|------------------|
| Storage utilization | >70% of tier limit | Expand S3 bucket lifecycle policy | Automated (Terraform) |
| Query latency P95 | >200 ms for 7 days | Scale RDS instance class | Manual (capacity review) |
| Pipeline duration | >30 min for daily run | Add parallelization or spot fleet | Manual (architecture review) |
| Memory pressure | >80% sustained | Increase container limits | Automated (K8s HPA in Phase 3) |
| Cost variance | >20% vs. projection | Investigate anomalies, adjust forecasts | Manual (monthly review) |

## Cost Optimization Strategies

1. **Storage Tiering**: Move Bronze data >90 days old to S3 Glacier Instant Retrieval ($0.004/GB/month)
2. **Spot Instances**: Run stateless ingestion containers on spot (70% savings)
3. **Query Caching**: Materialize frequent Gold-layer aggregations (reduce compute 40%)
4. **Data Partitioning**: Partition Silver/Gold by `as_of_date` to prune scan scope
5. **Compression**: Use ZSTD for Parquet (30% size reduction vs. SNAPPY)

## Monitoring & Alerting

- **Daily**: Storage growth rate, pipeline duration, query count
- **Weekly**: Cost vs. budget, latency percentiles, error rates
- **Monthly**: Capacity review meeting, forecast adjustment, scaling decisions

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-09-11 | 1.0 | Platform Team | Initial capacity model |

---

**Related Documents**: `nfr.md` (NFR-PERF-001, NFR-COST-001), `architecture/overview.md`, `runbooks/capacity-scaling.md`
