# Dataset

`sample_application.log` is entirely synthetic and contains no real customer,
employee, credential, or production information. It is generated with a fixed
seed from `config/config.yaml`, making results reproducible.

Each line contains an ISO-8601 timestamp followed by key-value fields. The
environment value is deliberately `production-simulated` to prevent the sample
from being mistaken for real production data.

Regenerate the dataset from the repository root:

```bash
python scripts/generate_logs.py
```
