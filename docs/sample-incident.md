# INC-20260901-001 — Database timeout spike

> Synthetic worked example. It does not describe a real system or incident.

| Field | Value |
|---|---|
| Severity | SEV-2 |
| Status | Resolved |
| First detected | 2026-09-01 09:30 UTC |
| Detection source | Rolling z-score detector |
| Environment | `production-simulated` |
| Primary runbook | RB-01 — Database connection timeout |

## Impact and evidence

The five-minute window beginning at 09:30 UTC contained 52 error/critical
events versus a preceding rolling mean of approximately 4.8. The synthetic
dataset indicates increased failures and latency; no real users were involved.

```spl
index=app_support earliest="09/01/2026:09:25:00" latest="09/01/2026:09:40:00"
| stats count avg(response_time_ms) AS avg_latency_ms by error_type service host
| sort - count
```

## Timeline

| Time (UTC) | Observation or action |
|---|---|
| 09:30 | Detector opened an anomaly window with 52 error/critical events. |
| 09:32 | Events grouped by error type, service, host, and request ID. |
| 09:35 | Database timeout pattern prioritized using RB-01. |
| 09:40 | Subsequent window reviewed for persistence and wider impact. |
| 09:50 | Two-window validation completed in the synthetic exercise. |

## Root-cause exercise

- **Symptom:** error spike, HTTP 5xx responses, and elevated response time.
- **Troubleshooting hypothesis:** temporary connection-pool saturation.
- **Evidence limitation:** the generator does not model real pool metrics, so
  this is not presented as a verified production root cause.

## Follow-up actions

| Action | Owner | Status |
|---|---|---|
| Add pool active/pending metrics to the dashboard | Application team | Proposed |
| Alert on timeout count and pool saturation together | Monitoring team | Proposed |
| Load-test configured pool limits before release | Engineering | Proposed |
