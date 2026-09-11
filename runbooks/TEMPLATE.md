# Runbook Template

## Purpose
This template ensures consistent, repeatable operational procedures for the Finance & Economic Data Platform. All runbooks must follow this structure to meet NFR-MAINT-001 (Maintainability) requirements.

---

## Runbook: [RUNBOOK-XXX] - [Title]

**Owner**: [Team/Role]  
**Last Reviewed**: [YYYY-MM-DD]  
**Next Review**: [YYYY-MM-DD] (quarterly)  
**Severity Level**: [P0/P1/P2/P3]  
**Estimated Execution Time**: [X minutes/hours]  

---

### 1. Overview

**Description**:  
[Brief description of what this runbook covers]

**Trigger Conditions**:  
[List the events, alerts, or conditions that initiate this procedure]

**Expected Outcome**:  
[What success looks like after execution]

---

### 2. Prerequisites

#### 2.1 Access Requirements

| System | Access Level | How to Obtain |
|--------|--------------|---------------|
| [e.g., AWS Console] | [e.g., ReadOnly, Admin] | [e.g., IAM role assignment via Okta] |
| [e.g., Dagster UI] | [e.g., Operator] | [e.g., Added to dagster-operators Slack group] |

#### 2.2 Tools Required

- [ ] CLI tool: `[command --version]`
- [ ] Access to [system/dashboard]
- [ ] Communication channel: [Slack channel, PagerDuty]

#### 2.3 Related Documentation

- [Link to architecture doc]
- [Link to threat model]
- [Link to monitoring dashboard]

---

### 3. Diagnosis

#### 3.1 Initial Assessment

```bash
# Command 1: Check system status
[command with expected output example]

# Command 2: Query logs
[command with expected output example]

# Command 3: Verify alert condition
[command with expected output example]
```

#### 3.2 Decision Tree

```
Is [condition A] true?
├─ Yes → Proceed to Section 4.1
└─ No → Is [condition B] true?
    ├─ Yes → Proceed to Section 4.2
    └─ No → Escalate to [Team/Person], stop here
```

#### 3.3 Common False Positives

| Symptom | Actual Cause | How to Distinguish |
|---------|--------------|-------------------|
| [Symptom] | [Root cause] | [Differentiating factor] |

---

### 4. Resolution Procedures

#### 4.1 [Scenario A: Most Common]

**Steps**:

1. **[Action]**  
   ```bash
   [exact command]
   ```
   **Expected Output**:  
   ```
   [example output]
   ```
   ⚠️ **Warning**: [Any risks or caveats]

2. **[Action]**  
   ```bash
   [exact command]
   ```

3. **[Verification]**  
   ```bash
   [command to confirm success]
   ```
   **Success Criteria**: [Specific metric/state change]

#### 4.2 [Scenario B: Alternative Path]

**Steps**:

1. **[Action]**  
   ...

---

### 5. Rollback Procedure

If resolution fails or causes unintended consequences:

1. **Immediate Action**:  
   ```bash
   [rollback command]
   ```

2. **Verification**:  
   ```bash
   [command to confirm rollback]
   ```

3. **Escalation**:  
   - Contact: [Name/Role]
   - Channel: [Slack/PagerDuty]
   - Information to provide: [List]

---

### 6. Post-Incident Actions

#### 6.1 Validation

- [ ] Confirm [metric] returned to baseline
- [ ] Verify [downstream system] operating normally
- [ ] Check [dashboard/alert] cleared

#### 6.2 Communication

- [ ] Notify stakeholders in #[Slack-channel]
- [ ] Update incident ticket #[ID]
- [ ] Schedule post-mortem if P0/P1

#### 6.3 Documentation Updates

- [ ] Was this runbook sufficient? ☐ Yes ☐ No
- [ ] Were there unexpected steps? ☐ Yes ☐ No
- [ ] Does this reveal a gap in automation? ☐ Yes ☐ No

**If any "No" or "Yes" above, create GitHub Issue**:  
- Label: `runbook-improvement`
- Reference: This runbook + incident ID
- Assignee: Runbook owner

---

### 7. Appendix

#### 7.1 Command Reference

| Command | Purpose | Safe to Run Multiple Times? |
|---------|---------|----------------------------|
| `[command]` | [Description] | ☐ Yes ☐ No |

#### 7.2 Contact List

| Role | Primary | Backup | Escalation |
|------|---------|--------|------------|
| On-Call Engineer | [PagerDuty] | [Slack] | [Phone] |
| Platform Lead | [Email] | [Slack] | - |
| Security Team | [Email] | - | [PagerDuty] |

#### 7.3 Revision History

| Date | Version | Author | Changes | Incident Reference |
|------|---------|--------|---------|-------------------|
| YYYY-MM-DD | 1.0 | [Name] | Initial version | - |

---

## Runbook Index

| ID | Title | Owner | Severity | Last Reviewed |
|----|-------|-------|----------|---------------|
| RUNBOOK-001 | [Template - This File] | Platform Team | N/A | 2026-09-11 |
| RUNBOOK-002 | Capacity Scaling | Platform Team | P2 | TBD |
| RUNBOOK-003 | Incident Response | Security Team | P0 | TBD |
| RUNBOOK-004 | Pipeline Failure Recovery | Data Engineering | P1 | TBD |
| RUNBOOK-005 | Secret Rotation | DevOps | P2 | TBD |

---

**Notes**:
- All runbooks must be reviewed quarterly
- Test runbooks annually via game-day exercises
- Store executed runbook logs in `/workspace/runbooks/executions/[YYYY-MM-DD]-[runbook-id].md`
