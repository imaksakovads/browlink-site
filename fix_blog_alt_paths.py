#!/usr/bin/env python3
"""Fix Latin alt texts → Cyrillic + relative og:image paths → absolute in blog posts."""
from pathlib import Path

ROOT = Path("/Users/igor/brow/browlink-site-main")
BLOG = ROOT / "blog"
DOMAIN = "https://www.ostinkosmo.online"

# Latin → Cyrillic alt text mapping
LATIN_TO_CYR = {
    "Uhod posle laminirovaniya resnic i brovej": "Уход после ламинирования ресниц и бровей",
    "Trendy brovej 2026 goda": "Тренды бровей 2026 года",
    "Protivopokazaniya dlya laminirovaniya resnic i brovej": "Противопоказания для ламинирования ресниц и бровей",
    "Poshagovyj gid laminirovaniya resnic": "Пошаговый гид ламинирования ресниц",
    "Kak vybrat mastera po laminirovaniyu": "Как выбрать мастера по ламинированию",
}

# Older blog posts with relative og:image paths
OLD_POSTS = [
    "plyusy-laminirovaniya-resnits-estestvennyy-izgib.html",
    "pochemu-simmetrichnye-litsa-vyzyvayut-doverie-avtomate.html",
    "lomkie-brovi-posle-laminirovaniya.html",
    "nauka-o-simmetrii.html",
    "laminirovanie-brovey-komu-deystvitelno-nuzhno.html",
    "okruzhayuschie-schityvayut-harakter-forme-brovey-delo-vot.html",
]

alt_fixes = 0
path_fixes = 0

# 1. Fix Latin alt texts in 5 newer posts + blog index
for fpath in list(BLOG.glob("*.html")):
    text = fpath.read_text(encoding="utf-8")
    modified = False
    for latin, cyr in LATIN_TO_CYR.items():
        if latin in text:
            text = text.replace(latin, cyr)
            alt_fixes += 1
            modified = True
            print(f"  ✅ alt: {fpath.name} — '{latin[:40]}...' → Cyrillic")
    if modified:
        fpath.write_text(text, encoding="utf-8")

# 2. Fix relative og:image paths in 6 older posts
for fname in OLD_POSTS:
    fpath = BLOG / fname
    if not fpath.exists():
        print(f"  ⚠️  Not found: {fname}")
        continue
    text = fpath.read_text(encoding="utf-8")
    # Replace relative og:image and twitter:image
    old_content = 'content="/images/'
    new_content = f'content="{DOMAIN}/images/'
    if old_content in text:
        text = text.replace(old_content, new_content)
        path_fixes += 1
        fpath.write_text(text, encoding="utf-8")
        print(f"  ✅ paths: {fname} — relative → absolute")

print(f"\nDone — {alt_fixes} alt texts, {path_fixes} image paths fixed")
