# Application Support Incident Runbook

This runbook covers the five recurring failure categories in the synthetic
dataset. It is a portfolio artifact, not a record of production incidents.

## Triage standard

| Severity | Definition | Response target | Escalation |
|---|---|---:|---|
| SEV-1 | Complete outage, data-integrity risk, or widespread critical failure | 15 min | Incident commander and service owner immediately |
| SEV-2 | Major degradation or repeated failures affecting a service | 30 min | Service owner and platform/database team |
| SEV-3 | Limited impact with a workaround | 4 business hours | Owning team during support hours |
| SEV-4 | Warning, isolated defect, or informational follow-up | Next business day | Backlog unless frequency increases |

For every incident: acknowledge, determine impact, preserve evidence, assign
severity, mitigate, validate recovery, document root cause, and assign follow-up.
Never declare resolution from a falling alert count alone; test the affected
user transaction.

## Common first response

1. Record first-seen time, source, service, host, request ID, and environment.
2. Confirm current impact and whether multiple services or hosts are affected.
3. Compare the event rate with its baseline and recent changes.
4. Correlate by `request_id`, `client_id`, `service`, and `host`.
5. Preserve sanitized evidence; never copy credentials or personal data.
6. Apply the smallest reversible approved mitigation.
7. Validate monitoring recovery and a representative transaction.

## RB-01 — Database connection timeout

**Signature:** `DATABASE_TIMEOUT`, normally HTTP `503`

**Default severity:** SEV-2; SEV-1 if all transactions fail or data integrity is at risk.

```spl
index=app_support error_type=DATABASE_TIMEOUT
| timechart span=5m count by service
```

**Likely causes:** database unavailability; exhausted connection pool; blocking
queries; DNS/firewall/certificate failure; incorrect post-deployment settings.

**Investigation**

1. Identify affected services and hosts and correlate request IDs.
2. Check pool active, idle, pending, and timeout metrics.
3. Review database availability, sessions, locks, slow queries, and saturation.
4. Check recent application, secret, network, DNS, and certificate changes.

**Mitigation:** roll back a confirmed bad change; restart only the exhausted
pool/instance when approved; shift traffic if capacity permits; involve the
database team for blocking sessions or service restoration.

**Validation:** a new database-backed transaction succeeds; timeouts and pool
saturation remain at baseline for two windows; no integrity errors appear.

**Escalate:** database unavailable, multiple services affected, credentials or
certificates invalid, persistent saturation, or any data-integrity risk.

## RB-02 — Authentication failure

**Signature:** `AUTHENTICATION_FAILURE`, normally HTTP `401`

**Default severity:** SEV-3; SEV-2 for widespread login failure or suspected attack.

```spl
index=app_support error_type=AUTHENTICATION_FAILURE
| bin _time span=5m
| stats count dc(client_id) AS affected_clients by _time service
| where count >= 5
```

**Likely causes:** expired/revoked token; clock skew; identity-provider outage;
incorrect issuer, audience, redirect, or secret; automated credential abuse.

**Investigation**

1. Determine whether one client, many clients, or every login is affected.
2. Distinguish `401` authentication failure from `403` authorization failure.
3. Check token expiry, issuer, audience, signing-key rotation, and system clock.
4. Review identity-provider health, config changes, source patterns, and limits.

**Mitigation:** roll back incorrect identity configuration; refresh approved
service credentials through secret management; involve security for abuse;
never weaken authentication as a workaround.

**Validation:** a valid test user authenticates and accesses an authorized
endpoint; invalid credentials still fail; failure rate returns to baseline.

**Escalate:** all users affected, key rotation failed, privileged accounts are
involved, suspicious automation exists, or credential exposure is suspected.

## RB-03 — Internal server error

**Signature:** `INTERNAL_SERVER_ERROR`, HTTP `500`

**Default severity:** SEV-2 when sustained; SEV-3 when isolated.

```spl
index=app_support status_code>=500 status_code<600
| stats count values(error_type) AS errors by service host endpoint
| sort - count
```

**Likely causes:** unhandled exception; failed dependency; incompatible release,
schema, or configuration; invalid data edge case; resource exhaustion.

**Investigation**

1. Correlate request ID with the complete stack trace and downstream calls.
2. Identify the first failing service, not merely the final `500` response.
3. Compare endpoints, hosts, versions, deployments, and exception signatures.
4. Reproduce with sanitized input outside production where possible.

**Mitigation:** roll back a defective release; disable the affected feature
through an approved flag; route away from an unhealthy instance; restore the
failed dependency. Do not simply suppress the exception.

**Validation:** previously failing requests succeed; errors remain at baseline
for two windows; no new exception or downstream regression appears.

**Escalate:** payments or data writes affected, multiple dependencies involved,
or resolution requires code or schema changes.

## RB-04 — API rate limit exceeded

**Signature:** `RATE_LIMIT_EXCEEDED`, HTTP `429`

**Default severity:** SEV-3; SEV-2 when legitimate traffic is broadly blocked.

```spl
index=app_support status_code=429
| timechart span=5m count by client_id limit=10
```

**Likely causes:** traffic burst; retry storm; missing backoff; incorrect quota;
abuse; downstream throttling.

**Investigation**

1. Find top clients, endpoints, services, and burst start time.
2. Distinguish expected enforcement from accidental throttling.
3. Check retries, `Retry-After`, duplication, and recent traffic changes.
4. Locate the limit at application, gateway, or downstream level.

**Mitigation:** correct retry behavior with exponential backoff and jitter;
adjust quotas only after capacity/security review; cache safe repeated reads;
block malicious traffic through approved controls.

**Validation:** legitimate requests work within quota; `429` volume normalizes;
latency and capacity stay healthy after any adjustment.

**Escalate:** capacity near exhaustion, global quota incorrect, abusive activity
suspected, or downstream throttling cannot be controlled locally.

## RB-05 — Resource pressure

**Signature:** `RESOURCE_PRESSURE`, normally HTTP `503`

**Default severity:** SEV-2; SEV-1 when all capacity is exhausted.

```spl
index=app_support error_type=RESOURCE_PRESSURE
| stats count by host service
| sort - count
```

**Likely causes:** disk/inode exhaustion; memory leak or OOM; CPU saturation;
capacity imbalance; missing log rotation or scaling.

**Investigation**

1. Identify the constrained resource and host; do not restart blindly.
2. Check disk, inode, memory, swap, CPU, process, and container limits.
3. Find the top process/directory and correlate the growth start time.
4. Review traffic, deployments, batch jobs, rotation, and retention changes.

**Mitigation:** rotate/archive approved logs without deleting unknown data;
drain unhealthy hosts when capacity permits; restart a verified leaking process
only with approval and captured diagnostics; temporarily scale if authorized.

**Validation:** utilization remains below threshold; health and representative
transactions pass; no required evidence or data was lost.

**Escalate:** all hosts affected, capacity continues falling, OOM recurs, data
retention is involved, or infrastructure changes are required.

## Closure checklist

- [ ] Impact, duration, severity, and affected components recorded
- [ ] Timeline and sanitized evidence linked
- [ ] Root cause distinguished from trigger and contributing factors
- [ ] Mitigation, permanent action, and validation documented
- [ ] Owner and due date assigned to every follow-up
- [ ] Incident note reviewed for secrets and personal data
