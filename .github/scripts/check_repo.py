"""Repository sanity checks (run by CI, also fine to run locally: python .github/scripts/check_repo.py).

1. Every .py file compiles.
2. JSON files (e.g. the Fusion 360 add-in manifest) are valid.
3. Every relative link / image in the Markdown files points to a file that exists.
4. No file is large enough to be a problem for GitHub (>50 MB) unless it is a Git LFS pointer.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}
errors = []


def files(*suffixes):
    for p in ROOT.rglob("*"):
        if p.is_file() and not (set(p.relative_to(ROOT).parts) & SKIP_DIRS) and p.suffix.lower() in suffixes:
            yield p


# 1. Python syntax
for p in files(".py"):
    try:
        compile(p.read_text(encoding="utf8"), str(p), "exec")
    except SyntaxError as e:
        errors.append(f"Python syntax error in {p.relative_to(ROOT)}, line {e.lineno}: {e.msg}")

# 2. JSON validity (the .manifest file is JSON too)
for p in list(files(".json")) + list(ROOT.rglob("*.manifest")):
    try:
        json.loads(p.read_text(encoding="utf8"))
    except Exception as e:
        errors.append(f"Invalid JSON in {p.relative_to(ROOT)}: {e}")

# 3. Markdown links and images
LINK = re.compile(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)|(?:src|href)=\"([^\"]+)\"")
for md in files(".md"):
    text = md.read_text(encoding="utf8")
    text = re.sub(r"```.*?```", "", text, flags=re.S)  # ignore code blocks
    for m in LINK.finditer(text):
        target = (m.group(1) or m.group(2) or "").split("#")[0].split("?")[0]
        if not target or re.match(r"^(https?:|mailto:|data:)", target):
            continue
        base = ROOT if target.startswith("/") else md.parent
        if not (base / target.lstrip("/")).exists():
            errors.append(f"Broken link in {md.relative_to(ROOT)}: {target}")

# 4. Large files
for p in ROOT.rglob("*"):
    if p.is_file() and not (set(p.relative_to(ROOT).parts) & SKIP_DIRS) and p.stat().st_size > 50 * 1024 * 1024:
        errors.append(f"File over 50 MB (use Git LFS or link to it): {p.relative_to(ROOT)}")

if errors:
    print("\n".join("FAIL " + e for e in errors))
    sys.exit(1)
print("All repository checks passed.")
