# Log Anomaly Detection & Incident Monitoring System

A support-engineering portfolio project that generates reproducible application
logs and will analyze failures with Python, pandas, regular expressions, and
Splunk. The project focuses on explainable operational diagnostics, measurable
benchmarks, and reusable incident documentation.

> **Project status:** Day 1 foundation complete. The current dataset and results
> are synthetic; no production system or customer data is represented.

## Day 1 capabilities

- Generates 5,000 deterministic application events from configuration.
- Models four services, four hosts, HTTP metrics, request correlation, and five
  recurring failure categories.
- Injects two configured error-spike windows for later detection testing.
- Produces Splunk-friendly line-oriented logs without secrets or personal data.
- Includes tests for deterministic identifiers, anomaly boundaries, and schema.

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
python scripts/generate_logs.py
python -m pytest
```

Example successful output:

```text
Generated 5000 events at data/sample_application.log (304 errors, 20 critical, 209 warnings).
```

These counts are reproducible with seed `42`; changing the configuration changes the results.

## Roadmap

- [x] Repository structure and reproducible log generator
- [ ] Regex parser and malformed-record handling
- [ ] Explainable rule-based and statistical anomaly detection
- [ ] CSV and HTML operational reports
- [ ] Splunk dashboard, saved searches, and trial-license alert
- [ ] Five-error incident runbook and measured benchmark
- [ ] GitHub Pages report and demonstration media

## Documentation

- [Architecture](docs/architecture.md)
- [Local setup](docs/setup-guide.md)
- [Dataset notes](data/README.md)

## Ethics and measurement

This project does not claim production impact. Any future time-saving percentage
will be published only with its benchmark method, raw timings, and calculation.

## License

MIT
