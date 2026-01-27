# Security Gates Rollout Plan

**Version:** 1.0.0
**Last Updated:** 2026-01-27
**Status:** Soft gates deployed (all gates informational only)

---

## Table of Contents

1. [Overview](#overview)
2. [Current Security Scanners](#current-security-scanners)
3. [Current State: Soft Gates](#current-state-soft-gates)
4. [Rollout Plan to Hard Gates](#rollout-plan-to-hard-gates)
5. [Criteria for Hard Gate Activation](#criteria-for-hard-gate-activation)
6. [Tuning False Positives](#tuning-false-positives)
7. [Monitoring & Reporting](#monitoring--reporting)
8. [Escalation & Exceptions](#escalation--exceptions)

---

## Overview

This document describes the security gates implemented in the CI/CD pipeline for content-generator, their current "soft gate" status, and the plan to progressively harden them into "hard gates" (build-blocking) once baseline stability is established.

**Philosophy:**
- **Soft gates first**: Gather data, understand baseline, tune false positives
- **Hard gates later**: Only after 2 consecutive weeks of clean scans with no findings
- **Gradual rollout**: Enable one gate at a time, monitor impact

**Current Status:**
- All 3 security gates deployed as soft gates (informational only)
- Gates run on every PR and push to main
- Reports uploaded as CI artifacts (30-day retention)
- No build failures from security findings

---

## Current Security Scanners

### 1. Bandit (Security Linting)

**Purpose:** Static analysis of Python code to identify common security issues

**What it detects:**
- Hardcoded passwords or secrets
- Use of insecure functions (e.g., `exec`, `eval`, `pickle`)
- SQL injection risks
- Path traversal vulnerabilities
- Insecure cryptography (MD5, weak random)
- Shell injection risks

**Command:**
```bash
bandit -r src -x tests -f txt -o reports/bandit_report.txt
```

**Exclusions:**
- `tests/` directory (test code not scanned)

**Configuration:**
- Default ruleset (all security checks enabled)
- Can be tuned via `.bandit` config file

**CI Integration:**
```yaml
- name: Run Bandit (Security Linting)
  continue-on-error: true  # Soft gate
  run: |
    bandit -r src -x tests -f txt -o reports/bandit_report.txt || true
```

### 2. pip-audit (Dependency Vulnerability Scan)

**Purpose:** Scan Python dependencies for known CVEs and security vulnerabilities

**What it detects:**
- Vulnerable package versions in `requirements.txt`
- Known CVEs from PyPI Advisory Database
- Outdated packages with security fixes available

**Command:**
```bash
pip-audit -r requirements.txt --desc -o reports/pip_audit_report.txt
```

**Data Sources:**
- PyPI Advisory Database
- OSV (Open Source Vulnerabilities)
- GitHub Security Advisories

**CI Integration:**
```yaml
- name: Run pip-audit (Dependency Vulnerability Scan)
  continue-on-error: true  # Soft gate
  run: |
    pip-audit -r requirements.txt --desc -o reports/pip_audit_report.txt || true
```

### 3. detect-secrets (Secret Scanning)

**Purpose:** Detect accidentally committed secrets, API keys, and credentials

**What it detects:**
- AWS keys
- API keys and tokens
- Private keys (RSA, SSH)
- High entropy strings (potential secrets)
- Generic secrets (passwords, tokens)

**Command:**
```bash
# Create baseline (first run)
detect-secrets scan --baseline .secrets.baseline --exclude-files 'reports/.*'

# Scan for new secrets
detect-secrets scan --baseline .secrets.baseline --exclude-files 'reports/.*'
```

**Exclusions:**
- `reports/` directory (test outputs, artifacts)

**Baseline Management:**
- Baseline file: `.secrets.baseline` (committed to repo)
- Contains known false positives (marked as safe)
- Updated when legitimate secrets are added (with review)

**CI Integration:**
```yaml
- name: Run detect-secrets (Secret Scanning)
  continue-on-error: true  # Soft gate
  run: |
    if [ ! -f .secrets.baseline ]; then
      detect-secrets scan --baseline .secrets.baseline --exclude-files 'reports/.*'
    fi
    detect-secrets scan --baseline .secrets.baseline --exclude-files 'reports/.*'
```

---

## Current State: Soft Gates

### What "Soft Gate" Means

**Definition:** Security gates run on every PR/push but do NOT fail the build

**Implementation:**
```yaml
continue-on-error: true  # Does not block merge
```

**Behavior:**
- Scanners execute and generate reports
- Reports uploaded as CI artifacts (30-day retention)
- Findings logged as GitHub notices (visible in CI logs)
- **Build PASSES regardless of findings**

### Why Soft Gates First?

1. **Establish Baseline**
   - Understand current security posture
   - Identify existing issues without blocking development
   - Measure scanning noise and false positive rate

2. **Tune Scanners**
   - Identify false positives
   - Configure exclusions and baselines
   - Adjust sensitivity levels

3. **Developer Onboarding**
   - Allow team to familiarize with security tools
   - Provide time to fix existing issues
   - Build muscle memory for security practices

4. **Gradual Hardening**
   - Prove stability over 2+ weeks
   - Ensure no legitimate code is blocked
   - Build confidence before making gates mandatory

### Current Reporting

**Where to Find Reports:**
```bash
# Download artifacts from GitHub Actions
# Navigate to: Actions → Workflow Run → Artifacts → security-reports

# Local reports (if running scripts/verify_all.ps1 with security gates)
cat reports/bandit_report.txt
cat reports/pip_audit_report.txt
cat reports/detect_secrets.json  # if run locally
```

**GitHub Notices:**
- Soft gate completion logged as `::notice::`
- Visible in CI logs: "Bandit scan completed (soft gate - does not fail build)"

---

## Rollout Plan to Hard Gates

### Phase 1: Soft Gates (Current) - COMPLETED

**Duration:** 2 weeks (2026-01-14 to 2026-01-27)

**Goals:**
- ✅ Deploy all 3 security gates as soft gates
- ✅ Collect baseline data
- ✅ Identify false positives

**Status:** COMPLETED (as of 2026-01-27)

### Phase 2: Baseline Stabilization (2 Weeks)

**Duration:** 2 weeks (2026-01-28 to 2026-02-10)

**Goals:**
- Monitor security reports for 2 consecutive weeks
- Fix all legitimate findings
- Tune false positives (update `.bandit`, `.secrets.baseline`)
- Document baseline state

**Exit Criteria:**
- Zero high-severity findings for 2 consecutive weeks
- Zero new secrets detected for 2 consecutive weeks
- False positive rate < 5%

**Actions:**
1. **Week 1 (2026-01-28 to 2026-02-03):**
   - Daily review of security reports
   - Fix high-severity findings (if any)
   - Mark false positives in baseline files
   - Document tuning decisions

2. **Week 2 (2026-02-04 to 2026-02-10):**
   - Continue monitoring
   - Verify no new findings
   - Confirm false positive tuning is stable
   - Prepare for hard gate activation

### Phase 3: Hard Gate Activation (Progressive Rollout)

**Duration:** 3 weeks (2026-02-11 to 2026-03-03)

#### Week 1: Enable detect-secrets Hard Gate (2026-02-11 to 2026-02-17)

**Rationale:** Secret detection is critical; false positives are rare once baseline is set

**Change:**
```yaml
- name: Run detect-secrets (Secret Scanning)
  continue-on-error: false  # HARD GATE ENABLED
  run: |
    detect-secrets scan --baseline .secrets.baseline --exclude-files 'reports/.*'
    # Exit code ≠ 0 will fail the build
```

**Monitoring:**
- Watch for unexpected build failures
- Review any new secret detections
- Adjust baseline if legitimate false positives emerge

**Rollback Plan:**
- If > 2 false positive build failures in the first week, revert to soft gate
- Investigate root cause, tune baseline, retry next week

#### Week 2: Enable pip-audit Hard Gate (2026-02-18 to 2026-02-24)

**Rationale:** Dependency vulnerabilities are critical; usually have clear remediation

**Change:**
```yaml
- name: Run pip-audit (Dependency Vulnerability Scan)
  continue-on-error: false  # HARD GATE ENABLED
  run: |
    pip-audit -r requirements.txt --desc
    # Exit code ≠ 0 will fail the build
```

**Exceptions:**
- Allow `--ignore-vuln <CVE-ID>` for known false positives or accepted risks
- Document exceptions in `pip-audit.toml` config file

**Monitoring:**
- Watch for vulnerability alerts from newly added dependencies
- Ensure upgrade paths exist for flagged packages
- Review any ignored vulnerabilities weekly

**Rollback Plan:**
- If critical dependency has no fix available, temporarily add to ignore list
- Document in security log with remediation timeline

#### Week 3: Enable Bandit Hard Gate (2026-02-25 to 2026-03-03)

**Rationale:** Code security issues require careful review; most likely to have false positives

**Change:**
```yaml
- name: Run Bandit (Security Linting)
  continue-on-error: false  # HARD GATE ENABLED
  run: |
    bandit -r src -x tests -f txt
    # Exit code ≠ 0 will fail the build
```

**Tuning:**
- Use `.bandit` config to skip specific tests if needed:
  ```yaml
  # .bandit
  skips: ['B101']  # Skip assert_used check (if legitimate)
  exclude_dirs: ['/tests/', '/archive/']
  ```

**Monitoring:**
- Watch for false positives in legitimate use cases (e.g., `subprocess.run` with validated inputs)
- Review all Bandit findings with security lens
- Document skip decisions in config with rationale

**Rollback Plan:**
- If > 3 false positive build failures in the first week, revert to soft gate
- Investigate root cause, add skips to `.bandit`, retry next week

### Phase 4: Continuous Monitoring (Ongoing)

**Start Date:** 2026-03-04 onwards

**Goals:**
- All 3 security gates are hard gates (blocking)
- Weekly review of security reports
- Quarterly security audit

**Ongoing Actions:**
- **Weekly:** Review security artifacts for trends
- **Monthly:** Update pip-audit baseline (upgrade dependencies)
- **Quarterly:** Full security audit (manual review + automated scans)

---

## Criteria for Hard Gate Activation

### Prerequisites (MUST be met before enabling hard gate)

1. **Zero High-Severity Findings:**
   - No high-severity Bandit findings for 2 consecutive weeks
   - No critical CVEs from pip-audit for 2 consecutive weeks
   - No secrets detected for 2 consecutive weeks

2. **False Positive Rate < 5%:**
   - Less than 1 in 20 findings are false positives
   - Baseline files tuned appropriately

3. **Team Readiness:**
   - Developers trained on security tools
   - Documentation updated (this document + CONTRIBUTING.md)
   - Escalation path defined

4. **Rollback Plan Tested:**
   - Verify revert procedure works
   - Document rollback steps (see below)

### Decision Authority

**Who can enable hard gates:**
- Release Manager
- Security Lead
- DevOps Lead

**Approval Process:**
1. Verify all prerequisites met
2. Document decision in GitHub issue
3. Create PR with gate change
4. Get approval from 2 stakeholders
5. Merge and monitor

### Rollback Triggers

**Revert to soft gate if:**
- > 3 false positive build failures in first week after activation
- Critical dependency has no vulnerability fix available
- Legitimate code change blocked by scanner

**Rollback Procedure:**
```bash
# 1. Create rollback PR
git checkout -b revert-hard-gate-<scanner>

# 2. Change continue-on-error back to true
# Edit .github/workflows/ci.yml:
#   continue-on-error: true

# 3. Commit with rationale
git commit -m "revert(security): rollback <scanner> to soft gate

Reason: <detailed explanation>
Findings: <link to issue or artifact>
Next Steps: <remediation plan>"

# 4. Emergency merge (bypass normal approval if needed)
git push origin revert-hard-gate-<scanner>
# Create PR, mark as urgent, merge

# 5. Post-mortem
# Document in GitHub issue:
# - What triggered rollback
# - Root cause
# - Tuning needed
# - Timeline for retry
```

---

## Tuning False Positives

### Bandit False Positives

**Common False Positives:**
- `B101`: Use of assert (acceptable in test code)
- `B404`: Import of subprocess module (acceptable with validation)
- `B603`: subprocess without shell=True (acceptable)

**How to Suppress:**

**Option 1: Inline comment (preferred for specific cases)**
```python
# nosec B101
assert user_input is not None  # Input validated upstream
```

**Option 2: Config file (preferred for project-wide)**
```yaml
# .bandit
skips:
  - B101  # assert_used - legitimate in our context

exclude_dirs:
  - /tests/
  - /archive/
```

**Review Process:**
- All `nosec` comments MUST include justification
- Config file changes MUST be reviewed by security lead
- Document in `docs/security.md` why each skip is safe

### pip-audit False Positives

**Common False Positives:**
- Transitive dependency vulnerabilities (not directly used)
- CVEs that don't affect our usage pattern

**How to Suppress:**

**Option 1: Ignore specific CVE (temporary)**
```bash
pip-audit -r requirements.txt --ignore-vuln CVE-2024-12345
```

**Option 2: Config file (persistent)**
```toml
# pip-audit.toml
[audit]
ignore-vulns = [
    "CVE-2024-12345",  # Reason: Transitive dep, not used by us
]
```

**Review Process:**
- ALL ignored CVEs MUST be documented with rationale
- Re-review ignored CVEs monthly
- Escalate to security lead if no fix available after 30 days

### detect-secrets False Positives

**Common False Positives:**
- Test fixtures (sample API keys, mock tokens)
- High entropy strings that are not secrets (hashes, IDs)

**How to Suppress:**

**Option 1: Update baseline (mark as false positive)**
```bash
# Audit current findings
detect-secrets audit .secrets.baseline

# For each finding:
# - Press 'y' to mark as false positive (safe)
# - Press 'n' to mark as real secret (unsafe)
# - Press 's' to skip (decide later)

# Commit updated baseline
git add .secrets.baseline
git commit -m "chore(security): update secrets baseline with false positives"
```

**Option 2: Inline pragma (for specific lines)**
```python
API_KEY_PATTERN = r"[A-Z0-9]{32}"  # pragma: allowlist secret
```

**Review Process:**
- Baseline audits MUST be done by 2 people (4-eyes principle)
- Document each false positive in commit message
- Never mark real secrets as false positives (use env vars instead)

---

## Monitoring & Reporting

### Daily Monitoring (Automated)

**GitHub Actions:**
- Security gates run on every PR/push
- Reports uploaded as artifacts (retention: 30 days)
- Notifications sent via GitHub notices

**Artifact Locations:**
```
Actions → Workflow Run → Artifacts → security-reports/
  ├── bandit_report.txt
  ├── pip_audit_report.txt
  └── detect_secrets.json (if baseline updated)
```

### Weekly Review (Manual)

**Reviewer:** Security Lead or Release Manager

**Checklist:**
- [ ] Download security artifacts from last 7 days
- [ ] Review new findings (if any)
- [ ] Check false positive rate
- [ ] Update baseline files if needed
- [ ] Document trends in security log

**Report Template:**
```markdown
# Security Gates Weekly Review - Week of YYYY-MM-DD

## Findings Summary
- Bandit: X findings (Y high, Z medium, W low)
- pip-audit: X vulnerabilities (Y critical, Z high, W medium)
- detect-secrets: X secrets detected

## Actions Taken
- Fixed: [list of fixed issues]
- False positives marked: [list of FPs added to baseline]
- Ignored CVEs: [list with rationale]

## Trends
- [Any patterns observed]

## Next Steps
- [Action items for next week]
```

### Monthly Audit (Comprehensive)

**Reviewer:** Security Lead + External Auditor (optional)

**Scope:**
- Review all ignored CVEs (verify still relevant)
- Review all Bandit skips (verify still needed)
- Review secrets baseline (audit false positives)
- Run manual security testing (penetration tests, code review)

**Deliverable:** Monthly Security Report (uploaded to `reports/security/YYYY-MM.md`)

---

## Escalation & Exceptions

### When to Escalate

**Escalate to Security Lead if:**
- High-severity Bandit finding with no clear fix
- Critical CVE with no available patch
- Real secret detected in commit history

**Escalation Process:**
1. Stop the build (if hard gate is enabled)
2. Create GitHub issue: `[SECURITY] <brief description>`
3. Tag security lead and release manager
4. Provide context: scanner output, affected code, proposed fix
5. Wait for approval before proceeding

### Exception Process

**When exceptions are allowed:**
- Dependency vulnerability with no fix available (temporary)
- False positive that cannot be tuned (rare)
- Legacy code that cannot be refactored immediately

**How to request exception:**
1. Create GitHub issue: `[SECURITY EXCEPTION] <scanner> - <reason>`
2. Provide:
   - Scanner name (Bandit, pip-audit, detect-secrets)
   - Finding details (CVE ID, file/line, description)
   - Why it's safe to ignore
   - Remediation plan (if applicable)
   - Expiration date (max 90 days)
3. Get approval from security lead
4. Document in scanner config with reference to issue
5. Add to security log

**Example:**
```yaml
# .bandit (example exception)
skips:
  - B404  # Issue #123: subprocess import needed for CLI tools, validated inputs

# pip-audit.toml (example exception)
[audit]
ignore-vulns = [
    "CVE-2024-99999",  # Issue #124: No fix available, mitigated by input validation
]
```

### Security Incident Response

**If a real secret is detected in commit history:**

1. **Immediate Actions:**
   - Revoke the exposed secret immediately (API key, token, password)
   - Rotate credentials
   - Audit access logs for unauthorized usage

2. **Remediation:**
   - Remove secret from commit history (use BFG Repo Cleaner or `git filter-branch`)
   - Add secret to `.secrets.baseline` to prevent future commits
   - Update documentation on secret management

3. **Post-Incident:**
   - Document incident in security log
   - Review secret management practices
   - Train team on secure secret handling

---

## Appendix: Quick Reference

### Enabling Hard Gates (Step-by-Step)

```bash
# 1. Verify prerequisites
# - Zero high-severity findings for 2 weeks
# - False positive rate < 5%
# - Team trained and ready

# 2. Create PR for hard gate activation
git checkout -b enable-hard-gate-<scanner>

# 3. Edit .github/workflows/ci.yml
# Change:
#   continue-on-error: true
# To:
#   continue-on-error: false

# 4. Test locally (optional)
bandit -r src -x tests          # Should exit 0
pip-audit -r requirements.txt   # Should exit 0
detect-secrets scan --baseline .secrets.baseline  # Should exit 0

# 5. Commit and push
git add .github/workflows/ci.yml
git commit -m "feat(security): enable hard gate for <scanner>

Rationale: <explanation>
Prerequisites verified: <checklist>
Rollback plan: Revert this commit if > 3 FP failures in Week 1"

git push origin enable-hard-gate-<scanner>

# 6. Create PR, get approvals, merge

# 7. Monitor closely for 1 week
# - Watch for false positive build failures
# - Be ready to rollback if needed
```

### Disabling Hard Gates (Rollback)

```bash
# 1. Create rollback PR
git checkout -b rollback-hard-gate-<scanner>

# 2. Revert change in .github/workflows/ci.yml
# Change:
#   continue-on-error: false
# To:
#   continue-on-error: true

# 3. Commit with detailed explanation
git add .github/workflows/ci.yml
git commit -m "revert(security): rollback <scanner> to soft gate

Reason: <detailed explanation>
Findings: <link to issue or failing build>
Next Steps: <remediation plan and timeline>"

git push origin rollback-hard-gate-<scanner>

# 4. Emergency merge (if needed)
# Skip normal approval process if builds are blocked

# 5. Create post-mortem issue
# Document root cause and plan for retry
```

### Security Tools Installation (Local)

```bash
# Install security scanners
pip install bandit pip-audit detect-secrets

# Run scans locally
bandit -r src -x tests -f txt -o reports/bandit_report.txt
pip-audit -r requirements.txt --desc -o reports/pip_audit_report.txt
detect-secrets scan --baseline .secrets.baseline
```

---

**End of Security Gates Rollout Plan**

**Maintained By:** Release Orchestrator Agent / Security Lead
**Version History:**
- v1.0.0 (2026-01-27): Initial rollout plan for soft → hard gate transition
