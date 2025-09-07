# Security Egress Check Procedure

## Overview
This document outlines the manual procedure for verifying that CiteSpine operates in true offline mode with zero unintended egress.

## Prerequisites
- CiteSpine running in Docker Compose
- Root/sudo access for packet capture
- `tcpdump`, `wireshark`, or equivalent packet analysis tools
- Test dataset and evaluation suite ready

## Step 1: Baseline Network Capture

### Start Packet Capture
```bash
# Terminal 1 - Start packet capture for all interfaces
sudo tcpdump -i any -w data/security/egress_capture_$(date +%Y%m%d_%H%M%S).pcap

# Or if using Docker network specifically:
sudo tcpdump -i docker0 -w data/security/egress_docker_$(date +%Y%m%d_%H%M%S).pcap

# Note the start time
echo "Capture started: $(date -Iseconds)" > data/security/egress_test_log.txt
```

## Step 2: Configure Offline Mode

### Set Environment Variables
```bash
# In docker-compose.yml or environment
export OFFLINE=true
export DISABLE_EXTERNAL_APIS=true

# Restart services in offline mode
docker compose down
OFFLINE=true docker compose up -d
```

### Verify Configuration
```bash
# Check that OFFLINE flag is set in container
docker compose exec api python -c "import os; print('OFFLINE:', os.getenv('OFFLINE'))"

# Should print: OFFLINE: true
```

## Step 3: Execute Full Test Suite

### Run All Endpoints
```bash
# Health check
curl -s http://localhost:8000/health

# Query endpoint (should work with local data)
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "q": "What does PCAOB require for audit documentation?",
    "filters": {"framework": "Other", "jurisdiction": "US"},
    "top_k": 5
  }'

# Generate artifacts
curl -X POST http://localhost:8000/generate/memo \
  -H "Content-Type: application/json" \
  -d '{"q": "PCAOB audit documentation requirements"}'

# Upload and process PDF (if test files available)
curl -X POST http://localhost:8000/upload \
  -F "file=@test_document.pdf" \
  -F "title=Test Document" \
  -F "framework=Other"
```

### Run Evaluation Suite
```bash
# Run complete evaluation pipeline
make eval_all

# This should trigger:
# - faithfulness evaluation
# - filter compliance checks  
# - temporal accuracy validation
# - negative controls testing
# - structured output verification
# - performance testing
# - reproducibility checks
# - PII redaction validation
```

### Test Error Conditions
```bash
# Test scenarios that might trigger external calls
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"q": "What is the weather today?"}'  # Out of corpus

# Upload invalid file
curl -X POST http://localhost:8000/upload \
  -F "file=@invalid.txt" \
  -F "title=Invalid"
```

## Step 4: Stop Capture and Analyze

### Stop Packet Capture
```bash
# Stop tcpdump (Ctrl+C in capture terminal)
# Note end time
echo "Capture ended: $(date -Iseconds)" >> data/security/egress_test_log.txt
```

### Analyze Capture File
```bash
# Basic analysis - check for external IPs
tcpdump -r data/security/egress_capture_*.pcap | grep -v "127.0.0.1\|localhost\|172.\|192.168.\|10\."

# More detailed analysis with Wireshark (if available)
wireshark data/security/egress_capture_*.pcap

# Or use tshark for command-line analysis
tshark -r data/security/egress_capture_*.pcap -Y "ip.dst_host != 127.0.0.1 and ip.dst_host != localhost and not ip.addr matches \"^(10|172\\.(1[6-9]|2[0-9]|3[01])|192\\.168)\\.\""
```

### Generate Analysis Report
```bash
# Create structured analysis
cat > data/security/egress_analysis_$(date +%Y%m%d).md << EOF
# Egress Analysis Report

**Date:** $(date -Iseconds)
**Duration:** [Start time] to [End time]
**Capture File:** egress_capture_*.pcap
**File Size:** $(ls -lh data/security/egress_capture_*.pcap | awk '{print $5}')

## Test Scenarios Executed
- [x] Health checks
- [x] Query execution  
- [x] Artifact generation
- [x] PDF upload and processing
- [x] Full evaluation suite
- [x] Error condition testing

## Analysis Results
**External Connections Detected:** [COUNT]
**External IPs Contacted:** [LIST OR "None"]
**DNS Queries to External Servers:** [COUNT]
**Unexpected Protocol Traffic:** [LIST OR "None"]

## Verdict
- [ ] PASS - Zero external connections detected
- [ ] FAIL - External connections found (details below)

## Details
[Detailed findings, IPs, protocols, timestamps]

## Recommendations
[Any suggested improvements or follow-up actions]
EOF
```

## Step 5: Documentation and Archival

### Generate Checksums
```bash
# Create checksums for all security artifacts
cd data/security
sha256sum egress_capture_*.pcap egress_analysis_*.md egress_test_log.txt > checksums_$(date +%Y%m%d).txt
echo "Generated: $(date -Iseconds)" >> checksums_$(date +%Y%m%d).txt
echo "Git commit: $(git rev-parse HEAD)" >> checksums_$(date +%Y%m%d).txt
```

### Archive Results
```bash
# Create archive for audit trail
tar -czf egress_verification_$(date +%Y%m%d).tar.gz \
  egress_capture_*.pcap \
  egress_analysis_*.md \
  egress_test_log.txt \
  checksums_*.txt

# Optional: Generate GPG signature for archive
gpg --armor --detach-sign egress_verification_$(date +%Y%m%d).tar.gz
```

## Step 6: Reporting

### Update Security Documentation
Add results to `docs/SECURITY.md` under "Security Audit Trail" section:

```markdown
## Latest Egress Verification
- **Date:** [DATE]
- **Result:** PASS/FAIL
- **External Connections:** [COUNT]
- **Archive:** `data/security/egress_verification_[DATE].tar.gz`
- **Checksum:** [SHA256]
```

### Generate Compliance Artifact
Create downloadable proof for trust page:

```bash
# Create public summary for trust page
cat > data/security/egress_verification_summary.json << EOF
{
  "verification_date": "$(date -Iseconds)",
  "test_duration_minutes": "[DURATION]",
  "scenarios_tested": 8,
  "external_connections": 0,
  "verdict": "PASS",
  "archive_checksum": "$(sha256sum egress_verification_*.tar.gz | cut -d' ' -f1)",
  "methodology": "docs/SECURITY.md#security-egress-check"
}
EOF
```

## Troubleshooting

### Common Issues
1. **Docker network interfaces**: Ensure packet capture covers Docker bridge networks
2. **DNS resolution**: Check for DNS queries that might leak information
3. **NTP traffic**: System clock synchronization may generate traffic
4. **Package manager**: Container startup might check for updates

### False Positives
- Local Docker network traffic (172.x.x.x ranges)
- Localhost/loopback traffic (127.0.0.1, ::1)
- Container-to-container communication
- Host system background processes

### Validation Commands
```bash
# Verify offline mode is working
docker compose exec api python -c "
import requests
try:
    requests.get('https://api.openai.com', timeout=5)
    print('FAIL: External request succeeded')
except:
    print('PASS: External requests blocked')
"

# Check environment variables are set
docker compose exec api env | grep OFFLINE
```

## Annual Review
- Repeat this procedure quarterly or after major releases
- Update methodology based on new attack vectors
- Archive historical results for compliance tracking
- Review and update network monitoring procedures
