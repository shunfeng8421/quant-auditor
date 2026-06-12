#!/usr/bin/env python3
"""
Quant Auditor — 30 Rules for Strategy Quality
Usage:
  python auditor.py --path strategy.py
  python auditor.py --dir /path/to/strategies/
"""
import json, os, sys, time
from datetime import datetime, timezone, timedelta

TZ_CN = timezone(timedelta(hours=8))


def audit_file(filepath: str) -> dict:
    t0 = time.time()

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        code = f.read()

    from rules.quant_rules import RULES

    # Extract ctx from code
    ctx = {}
    # Try to detect backtest days
    import re
    days_match = re.findall(r'(?:days|DAYS)\w*\s*=\s*(\d+)', code)
    if days_match:
        ctx["backtest_days"] = int(days_match[0])

    results = []
    for r in RULES:
        try:
            result = r["check"](code, os.path.basename(filepath), ctx)
            result["rule_id"] = r["id"]
            result["rule_name"] = r["name"]
            result["severity"] = r["severity"]
            result["max_score"] = r["max_score"]
            result["score"] = result.get("score", 0)
            results.append(result)
        except Exception as e:
            results.append({
                "rule_id": r["id"], "rule_name": r["name"],
                "severity": r["severity"], "max_score": r["max_score"],
                "pass": False, "score": 0, "detail": f"Error: {e}"
            })

    total = sum(r.get("score", 0) for r in results)
    max_possible = sum(r["max_score"] for r in RULES)
    pct = round(total / max_possible * 100) if max_possible > 0 else 0
    grade = "A" if pct >= 80 else ("B" if pct >= 60 else ("C" if pct >= 40 else "D"))

    failures = [r for r in results if not r.get("pass")]
    critical = [r for r in failures if r["severity"] == "critical"]
    high = [r for r in failures if r["severity"] == "high"]

    return {
        "file": filepath,
        "timestamp": datetime.now(TZ_CN).isoformat(),
        "score": {"total": total, "max": max_possible, "pct": pct, "grade": grade},
        "findings": {
            "total": len(failures), "critical": len(critical), "high": len(high),
            "details": [{
                "rule_id": r["rule_id"], "rule_name": r["rule_name"],
                "severity": r["severity"], "detail": r["detail"],
            } for r in failures]
        },
        "meta": {"elapsed_s": round(time.time() - t0, 1)},
    }


def audit_dir(dir_path: str) -> list:
    reports = []
    for root, _, files in os.walk(dir_path):
        if ".git" in root or "__pycache__" in root:
            continue
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                report = audit_file(path)
                reports.append(report)
                print(f"  {report['score']['pct']:3d}/100 {report['score']['grade']}  {os.path.relpath(path, dir_path)}",
                      file=sys.stderr)
    return reports


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Quant Auditor — 30 rules")
    ap.add_argument("--path"); ap.add_argument("--dir"); ap.add_argument("--output", default="quant_audit.json")
    args = ap.parse_args()

    if args.path:
        reports = [audit_file(args.path)]
    elif args.dir:
        reports = audit_dir(args.dir)
    else:
        ap.print_help(); sys.exit(1)

    total_f = sum(r["findings"]["total"] for r in reports)
    crit = sum(r["findings"]["critical"] for r in reports)

    output = {"auditor": "quant-auditor v1.0", "timestamp": datetime.now(TZ_CN).isoformat(),
              "summary": {"files": len(reports), "total_findings": total_f, "critical": crit},
              "reports": reports}

    with open(args.output, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nReport: {args.output} | {len(reports)} files | {total_f} findings (↓{crit})", file=sys.stderr)


if __name__ == "__main__":
    main()
