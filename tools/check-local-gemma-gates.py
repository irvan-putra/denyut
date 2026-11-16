#!/usr/bin/env python3
"""Fail CI if either local-model activation gate is changed from false."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
gemma = (ROOT / "android/app/src/main/java/com/vanipy/denyut/LocalGemma.java").read_text()
work = (ROOT / "android/app/src/main/java/com/vanipy/denyut/LocalModelWork.java").read_text()
checks = {
    "LocalGemma activation gate": (gemma, r"private\s+static\s+final\s+boolean\s+ACTIVATION_REVIEWED\s*=\s*false\s*;"),
    "LocalModelWork activation gate": (work, r"public\s+static\s+boolean\s+activationAllowed\s*\(\s*\)\s*\{\s*return\s+false\s*;\s*\}"),
}
for name, (source, pattern) in checks.items():
    if not re.search(pattern, source):
        raise SystemExit(f"FAIL: {name} is missing or not literally false")
    print(f"PASS: {name} is explicitly false")
