#!/usr/bin/env python3
"""Generate deterministic, privacy-safe application logs for local analysis."""

from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from log_anomaly_detector.models import LogEvent  # noqa: E402

SERVICES = ("auth-service", "order-service", "payment-service", "catalog-service")
ENDPOINTS = {
    "auth-service": ("/api/v1/login", "/api/v1/token"),
    "order-service": ("/api/v1/orders", "/api/v1/orders/status"),
    "payment-service": ("/api/v1/payments", "/api/v1/refunds"),
    "catalog-service": ("/api/v1/products", "/api/v1/search"),
}
FAILURES = (
    ("DATABASE_TIMEOUT", "Database connection timed out", 503),
    ("AUTHENTICATION_FAILURE", "Invalid or expired credentials", 401),
    ("INTERNAL_SERVER_ERROR", "Unhandled application exception", 500),
    ("RATE_LIMIT_EXCEEDED", "Client request limit exceeded", 429),
    ("RESOURCE_PRESSURE", "Host disk or memory threshold exceeded", 503),
)


def stable_identifier(seed: int, event_number: int) -> str:
    """Return a deterministic UUID-like identifier without personal data."""
    value = ((seed & ((1 << 32) - 1)) << 96) | event_number
    return str(UUID(int=value))


def is_anomaly_event(event_number: int, windows: list[dict[str, int]]) -> bool:
    return any(
        window["start_event"] <= event_number < window["start_event"] + window["length"]
        for window in windows
    )


def build_event(
    rng: random.Random,
    event_number: int,
    timestamp: datetime,
    seed: int,
    anomaly: bool,
) -> LogEvent:
    service = rng.choice(SERVICES)
    failure_probability = 0.55 if anomaly else 0.035
    warning_probability = 0.12 if anomaly else 0.045
    roll = rng.random()

    error_type = "NONE"
    status_code = 200
    level = "INFO"
    message = "Request completed successfully"
    response_time_ms = max(20, int(rng.gauss(220, 85)))

    if roll < failure_probability:
        error_type, message, status_code = rng.choice(FAILURES)
        level = "CRITICAL" if error_type in {"DATABASE_TIMEOUT", "RESOURCE_PRESSURE"} and rng.random() < 0.2 else "ERROR"
        response_time_ms = rng.randint(900, 4500)
    elif roll < failure_probability + warning_probability:
        level = "WARNING"
        error_type = "SLOW_REQUEST"
        message = "Request latency exceeded warning threshold"
        response_time_ms = rng.randint(1500, 3500)

    request_id = stable_identifier(seed, event_number)
    return LogEvent(
        timestamp=timestamp.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        level=level,
        service=service,
        environment="production-simulated",
        host=f"app-{rng.randint(1, 4):02d}",
        request_id=request_id,
        client_id=f"client-{rng.randint(1, 250):04d}",
        method=rng.choice(("GET", "POST", "PUT")),
        endpoint=rng.choice(ENDPOINTS[service]),
        status_code=status_code,
        response_time_ms=response_time_ms,
        error_type=error_type,
        message=message,
    )


def generate(config_path: Path, output_path: Path, count_override: int | None = None) -> dict[str, int]:
    with config_path.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)["generator"]

    seed = int(config["seed"])
    count = int(count_override if count_override is not None else config["event_count"])
    if count < 1:
        raise ValueError("event count must be at least 1")

    start_time = datetime.fromisoformat(config["start_time"].replace("Z", "+00:00"))
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    interval = timedelta(seconds=int(config["interval_seconds"]))
    windows = config.get("anomaly_windows", [])
    rng = random.Random(seed)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    counts = {"events": 0, "errors": 0, "critical": 0, "warnings": 0}
    with output_path.open("w", encoding="utf-8", newline="\n") as stream:
        for index in range(count):
            event = build_event(
                rng=rng,
                event_number=index,
                timestamp=start_time + index * interval,
                seed=seed,
                anomaly=is_anomaly_event(index, windows),
            )
            stream.write(event.to_log_line() + "\n")
            counts["events"] += 1
            if event.level in {"ERROR", "CRITICAL"}:
                counts["errors"] += 1
            if event.level == "CRITICAL":
                counts["critical"] += 1
            if event.level == "WARNING":
                counts["warnings"] += 1
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config" / "config.yaml")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "sample_application.log")
    parser.add_argument("--count", type=int, help="Override event count from config")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        counts = generate(args.config, args.output, args.count)
    except (OSError, KeyError, TypeError, ValueError, yaml.YAMLError) as exc:
        print(f"Generation failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"Generated {counts['events']} events at {args.output} "
        f"({counts['errors']} errors, {counts['critical']} critical, "
        f"{counts['warnings']} warnings)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
