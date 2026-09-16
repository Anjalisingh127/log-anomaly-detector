from datetime import datetime, timezone
from pathlib import Path
import importlib.util


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_logs.py"
SPEC = importlib.util.spec_from_file_location("generate_logs", SCRIPT)
generate_logs = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generate_logs)


def test_stable_identifier_is_deterministic():
    assert generate_logs.stable_identifier(42, 7) == generate_logs.stable_identifier(42, 7)
    assert generate_logs.stable_identifier(42, 7) != generate_logs.stable_identifier(42, 8)


def test_anomaly_window_boundaries():
    windows = [{"start_event": 10, "length": 3}]
    assert not generate_logs.is_anomaly_event(9, windows)
    assert generate_logs.is_anomaly_event(10, windows)
    assert generate_logs.is_anomaly_event(12, windows)
    assert not generate_logs.is_anomaly_event(13, windows)


def test_build_event_contains_expected_operational_fields():
    import random

    event = generate_logs.build_event(
        random.Random(42), 1, datetime(2026, 9, 1, tzinfo=timezone.utc), 42, False
    )
    line = event.to_log_line()
    for field in ("level=", "service=", "request_id=", "status_code=", "response_time_ms="):
        assert field in line
