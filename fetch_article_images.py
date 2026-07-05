#!/usr/bin/env python3
"""Download 10 article images → WebP 100%"""
import io, subprocess, sys
from pathlib import Path
from PIL import Image

IMAGES_DIR = Path(__file__).parent / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

URLS = [
    ("https://i.ibb.co/RTdDdcGQ/1.jpg", "article-uhod-1.webp"),
    ("https://i.ibb.co/mCW02z6T/2.jpg", "article-uhod-2.webp"),
    ("https://i.ibb.co/JRqjqcP6/22.jpg", "article-protiv-1.webp"),
    ("https://i.ibb.co/CsYSFtGS/222.jpg", "article-protiv-2.webp"),
    ("https://i.ibb.co/9kmmqFJW/55.jpg", "article-master-1.webp"),
    ("https://i.ibb.co/6cPWn2WW/555.jpg", "article-master-2.webp"),
    ("https://i.ibb.co/YT7j8gk6/66.jpg", "article-gid-1.webp"),
    ("https://i.ibb.co/3m2tZPQP/666.jpg", "article-gid-2.webp"),
    ("https://i.ibb.co/x9qBGmT/777.jpg", "article-trendy-1.webp"),
    ("https://i.ibb.co/20dsN8b8/77.jpg", "article-trendy-2.webp"),
]

for url, fname in URLS:
    local = IMAGES_DIR / fname
    if local.exists():
        print(f"⏭️  {fname} ({local.stat().st_size // 1024}K)")
        continue
    print(f"⬇️  {fname}...", end=" ")
    r = subprocess.run(
        ["curl", "-sS", "-L", "--max-time", "60",
         "-A", "Mozilla/5.0 (compatible; OSTINKOSMO/1.0)", url],
        capture_output=True, timeout=120)
    if r.returncode != 0 or len(r.stdout) < 100:
        print(f"❌ download failed"); continue
    print(f"{len(r.stdout)//1024}K", end=" → ")
    img = Image.open(io.BytesIO(r.stdout))
    if img.mode in ("RGBA", "PA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    img.save(local, "WEBP", quality=100, method=6)
    print(f"{local.stat().st_size // 1024}K ✅")
