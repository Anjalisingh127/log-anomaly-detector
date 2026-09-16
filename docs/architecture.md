# Architecture

## Goal

Provide a reproducible support-engineering workflow that turns application logs
into actionable anomaly evidence without representing synthetic results as real
production impact.

## Planned data flow

1. `generate_logs.py` produces privacy-safe application events.
2. The parser validates and normalizes fields into tabular records.
3. Rule-based and statistical detectors identify failures and spikes.
4. The reporter creates CSV and public HTML evidence.
5. Splunk ingests the same source file for SPL searches, dashboards, and a trial-license alert.
6. The incident runbook maps each frequent error type to investigation and resolution steps.

## Log schema

| Field | Example | Support use |
|---|---|---|
| `timestamp` | `2026-09-01T09:00:00.000Z` | Timeline and time windows |
| `level` | `ERROR` | Severity triage |
| `service` | `payment-service` | Application ownership |
| `host` | `app-03` | Infrastructure isolation |
| `request_id` | UUID | Request correlation |
| `status_code` | `503` | HTTP failure analysis |
| `response_time_ms` | `2150` | Performance diagnosis |
| `error_type` | `DATABASE_TIMEOUT` | Root-cause categorization |

## Reliability decisions

- Fixed random seed for reproducible demonstrations.
- Explicit `production-simulated` label to prevent misleading claims.
- Configuration-driven volume and anomaly windows.
- Line-oriented logs that Python and Splunk can both ingest.
- No secrets or real personal data.
