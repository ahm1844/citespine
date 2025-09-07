.PHONY: up down api install ingest index eval lint test eval_all eval_faithfulness eval_filters eval_asof eval_negatives eval_structured eval_perf eval_replay eval_security eval_pii gates ci sbom scan_trivy scan_grype

up:
	docker compose up -d

down:
	docker compose down

api:
	docker compose up -d api

install:
	pip install -r requirements.txt || true

ingest:
	docker compose run --rm api python -m src.ingest.runner

index:
	docker compose run --rm api python -m src.index.build_index

eval:
	docker compose run --rm api python -m src.eval.evaluate || true

lint:
	ruff check . ; black --check . ; mypy || true

test:
	pytest -q

label_add:
	docker compose run --rm api python -m src.eval.label add $(Q) $(C)
label_remove:
	docker compose run --rm api python -m src.eval.label remove $(Q) $(C)

fetch_urls:
	docker compose run --rm api python -m src.tools.fetch_urls --urls-file $(URLS) --framework $(FW) --jurisdiction $(JUR) --doc-type $(DT) --authority-level $(AL) --effective-date $(EFD) --version $(VER) --title-prefix "$(TP)" --workers $(W)

parity:
	docker compose run --rm api python -m src.eval.parity --top-k $(K) --probes $(P)

pc_upsert:
	docker compose run --rm api python -m src.tools.pinecone_upsert --processed-dir data/processed --namespace $(NS) --batch-size $(B) --max-chunks $(M) --create-index $(CREATE)

seed_diag:
	docker compose run --rm api python -m src.eval.seed_diag --top-k $(K) --probes $(P)

seed_dump:
	docker compose run --rm api python -m src.eval.seed_dump --top-k $(K) --probes $(P) --ids "$(IDS)"

# Run everything
eval_all: eval_faithfulness eval_filters eval_asof eval_negatives eval_structured eval_perf eval_replay eval_pii gates

# Run inside the api container so deps are consistent
PY := docker compose run --rm api python

eval_faithfulness:
	$(PY) -m src.eval.runners.faithfulness --in src/eval/datasets/seed_questions.jsonl --out data/eval/faithfulness_report.json

eval_filters:
	$(PY) -m src.eval.runners.filters --in src/eval/datasets/seed_questions.jsonl --out data/eval/filter_leak_report.json

eval_asof:
	$(PY) -m src.eval.runners.asof --in src/eval/datasets/time_travel.jsonl --out data/eval/asof_report.json

eval_negatives:
	$(PY) -m src.eval.runners.negatives --in src/eval/datasets/negative_controls.jsonl --out data/eval/negatives_report.json

eval_structured:
	$(PY) -m src.eval.runners.structured_fidelity --in src/eval/datasets/seed_questions.jsonl --out data/eval/structured_fidelity.json

# Export perf JSON directly from k6
eval_perf:
	docker compose run --rm --profile perf k6 run \
	  --summary-export data/eval/perf_load.json src/eval/runners/perf.js

eval_replay:
	$(PY) -m src.eval.runners.replay --manifests data/manifests --out data/eval/replay_report.json

eval_security:
	@echo "See docs/SECURITY.md for packet-capture & CVE scan steps"; exit 0

eval_pii:
	$(PY) -m src.eval.runners.pii_redaction --in src/eval/datasets/seed_questions.jsonl --out data/eval/pii_redaction_report.json

# Hard-gate based on acceptance thresholds (this script reads all reports, fails non-zero if any fail)
gates:
	$(PY) -m src.eval.runners.gates

ci:
	docker compose up -d postgres api && make eval_all

sbom:
	docker run --rm -v $(PWD):/work anchore/syft:latest packages dir:/work -o json > data/security/sbom.json

scan_trivy:
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image citespine-api:latest > data/security/trivy.txt || true

scan_grype:
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock anchore/grype:latest citespine-api:latest > data/security/grype.txt || true