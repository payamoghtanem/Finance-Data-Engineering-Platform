# Runbook: RUNBOOK-002 - Capacity Scaling

**Owner**: Platform Team  
**Last Reviewed**: 2026-09-11  
**Next Review**: 2026-12-11 (quarterly)  
**Severity Level**: P2  
**Estimated Execution Time**: 30-60 minutes  

---

## 1. Overview

**Description**:  
This runbook covers procedures for scaling platform capacity when resource utilization exceeds thresholds defined in `docs/architecture/capacity-model.md`. Covers storage, compute, and query layer scaling.

**Trigger Conditions**:  
- Storage utilization >70% of tier limit (alert: `capacity-storage-threshold`)
- Query latency P95 >200 ms for 7 consecutive days (alert: `query-latency-slo-breach`)
- Pipeline duration >30 min for daily run (alert: `pipeline-duration-warning`)
- Memory pressure >80% sustained for 1 hour (alert: `container-memory-pressure`)

**Expected Outcome**:  
Resource capacity increased to bring utilization below 60% with 6-month growth headroom.

---

## 2. Prerequisites

### 2.1 Access Requirements

| System | Access Level | How to Obtain |
|--------|--------------|---------------|
| AWS Console | Admin | IAM role assignment via Okta |
| Terraform Cloud | Admin | Team membership in `platform-engineering` |
| RDS Console | DBAdmin | IAM role `rds-admin` |
| Dagster UI | Operator | Added to `dagster-operators` Slack group |

### 2.2 Tools Required

- [ ] AWS CLI v2 (`aws --version`)
- [ ] Terraform CLI v1.5+ (`terraform --version`)
- [ ] kubectl (Phase 3+)
- [ ] Access to Grafana dashboard: `Platform Capacity`
- [ ] Communication channel: `#platform-alerts` Slack channel

### 2.3 Related Documentation

- `docs/architecture/capacity-model.md` - Growth projections and thresholds
- `docs/architecture/overview.md` - System architecture
- `infra/terraform/` - IaC templates
- Grafana Dashboard: `Platform Capacity` (ID: TBD)

---

## 3. Diagnosis

### 3.1 Initial Assessment

```bash
# Command 1: Check S3 bucket sizes
aws s3api get-bucket-metrics --bucket finance-data-bronze --period P7D
# Expected: JSON with StorageBytes trend

# Command 2: Check RDS instance metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name ReadLatency \
  --dimensions Name=DBInstanceIdentifier,Value=finance-gold-db \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 \
  --statistics Average
# Expected: Time-series data showing latency trend

# Command 3: Check Dagster pipeline durations
dagster asset list --prefix fred | xargs -I {} dagster asset materialize --async {}
# Or query Dagster GraphQL API for run durations
```

### 3.2 Decision Tree

```
Is storage utilization >70%?
├─ Yes → Is Bronze data >90 days old?
│   ├─ Yes → Execute Section 4.1 (Storage Tiering)
│   └─ No → Execute Section 4.2 (Bucket Expansion)
└─ No → Is query latency P95 >200ms?
    ├─ Yes → Execute Section 4.3 (RDS Scale-Up)
    └─ No → Is pipeline duration >30min?
        ├─ Yes → Execute Section 4.4 (Compute Parallelization)
        └─ No → False positive, monitor for 24h
```

### 3.3 Common False Positives

| Symptom | Actual Cause | How to Distinguish |
|---------|--------------|-------------------|
| Storage spike | One-time backfill job | Check `operation_type` tag in S3 inventory |
| Latency spike | Single slow query | Check query distribution; P99 >> P95 indicates outlier |
| Memory pressure | Leaky test container | Check container age; restart if >7 days |

---

## 4. Resolution Procedures

### 4.1 Scenario A: Storage Tiering (Bronze data >90 days)

**Steps**:

1. **Identify objects older than 90 days**
   ```bash
   aws s3api list-objects-v2 \
     --bucket finance-data-bronze \
     --query "Contents[?LastModified<='$(date -u -d '90 days ago' +%Y-%m-%dT%H:%M:%SZ)'].Key" \
     --output text > /tmp/tier-candidates.txt
   ```
   **Expected Output**: List of object keys ( ~500-1000 keys)
   ⚠️ **Warning**: Do NOT delete objects; only change storage class

2. **Apply Glacier Instant Retrieval tier**
   ```bash
   cat /tmp/tier-candidates.txt | xargs -n 100 aws s3api copy-object \
     --bucket finance-data-bronze \
     --copy-source finance-data-bronze/<key> \
     --key <key> \
     --storage-class GLACIER_INSTANT_RETRIEVAL
   ```

3. **Verify tiering applied**
   ```bash
   aws s3api head-object --bucket finance-data-bronze --key <sample-key> \
     --query 'StorageClass'
   ```
   **Success Criteria**: Returns `"GLACIER_INSTANT_RETRIEVAL"`

4. **Update Terraform lifecycle policy**
   ```hcl
   # infra/terraform/modules/storage/s3-lifecycle.tf
   # Add rule for automatic tiering after 90 days
   ```
   ```bash
   cd infra/terraform && terraform apply -target module.storage
   ```

### 4.2 Scenario B: Bucket Expansion (Active storage growth)

**Steps**:

1. **Check current bucket quota**
   ```bash
   aws s3api get-bucket-policy --bucket finance-data-bronze
   ```

2. **Request quota increase (if using VPC endpoint limits)**
   - Navigate to AWS Service Quotas console
   - Search "S3 VPC endpoint"
   - Request increase from [current] to [current × 2]
   - Justification: "Organic data growth per capacity model"

3. **Enable S3 Intelligent Tiering (optional)**
   ```bash
   aws s3api put-bucket-lifecycle-configuration \
     --bucket finance-data-bronze \
     --lifecycle-configuration file://intel-tiering.json
   ```

### 4.3 Scenario C: RDS Scale-Up (Query latency breach)

**Steps**:

1. **Check current instance class**
   ```bash
   aws rds describe-db-instances \
     --db-instance-identifier finance-gold-db \
     --query 'DBInstances[0].DBInstanceClass'
   # Expected: "db.t3.small" or similar
   ```

2. **Schedule maintenance window**
   - Coordinate with analytics team via `#analytics-users` Slack
   - Choose low-traffic window (typically Saturday 02:00-04:00 UTC)

3. **Modify instance class**
   ```bash
   aws rds modify-db-instance \
     --db-instance-identifier finance-gold-db \
     --db-instance-class db.t3.medium \
     --apply-immediately
   # For production: use --no-apply-immediately + maintenance window
   ```

4. **Monitor failover**
   ```bash
   watch aws rds describe-db-instances \
     --db-instance-identifier finance-gold-db \
     --query 'DBInstances[0].DBInstanceStatus'
   ```
   **Success Criteria**: Status returns `available` within 5-10 minutes

5. **Validate latency improvement**
   - Wait 1 hour for CloudWatch metrics
   - Check Grafana dashboard: P95 latency should drop <100ms

### 4.4 Scenario D: Compute Parallelization (Pipeline duration breach)

**Steps**:

1. **Identify bottleneck assets**
   ```bash
   dagster asset list --prefix fred --sort-by materialization_time
   ```

2. **Enable parallel execution in Dagster**
   ```python
   # pipelines/dagster/orchestration.py
   # Update Definitions to allow concurrent runs
   defs = Definitions(
     assets=[...],
     executor_def=multiprocess_executor.configured({"max_concurrent": 4})
   )
   ```

3. **Deploy updated orchestration**
   ```bash
   cd /workspace && git commit -m "Enable parallel asset execution"
   git push origin main
   # CI/CD will deploy via GitHub Actions
   ```

4. **Monitor pipeline duration**
   - Check Dagster UI for next scheduled run
   - Duration should decrease by ~60% with 4x parallelism

---

## 5. Rollback Procedure

If scaling causes issues:

### Immediate Rollback (RDS)
```bash
aws rds modify-db-instance \
  --db-instance-identifier finance-gold-db \
  --db-instance-class db.t3.small \
  --apply-immediately
```

### Revert Terraform Changes
```bash
cd infra/terraform
git revert HEAD
terraform apply
```

### Disable Parallelism
```python
# Revert executor config to max_concurrent: 1
```

**Escalation**:
- Contact: Platform Lead (@platform-lead on Slack)
- Channel: `#platform-incidents`
- Information: Instance ID, timestamp, error messages from CloudWatch

---

## 6. Post-Incident Actions

### 6.1 Validation

- [ ] Confirm storage utilization <60% (or latency <100ms P95)
- [ ] Verify downstream dashboards loading normally
- [ ] Check Grafana alerts cleared
- [ ] Confirm no cost anomaly alerts (budget variance <10%)

### 6.2 Communication

- [ ] Notify stakeholders in `#platform-updates` Slack
- [ ] Update capacity model if projections were inaccurate
- [ ] Log action in incident tracker (Jira/Linear)

### 6.3 Documentation Updates

- [ ] Was this runbook sufficient? ☐ Yes ☐ No
- [ ] Were there unexpected steps? ☐ Yes ☐ No
- [ ] Does this reveal automation opportunities? ☐ Yes ☐ No

**Create GitHub Issue if improvements needed**:
- Label: `runbook-improvement`, `capacity`
- Reference: This runbook + date executed
- Assignee: Platform Team

---

## 7. Appendix

### 7.1 Command Reference

| Command | Purpose | Safe to Run Multiple Times? |
|---------|---------|----------------------------|
| `aws s3api list-objects-v2` | Inventory bucket contents | ☐ Yes ☐ No |
| `aws rds modify-db-instance` | Scale RDS instance | ☐ Yes ☐ No (causes brief downtime) |
| `terraform apply` | Deploy infra changes | ☐ Yes ☐ No (idempotent) |

### 7.2 Cost Impact

| Action | Monthly Cost Increase | Approval Required |
|--------|----------------------|-------------------|
| S3 Tiering | -$0.50 (savings) | None |
| RDS t3.small → medium | +$25 | Platform Lead |
| RDS t3.medium → large | +$60 | Finance + Platform Lead |
| Parallel compute (spot) | +$15 | None |

### 7.3 Contact List

| Role | Primary | Backup | Escalation |
|------|---------|--------|------------|
| On-Call Engineer | PagerDuty: `platform-oncall` | Slack: `@platform-oncall` | Phone: +1-XXX-XXX-XXXX |
| Platform Lead | email: platform-lead@company.com | Slack: `@platform-lead` | - |
| FinOps Analyst | email: finops@company.com | Slack: `@finops` | - |

### 7.4 Revision History

| Date | Version | Author | Changes | Incident Reference |
|------|---------|--------|---------|-------------------|
| 2026-09-11 | 1.0 | Platform Team | Initial version | - |

---

**Related Runbooks**:
- RUNBOOK-003: Incident Response (for P0/P1 capacity crises)
- RUNBOOK-005: Secret Rotation (if scaling requires new credentials)
