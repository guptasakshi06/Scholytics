#!/usr/bin/env python3
"""Check local Markdown links, sprint ledger/card consistency and course hash."""
import hashlib
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
files = [ROOT / name for name in ("README.md", "HANDOFF.md", "AGENTS.md")]
files += list((ROOT / "docs").rglob("*.md"))
files += list((ROOT / "data").glob("*.md"))
files += list((ROOT / "tests/fixtures").rglob("*.md"))
links = 0
for path in files:
    content = path.read_text(encoding="utf-8")
    assert content.count("```") % 2 == 0, f"Unbalanced fence: {path}"
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
        if target.startswith(("https://", "http://", "mailto:", "#")):
            continue
        local = target.split("#")[0]
        assert (path.parent / local).exists(), f"Broken link: {path}: {target}"
        links += 1
handoff = (ROOT / "HANDOFF.md").read_text()
ledger = re.findall(r"^\| (S\d{2}) \| [^\n]+? \| (NOT_STARTED|IN_PROGRESS|BLOCKED|DONE) \|", handoff, re.M)
cards = re.findall(r"^### (S\d{2}) —", handoff, re.M)
assert len(ledger) == 12 and [s for s, _ in ledger] == cards
for sprint, status in ledger:
    section = handoff.split(f"### {sprint} —", 1)[1].split("\n### ", 1)[0]
    if status == "DONE":
        assert "- [ ]" not in section, f"Unchecked task in done sprint {sprint}"
reference = ROOT / "docs/reference/DIP_Course_Project_Guidelines_2026.pdf"
assert hashlib.sha256(reference.read_bytes()).hexdigest() == "805afb1b48ff58a145e8eb0b506fd0b944b2addbfae987871a5c400a78546017"
print(f"PASS: {len(files)} Markdown files; {links} local links; balanced fences; 12 consistent sprint cards/statuses; course PDF unchanged.")
