#!/usr/bin/env python3
"""radar.py — Design-Ops Radar MVP: weekly GitHub scan → digest issue.

Hard thresholds against noise (concept: docs/v7/ТЗ-v7.0.md §3.7):
  >=100 stars, age >90 days, pushed <30 days ago, 5 tracked topic queries,
  digest = top-5 as ONE GitHub issue. No external APIs, $0.

Env: GITHUB_TOKEN (required), GITHUB_REPOSITORY (owner/repo, required).
Exit: 0 ok (issue created or nothing above thresholds), 1 error, 2 usage.
"""
import datetime
import json
import os
import sys
import urllib.parse
import urllib.request

QUERIES = [
    "topic:ui-generator",
    "topic:design-system",
    "topic:design-tokens",
    "topic:visual-regression",
    "topic:ai-design",
]
MIN_STARS, MIN_AGE_DAYS, MAX_IDLE_DAYS = 100, 90, 30
TOP_N = 5

TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = os.environ.get("GITHUB_REPOSITORY", "")
NOW = datetime.datetime.now(datetime.timezone.utc)


def gh(url, data=None, method=None):
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "design-ops-radar",
    })
    return json.load(urllib.request.urlopen(req, timeout=30))


def parse_dt(s):
    return datetime.datetime.fromisoformat(s.rstrip("Z")).replace(
        tzinfo=datetime.timezone.utc)


def scan():
    seen, found = set(), []
    for q in QUERIES:
        url = ("https://api.github.com/search/repositories?q="
               + urllib.parse.quote(f"{q} stars:>={MIN_STARS}")
               + "&sort=updated&per_page=20")
        try:
            items = gh(url).get("items", [])
        except Exception as e:  # rate limit / network — report, don't crash
            print(f"radar: query '{q}' failed: {e}", file=sys.stderr)
            continue
        for r in items:
            if r["full_name"] in seen:
                continue
            seen.add(r["full_name"])
            if (NOW - parse_dt(r["created_at"])).days < MIN_AGE_DAYS:
                continue
            if (NOW - parse_dt(r["pushed_at"])).days > MAX_IDLE_DAYS:
                continue
            found.append(r)
    found.sort(key=lambda r: r["stargazers_count"], reverse=True)
    return found[:TOP_N]


def make_issue(top):
    week = NOW.strftime("%Y-W%V")
    body = [
        f"Radar digest {week}. Thresholds: ≥{MIN_STARS} stars, "
        f"age >{MIN_AGE_DAYS}d, pushed <{MAX_IDLE_DAYS}d ago. "
        f"Queries: {', '.join(q.removeprefix('topic:') for q in QUERIES)}.",
        "",
    ]
    for r in top:
        body.append(
            f"- **[{r['full_name']}]({r['html_url']})** "
            f"★{r['stargazers_count']} — {(r.get('description') or 'no description')[:140]}")
    body += [
        "",
        "Action: owner review → accept (open an integration issue) / "
        "defer (v7.x backlog) / reject. Radar rules: digest unread 4 weeks "
        "→ disable the workflow.",
    ]
    payload = json.dumps({
        "title": f"Radar digest {week}",
        "body": "\n".join(body),
        "labels": ["radar"],
    }).encode()
    res = gh(f"https://api.github.com/repos/{REPO}/issues",
             data=payload, method="POST")
    return res.get("html_url", "(issue created)")


def main():
    if not TOKEN or not REPO:
        print("radar: GITHUB_TOKEN and GITHUB_REPOSITORY are required",
              file=sys.stderr)
        return 2
    top = scan()
    if not top:
        print("radar: nothing above thresholds — no issue created")
        return 0
    url = make_issue(top)
    print(f"radar: digest issue created ({len(top)} items): {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
