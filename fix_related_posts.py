#!/usr/bin/env python3
"""Add Related Posts cross-linking block to all 11 blog articles."""
from pathlib import Path

ROOT = Path("/Users/igor/brow/browlink-site-main")
BLOG = ROOT / "blog"
DOMAIN = "https://www.ostinkosmo.online"

# Thematic article groups with related links
RELATED = {
    # Brow lamination cluster
    "laminirovanie-brovey-komu-deystvitelno-nuzhno": [
        ("lomkie-brovi-posle-laminirovaniya", "Ломкие брови после ламинирования"),
        ("protivopokazaniya-laminirovaniya-resnits-brovey-komu-nelzya", "Противопоказания для ламинирования"),
        ("uhod-posle-laminirovaniya-resnits-brovey-mozhno-nelzya", "Уход после ламинирования"),
    ],
    "lomkie-brovi-posle-laminirovaniya": [
        ("laminirovanie-brovey-komu-deystvitelno-nuzhno", "Кому нужно ламинирование бровей"),
        ("uhod-posle-laminirovaniya-resnits-brovey-mozhno-nelzya", "Уход после ламинирования"),
        ("protivopokazaniya-laminirovaniya-resnits-brovey-komu-nelzya", "Противопоказания"),
    ],
    "uhod-posle-laminirovaniya-resnits-brovey-mozhno-nelzya": [
        ("lomkie-brovi-posle-laminirovaniya", "Ломкие брови после ламинирования"),
        ("laminirovanie-brovey-komu-deystvitelno-nuzhno", "Кому нужно ламинирование бровей"),
        ("vybrat-mastera-laminirovaniyu-resnits-brovey", "Как выбрать мастера"),
    ],
    "protivopokazaniya-laminirovaniya-resnits-brovey-komu-nelzya": [
        ("laminirovanie-brovey-komu-deystvitelno-nuzhno", "Кому нужно ламинирование бровей"),
        ("lomkie-brovi-posle-laminirovaniya", "Ломкие брови после ламинирования"),
        ("uhod-posle-laminirovaniya-resnits-brovey-mozhno-nelzya", "Уход после ламинирования"),
    ],
    # Lash lamination cluster
    "laminirovanie-resnits-poshagovyy-gid-protsedure": [
        ("plyusy-laminirovaniya-resnits-estestvennyy-izgib", "Плюсы ламинирования ресниц"),
        ("vybrat-mastera-laminirovaniyu-resnits-brovey", "Как выбрать мастера"),
        ("trendy-brovey-2026-naturalnosti-arhitekture", "Тренды бровей 2026"),
    ],
    "plyusy-laminirovaniya-resnits-estestvennyy-izgib": [
        ("laminirovanie-resnits-poshagovyy-gid-protsedure", "Пошаговый гид ламинирования ресниц"),
        ("vybrat-mastera-laminirovaniyu-resnits-brovey", "Как выбрать мастера"),
        ("trendy-brovey-2026-naturalnosti-arhitekture", "Тренды бровей 2026"),
    ],
    # Trends + master selection
    "trendy-brovey-2026-naturalnosti-arhitekture": [
        ("vybrat-mastera-laminirovaniyu-resnits-brovey", "Как выбрать мастера"),
        ("laminirovanie-brovey-komu-deystvitelno-nuzhno", "Кому нужно ламинирование бровей"),
        ("laminirovanie-resnits-poshagovyy-gid-protsedure", "Гид по ламинированию ресниц"),
    ],
    "vybrat-mastera-laminirovaniyu-resnits-brovey": [
        ("trendy-brovey-2026-naturalnosti-arhitekture", "Тренды бровей 2026"),
        ("laminirovanie-resnits-poshagovyy-gid-protsedure", "Гид по ламинированию ресниц"),
        ("protivopokazaniya-laminirovaniya-resnits-brovey-komu-nelzya", "Противопоказания"),
    ],
    # Symmetry / psychology cluster
    "nauka-o-simmetrii": [
        ("pochemu-simmetrichnye-litsa-vyzyvayut-doverie-avtomate", "Почему симметрия вызывает доверие"),
        ("okruzhayuschie-schityvayut-harakter-forme-brovey-delo-vot", "Характер по форме бровей"),
    ],
    "pochemu-simmetrichnye-litsa-vyzyvayut-doverie-avtomate": [
        ("nauka-o-simmetrii", "Наука о симметрии бровей"),
        ("okruzhayuschie-schityvayut-harakter-forme-brovey-delo-vot", "Характер по форме бровей"),
    ],
    "okruzhayuschie-schityvayut-harakter-forme-brovey-delo-vot": [
        ("pochemu-simmetrichnye-litsa-vyzyvayut-doverie-avtomate", "Симметрия и доверие"),
        ("nauka-o-simmetrii", "Наука о симметрии бровей"),
        ("trendy-brovey-2026-naturalnosti-arhitekture", "Тренды бровей 2026"),
    ],
}


def make_block(fname: str) -> str:
    slug = fname.replace(".html", "")
    links = RELATED.get(slug)
    if not links:
        raise KeyError(f"No related links defined for {fname}")

    items = []
    for target_slug, title in links:
        url = f"{DOMAIN}/blog/{target_slug}.html"
        items.append(
            f'                <a href="{url}" class="block p-4 border border-gray-200 hover:border-gray-400 transition group">\n'
            f'                    <span class="font-display text-base uppercase leading-tight group-hover:text-gray-500 transition">{title}</span>\n'
            f'                    <span class="block mt-1 font-mono text-xs text-gray-400">Читать →</span>\n'
            f'                </a>'
        )

    return f"""            <!-- Related Posts -->
            <section class="mt-12 pt-8 border-t border-gray-200">
                <h2 class="font-display text-sm uppercase tracking-widest mb-6">Похожие статьи</h2>
                <div class="grid gap-4">
{chr(10).join(items)}
                </div>
            </section>"""


count = 0
for fpath in sorted(BLOG.glob("*.html")):
    if fpath.name == "index.html":
        continue

    text = fpath.read_text(encoding="utf-8")
    slug = fpath.stem

    if slug not in RELATED:
        print(f"  ⚠️  SKIP {fpath.name} — no related links defined")
        continue

    if "Похожие статьи" in text:
        print(f"  ⚠️  SKIP {fpath.name} — already has related posts")
        continue

    block = make_block(fpath.name)

    # Insert before </article>, matching the indented closing tag
    # Newer posts: "            </article>"
    # Older posts: " </article>"
    markers = ["            </article>", " </article>"]
    inserted = False
    for marker in markers:
        if marker in text:
            text = text.replace(marker, block + "\n" + marker, 1)
            inserted = True
            break

    if not inserted:
        print(f"  ❌ {fpath.name} — </article> not found")
        continue

    fpath.write_text(text, encoding="utf-8")
    count += 1
    related_count = len(RELATED[slug])
    print(f"  ✅ {fpath.name} — {related_count} related links")

print(f"\nDone — {count} articles updated")
