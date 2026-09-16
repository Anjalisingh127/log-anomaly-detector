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
python scripts/generate_logs.py
python -m pytest
```

## Linux or macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python scripts/generate_logs.py
python -m pytest
```

The generator returns exit code `0` on success and `1` for configuration or
file errors. Day 2 will add parser-specific exit codes and structured runtime
logging.
