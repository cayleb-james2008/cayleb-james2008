#!/usr/bin/env python3
"""copy_guard.py: fail if the owner-approved profile copy is rewritten. See COPY-RULES.md.

Sync jobs may update links and the numbers text the workflow writes. They may not rewrite the Q&A,
add feature lists, or bring back removed projects. Run:  python3 scripts/copy_guard.py
"""
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
README_SHA256 = "3aedf79546a7d141e8bd7e181045bb51feb993266d255757df6aa5f699992eeb"
PROFILE_SHA256 = "a02af311061fbad8aea016454c73adeb5f2c41158093bd60bd4caa421565978b"
FROZEN_KEYS = ("open_to", "intro", "work", "repos", "repo_order", "now", "stack", "stack_groups", "sections")
# Written with character classes so the removed names never appear as plain text in this public repo.
BANNED = re.compile(r"\b(Open-?K[a]l|K[a]lshi|S[o]phos|d[o]tz|Asm[o]deus|Industry A[I] Suite)\b")


def readme_hash(text):
    m = re.search(r"<!-- FROZEN-COPY-START[^>]*-->\n([\s\S]*?)\n<!-- FROZEN-COPY-END -->", text)
    return hashlib.sha256(m.group(1).encode()).hexdigest() if m else None


def profile_hash(profile):
    frozen = {k: profile.get(k) for k in FROZEN_KEYS}
    return hashlib.sha256(json.dumps(frozen, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def problems():
    out = []
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    profile = json.loads((ROOT / "data" / "profile.json").read_text(encoding="utf-8"))
    h = readme_hash(readme)
    if h is None:
        out.append("README.md: the FROZEN-COPY-START/END markers are missing.")
    elif h != README_SHA256:
        out.append(f"README.md: the frozen copy block changed (sha256 {h}). Only Cayleb changes this text.")
    if profile_hash(profile) != PROFILE_SHA256:
        out.append("data/profile.json: a frozen field changed (" + ", ".join(FROZEN_KEYS) + "). Only Cayleb changes these.")
    files = [ROOT / "README.md", ROOT / "data" / "profile.json", ROOT / "data" / "snapshot.json", *sorted((ROOT / "assets").rglob("*.svg"))]
    for f in files:
        hit = BANNED.search(f.read_text(encoding="utf-8"))
        if hit:
            out.append(f"{f.relative_to(ROOT)}: '{hit.group(0)}' must not appear (removed by the owner).")
    return out


def check():
    p = problems()
    if p:
        print("copy_guard FAILED. Read COPY-RULES.md before changing profile copy.\n- " + "\n- ".join(p), file=sys.stderr)
        sys.exit(1)
    print("copy_guard ok")


if __name__ == "__main__":
    check()
