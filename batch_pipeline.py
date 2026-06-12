#!/usr/bin/env python3
"""
Quant Auditor — Batch Discovery + Audit Pipeline
对标 Hermes Skill Auditor 的 discover.py + audit_pipeline.py

用法:
  python discover.py                     # 搜索量化策略仓库
  python audit_pipeline.py               # 批量审计
"""
import json, os, sys, subprocess, time
from datetime import datetime, timezone, timedelta

TZ_CN = timezone(timedelta(hours=8))
PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(PIPELINE_DIR, "output")
EVENTS_LOG = os.path.join(PIPELINE_DIR, "events.jsonl")


def log_event(workflow, event, data=None):
    entry = {"timestamp": datetime.now(TZ_CN).isoformat(), "workflow": workflow, "event": event}
    if data: entry["data"] = data
    with open(EVENTS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def discover_repos(queries=None, min_stars=0, max_results=50):
    """Search GitHub for quant strategy repos"""
    if queries is None:
        queries = [
            "backtest+strategy+python+trading+NOT+bot+NOT+framework",
            "quantitative+trading+strategy+python",
            "algorithmic+trading+python+NOT+bot",
            "crypto+trading+strategy+backtest+python",
        ]

    all_repos = {}
    for query in queries:
        for page in range(1, 4):
            url = f"https://api.github.com/search/repositories?q={query}&sort=stars&per_page=30&page={page}"
            try:
                r = subprocess.run(["curl", "-s", "--max-time", "30", "--proxy", "http://127.0.0.1:15236",
                                   "-H", "Accept: application/vnd.github.v3+json", url],
                                  capture_output=True, text=True, timeout=35)
                items = json.loads(r.stdout).get("items", [])
                if not items: break
                for repo in items:
                    fn = repo["full_name"]
                    if fn not in all_repos and repo.get("stargazers_count", 0) >= min_stars:
                        all_repos[fn] = {
                            "full_name": fn, "url": repo["html_url"],
                            "stars": repo.get("stargazers_count", 0),
                            "description": (repo.get("description") or "")[:200],
                            "language": repo.get("language", ""),
                            "updated_at": repo.get("updated_at", ""),
                        }
                time.sleep(0.5)
            except Exception as e:
                print(f"  Search error: {e}", file=sys.stderr)

    result = sorted(all_repos.values(), key=lambda x: -x["stars"])
    return result


def audit_repo(repo_url):
    """Clone and audit a repo"""
    import tempfile, shutil
    name = repo_url.split("/")[-1]
    tmpdir = tempfile.mkdtemp(prefix="qa-")
    try:
        clone_url = f"https://github.com/{repo_url}.git"
        r = subprocess.run(["git", "clone", "--depth", "1", clone_url, tmpdir],
                          capture_output=True, text=True, timeout=60)
        if r.returncode != 0: return {"repo": repo_url, "error": f"Clone failed"}

        py_files = []
        for root, _, files in os.walk(tmpdir):
            if ".git" in root: continue
            py_files.extend(os.path.join(root, f) for f in files if f.endswith(".py"))

        if not py_files: return {"repo": repo_url, "files": 0, "findings": 0}

        sys.path.insert(0, PIPELINE_DIR)
        from auditor import audit_file
        reports = [audit_file(p) for p in py_files[:200]]  # Limit to 200

        total_f = sum(r["findings"]["total"] for r in reports)
        crit = sum(r["findings"]["critical"] for r in reports)
        return {"repo": repo_url, "files": len(reports), "findings": total_f, "critical": crit}

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--discover", action="store_true")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--full", action="store_true", help="Discover + Audit")
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args()

    if args.discover or args.full:
        print("🔍 Discovering quant strategy repos...", file=sys.stderr)
        repos = discover_repos()
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        path = os.path.join(OUTPUT_DIR, "discovered_quant_repos.json")
        with open(path, "w") as f:
            json.dump({"timestamp": datetime.now(TZ_CN).isoformat(), "total": len(repos), "repos": repos}, f, ensure_ascii=False, indent=2)
        print(f"  Found {len(repos)} repos → {path}", file=sys.stderr)
        log_event("discover", "repos_found", {"count": len(repos)})

    if args.audit or args.full:
        repo_path = os.path.join(OUTPUT_DIR, "discovered_quant_repos.json")
        if not os.path.exists(repo_path):
            print("  Run --discover first", file=sys.stderr)
            sys.exit(1)

        with open(repo_path) as f:
            repos = json.load(f)["repos"]

        repos = repos[:args.limit]
        print(f"🔍 Auditing {len(repos)} repos...", file=sys.stderr)
        t0 = time.time()

        results = []
        for i, repo in enumerate(repos):
            name = repo["full_name"]
            print(f"  [{i+1}/{len(repos)}] {name} ...", file=sys.stderr, end=" ")
            r = audit_repo(name)
            results.append(r)
            print(f"{r.get('files',0)} files, {r.get('findings',0)} findings", file=sys.stderr)

        batch_path = os.path.join(OUTPUT_DIR, "batch_audit.json")
        with open(batch_path, "w") as f:
            json.dump({"timestamp": datetime.now(TZ_CN).isoformat(), "repos": len(repos),
                        "elapsed": round(time.time() - t0), "results": results}, f, ensure_ascii=False, indent=2)

        total = sum(r.get("findings", 0) for r in results)
        crit = sum(r.get("critical", 0) for r in results)
        print(f"\n✅ {len(repos)} repos | {total} findings ({crit} crit) | {batch_path}", file=sys.stderr)
        log_event("audit", "batch_complete", {"repos": len(repos), "findings": total, "critical": crit})


if __name__ == "__main__":
    main()
