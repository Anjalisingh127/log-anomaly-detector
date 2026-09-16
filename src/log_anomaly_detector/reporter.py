"""Generate a self-contained public HTML operations report."""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd

from .detector import DetectionResult
from .parser import ParseResult


def _bar_chart(values: dict[str, int], title: str) -> str:
    width, height, left, top = 760, 300, 190, 42
    chart_width = width - left - 35
    row_height = 42
    maximum = max(values.values(), default=1)
    rows = []
    for index, (label, value) in enumerate(values.items()):
        y = top + index * row_height
        bar_width = int(chart_width * value / maximum) if maximum else 0
        rows.append(
            f'<text x="{left - 12}" y="{y + 18}" text-anchor="end">{escape(label)}</text>'
            f'<rect x="{left}" y="{y}" width="{bar_width}" height="25" rx="4" />'
            f'<text x="{left + bar_width + 8}" y="{y + 18}">{value}</text>'
        )
    rendered_height = max(height, top + len(values) * row_height + 20)
    return (
        f'<figure><figcaption>{escape(title)}</figcaption>'
        f'<svg viewBox="0 0 {width} {rendered_height}" role="img" aria-label="{escape(title)}">'
        + "".join(rows)
        + "</svg></figure>"
    )


def _timeline_chart(windows: pd.DataFrame) -> str:
    width, height, left, top = 900, 280, 48, 30
    plot_width, plot_height = width - left - 24, height - top - 42
    counts = windows["error_count"].astype(float).tolist()
    maximum = max(counts, default=1) or 1
    denominator = max(len(counts) - 1, 1)
    points = []
    spike_points = []
    for index, (_, row) in enumerate(windows.iterrows()):
        x = left + plot_width * index / denominator
        y = top + plot_height - plot_height * float(row["error_count"]) / maximum
        points.append(f"{x:.1f},{y:.1f}")
        if bool(row["is_spike"]):
            spike_points.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6"><title>{escape(str(row["timestamp"]))}: {int(row["error_count"])} errors</title></circle>')
    return (
        '<figure><figcaption>Errors per five-minute window</figcaption>'
        f'<svg class="timeline" viewBox="0 0 {width} {height}" role="img" aria-label="Error timeline with spike windows">'
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" y2="{top + plot_height}" />'
        f'<polyline points="{" ".join(points)}" />{"".join(spike_points)}</svg>'
        '<p class="legend"><span></span> Red markers indicate statistically flagged spike windows.</p></figure>'
    )


def generate_html_report(parsed: ParseResult, detected: DetectionResult, output_path: Path) -> Path:
    events = pd.DataFrame(parsed.events)
    errors = events.loc[events["level"].isin(["ERROR", "CRITICAL"])]
    category_counts = errors["error_type"].value_counts().head(5).to_dict()
    service_counts = errors["service"].value_counts().to_dict()
    host_counts = errors["host"].value_counts().to_dict()
    error_rate = len(errors) / len(events) * 100 if len(events) else 0.0
    generated_at = events["timestamp"].max() if not events.empty else "No data"
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Application Support Operations Report</title><style>
:root{{--ink:#172033;--muted:#627089;--panel:#fff;--bg:#f4f7fb;--accent:#3757d5;--danger:#dc3545}}
*{{box-sizing:border-box}}body{{margin:0;font:16px/1.5 system-ui,sans-serif;color:var(--ink);background:var(--bg)}}
main{{max-width:1120px;margin:auto;padding:42px 22px}}header{{padding:30px;background:#172033;color:white;border-radius:16px}}
h1{{margin:0 0 8px;font-size:2rem}}h2{{margin-top:36px}}.sub{{color:#d7deed;margin:0}}.notice{{color:var(--muted)}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin:24px 0}}
.card,figure,table{{background:var(--panel);border:1px solid #dce3ef;border-radius:12px;box-shadow:0 5px 16px #1720330d}}
.card{{padding:20px}}.metric{{font-size:1.8rem;font-weight:750}}.label{{color:var(--muted)}}figure{{margin:16px 0;padding:20px;overflow:hidden}}
figcaption{{font-weight:700;margin-bottom:12px}}svg{{display:block;width:100%;height:auto}}svg text{{fill:var(--ink);font-size:14px}}svg rect{{fill:var(--accent)}}
.timeline line{{stroke:#9aa7bb}}.timeline polyline{{fill:none;stroke:var(--accent);stroke-width:3}}.timeline circle{{fill:var(--danger)}}
.legend{{color:var(--muted)}}.legend span{{display:inline-block;width:10px;height:10px;background:var(--danger);border-radius:50%;margin-right:6px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,430px),1fr));gap:16px}}table{{width:100%;border-collapse:collapse;overflow:hidden}}
th,td{{padding:12px;text-align:left;border-bottom:1px solid #e7ebf2}}th{{background:#eef2fa}}footer{{margin-top:38px;color:var(--muted)}}
</style></head><body><main><header><h1>Application Support Operations Report</h1>
<p class="sub">Explainable log analysis for a reproducible synthetic application environment</p></header>
<p class="notice"><strong>Portfolio evidence:</strong> All events are synthetic. No production or customer data is represented. Dataset final timestamp: {escape(str(generated_at))}.</p>
<section class="cards"><div class="card"><div class="metric">{len(events):,}</div><div class="label">Events analyzed</div></div>
<div class="card"><div class="metric">{len(errors):,}</div><div class="label">Error/critical events</div></div>
<div class="card"><div class="metric">{error_rate:.2f}%</div><div class="label">Error rate</div></div>
<div class="card"><div class="metric">{detected.summary.get('spike_windows', 0)}</div><div class="label">Spike windows</div></div>
<div class="card"><div class="metric">{parsed.malformed_count}</div><div class="label">Malformed records</div></div></section>
<h2>Operational timeline</h2>{_timeline_chart(detected.error_windows)}
<div class="grid">{_bar_chart({str(k): int(v) for k,v in category_counts.items()}, 'Top failure categories')}
{_bar_chart({str(k): int(v) for k,v in service_counts.items()}, 'Errors by service')}
{_bar_chart({str(k): int(v) for k,v in host_counts.items()}, 'Errors by host')}</div>
<h2>Detection controls</h2><table><thead><tr><th>Control</th><th>Configured value</th><th>Purpose</th></tr></thead><tbody>
<tr><td>Window</td><td>{detected.summary['thresholds']['window_minutes']} minutes</td><td>Operational aggregation</td></tr>
<tr><td>Z-score</td><td>{detected.summary['thresholds']['z_score_threshold']}</td><td>Error-spike threshold</td></tr>
<tr><td>Slow request</td><td>{detected.summary['thresholds']['slow_request_ms']} ms</td><td>Latency rule</td></tr>
<tr><td>Authentication sequence</td><td>{detected.summary['thresholds']['consecutive_auth_failures']}</td><td>Repeated-failure rule</td></tr>
</tbody></table><footer>Generated locally by Log Anomaly Detector. Results are deterministic for seed 42.</footer>
</main></body></html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
