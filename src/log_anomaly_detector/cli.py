"""Command-line interface for support log analysis."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .detector import detect_anomalies, export_detections, load_detection_config
from .parser import export_result, parse_file

EXIT_SUCCESS = 0
EXIT_INPUT_ERROR = 2
EXIT_PROCESSING_ERROR = 3
EXIT_MALFORMED_THRESHOLD = 4


class JsonFormatter(logging.Formatter):
    """Emit machine-readable runtime messages for operational troubleshooting."""

    STANDARD_FIELDS = {
        "args", "asctime", "created", "exc_info", "exc_text", "filename",
        "funcName", "levelname", "levelno", "lineno", "module", "msecs",
        "message", "msg", "name", "pathname", "process", "processName",
        "relativeCreated", "stack_info", "thread", "threadName", "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in self.STANDARD_FIELDS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(verbose: bool) -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if verbose else logging.INFO)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="log-anomaly-detector")
    parser.add_argument("--verbose", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    parse_command = subparsers.add_parser("parse", help="Parse and normalize an application log")
    parse_command.add_argument("--input", type=Path, required=True)
    parse_command.add_argument("--output", type=Path, default=Path("reports"))
    parse_command.add_argument(
        "--fail-on-malformed",
        action="store_true",
        help="Return exit code 4 when any malformed records are found",
    )
    analyze_command = subparsers.add_parser("analyze", help="Parse logs and detect operational anomalies")
    analyze_command.add_argument("--input", type=Path, required=True)
    analyze_command.add_argument("--output", type=Path, default=Path("reports"))
    analyze_command.add_argument("--config", type=Path, default=Path("config/config.yaml"))
    return parser


def run_parse(args: argparse.Namespace) -> int:
    if not args.input.is_file():
        logging.getLogger(__name__).error(
            "input_not_found", extra={"input_path": str(args.input)}
        )
        return EXIT_INPUT_ERROR
    try:
        result = parse_file(args.input)
        paths = export_result(result, args.output)
    except (OSError, UnicodeError) as exc:
        logging.getLogger(__name__).exception(
            "processing_failed", extra={"reason": str(exc)}
        )
        return EXIT_PROCESSING_ERROR

    print(
        f"Parsed {result.total_lines} lines: {result.valid_count} valid, "
        f"{result.malformed_count} malformed. Summary: {paths['summary_json']}"
    )
    if args.fail_on_malformed and result.malformed_count:
        return EXIT_MALFORMED_THRESHOLD
    return EXIT_SUCCESS


def run_analyze(args: argparse.Namespace) -> int:
    if not args.input.is_file() or not args.config.is_file():
        logging.getLogger(__name__).error(
            "input_or_config_not_found",
            extra={"input_path": str(args.input), "config_path": str(args.config)},
        )
        return EXIT_INPUT_ERROR
    try:
        parsed = parse_file(args.input)
        export_result(parsed, args.output)
        config = load_detection_config(args.config)
        result = detect_anomalies(parsed.events, config)
        paths = export_detections(result, args.output)
    except (OSError, UnicodeError, TypeError, ValueError, yaml.YAMLError) as exc:
        logging.getLogger(__name__).exception("analysis_failed", extra={"reason": str(exc)})
        return EXIT_PROCESSING_ERROR
    print(
        f"Analyzed {result.summary['events_analyzed']} events: "
        f"{result.summary['detections']} rule detections, "
        f"{result.summary['spike_windows']} spike windows. "
        f"Summary: {paths['summary']}"
    )
    return EXIT_SUCCESS


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)
    if args.command == "parse":
        return run_parse(args)
    if args.command == "analyze":
        return run_analyze(args)
    parser.error("unsupported command")
    return EXIT_PROCESSING_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
