#!/usr/bin/env python3
"""Comprehensive SEO fixes: www canonical, og:image paths, robots, hreflang, priceCurrency, footer counts."""
from pathlib import Path
import re

ROOT = Path("/Users/igor/brow/browlink-site-main")
WWW_DOMAIN = "https://www.ostinkosmo.online"
NON_WWW = "https://ostinkosmo.online"

# All HTML files to process
HTML_FILES = (
    [ROOT / "index.html"]
    + list((ROOT / "services").glob("*.html"))
    + list((ROOT / "blog").glob("*.html"))
)

# Files that should be SKIPPED for www replacement (already correct)
SKIP_WWW = {ROOT / "index.html"}

stats = {"www_fixed": 0, "og_image_fixed": 0, "robots_added": 0, "hreflang_added": 0,
         "price_currency": 0, "blog_count": 0, "blog_og_image": 0}

for fpath in HTML_FILES:
    if not fpath.exists():
        continue
    text = fpath.read_text(encoding="utf-8")
    modified = False
    rel = str(fpath.relative_to(ROOT))

    # --- 1. www canonical fix ---
    if fpath not in SKIP_WWW:
        new_text = text.replace(NON_WWW, WWW_DOMAIN)
        if new_text != text:
            stats["www_fixed"] += 1
            text = new_text
            modified = True
            print(f"  ✅ www: {rel}")

    # --- 2. Main page: absolute og:image ---
    if fpath.name == "index.html":
        old_og = 'content="/images/review-default.webp"'
        new_og = f'content="{WWW_DOMAIN}/images/review-default.webp"'
        if old_og in text:
            text = text.replace(old_og, new_og)
            stats["og_image_fixed"] += 1
            modified = True
            print(f"  ✅ og:image absolute: {rel}")

    # --- 3. Blog index: empty og:image ---
    if fpath == ROOT / "blog" / "index.html":
        if '<meta property="og:image" content="">' in text:
            text = text.replace(
                '<meta property="og:image" content="">',
                f'<meta property="og:image" content="{WWW_DOMAIN}/images/blog-lam-brovey.webp">'
            )
            stats["blog_og_image"] += 1
            modified = True
            print(f"  ✅ blog og:image filled: {rel}")
        # Add twitter:image
        if '<meta name="twitter:description"' in text and '<meta name="twitter:image"' not in text:
            text = text.replace(
                '<meta name="twitter:description"',
                f'<meta name="twitter:image" content="{WWW_DOMAIN}/images/blog-lam-brovey.webp">\n    <meta name="twitter:description"'
            )
            modified = True
            print(f"  ✅ twitter:image added: {rel}")

    # --- 4. Add robots meta (after viewport) ---
    if '<meta name="robots"' not in text:
        text = text.replace(
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <meta name="robots" content="index, follow">',
            1  # only first occurrence
        )
        stats["robots_added"] += 1
        modified = True
        print(f"  ✅ robots: {rel}")

    # --- 5. Add hreflang (after canonical) ---
    if 'hreflang' not in text:
        canon_match = re.search(r'<link rel="canonical" href="([^"]+)"\s*/?>', text)
        if canon_match:
            full_tag = canon_match.group(0)
            canon_url = canon_match.group(1)
            hreflang_tag = f'\n    <link rel="alternate" hreflang="ru" href="{canon_url}">'
            text = text.replace(full_tag, full_tag + hreflang_tag, 1)
            stats["hreflang_added"] += 1
            modified = True
            print(f"  ✅ hreflang: {rel}")

    # --- 6. Blog index: "5 статей" → "11 статей" ---
    if fpath == ROOT / "blog" / "index.html":
        if "5 статей" in text:
            text = text.replace("5 статей", "11 статей")
            stats["blog_count"] += 1
            modified = True
            print(f"  ✅ blog count: {rel}")

    if modified:
        fpath.write_text(text, encoding="utf-8")

# --- 7. Main page: priceCurrency in JSON-LD ---
index_path = ROOT / "index.html"
index_text = index_path.read_text(encoding="utf-8")

# Add priceCurrency to each Offer
offer_pattern = re.compile(r'("price": "\d+")')
new_offers = offer_pattern.sub(r'\1,\n        "priceCurrency": "RUB"', index_text)
if new_offers != index_text:
    index_path.write_text(new_offers, encoding="utf-8")
    stats["price_currency"] = offer_pattern.findall(index_text).count(
        offer_pattern.findall(index_text)[0] if offer_pattern.findall(index_text) else "")
    # Use a simpler check
    count = len(offer_pattern.findall(index_text))
    stats["price_currency"] = count
    print(f"  ✅ priceCurrency: {count} offers in index.html")

# --- 8. Sitemap: add lastmod ---
sitemap_path = ROOT / "sitemap.xml"
sitemap = sitemap_path.read_text(encoding="utf-8")
# Add lastmod after each changefreq line if not present
if "<lastmod>" not in sitemap:
    sitemap = sitemap.replace(
        "</changefreq>",
        "</changefreq>\n      <lastmod>2026-07-06</lastmod>"
    )
    sitemap_path.write_text(sitemap, encoding="utf-8")
    print("  ✅ sitemap: lastmod added to all URLs")

print(f"\n--- Summary ---")
print(f"www canonical fixed: {stats['www_fixed']} files")
print(f"og:image absolute:    {stats['og_image_fixed']} files")
print(f"blog og:image:        {stats['blog_og_image']} files")
print(f"robots meta added:    {stats['robots_added']} files")
print(f"hreflang added:       {stats['hreflang_added']} files")
print(f"priceCurrency:        {stats['price_currency']} offers")
print(f"blog count fixed:     {stats['blog_count']} files")
