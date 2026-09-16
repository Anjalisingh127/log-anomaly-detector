# Performance methodology

The project does not claim a time-saving percentage until both scripted and
manual trials have been recorded. The dataset is synthetic, and the result is a
portfolio benchmark rather than production impact.

## Scripted trial

Run at least seven repetitions and use the median:

```powershell
python scripts/benchmark.py --runs 7
```

## Manual trial

1. Use the same unmodified `sample_application.log` file.
2. Start a timer before opening the file.
3. Manually identify every `ERROR` and `CRITICAL` line, categorize the five
   failure types, and record five-minute error counts.
4. Stop when the counts and categories have been written down.
5. Repeat three times and use the median number of seconds.
6. Record the median with `--manual-seconds`; do not estimate it from memory.

```powershell
python scripts/benchmark.py --runs 7 --manual-seconds YOUR_MEASURED_MEDIAN
```

The tool calculates:

```text
(manual seconds - median script seconds) / manual seconds * 100
```

The README or resume may use the resulting percentage only while describing it
as a controlled synthetic-data benchmark.
