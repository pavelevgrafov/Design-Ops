#!/usr/bin/env python3
"""check-secrets.py — D23: secrets scan over project files (blocking).

Scans text files for known credential patterns and high-entropy assignments.
A finding is a blocking FAIL — secrets live in env only, never in the repo.
Runs BEFORE any deploy (Gate 3 precondition).

Usage: python3 check-secrets.py <root>
Exit: 0 = clean, 1 = findings.
"""
import math, os, re, sys

PATTERNS = [
    ("aws_access_key",    re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("aws_secret",        re.compile(r"(?i)aws(.{0,20})?secret(.{0,20})?['\"=:\s]{2,}[0-9a-zA-Z/+]{40}")),
    ("github_token",      re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b")),
    ("google_api_key",    re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    ("private_key_block", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("slack_token",       re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    ("stripe_key",        re.compile(r"\b(sk|pk)_(live|test)_[0-9A-Za-z]{16,}\b")),
    ("generic_secret",    re.compile(r"(?i)\b(api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*['\"][^'\"]{12,}['\"]")),
]
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".pack-cache", "__pycache__"}
SKIP_FILES = {"check-secrets.py", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"}
ALLOW_MARK = "SECRET-ALLOW:"   # documented false positive on the same line

def entropy(s):
    if not s:
        return 0.0
    freq = {}
    for ch in s:
        freq[ch] = freq.get(ch, 0) + 1
    return -sum((n / len(s)) * math.log2(n / len(s)) for n in freq.values())

def looks_assigned_secret(line):
    m = re.search(r"[:=]\s*['\"]([A-Za-z0-9/+_\-]{20,})['\"]", line)
    return bool(m) and entropy(m.group(1)) >= 4.2

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    findings = []
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in files:
            if fn in SKIP_FILES:
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, encoding="utf-8", errors="strict") as f:
                    lines = f.readlines()
            except (UnicodeDecodeError, OSError):
                continue
            for i, line in enumerate(lines, 1):
                if ALLOW_MARK in line:
                    continue
                for name, rx in PATTERNS:
                    if rx.search(line):
                        findings.append(f"{p}:{i}: {name}")
                        break
                else:
                    if looks_assigned_secret(line):
                        findings.append(f"{p}:{i}: high-entropy assignment")
    if findings:
        print("fail D23 secrets-scan:")
        for f_ in findings[:50]:
            print("  " + f_)
        print(f"\n{len(findings)} finding(s) — BLOCKING. Move secrets to env; "
              f"document false positives with {ALLOW_MARK}")
        return 1
    print("pass D23: no secrets in tracked files")
    return 0

if __name__ == "__main__":
    sys.exit(main())
