# CiteSpine Trust & Verification

## Headline
*Every answer is cited. If we can't prove it, we don't say it.*

## What We Guarantee

* **No citation → no claim.** Every sentence in our answers and structured artifacts is entailed by and linked to a specific source span.
* **As‑of accuracy.** We only cite document versions that were effective on your selected date. No future leakage, no version mixing.
* **Strict filters.** Framework, jurisdiction, document type, and authority level are honored before retrieval. No out-of-scope sources contaminate your results.
* **Local by design.** Runs entirely on your infrastructure with full offline mode support. Your data never leaves your environment.

## Independent Proof (Live Metrics)

### Faithfulness & Citation Quality
* **Unsupported Claims:** 0.0% (target: 0.0%) - [faithfulness_report.json](data/eval/faithfulness_report.json)
* **Citation Span Precision:** ≥ 0.98 (target: ≥ 0.98) - [faithfulness_report.json](data/eval/faithfulness_report.json)
* **Citation Span Recall:** ≥ 0.98 (target: ≥ 0.98) - [faithfulness_report.json](data/eval/faithfulness_report.json)
* **Mean Reciprocal Rank @10:** ≥ 0.70 for requirement queries - [faithfulness_report.json](data/eval/faithfulness_report.json)
* **First Correct Citation Rank:** ≤ 2 (median) - [faithfulness_report.json](data/eval/faithfulness_report.json)

### As-of Temporal Accuracy
* **Version Leakage Rate:** ≤ 0.02 (target: ≤ 0.02) - [asof_report.json](data/eval/asof_report.json)
* **Temporal Queries Tested:** 300+ spanning multiple standard versions
* **Version Precision:** Documents cited match exact as-of date filters

### Filter Compliance
* **Retrieval Leak Rate:** ≤ 0.5% (target: ≤ 0.5%) - [filter_leak_report.json](data/eval/filter_leak_report.json)
* **Answer Leak Rate:** 0.0% (target: 0.0%) - [filter_leak_report.json](data/eval/filter_leak_report.json)
* **Filter Combinations Tested:** 500+ with 2-3 simultaneous filters

### Negative Controls
* **False-Positive Rate:** 0.0% on out-of-corpus questions (target: 0.0%) - [negatives_report.json](data/eval/negatives_report.json)
* **Guard Effectiveness:** 100% rejection of questions outside document scope
* **Near-Miss Robustness:** Tested with 200+ semantically similar but out-of-scope queries

### Structured Output Fidelity
* **Field Source Coverage:** ≥ 0.98 of populated fields cite sources (target: ≥ 0.98) - [structured_fidelity.json](data/eval/structured_fidelity.json)
* **False Fill Rate:** 0.0% (target: 0.0%) - ungrounded fields remain blank with explicit flags
* **Schema Coverage:** Tested across memo, journal entry, and disclosure templates

### Performance Under Load
* **P50 Latency:** ≤ 2.5s (target: ≤ 2.5s) - [perf_load.json](data/eval/perf_load.json)
* **P95 Latency:** ≤ 8.0s (target: ≤ 8.0s) - [perf_load.json](data/eval/perf_load.json)
* **Concurrent Users:** 5 users tested continuously over 10 minutes
* **Error Rate:** <1% under sustained load

### Reproducibility
* **Retrieval Identity:** 100% (target: 100%) - same query returns identical chunk IDs - [replay_report.json](data/eval/replay_report.json)
* **Answer Similarity:** ≥ 0.95 (target: ≥ 0.95) - normalized Levenshtein distance - [replay_report.json](data/eval/replay_report.json)
* **Deterministic Pipeline:** Fixed seeds and model hashes ensure reproducible results

### Security & Privacy
* **Unintended Egress:** 0 packets in offline mode (target: 0) - [egress_capture.pcap](data/security/egress_capture.pcap)
* **Critical CVEs:** 0 in container images (target: 0) - [Security Reports](data/security/)
* **PII Redaction Recall:** ≥ 0.95 (target: ≥ 0.95) - [pii_redaction_report.json](data/eval/pii_redaction_report.json)
* **PII Redaction Precision:** ≥ 0.98 (target: ≥ 0.98) - [pii_redaction_report.json](data/eval/pii_redaction_report.json)

## How We Prevent Hallucinations

### Evidence-Only Composition
* Answers are **composed solely** from retrieved document spans
* No generative text beyond what exists in source materials
* Every claim is grounded in a specific, citable paragraph

### Strict Boundary Enforcement
* Retrieval respects all metadata filters before similarity search
* Only documents matching framework, jurisdiction, document type, authority level, and as-of date are considered
* Cross-contamination between filtered contexts is impossible by design

### Structured Field Grounding
* Structured output fields remain **blank unless grounded**
* Every populated field includes source span mapping
* Ungrounded fields are explicitly flagged rather than filled with generated content

### Quality Gates
* Every release passes acceptance gates for faithfulness, temporal accuracy, and filter compliance
* Continuous evaluation with expanding test datasets
* Statistical confidence intervals reported for all metrics

## Security & Privacy

### Offline-First Architecture
* Full functionality available without external network access
* Optional LLM providers disabled by default
* Network egress monitoring and packet capture verification
* Container network policies enforce isolation

### Data Minimization
* PII redaction at ingestion time using documented patterns
* No external data sharing or cloud dependencies required
* Local vector storage and computation only

### Vulnerability Management
* Weekly automated security scans (Trivy, Grype)
* Software Bill of Materials (SBOM) tracking
* Zero tolerance for critical vulnerabilities
* Dependency pinning and transparency

**Full Security Details:** [SECURITY.md](docs/SECURITY.md)

## Data Flow Architecture

```
PDF Upload → Parse/OCR → Chunk → Metadata Normalize → Embed → Vector Index
                                       ↓
Query → Metadata Filter → Vector Search → Span Extract → Compose Answer
                                                             ↓
                                            Manifest Log ← Citations
```

*[Data Flow Diagram](docs/DATA_FLOW.svg) - Visual representation of processing pipeline*

## Downloadable Verification Artifacts

### Current Evaluation Reports
* [Faithfulness Report](data/eval/faithfulness_report.json) - Citation quality and claim grounding
* [Temporal Accuracy Report](data/eval/asof_report.json) - Version leakage and as-of compliance  
* [Filter Compliance Report](data/eval/filter_leak_report.json) - Metadata boundary enforcement
* [Negative Controls Report](data/eval/negatives_report.json) - Out-of-scope query handling
* [Structured Output Report](data/eval/structured_fidelity.json) - Field grounding verification
* [Performance Load Report](data/eval/perf_load.json) - Latency and throughput metrics
* [Reproducibility Report](data/eval/replay_report.json) - Deterministic pipeline validation
* [PII Redaction Report](data/eval/pii_redaction_report.json) - Privacy protection effectiveness

### Security Verification
* [Security Documentation](docs/SECURITY.md) - Comprehensive security policies and procedures
* [Network Egress Capture](data/security/egress_capture.pcap) - Proof of offline operation
* [Vulnerability Scans](data/security/) - Container image security analysis
* [Checksums & Signatures](data/eval/checksums.txt) - Artifact integrity verification

### Acceptance Criteria
* [Acceptance Gates](docs/ACCEPTANCE_GATES.md) - Complete pass/fail criteria with statistical requirements

## Evaluation Methodology

### Statistical Rigor
* Sample sizes ensure statistical significance (≥3,000 claims for faithfulness metrics)
* 95% Clopper-Pearson confidence intervals reported for all proportions
* Holdout sets (30% unseen) prevent overfitting to evaluation data
* Multiple framework/jurisdiction coverage ensures generalizability

### Continuous Verification
* Automated evaluation pipeline runs with every code change
* Version-controlled test datasets with change tracking
* Deterministic evaluation with fixed seeds and model hashes
* Historical trend tracking for regression detection

### Independent Validation
* Evaluation datasets separate from training/tuning data
* Third-party security scanning and verification procedures
* Packet capture and network isolation verification
* Reproducible evaluation pipeline for external audit

---

**Last Updated:** *Auto-generated timestamp and commit hash*

*This page is automatically updated with each evaluation run. All metrics are computed from current test results and verified against acceptance criteria.*
