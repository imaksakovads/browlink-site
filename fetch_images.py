"""
Скачивание внешних изображений → WebP (quality 100%) в /images/.
Пропускает уже существующие файлы.
Использует curl (обходит SSL-проблемы Python 3.12 на macOS).
"""

import io
import os
import subprocess
import sys
from pathlib import Path

SITE_ROOT = Path(__file__).parent
IMAGES_DIR = SITE_ROOT / "images"
WEBP_QUALITY = 100

ALL_IMAGES = [
    ("https://i.ibb.co/JWknsnnC/1274ccc8-6aee-431c-8f76-aa8f9c182a41.jpg", "blog-lam-resnits.webp"),
    ("https://i.ibb.co/7d1VPP2f/image.jpg", "blog-lam-brovey.webp"),
    ("https://i.ibb.co/fzdjy7xp/image.png", "blog-simmetriya.webp"),
    ("https://i.ibb.co/Zpzy266W/11.jpg", "blog-harakter-brovi.webp"),
    ("https://i.ibb.co/mrSRvgmB/image.jpg", "blog-lomkie-brovi.webp"),
    ("https://i.ibb.co/35K8F7jb/2.jpg", "blog-nauka-simmetriya.webp"),
    ("https://i.ibb.co/27QQgs5Q/12.jpg", "blog-okruzh-char.webp"),
    ("https://i.ibb.co/KYbcN2g/22.jpg", "blog-brow-22.webp"),
    ("https://i.ibb.co/XxYDkpSg/11-1-1.png", "blog-brow-11-1.webp"),
    ("https://i.postimg.cc/QtDtLm6Y/photo-2025-08-09-17-37-33.jpg", "review-default.webp"),
    ("https://i.postimg.cc/6pDqctCX/photo-2025-08-09-17-25-54-2.jpg", "review-1.webp"),
    ("https://i.postimg.cc/7Y9QSL85/photo-2024-10-04-14-40-45-1.jpg", "review-2.webp"),
    ("https://i.postimg.cc/7ZCbSfG9/photo-2025-08-09-22-22-30.jpg", "review-3.webp"),
    ("https://i.postimg.cc/CRZTq1J2/photo-2024-10-04-14-34-27-1.jpg", "review-4.webp"),
    ("https://i.postimg.cc/JhYLxQfB/photo-2024-11-20-17-18-02.jpg", "review-5.webp"),
    ("https://github.com/user-attachments/assets/0de0f77b-700d-41c3-9251-e9a6a0fe9d74", "gh-screenshot-1.webp"),
    ("https://github.com/user-attachments/assets/315d3a42-3672-475f-a28b-1e925947572a", "gh-screenshot-2.webp"),
    ("https://github.com/user-attachments/assets/5841e948-e141-4bb2-b9f8-af499387237c", "gh-screenshot-3.webp"),
    ("https://github.com/user-attachments/assets/91bc0bd2-24fa-441e-badf-5c2b33effc5b", "gh-screenshot-4.webp"),
    ("https://github.com/user-attachments/assets/f82e6fab-e2f8-4e73-9d67-4e3d0ee3ec5f", "gh-screenshot-5.webp"),
]

LOCAL_KIRILLICA = {
    "---Комплекс.webp": "service-complex.webp",
    "---Коррекция бровей.webp": "service-korrekciya.webp",
    "---Ламинирование бровей.webp": "service-lam-brovey.webp",
    "---Ламинирование ресниц.webp": "service-lam-resnits.webp",
    "---Оформление бровей.webp": "service-oformlenie.webp",
}


def download_via_curl(url: str) -> bytes | None:
    """Download via curl — bypasses Python SSL issues on macOS."""
    try:
        r = subprocess.run(
            ["curl", "-sS", "-L", "--max-time", "60",
             "-A", "Mozilla/5.0 (compatible; OSTINKOSMO/1.0)",
             url],
            capture_output=True, timeout=120)
        if r.returncode != 0:
            print(f"  ❌ curl error ({r.returncode})")
            return None
        data = r.stdout
        if len(data) < 100:
            print(f"  ❌ Too small ({len(data)} bytes)")
            return None
        print(f"  ✅ {len(data)} bytes")
        return data
    except Exception as e:
        print(f"  ❌ {e}")
        return None


def to_webp(data: bytes, out: Path) -> bool:
    """Convert to WebP via Pillow."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        if img.mode in ("RGBA", "PA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        img.save(out, "WEBP", quality=WEBP_QUALITY, method=6)
        kb = out.stat().st_size / 1024
        pct = (1 - kb / (len(data) / 1024)) * 100
        print(f"     WebP: {kb:.0f}K (save {pct:.0f}%)")
        return True
    except Exception as e:
        print(f"     Conversion failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🖼  ОПТИМИЗАЦИЯ ИЗОБРАЖЕНИЙ")
    print("=" * 60)

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # --- Step 1: external images ---
    print("\n📥 Внешние изображения:")
    url_map = {}
    for url, fname in ALL_IMAGES:
        local = IMAGES_DIR / fname
        if local.exists():
            print(f"  ⏭️  {fname} (already exists, {local.stat().st_size // 1024}K)")
            url_map[url] = f"/images/{fname}"
            continue
        print(f"  {fname} ...", end=" ")
        data = download_via_curl(url)
        if data and to_webp(data, local):
            url_map[url] = f"/images/{fname}"

    # --- Step 2: local kirillica ---
    print("\n📦 Локальные кириллические:")
    for old, new in LOCAL_KIRILLICA.items():
        old_path = SITE_ROOT / old
        new_path = IMAGES_DIR / new
        if not old_path.exists():
            print(f"  ⏭️  {old} (not found)")
            continue
        if new_path.exists():
            print(f"  ⏭️  {new} (already exists)")
            continue
        old_path.rename(new_path)
        print(f"  ✅ {old} → images/{new} ({new_path.stat().st_size // 1024}K)")

    # --- Report ---
    print("\n" + "=" * 60)
    print("📊 ИТОГО")
    print("=" * 60)
    webps = sorted(IMAGES_DIR.glob("*.webp"))
    print(f"  Файлов в /images/: {len(webps)}")
    total_kb = sum(f.stat().st_size for f in webps) / 1024
    print(f"  Общий размер: {total_kb:.0f}K")
    print(f"\n  Файлы:")
    for f in webps:
        print(f"    {f.name:<45} {f.stat().st_size // 1024:>4}K")
    print("\n✅ ГОТОВО")
