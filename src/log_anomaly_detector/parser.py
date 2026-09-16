"""Parse and validate the project's line-oriented application logs."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

import pandas as pd

LOGGER = logging.getLogger(__name__)

LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\S+) "
    r"level=(?P<level>\S+) "
    r"service=(?P<service>\S+) "
    r"environment=(?P<environment>\S+) "
    r"host=(?P<host>\S+) "
    r"request_id=(?P<request_id>\S+) "
    r"client_id=(?P<client_id>\S+) "
    r"method=(?P<method>\S+) "
    r"endpoint=(?P<endpoint>\S+) "
    r"status_code=(?P<status_code>\S+) "
    r"response_time_ms=(?P<response_time_ms>\S+) "
    r"error_type=(?P<error_type>\S+) "
    r'message="(?P<message>.*)"$'
)

ALLOWED_LEVELS = {"INFO", "WARNING", "ERROR", "CRITICAL"}
ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


@dataclass(frozen=True)
class MalformedRecord:
    """A rejected input line with enough evidence to troubleshoot it."""

    line_number: int
    reason: str
    raw_line: str


@dataclass
class ParseResult:
    """Valid events and rejected records from one input file."""

    events: list[dict[str, object]]
    malformed: list[MalformedRecord]
    total_lines: int

    @property
    def valid_count(self) -> int:
        return len(self.events)

    @property
    def malformed_count(self) -> int:
        return len(self.malformed)


def _parse_timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _validate_match(values: dict[str, str]) -> dict[str, object]:
    level = values["level"]
    if level not in ALLOWED_LEVELS:
        raise ValueError(f"unsupported level: {level}")

    method = values["method"]
    if method not in ALLOWED_METHODS:
        raise ValueError(f"unsupported HTTP method: {method}")

    status_code = int(values["status_code"])
    if not 100 <= status_code <= 599:
        raise ValueError("status_code must be between 100 and 599")

    response_time_ms = int(values["response_time_ms"])
    if response_time_ms < 0:
        raise ValueError("response_time_ms cannot be negative")

    if not values["endpoint"].startswith("/"):
        raise ValueError("endpoint must start with '/'")

    return {
        **values,
        "timestamp": _parse_timestamp(values["timestamp"]),
        "status_code": status_code,
        "response_time_ms": response_time_ms,
    }


def parse_line(raw_line: str) -> dict[str, object]:
    """Parse one log line or raise ValueError with an actionable reason."""
    line = raw_line.rstrip("\r\n")
    if not line:
        raise ValueError("empty line")
    match = LOG_PATTERN.fullmatch(line)
    if match is None:
        raise ValueError("line does not match the expected log format")
    try:
        return _validate_match(match.groupdict())
    except (TypeError, ValueError) as exc:
        raise ValueError(str(exc)) from exc


def iter_lines(input_path: Path) -> Iterator[tuple[int, str]]:
    """Yield numbered lines lazily so large files are not loaded twice."""
    with input_path.open(encoding="utf-8") as stream:
        for line_number, raw_line in enumerate(stream, start=1):
            yield line_number, raw_line


def parse_file(input_path: Path) -> ParseResult:
    """Parse a file while isolating malformed records instead of crashing."""
    events: list[dict[str, object]] = []
    malformed: list[MalformedRecord] = []
    total_lines = 0

    LOGGER.info("parse_started", extra={"input_path": str(input_path)})
    for line_number, raw_line in iter_lines(input_path):
        total_lines = line_number
        try:
            events.append(parse_line(raw_line))
        except ValueError as exc:
            malformed.append(
                MalformedRecord(
                    line_number=line_number,
                    reason=str(exc),
                    raw_line=raw_line.rstrip("\r\n"),
                )
            )
            LOGGER.warning(
                "malformed_record",
                extra={"line_number": line_number, "reason": str(exc)},
            )

    LOGGER.info(
        "parse_completed",
        extra={
            "total_lines": total_lines,
            "valid_records": len(events),
            "malformed_records": len(malformed),
        },
    )
    return ParseResult(events=events, malformed=malformed, total_lines=total_lines)


def export_result(result: ParseResult, output_dir: Path) -> dict[str, Path]:
    """Export normalized records and malformed-line evidence."""
    output_dir.mkdir(parents=True, exist_ok=True)
    events_csv = output_dir / "normalized_events.csv"
    events_json = output_dir / "normalized_events.json"
    malformed_csv = output_dir / "malformed_records.csv"
    summary_json = output_dir / "parse_summary.json"

    events_frame = pd.DataFrame(result.events)
    malformed_columns = ["line_number", "reason", "raw_line"]
    malformed_frame = pd.DataFrame(
        (asdict(record) for record in result.malformed),
        columns=malformed_columns,
    )
    events_frame.to_csv(events_csv, index=False)
    events_frame.to_json(events_json, orient="records", indent=2)
    malformed_frame.to_csv(
        malformed_csv,
        index=False,
        columns=malformed_columns,
    )
    summary = {
        "total_lines": result.total_lines,
        "valid_records": result.valid_count,
        "malformed_records": result.malformed_count,
        "valid_percentage": round(
            (result.valid_count / result.total_lines * 100) if result.total_lines else 0.0,
            2,
        ),
    }
    summary_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return {
        "events_csv": events_csv,
        "events_json": events_json,
        "malformed_csv": malformed_csv,
        "summary_json": summary_json,
    }
