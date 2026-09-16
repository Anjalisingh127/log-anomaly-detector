from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from log_anomaly_detector.detector import (
    DetectionConfig,
    detect_anomalies,
    export_detections,
    load_detection_config,
)


def event(
    minute: int,
    *,
    level: str = "INFO",
    status: int = 200,
    latency: int = 100,
    error: str = "NONE",
    client: str = "client-1",
    request: str | None = None,
) -> dict[str, object]:
    timestamp = datetime(2026, 9, 1, tzinfo=timezone.utc) + timedelta(minutes=minute)
    return {
        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
        "level": level,
        "service": "auth-service",
        "environment": "production-simulated",
        "host": "app-01",
        "request_id": request or f"req-{minute}-{client}",
        "client_id": client,
        "method": "POST",
        "endpoint": "/api/v1/login",
        "status_code": status,
        "response_time_ms": latency,
        "error_type": error,
        "message": "test event",
    }


def test_rule_detectors_are_explainable():
    events = [
        event(0),
        event(1, level="ERROR", status=503, latency=2200, error="DATABASE_TIMEOUT"),
    ]
    result = detect_anomalies(events, DetectionConfig())
    types = set(result.anomalies["detection_type"])
    assert types == {"severity_error", "http_5xx", "slow_request", "database_timeout"}
    assert result.summary["detections"] == 4


def test_consecutive_authentication_failures_reset_after_success():
    events = [
        event(0, level="ERROR", status=401, error="AUTHENTICATION_FAILURE"),
        event(1, level="ERROR", status=401, error="AUTHENTICATION_FAILURE"),
        event(2),
        event(3, level="ERROR", status=401, error="AUTHENTICATION_FAILURE"),
        event(4, level="ERROR", status=401, error="AUTHENTICATION_FAILURE"),
        event(5, level="ERROR", status=401, error="AUTHENTICATION_FAILURE"),
    ]
    result = detect_anomalies(events, DetectionConfig(consecutive_auth_failures=3))
    repeated = result.anomalies.loc[
        result.anomalies["detection_type"].eq("repeated_authentication_failure")
    ]
    assert len(repeated) == 3
    assert repeated["details"].str.contains("failures=3").all()


def test_error_spike_handles_zero_variance_baseline():
    events = [event(minute * 5, level="ERROR", status=500, error="INTERNAL_SERVER_ERROR") for minute in range(6)]
    events.extend(
        event(30, level="ERROR", status=500, error="INTERNAL_SERVER_ERROR", request=f"spike-{i}")
        for i in range(10)
    )
    result = detect_anomalies(events, DetectionConfig())
    assert result.summary["spike_windows"] == 1
    spike = result.error_windows.loc[result.error_windows["is_spike"]].iloc[0]
    assert spike["error_count"] == 10
    assert spike["z_score"] == float("inf")


def test_load_config_and_export(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "detection:\n  window_minutes: 10\n  z_score_threshold: 3\n"
        "  slow_request_ms: 1000\n  consecutive_auth_failures: 4\n  baseline_windows: 5\n",
        encoding="utf-8",
    )
    config = load_detection_config(config_path)
    assert config.window_minutes == 10
    result = detect_anomalies([event(0)], config)
    paths = export_detections(result, tmp_path / "reports")
    assert set(paths) == {"anomalies", "error_windows", "summary"}
    assert pd.read_csv(paths["error_windows"]).shape[0] >= 1
