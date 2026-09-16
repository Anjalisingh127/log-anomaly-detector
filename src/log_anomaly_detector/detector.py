"""Explainable rule-based and statistical anomaly detection."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd
import yaml


@dataclass(frozen=True)
class DetectionConfig:
    window_minutes: int = 5
    z_score_threshold: float = 2.5
    slow_request_ms: int = 1500
    consecutive_auth_failures: int = 5
    baseline_windows: int = 6

    def __post_init__(self) -> None:
        if self.window_minutes < 1:
            raise ValueError("window_minutes must be at least 1")
        if self.z_score_threshold <= 0:
            raise ValueError("z_score_threshold must be positive")
        if self.slow_request_ms < 0:
            raise ValueError("slow_request_ms cannot be negative")
        if self.consecutive_auth_failures < 2:
            raise ValueError("consecutive_auth_failures must be at least 2")
        if self.baseline_windows < 3:
            raise ValueError("baseline_windows must be at least 3")


@dataclass
class DetectionResult:
    anomalies: pd.DataFrame
    error_windows: pd.DataFrame
    summary: dict[str, object]


def load_detection_config(config_path: Path) -> DetectionConfig:
    with config_path.open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    values = document.get("detection", {})
    return DetectionConfig(**values)


def _event_anomalies(frame: pd.DataFrame, config: DetectionConfig) -> pd.DataFrame:
    rules = {
        "severity_error": frame["level"].isin(["ERROR", "CRITICAL"]),
        "http_5xx": frame["status_code"].between(500, 599),
        "slow_request": frame["response_time_ms"] >= config.slow_request_ms,
        "database_timeout": frame["error_type"].eq("DATABASE_TIMEOUT"),
    }
    rows: list[pd.DataFrame] = []
    for rule_name, mask in rules.items():
        matches = frame.loc[mask].copy()
        if matches.empty:
            continue
        matches["detection_type"] = rule_name
        matches["details"] = matches.apply(
            lambda row: (
                f"level={row['level']}; status={row['status_code']}; "
                f"latency_ms={row['response_time_ms']}; error={row['error_type']}"
            ),
            axis=1,
        )
        rows.append(matches)
    if not rows:
        return pd.DataFrame(columns=[*frame.columns, "detection_type", "details"])
    return pd.concat(rows, ignore_index=True)


def _authentication_sequences(frame: pd.DataFrame, threshold: int) -> pd.DataFrame:
    ordered = frame.sort_values(["client_id", "timestamp"]).copy()
    ordered["is_auth_failure"] = ordered["error_type"].eq("AUTHENTICATION_FAILURE")
    previous = ordered.groupby("client_id")["is_auth_failure"].shift(fill_value=False)
    ordered["sequence"] = ordered["is_auth_failure"].ne(previous).groupby(ordered["client_id"]).cumsum()
    failures = ordered.loc[ordered["is_auth_failure"]].copy()
    if failures.empty:
        return pd.DataFrame(columns=[*frame.columns, "detection_type", "details"])
    grouped = failures.groupby(["client_id", "sequence"], sort=False)
    failures["sequence_length"] = grouped["request_id"].transform("size")
    matches = failures.loc[failures["sequence_length"] >= threshold].copy()
    if matches.empty:
        return pd.DataFrame(columns=[*frame.columns, "detection_type", "details"])
    matches["detection_type"] = "repeated_authentication_failure"
    matches["details"] = matches.apply(
        lambda row: f"client={row['client_id']}; failures={row['sequence_length']}", axis=1
    )
    return matches.drop(columns=["is_auth_failure", "sequence", "sequence_length"])


def _error_spikes(frame: pd.DataFrame, config: DetectionConfig) -> pd.DataFrame:
    errors = frame.loc[frame["level"].isin(["ERROR", "CRITICAL"]), ["timestamp"]].copy()
    if frame.empty:
        return pd.DataFrame(
            columns=["timestamp", "error_count", "baseline_mean", "baseline_std", "z_score", "is_spike"]
        )
    start = frame["timestamp"].min().floor(f"{config.window_minutes}min")
    end = frame["timestamp"].max().ceil(f"{config.window_minutes}min")
    index = pd.date_range(start=start, end=end, freq=f"{config.window_minutes}min", tz="UTC")
    if errors.empty:
        counts = pd.Series(0, index=index, dtype="int64")
    else:
        counts = errors.set_index("timestamp").resample(f"{config.window_minutes}min").size()
        counts = counts.reindex(index, fill_value=0)
    baseline = counts.shift(1).rolling(config.baseline_windows, min_periods=3)
    mean = baseline.mean()
    std = baseline.std(ddof=0)
    z_score = ((counts - mean) / std).where(std > 0)
    z_score = z_score.mask(std.eq(0) & counts.gt(mean), float("inf"))
    z_score = z_score.mask(std.eq(0) & counts.eq(mean), 0.0)
    spike = z_score.ge(config.z_score_threshold).fillna(False)
    return pd.DataFrame(
        {
            "timestamp": index,
            "error_count": counts.to_numpy(),
            "baseline_mean": mean.round(3).to_numpy(),
            "baseline_std": std.round(3).to_numpy(),
            "z_score": z_score.round(3).to_numpy(),
            "is_spike": spike.to_numpy(),
        }
    )


def detect_anomalies(events: list[dict[str, object]], config: DetectionConfig) -> DetectionResult:
    frame = pd.DataFrame(events)
    if frame.empty:
        empty = pd.DataFrame(columns=["detection_type", "details"])
        return DetectionResult(empty, _error_spikes(frame, config), {"events_analyzed": 0, "detections": 0})
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    detection_frames = [
        _event_anomalies(frame, config),
        _authentication_sequences(frame, config.consecutive_auth_failures),
    ]
    non_empty_frames = [candidate for candidate in detection_frames if not candidate.empty]
    anomalies = (
        pd.concat(non_empty_frames, ignore_index=True)
        if non_empty_frames
        else pd.DataFrame(columns=[*frame.columns, "detection_type", "details"])
    )
    windows = _error_spikes(frame, config)
    counts = anomalies["detection_type"].value_counts().sort_index().to_dict()
    summary = {
        "events_analyzed": int(len(frame)),
        "detections": int(len(anomalies)),
        "spike_windows": int(windows["is_spike"].sum()),
        "detections_by_type": {key: int(value) for key, value in counts.items()},
        "thresholds": asdict(config),
    }
    return DetectionResult(anomalies=anomalies, error_windows=windows, summary=summary)


def export_detections(result: DetectionResult, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    anomalies_path = output_dir / "anomalies.csv"
    windows_path = output_dir / "error_windows.csv"
    summary_path = output_dir / "detection_summary.json"
    result.anomalies.to_csv(anomalies_path, index=False)
    result.error_windows.to_csv(windows_path, index=False)
    summary_path.write_text(json.dumps(result.summary, indent=2) + "\n", encoding="utf-8")
    return {"anomalies": anomalies_path, "error_windows": windows_path, "summary": summary_path}
