# Acceptance Gates (ship/no‑ship)

> **Source of truth:** `docs/ACCEPTANCE_GATES.yaml`. This Markdown is a human-friendly view.
> Metrics include MRR@10 and median First Correct Rank; sampling floors and 95% CIs apply.

| Area                   | Metric                               |            Pass Bar | Notes                                                                | Sampling & CI                                            |
| ---------------------- | ------------------------------------ | ------------------: | -------------------------------------------------------------------- | -------------------------------------------------------- |
| **Faithfulness**       | Unsupported claim rate               |            **0.0%** | Every sentence in answers/artifacts must be entailed by a cited span | ≥ 3,000 claims across ≥3 frameworks/jurisdictions, 95% Clopper–Pearson CI |
|                        | Citation span precision / recall     | **≥ 0.98 / ≥ 0.98** | Span actually contains the claim; all claims have a span             | ≥ 3,000 claims across ≥3 frameworks/jurisdictions, 95% Clopper–Pearson CI |
| **Quality**            | MRR@10                              |          **≥ 0.70** | Mean Reciprocal Rank at 10 for requirement-style queries (shall/must) | ≥ 500 requirement queries across standards |
|                        | FCR (median)                         |             **≤ 2** | First correct citation rank (median position)                        | ≥ 500 queries with ground truth citations |
| **As‑of correctness**  | Version leakage                      |          **≤ 0.02** | No future text; no mixed versions                                    | ≥ 300 time‑travel Qs spanning ≥2 versions per standard |
| **Metadata filters**   | Retrieval leak rate                  |          **≤ 0.5%** | Retrieved contexts must match all filters                            | ≥ 500 filtered Qs with 2–3 simultaneous filters |
|                        | Answer leak rate                     |            **0.0%** | No claim sourced outside allowed filter set                          | ≥ 500 filtered Qs with 2–3 simultaneous filters |
| **Negative controls**  | False‑positive answer rate           |            **0.0%** | Out‑of‑corpus questions must guard                                   | ≥ 200 OOD Qs with near‑miss phrasing |
| **Structured outputs** | Field source coverage                |          **≥ 0.98** | Every non‑empty field cites a span                                   | ≥ 100 structured outputs per schema type |
|                        | False fills                          |            **0.0%** | Ungrounded ⇒ blank + flag                                            | ≥ 100 structured outputs per schema type |
| **Performance**        | `/query` latency P50 / P95           |   **≤ 2.5s / ≤ 8s** | Small corpus ref hardware; 5 concurrent users                        | ≥ 1000 queries under load with 95% CI |
| **Reproducibility**    | Retrieval identity (manifest replay) |            **100%** | Same top‑k IDs per manifest                                          | All manifests in data/manifests/ |
|                        | Answer similarity                    |          **≥ 0.95** | Normalized Levenshtein                                               | All manifests with deterministic replay |
| **Security**           | Unintended egress                    |               **0** | Offline mode: no outbound packets                                    | Packet capture across all endpoints |
|                        | Critical CVEs                        |               **0** | Container image scans                                                | Weekly trivy/grype scans |
| **PII**                | Redaction recall / precision         | **≥ 0.95 / ≥ 0.98** | Plus retrieval test shows no PII surfacing                           | ≥ 1000 synthetic PII samples per category |

## Policies

### Error Budget & Flake Rules
- Allow **one-off infrastructure errors ≤ 0.5%** of runs
- Infrastructure errors must be **tagged as "infra"**, not counted as model failures
- Any error rate above 0.5% requires investigation and remediation

### Reproducibility & Seed Policy
- Pin seeds & model hashes for all evaluation runs
- **Any model change requires re-baseline** of all acceptance gates
- Include model hash, seed, and dataset version in all reports

### Holdout Set Policy
- At least **30%** of evaluation items must be from an **unseen holdout** set
- Holdout set curated after the last code change to prevent overfitting
- Holdout set rotated quarterly with new questions authored by SMEs

### Statistical Confidence Requirements
- Use **Clopper–Pearson confidence intervals** for all proportion estimates
- Report 95% confidence intervals for all metrics
- Minimum sample sizes as specified in "Sampling & CI" column
- For 0.0% claims: upper bound of 95% CI must be ≤ 0.1%
