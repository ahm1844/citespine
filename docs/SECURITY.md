# Security Documentation

## Scope & Deployment

* Self‑hosted via Docker Compose; services: API, Postgres+pgvector.
* Optional LLM providers disabled by default; **offline mode** = no external calls.

## Data Flow

* Upload → Ingest (parse/OCR) → Processed chunks + metadata → Vector index.
* Query → Pre‑filters → Similarity → Compose strictly from retrieved spans.
* Manifests recorded (model, params, corpus hash, cited chunk IDs, latency, backend).

## Egress Control

* In `OFFLINE=true`, outbound DNS/HTTP(S) blocked by container network policy.
* **Packet capture procedure:**

  1. `tcpdump -i any -w egress_capture.pcap` on host (or `docker run --cap-add=NET_ADMIN ...` sidecar).
  2. Run `/query`, `/generate`, `/eval_all`.
  3. Verify zero outbound packets to public IPs (save screenshot + pcap checksum in `docs/`).

### Network Policy Configuration

**Docker Compose Network Isolation:**

```yaml
services:
  api:
    networks:
      - internal
    # deny-all by default; allow Postgres only
    extra_hosts: []  # no accidental DNS overrides
networks:
  internal:
    internal: true
```

**Optional iptables rule for Linux hosts:**

```bash
# Block all outbound traffic from CiteSpine containers
iptables -I OUTPUT -m cgroup --cgroup docker/citespine-api -j DROP
# Allow Postgres communication
iptables -I OUTPUT -m cgroup --cgroup docker/citespine-api -d <postgres_ip> -j ACCEPT
```

## Secrets

* No API keys in repo; `.env` excluded.
* Logs/manifests scrubbed: keys and PII redacted (regex rules documented).

## Hashing & Signing

### Artifact Integrity
* Compute **SHA‑256** for all evaluation artifacts; store in `data/eval/checksums.txt`
* Each evaluation run generates checksums for all output files
* Format: `<sha256sum> <filename> <timestamp> <run_id>`

### Optional Digital Signatures
* Sign checksums with **Ed25519** key pair for tamper-evident trail
* Store public key in repository: `docs/artifacts_public_key.pem`
* Verify signatures before trusting evaluation results
* Command: `ed25519 verify data/eval/checksums.txt.sig artifacts_public_key.pem`

## Vulnerability Management

* Weekly image scans: `trivy image citespine-api:latest` and `grype`.
* **Target:** critical CVEs = 0; high CVEs remediated or documented within 7 days.

### Scanning Automation
```bash
# Weekly scan script
#!/bin/bash
DATE=$(date +%Y-%m-%d)
mkdir -p data/security/$DATE

# Trivy scan
trivy image --format json --output data/security/$DATE/trivy-report.json citespine-api:latest

# Grype scan  
grype citespine-api:latest -o json > data/security/$DATE/grype-report.json

# Fail if critical vulnerabilities found
trivy image --exit-code 1 --severity CRITICAL citespine-api:latest
```

## Dependency Transparency

### Container Image Pinning
* All images in `docker-compose.yml` use SHA256 digests or specific version tags
* No `latest` tags in production deployments
* Base images updated and tested monthly

### Software Bill of Materials (SBOM)
```bash
# Generate SBOM for audit trail
syft packages citespine-api:latest -o json > data/security/sbom.json
grype sbom:data/security/sbom.json -o json > data/security/sbom-vulns.json
```

### Archive Policy
* Store scan reports in `data/security/YYYY‑MM‑DD/` with 1-year retention
* Include SBOM, vulnerability reports, and remediation notes
* Link scan results in weekly security summary

## LLM Egress Guard

### Offline Mode Enforcement
```python
# In src/embedding/provider.py and src/answer/compose.py
import os

def check_offline_mode():
    if os.getenv("OFFLINE", "false").lower() == "true":
        raise RuntimeError("External API calls blocked in offline mode")

# Applied to all external HTTP requests
```

### Deny-list Implementation
* Maintain explicit deny-list of external endpoints in `src/common/config.py`
* Fail closed if `OFFLINE=true` environment variable set
* Log and block any external network requests in offline mode

```python
BLOCKED_DOMAINS = [
    "openai.com", "api.openai.com",
    "anthropic.com", "api.anthropic.com", 
    "huggingface.co", "api.huggingface.co"
]
```

## PII Minimization

### Ingest Pipeline PII Redaction
* Redact obvious PII before storage (emails, phones, SSNs, account numbers)
* Apply redaction rules documented in `src/ingest/pii_patterns.py`
* **Test:** seed synthetic PII; confirm redaction and non‑retrievability

### PII Test Corpus Policy

#### Synthetic PII Only
* **No real PII** in test datasets under any circumstances
* Use deterministic generators with fixed seeds for reproducible tests
* Document all PII generators and patterns used

#### Generator Sources
```python
# PII test data generators
GENERATORS = {
    "emails": "faker.providers.internet.email",
    "phones": "faker.providers.phone_number.phone_number", 
    "ssns": "custom_regex:999-99-9999",
    "accounts": "custom_regex:ACC[0-9]{8}",
    "names": "faker.providers.person.name"
}

LOCALES = ["en_US", "en_GB", "de_DE", "fr_FR"]
SEED = 42  # Fixed seed for deterministic generation
```

#### Test Procedures
1. Generate synthetic PII corpus with known patterns
2. Ingest through full pipeline with redaction enabled
3. Query for PII patterns - verify zero retrieval
4. Report metrics in `pii_redaction_report.json`:
   - Redaction recall: ≥ 0.95 (PII correctly redacted)
   - Redaction precision: ≥ 0.98 (non-PII not over-redacted)
   - Retrieval leak rate: 0.0% (redacted PII not retrievable)

### PII Seeds & Regeneration
* Store PII generation seeds in `src/eval/datasets/pii_seeds.json`
* Allow deterministic re-generation of test corpus
* Version control seeds but not generated PII data
* Include generation timestamp and corpus size metadata

## Security Audit Trail

### Packet Capture Verification
1. Start packet capture: `tcpdump -i any -w data/security/egress_capture.pcap`
2. Run full evaluation suite in offline mode: `OFFLINE=true make eval_all`
3. Analyze capture for external connections: `wireshark -r egress_capture.pcap`
4. Document findings with screenshots in `data/security/egress_report.md`

### Checksums and Verification
```bash
# Generate checksums for all evaluation artifacts
find data/eval -name "*.json" -exec sha256sum {} \; > data/eval/checksums.txt
echo "Generated: $(date -Iseconds)" >> data/eval/checksums.txt
echo "Git commit: $(git rev-parse HEAD)" >> data/eval/checksums.txt

# Verify integrity before publishing results
sha256sum -c data/eval/checksums.txt
```

### Compliance Documentation
* Maintain security incident log in `data/security/incidents.log`
* Document all security policy exceptions with business justification
* Quarterly security review with findings archived in `data/security/reviews/`
