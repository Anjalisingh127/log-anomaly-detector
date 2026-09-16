import json
from pathlib import Path

import pandas as pd
import pytest

from log_anomaly_detector.cli import EXIT_INPUT_ERROR, EXIT_MALFORMED_THRESHOLD, main
from log_anomaly_detector.parser import export_result, parse_file, parse_line


VALID_LINE = (
    '2026-09-01T09:00:00.000Z level=ERROR service=auth-service '
    'environment=production-simulated host=app-01 '
    'request_id=0000002a-0000-0000-0000-000000000000 client_id=client-0001 '
    'method=POST endpoint=/api/v1/login status_code=503 response_time_ms=3133 '
    'error_type=DATABASE_TIMEOUT message="Database connection timed out"'
)


def test_parse_line_converts_numeric_fields():
    event = parse_line(VALID_LINE)
    assert event["status_code"] == 503
    assert event["response_time_ms"] == 3133
    assert event["error_type"] == "DATABASE_TIMEOUT"


@pytest.mark.parametrize(
    ("old", "new", "reason"),
    [
        ("level=ERROR", "level=UNKNOWN", "unsupported level"),
        ("status_code=503", "status_code=700", "status_code"),
        ("response_time_ms=3133", "response_time_ms=-1", "cannot be negative"),
        ("method=POST", "method=CONNECT", "unsupported HTTP method"),
    ],
)
def test_parse_line_rejects_invalid_fields(old, new, reason):
    with pytest.raises(ValueError, match=reason):
        parse_line(VALID_LINE.replace(old, new))


def test_parse_file_isolates_malformed_record(tmp_path: Path):
    source = tmp_path / "application.log"
    source.write_text(f"{VALID_LINE}\nnot a valid log line\n", encoding="utf-8")
    result = parse_file(source)
    assert result.total_lines == 2
    assert result.valid_count == 1
    assert result.malformed_count == 1
    assert result.malformed[0].line_number == 2


def test_export_result_creates_machine_readable_outputs(tmp_path: Path):
    source = tmp_path / "application.log"
    source.write_text(f"{VALID_LINE}\nbroken\n", encoding="utf-8")
    result = parse_file(source)
    paths = export_result(result, tmp_path / "reports")
    assert set(paths) == {"events_csv", "events_json", "malformed_csv", "summary_json"}
    assert pd.read_csv(paths["events_csv"]).shape[0] == 1
    assert json.loads(paths["summary_json"].read_text())["malformed_records"] == 1


def test_export_result_handles_zero_malformed_records(tmp_path: Path):
    source = tmp_path / "application.log"
    source.write_text(f"{VALID_LINE}\n", encoding="utf-8")
    paths = export_result(parse_file(source), tmp_path / "reports")
    malformed = pd.read_csv(paths["malformed_csv"])
    assert malformed.empty
    assert list(malformed.columns) == ["line_number", "reason", "raw_line"]


def test_cli_returns_input_error_for_missing_file(tmp_path: Path):
    assert main(["parse", "--input", str(tmp_path / "missing.log")]) == EXIT_INPUT_ERROR


def test_cli_can_fail_on_malformed_records(tmp_path: Path):
    source = tmp_path / "application.log"
    source.write_text("broken\n", encoding="utf-8")
    assert main([
        "parse", "--input", str(source), "--output", str(tmp_path / "reports"),
        "--fail-on-malformed",
    ]) == EXIT_MALFORMED_THRESHOLD
