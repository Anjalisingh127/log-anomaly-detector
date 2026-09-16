# Log Anomaly Detection & Incident Monitoring System

A support-engineering portfolio project that generates reproducible application
logs and will analyze failures with Python, pandas, regular expressions, and
Splunk. The project focuses on explainable operational diagnostics, measurable
benchmarks, and reusable incident documentation.

**[Live operations report](https://anjalisingh127.github.io/log-anomaly-detector/)**
· **[Incident runbook](docs/incident-runbook.md)**
· **[Incident note template](docs/incident-note-template.md)**

> **Project status:** Day 4 reporting and benchmark tooling complete. The current dataset and results
> are synthetic; no production system or customer data is represented.

## Day 1 capabilities

- Generates 5,000 deterministic application events from configuration.
- Models four services, four hosts, HTTP metrics, request correlation, and five
  recurring failure categories.
- Injects two configured error-spike windows for later detection testing.
- Produces Splunk-friendly line-oriented logs without secrets or personal data.
- Includes tests for deterministic identifiers, anomaly boundaries, and schema.

## Day 2 capabilities

- Parses the complete log schema with compiled regular expressions.
- Validates timestamps, severity levels, HTTP methods, status codes, endpoints,
  and response times.
- Isolates malformed records with line number, reason, and original evidence.
- Exports normalized events to CSV and JSON for pandas and Splunk ingestion.
- Produces a machine-readable parse summary and JSON operational logs.
- Uses documented exit codes for automation and support diagnostics.

## Day 3 capabilities

- Flags `ERROR`/`CRITICAL`, HTTP 5xx, slow requests, and database timeouts.
- Detects configurable consecutive authentication-failure sequences.
- Aggregates errors into five-minute operational windows.
- Uses a six-window rolling baseline and explainable z-scores to flag spikes.
- Handles zero-variance baselines without division errors.
- Exports anomaly evidence, window metrics, and a JSON detection summary.

## Day 4 capabilities

- Generates a self-contained HTML operations report with no external scripts.
- Visualizes error trends, failure categories, affected services, and hosts.
- Publishes detection thresholds and synthetic-data disclosure with the evidence.
- Measures median scripted execution time across repeated trials.
- Calculates time reduction only after a real manual timing is supplied.

## Failure scenarios

1. Database connection timeout
2. Authentication failure
3. Internal server error
4. API rate-limit violation
5. Disk or memory pressure

## Quick start

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
python scripts/generate_logs.py
python -m log_anomaly_detector.cli parse --input data/sample_application.log --output reports
python -m log_anomaly_detector.cli analyze --input data/sample_application.log --output reports --html-report docs/index.html
python scripts/benchmark.py --runs 7
python -m pytest
```

Example successful output:

```text
Generated 5000 events at data/sample_application.log (304 errors, 20 critical, 209 warnings).
```

These counts are reproducible with seed `42`; changing the configuration changes the results.

## Roadmap

- [x] Repository structure and reproducible log generator
- [x] Regex parser and malformed-record handling
- [x] Explainable rule-based and statistical anomaly detection
- [x] CSV and HTML operational reports
- [ ] Splunk dashboard, saved searches, and trial-license alert
- [x] Five-error incident runbook
- [ ] Measured manual-versus-script benchmark
- [x] GitHub Pages report
- [ ] Demonstration media

## Documentation

- [Architecture](docs/architecture.md)
- [Local setup](docs/setup-guide.md)
- [Dataset notes](data/README.md)
- [Application support incident runbook](docs/incident-runbook.md)
- [Reusable incident note template](docs/incident-note-template.md)
- [Worked synthetic incident](docs/sample-incident.md)
- [Performance methodology](docs/performance-methodology.md)
- [Splunk Enterprise Docker setup](splunk/docker-setup.md)

## Ethics and measurement

This project does not claim production impact. Any future time-saving percentage
will be published only with its benchmark method, raw timings, and calculation.

## License

MIT
