from pathlib import Path

from log_anomaly_detector.detector import DetectionConfig, detect_anomalies
from log_anomaly_detector.parser import ParseResult
from log_anomaly_detector.reporter import generate_html_report


def test_html_report_is_self_contained_and_escapes_values(tmp_path: Path):
    event = {
        "timestamp": "2026-09-01T09:00:00.000Z", "level": "ERROR",
        "service": "<script>alert(1)</script>", "environment": "production-simulated",
        "host": "app-01", "request_id": "req-1", "client_id": "client-1",
        "method": "GET", "endpoint": "/health", "status_code": 500,
        "response_time_ms": 2000, "error_type": "INTERNAL_SERVER_ERROR", "message": "failed",
    }
    parsed = ParseResult(events=[event], malformed=[], total_lines=1)
    detected = detect_anomalies(parsed.events, DetectionConfig())
    target = generate_html_report(parsed, detected, tmp_path / "index.html")
    html = target.read_text(encoding="utf-8")
    assert "<!doctype html>" in html
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "https://" not in html
    assert "min-width:560px" not in html
    assert "Dataset final timestamp" in html
