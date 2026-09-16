#!/usr/bin/env python3
"""Measure scripted analysis time; optionally compare with a recorded manual trial."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from log_anomaly_detector.detector import detect_anomalies, load_detection_config  # noqa: E402
from log_anomaly_detector.parser import parse_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/sample_application.log")
    parser.add_argument("--config", type=Path, default=ROOT / "config/config.yaml")
    parser.add_argument("--runs", type=int, default=7)
    parser.add_argument("--manual-seconds", type=float)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/benchmark_results.json")
    args = parser.parse_args()
    if args.runs < 3 or (args.manual_seconds is not None and args.manual_seconds <= 0):
        parser.error("runs must be at least 3 and manual-seconds must be positive")
    config = load_detection_config(args.config)
    timings = []
    for _ in range(args.runs):
        started = perf_counter()
        parsed = parse_file(args.input)
        detected = detect_anomalies(parsed.events, config)
        timings.append(perf_counter() - started)
    median = statistics.median(timings)
    result = {
        "event_count": parsed.valid_count,
        "runs": args.runs,
        "script_seconds": [round(value, 6) for value in timings],
        "median_script_seconds": round(median, 6),
        "detections": detected.summary["detections"],
        "manual_seconds": args.manual_seconds,
        "estimated_time_reduction_percent": (
            round((args.manual_seconds - median) / args.manual_seconds * 100, 2)
            if args.manual_seconds is not None else None
        ),
        "claim_status": "measured" if args.manual_seconds is not None else "manual trial required",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
