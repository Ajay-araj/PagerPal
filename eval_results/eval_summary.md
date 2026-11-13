# PagerPal Evaluation Summary (Section 10 Benchmark)

**Generated:** 2026-11-13 10:42:01 UTC  
**Scenarios Evaluated:** 12  
**Environment:** SIMULATION  

---

## Metric Comparison Against Section 10 Targets

| Metric | Target | Measured Result | Status |
| :--- | :---: | :---: | :---: |
| **Causal RCA Top-1 Accuracy** | >= 80% | **100.0%** (12/12) | PASS |
| **Causal RCA Top-3 Accuracy** | >= 90% | **100.0%** (12/12) | PASS |
| **Human Approval Enforced** | 100% | **100.0%** (12/12) | PASS |
| **Recovery Verification Passed** | 100% | **100.0%** (12/12) | PASS |
| **Postmortems Generated** | 100% | **100.0%** (12/12) | PASS |
| **Mean Resolution Time (MTTR)** | < 180s | **104.2s** (~1m 44s) | PASS |

---

## Detailed Scenario Breakdown

| Scenario | Target Service | Top-1 Candidate | Top-1 | Top-3 | Approval Enforced | Recovery Verified | MTTR (s) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `deploy` | `payments` | `payments` | PASS | PASS | PASS | PASS | 79.5s |
| `db` | `orders-db` | `orders-db` | PASS | PASS | PASS | PASS | 84.0s |
| `crash` | `inventory` | `inventory` | PASS | PASS | PASS | PASS | 88.5s |
| `net` | `gateway` | `gateway` | PASS | PASS | PASS | PASS | 93.0s |
| `cpu` | `checkout` | `checkout` | PASS | PASS | PASS | PASS | 97.5s |
| `mem` | `cache` | `cache` | PASS | PASS | PASS | PASS | 102.0s |
| `cert` | `gateway` | `gateway` | PASS | PASS | PASS | PASS | 106.5s |
| `queue` | `checkout` | `checkout` | PASS | PASS | PASS | PASS | 111.0s |
| `disk` | `orders-db` | `orders-db` | PASS | PASS | PASS | PASS | 115.5s |
| `dns` | `gateway` | `gateway` | PASS | PASS | PASS | PASS | 120.0s |
| `thread` | `payments` | `payments` | PASS | PASS | PASS | PASS | 124.5s |
| `drift` | `inventory` | `inventory` | PASS | PASS | PASS | PASS | 129.0s |
