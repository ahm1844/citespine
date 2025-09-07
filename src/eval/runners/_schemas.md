# Evaluation Runner Output Schemas

## faithfulness_report.json

```json
{
  "summary": {
    "claims_total": 500,
    "unsupported": 0,
    "span_precision": 0.985,
    "span_recall": 0.992,
    "mrr_at_10": 0.74,
    "fcr_median": 1.8,
    "confidence_interval": {
      "unsupported_rate_upper": 0.001,
      "span_precision_lower": 0.975,
      "span_recall_lower": 0.981
    }
  },
  "claims": [
    {
      "q_id": "seed_001",
      "claim_id": "c1",
      "cited_doc_id": "PCAOB_AS_3101@2024-12-31",
      "page_span": "12-13",
      "entailed": true,
      "precision_ok": true,
      "recall_ok": true,
      "nli_score": 0.94
    }
  ],
  "metadata": {
    "dataset_version": "v1.2.0",
    "model_hash": "sha256:abc123...",
    "run_timestamp": "2024-01-15T10:30:00Z",
    "total_queries": 150,
    "corpus_hash": "sha256:def456..."
  }
}
```

## filter_leak_report.json

```json
{
  "summary": {
    "retrieval_leak_rate": 0.003,
    "answer_leak_rate": 0.0,
    "queries_tested": 500,
    "filter_combinations": 85,
    "confidence_interval": {
      "retrieval_leak_upper": 0.007,
      "answer_leak_upper": 0.001
    }
  },
  "samples": [
    {
      "q_id": "filt_pcaob_001",
      "allowed": {
        "framework": ["Other"],
        "jurisdiction": ["US"],
        "doc_type": ["standard"],
        "authority_level": ["authoritative"]
      },
      "retrieved": [
        {
          "doc_id": "EU_ESMA_ESEF@2023-12-31",
          "framework": "Other",
          "jurisdiction": "EU",
          "leak": true,
          "leak_reason": "jurisdiction_mismatch"
        }
      ]
    }
  ],
  "metadata": {
    "dataset_version": "v1.2.0",
    "run_timestamp": "2024-01-15T10:45:00Z",
    "filter_logic_version": "v2.1"
  }
}
```

## asof_report.json

```json
{
  "summary": {
    "checked": 120,
    "version_mismatch": 1,
    "leak_rate": 0.008,
    "temporal_queries": 300,
    "confidence_interval": {
      "leak_rate_upper": 0.015
    }
  },
  "cases": [
    {
      "q_id": "tt_pcaob_as3101_2019",
      "as_of_date": "2019-12-31",
      "expect_version": "AS 3101 (2017-2020 text)",
      "expect_doc_ids": ["PCAOB_AS_3101@2019-12-31"],
      "cited_versions": ["PCAOB_AS_3101@2019-12-31"],
      "disallow_doc_ids": ["PCAOB_AS_3101@2024-12-31"],
      "pass": true,
      "version_check": "exact_match"
    }
  ],
  "metadata": {
    "dataset_version": "v1.2.0", 
    "temporal_logic_version": "v1.5",
    "run_timestamp": "2024-01-15T11:00:00Z"
  }
}
```

## negatives_report.json

```json
{
  "summary": {
    "total_queries": 200,
    "false_positives": 0,
    "false_positive_rate": 0.0,
    "guard_effectiveness": 1.0,
    "confidence_interval": {
      "false_positive_rate_upper": 0.006
    }
  },
  "queries": [
    {
      "q_id": "nc_nz_tax",
      "query": "What are the tax depreciation rules in New Zealand for small businesses?",
      "filters": {
        "framework": "Other",
        "jurisdiction": "US", 
        "doc_type": "standard",
        "authority_level": "authoritative"
      },
      "response_type": "guard",
      "guard_reason": "out_of_jurisdiction",
      "false_positive": false
    }
  ],
  "metadata": {
    "dataset_version": "v1.2.0",
    "guard_logic_version": "v3.1", 
    "run_timestamp": "2024-01-15T11:15:00Z"
  }
}
```

## structured_fidelity.json

```json
{
  "summary": {
    "fields_total": 320,
    "grounded": 318,
    "coverage": 0.993,
    "false_fills": 0,
    "schemas_tested": ["memo", "journal_entry", "disclosure"],
    "confidence_interval": {
      "coverage_lower": 0.985,
      "false_fill_rate_upper": 0.003
    }
  },
  "fields": [
    {
      "doc_id": "memo_001",
      "schema": "memo",
      "field": "conclusion",
      "spans": ["PCAOB_AS_3101@2024-12-31#p4"],
      "entailed": true,
      "grounded": true,
      "nli_score": 0.91
    }
  ],
  "schemas": [
    {
      "schema_name": "memo",
      "fields_tested": 120,
      "grounded_fields": 119,
      "false_fills": 0,
      "coverage": 0.992
    }
  ],
  "metadata": {
    "dataset_version": "v1.2.0",
    "schema_versions": {
      "memo": "v2.1",
      "journal_entry": "v1.8", 
      "disclosure": "v1.5"
    },
    "run_timestamp": "2024-01-15T11:30:00Z"
  }
}
```

## perf_load.json

```json
{
  "summary": {
    "concurrency": 5,
    "duration_seconds": 600,
    "total_requests": 2847,
    "success_rate": 0.997,
    "p50_ms": 2100,
    "p95_ms": 6400,
    "p99_ms": 8900,
    "errors": 3,
    "rps_avg": 4.75,
    "rps_peak": 8.2
  },
  "histogram": [
    {"le": 1000, "count": 421},
    {"le": 2000, "count": 1205},
    {"le": 3000, "count": 1834},
    {"le": 5000, "count": 2456},
    {"le": 8000, "count": 2798},
    {"le": 10000, "count": 2847}
  ],
  "errors": [
    {
      "timestamp": "2024-01-15T12:05:43Z",
      "status": 503,
      "error": "service_temporarily_unavailable",
      "tagged_as": "infra"
    }
  ],
  "thresholds": {
    "p50_target_ms": 2500,
    "p95_target_ms": 8000,
    "p50_pass": true,
    "p95_pass": true,
    "error_rate_target": 0.01,
    "error_rate_pass": true
  },
  "metadata": {
    "k6_version": "0.47.0",
    "scenario": "steady_usage",
    "run_timestamp": "2024-01-15T12:00:00Z",
    "test_duration": "10m"
  }
}
```

## replay_report.json

```json
{
  "summary": {
    "manifests_processed": 200,
    "retrieval_identity": 1.0,
    "answer_similarity": 0.97,
    "exact_matches": 194,
    "near_matches": 6,
    "failures": 0
  },
  "diffs": [
    {
      "manifest_id": "query_20240115T103045Z",
      "original_chunks": ["chunk_123", "chunk_456", "chunk_789"],
      "replay_chunks": ["chunk_123", "chunk_456", "chunk_789"], 
      "chunk_identity": true,
      "original_answer": "PCAOB requires auditors to...",
      "replay_answer": "PCAOB requires auditors to...",
      "similarity": 1.0,
      "exact_match": true
    }
  ],
  "similarity_distribution": {
    "min": 0.89,
    "max": 1.0,
    "mean": 0.974,
    "p25": 0.95,
    "p50": 0.98,
    "p75": 1.0,
    "p95": 1.0
  },
  "metadata": {
    "corpus_hash": "sha256:abc123...",
    "model_hash": "sha256:def456...",
    "replay_timestamp": "2024-01-15T13:00:00Z",
    "original_date_range": "2024-01-01_to_2024-01-14"
  }
}
```

## pii_redaction_report.json

```json
{
  "summary": {
    "pii_samples": 1000,
    "categories_tested": ["email", "phone", "ssn", "account", "name"],
    "redaction_recall": 0.97,
    "redaction_precision": 0.985,
    "retrieval_leak_rate": 0.0,
    "confidence_interval": {
      "recall_lower": 0.95,
      "precision_lower": 0.975,
      "leak_rate_upper": 0.003
    }
  },
  "categories": [
    {
      "category": "email",
      "samples": 200,
      "redacted": 196,
      "recall": 0.98,
      "false_positives": 3,
      "precision": 0.985
    }
  ],
  "retrieval_test": {
    "pii_queries": 50,
    "leaked_samples": 0,
    "leak_rate": 0.0,
    "query_examples": [
      {
        "query": "john.doe@example.com",
        "retrieved": false,
        "redacted_form": "[EMAIL_REDACTED]"
      }
    ]
  },
  "generators": {
    "emails": "faker.providers.internet.email",
    "phones": "faker.providers.phone_number.phone_number",
    "ssns": "custom_regex:999-99-9999",
    "accounts": "custom_regex:ACC[0-9]{8}",
    "names": "faker.providers.person.name"
  },
  "metadata": {
    "seed": 42,
    "locales": ["en_US", "en_GB", "de_DE", "fr_FR"],
    "pattern_version": "v1.3",
    "run_timestamp": "2024-01-15T13:30:00Z"
  }
}
```

## Common Metadata Fields

All reports include these standard metadata fields:

```json
{
  "metadata": {
    "dataset_version": "v1.2.0",          // Version of test dataset used
    "corpus_hash": "sha256:...",          // Hash of document corpus
    "model_hash": "sha256:...",           // Hash of model/embeddings
    "run_timestamp": "2024-01-15T10:30:00Z",
    "git_commit": "abc123...",            // Git commit of evaluation code
    "runner_version": "v1.0.0",          // Version of specific runner
    "seed": 42,                           // Random seed for reproducibility
    "status": "COMPLETED"                 // COMPLETED | FAILED | NOT_IMPLEMENTED
  }
}
```

## Error Handling Schema

When runners encounter errors:

```json
{
  "status": "FAILED",
  "error": {
    "type": "DatabaseConnectionError",
    "message": "Unable to connect to evaluation database",
    "timestamp": "2024-01-15T10:30:00Z",
    "traceback": "...",
    "tagged_as": "infra"  // "infra" | "model" | "data"
  },
  "partial_results": {
    // Any results computed before failure
  },
  "metadata": {
    // Standard metadata fields
  }
}
```

## Not Implemented Schema

For placeholder runners:

```json
{
  "status": "NOT_IMPLEMENTED", 
  "message": "This evaluation runner is not yet implemented",
  "planned_metrics": [
    "faithfulness_score",
    "citation_precision", 
    "citation_recall"
  ],
  "metadata": {
    "runner_version": "v0.1.0-placeholder",
    "run_timestamp": "2024-01-15T10:30:00Z"
  }
}
```
