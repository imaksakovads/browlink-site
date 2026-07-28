"""Regenerate sitemap.xml and robots.txt for www.ostinkosmo.ru (GitHub Pages)."""
from datetime import date
from pathlib import Path

SITE_DIR = Path(__file__).parent
BASE_URL = "https://www.ostinkosmo.ru"
TODAY = date.today().isoformat()

SITEMAP_HEAD = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
'''
SITEMAP_TAIL = '</urlset>'

PAGES: list[dict] = [
    # (path, priority, changefreq)
    ("/", 1.0, "weekly"),
    ("/services/laminirovanie-resnic.html", 0.9, "monthly"),
    ("/services/oformlenie-brovey.html", 0.9, "monthly"),
    ("/services/laminirovanie-brovey.html", 0.9, "monthly"),
    ("/services/korrekciya-brovey.html", 0.9, "monthly"),
    ("/services/laminirovanie-korrekciya-brovey.html", 0.9, "monthly"),
    ("/blog", 0.8, "weekly"),
    ("/reviews.html", 0.6, "monthly"),
    ("/privacy.html", 0.3, "yearly"),
]


def build_sitemap() -> str:
    """Generate complete sitemap XML."""
    parts = [SITEMAP_HEAD]

    # static pages
    for path, priority, changefreq in PAGES:
        parts.append(f"""  <url>
    <loc>{BASE_URL}{path}</loc>
    <priority>{priority}</priority>
    <changefreq>{changefreq}</changefreq>
    <lastmod>{TODAY}</lastmod>
  </url>""")

    # blog articles (scan actual .html files)
    blog_dir = SITE_DIR / "blog"
    if blog_dir.exists():
        articles = sorted(f.stem for f in blog_dir.glob("*.html") if f.stem != "index")
        for slug in articles:
            # Use file mtime for article lastmod, fallback to today
            fpath = blog_dir / f"{slug}.html"
            mtime = date.fromtimestamp(fpath.stat().st_mtime).isoformat()
            parts.append(f"""  <url>
    <loc>{BASE_URL}/blog/{slug}.html</loc>
    <priority>0.7</priority>
    <changefreq>monthly</changefreq>
    <lastmod>{mtime}</lastmod>
  </url>""")

    parts.append(SITEMAP_TAIL)
    return "\n".join(parts) + "\n"


def main() -> None:
    sitemap = build_sitemap()
    (SITE_DIR / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    print(f"sitemap.xml — {sitemap.count('<loc>')} URLs")

    # robots.txt — create or fix
    robots = SITE_DIR / "robots.txt"
    robots_content = """# Правила для Яндекса
User-agent: Yandex
Disallow: /admin/
Disallow: /academy/
Disallow: /*?
Clean-param: tag /blog/
Clean-param: page /blog/
Clean-param: utm_source
Clean-param: utm_medium
Clean-param: utm_campaign
Clean-param: utm_content
Clean-param: utm_term
Clean-param: yclid
Clean-param: _openstat
Clean-param: from
Host: https://www.ostinkosmo.ru
Sitemap: https://www.ostinkosmo.ru/sitemap.xml

# Правила для всех остальных роботов
User-agent: *
Disallow: /admin/
Disallow: /academy/
Disallow: /*?
Allow: /blog/?$
Sitemap: https://www.ostinkosmo.ru/sitemap.xml
"""
    if not robots.exists():
        robots.write_text(robots_content, encoding="utf-8")
        print("robots.txt — created")
    else:
        content = robots.read_text(encoding="utf-8")
        if "ostinkosmo.online" in content:
            content = content.replace("ostinkosmo.online", "www.ostinkosmo.ru")
            robots.write_text(content, encoding="utf-8")
            print("robots.txt — fixed .online → .ru")
        elif "Sitemap:" not in content:
            robots.write_text(robots_content, encoding="utf-8")
            print("robots.txt — regenerated (missing Sitemap)")


if __name__ == "__main__":
    main()
