import argparse
import html
import json
import os
import statistics
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.github_data import pull_requests

REPO = "hariscats/agentic-sdlc-governance"


def hours(start: str, end: str) -> float:
    result = (
        datetime.fromisoformat(end.replace("Z", "+00:00"))
        - datetime.fromisoformat(start.replace("Z", "+00:00"))
    ).total_seconds() / 3600
    if result < 0:
        raise ValueError("Invalid negative duration")
    return result


def usage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows or any(
        r.get("schema") != "demo.usage.v1" or r.get("synthetic") is not True for r in rows
    ):
        raise ValueError("Expected explicitly labelled demo fixture schema")
    return {
        "source": "synthetic",
        "active_users": len({r["user"] for r in rows}),
        "engaged_users": len({r["user"] for r in rows if r["engaged"]}),
        "feature_users": dict(Counter(f for r in rows for f in set(r["features"]))),
    }


def flow(prs: list[dict[str, Any]]) -> dict[str, Any]:
    merged = [p for p in prs if p["mergedAt"]]
    agent = [
        p
        for p in merged
        if p["author"]["login"].lower() in {"copilot", "copilot[bot]", "copilot-swe-agent[bot]"}
        or any(x["name"] == "agent-authored" for x in p["labels"])
        or any("Co-authored-by: Copilot" in c.get("messageBody", "") for c in p.get("commits", []))
    ]
    lead = [hours(p["createdAt"], p["mergedAt"]) for p in merged]
    review = [
        hours(
            p["createdAt"],
            min(
                r["submittedAt"]
                for r in p["reviews"]
                if r.get("submittedAt") and r["author"]["login"] != p["author"]["login"]
            ),
        )
        for p in prs
        if any(
            r.get("submittedAt") and r["author"]["login"] != p["author"]["login"]
            for r in p["reviews"]
        )
    ]
    gates: dict[str, Counter[str]] = {}
    for p in prs:
        for check in p.get("statusCheckRollup") or []:
            if check.get("conclusion") in {
                "SUCCESS",
                "FAILURE",
                "TIMED_OUT",
                "CANCELLED",
                "success",
                "failure",
                "timed_out",
                "cancelled",
            }:
                name = check.get("name", "unknown")
                gates.setdefault(name, Counter())[check["conclusion"].lower()] += 1
    return {
        "sample_prs": len(prs),
        "merged_agent": len(agent),
        "merged_other": len(merged) - len(agent),
        "median_lead_hours": statistics.median(lead) if lead else None,
        "median_first_review_hours": statistics.median(review) if review else None,
        "follow_up_commits": sum(max(0, len(p.get("commits", [])) - 1) for p in prs),
        "gate_latest_conclusions": gates,
        "gate_failure_rate_definition": "Latest completed check per sampled PR, not all attempts",
        "converge_loops": None,
        "code_scanning_alerts": None,
        "autofix_attribution": None,
        "dependabot_remediation_hours": None,
        "unavailable_reason": (
            "Historical gate attempts and security alert collectors not configured"
        ),
    }


def render(summary: dict[str, Any]) -> str:
    counts = summary["usage"]["feature_users"]
    bars = "".join(
        f'<text x="0" y="{i * 40 + 20}">{html.escape(key)}: {value}</text>'
        f'<rect x="160" y="{i * 40 + 5}" width="{value * 50}" height="22" fill="#175cd3"/>'
        for i, (key, value) in enumerate(sorted(counts.items()))
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>Guardrails-as-Code outcomes</title>
<style>body{{font:18px system-ui;max-width:950px;margin:2rem auto;padding:1rem;color:#182230}}
.banner{{background:#fff1cc;border:3px solid #805500;padding:1rem;font-weight:bold}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f4f7;padding:1rem}}
svg{{max-width:100%;height:auto}}a:focus{{outline:3px solid #175cd3}}</style></head>
<body><main><h1>Guardrails-as-Code outcomes</h1>
<p class="banner">SYNTHETIC DATA: Copilot usage is fictional, not company telemetry.</p>
<p>Repository flow source: {html.escape(summary["flow_source"])}.
No data is sent to external services by this page.</p>
<h2>Illustrative feature adoption</h2>
<svg viewBox="0 0 480 220" role="img" aria-label="Synthetic feature usage; exact counts below">
{bars}</svg><h2>Measured and illustrative results</h2>
<pre>{html.escape(json.dumps(summary, indent=2))}</pre>
<p>Null means unavailable, not zero.
This is an illustrative control demo, not a compliance certification.</p>
</main></body></html>"""


def alerts(resource: str) -> tuple[list[dict[str, Any]] | None, str | None]:
    if resource not in {"code-scanning", "dependabot"}:
        raise ValueError("Only selected repository security endpoints are permitted")
    response = subprocess.run(
        [
            "gh",
            "api",
            "--method",
            "GET",
            f"repos/{REPO}/{resource}/alerts?per_page=100",
            "--paginate",
            "--slurp",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if response.returncode:
        try:
            error = json.loads(response.stdout)
            if isinstance(error, list) and len(error) == 1:
                error = error[0]
            if not isinstance(error, dict):
                raise ValueError("Unexpected error envelope")
            status = str(error.get("status"))
        except (json.JSONDecodeError, ValueError) as exc:
            raise RuntimeError(f"{resource} request failed without an API response") from exc
        if status not in {"403", "404"}:
            raise RuntimeError(f"{resource} API failed with HTTP {status}")
        reason = f"{resource}: policy, permission, or data unavailable (HTTP {status})"
        print(reason, file=sys.stderr)
        return None, reason
    pages = json.loads(response.stdout)
    return [alert for page in pages for alert in page], None


def security_metrics() -> dict[str, Any]:
    scanning, scanning_reason = alerts("code-scanning")
    dependencies, dependency_reason = alerts("dependabot")
    fixed = [hours(a["created_at"], a["fixed_at"]) for a in dependencies or [] if a.get("fixed_at")]
    return {
        "code_scanning_alerts": dict(Counter(a["state"] for a in scanning))
        if scanning is not None
        else None,
        "dependabot_alerts": dict(Counter(a["state"] for a in dependencies))
        if dependencies is not None
        else None,
        "dependabot_remediation_hours": statistics.median(fixed) if fixed else None,
        "security_scope": (
            "All alerts returned for this repository; state counts, not a time series"
        ),
        "unavailable_reason": [reason for reason in [scanning_reason, dependency_reason] if reason],
    }


def collect(live: bool = False) -> dict[str, Any]:
    rows = [
        json.loads(line) for line in Path("metrics/fixtures/usage.ndjson").read_text().splitlines()
    ]
    prs: list[dict[str, Any]] = []
    if live:
        prs = pull_requests("all")
    result: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "repository": REPO,
        "usage": usage(rows),
        "flow": flow(prs),
        "flow_source": "live (latest 100 PRs; bounded sample)" if live else "not collected",
    }
    if live:
        result["flow"].update(security_metrics())
    result["flow"]["gate_failure_rates"] = {
        name: (
            (counts["failure"] + counts["timed_out"])
            / (counts["success"] + counts["failure"] + counts["timed_out"])
        )
        if counts["success"] + counts["failure"] + counts["timed_out"]
        else None
        for name, counts in result["flow"]["gate_latest_conclusions"].items()
    }
    out = Path("metrics/out")
    out.mkdir(parents=True, exist_ok=True)
    Path("dashboard").mkdir(exist_ok=True)
    (out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    Path("dashboard/index.html").write_text(render(result))
    report = (
        "# Outcomes\n\n**SYNTHETIC DATA: Copilot usage only.**\n\n"
        f"Repository flow: {result['flow_source']}\n\n"
        f"Active synthetic users: {result['usage']['active_users']}\n"
    )
    (out / "summary.md").write_text(report)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as stream:
            stream.write(report)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-flow", action="store_true")
    collect(parser.parse_args().live_flow)
