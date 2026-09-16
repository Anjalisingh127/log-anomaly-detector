# Local setup

## Prerequisites

- Python 3.10 or newer
- Git

## Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
python scripts/generate_logs.py
python -m log_anomaly_detector.cli parse --input data/sample_application.log --output reports
python -m pytest
```

## Linux or macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
python scripts/generate_logs.py
python -m log_anomaly_detector.cli parse --input data/sample_application.log --output reports
python -m pytest
```

The generator returns exit code `0` on success and `1` for configuration or
file errors. The parser returns `0` for success, `2` for a missing input, `3`
for an I/O or encoding failure, and `4` when `--fail-on-malformed` finds rejected
records. Runtime diagnostic messages are emitted as JSON to standard error.
