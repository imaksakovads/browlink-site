#!/usr/bin/env python3
"""Download missing blog-lomkie-brovi.webp image."""
import io, subprocess
from pathlib import Path
from PIL import Image

url = "https://i.ibb.co/mrSRvgmB/image.jpg"
out_path = Path(__file__).parent / "images" / "blog-lomkie-brovi.webp"

print(f"Downloading {url}...")
r = subprocess.run(
    ["curl", "-sS", "-L", "--max-time", "60",
     "-A", "Mozilla/5.0 (compatible; OSTINKOSMO/1.0)", url],
    capture_output=True, timeout=120)

if r.returncode != 0 or len(r.stdout) < 100:
    print(f"Failed: rc={r.returncode}, size={len(r.stdout)}")
    exit(1)

print(f"Downloaded {len(r.stdout)//1024}K, converting to WebP...")
img = Image.open(io.BytesIO(r.stdout))
if img.mode in ("RGBA", "PA"):
    bg = Image.new("RGB", img.size, (255, 255, 255))
    bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
    img = bg
elif img.mode != "RGB":
    img = img.convert("RGB")
img.save(str(out_path), "WEBP", quality=100, method=6)
print(f"Saved: {out_path} ({out_path.stat().st_size//1024}K)")
