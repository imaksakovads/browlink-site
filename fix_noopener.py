#!/usr/bin/env python3
"""Add rel="noopener noreferrer nofollow" to all target="_blank" external links that lack it."""
import re
from pathlib import Path

ROOT = Path("/Users/igor/brow/browlink-site-main")
FILES = (
    [ROOT / "index.html"]
    + list((ROOT / "services").glob("*.html"))
    + list((ROOT / "blog").glob("*.html"))
)

count = 0
for fpath in FILES:
    if not fpath.exists():
        continue
    text = fpath.read_text(encoding="utf-8")
    modified = False

    # Pattern: target="_blank" NOT followed by rel= (with various possible spacing)
    pattern = re.compile(r'target="_blank"(?!\s+rel=)')

    new_text = pattern.sub('target="_blank" rel="noopener noreferrer nofollow"', text)
    if new_text != text:
        text = new_text
        modified = True
        count += 1
        print(f"  ✅ {fpath.name}")

    # Also fix existing incomplete rel attributes
    # "rel="nofollow"" without noopener
    text = text.replace('rel="nofollow"', 'rel="noopener noreferrer nofollow"')
    # "rel="noopener"" without nofollow (but keep existing)
    # Don't downgrade - noopener alone is fine for security, but add nofollow
    text = text.replace(
        'rel="noopener" target="_blank"',
        'target="_blank" rel="noopener noreferrer nofollow"'
    )

    if modified:
        fpath.write_text(text, encoding="utf-8")

print(f"\nDone — {count} files with target=_blank links fixed")
