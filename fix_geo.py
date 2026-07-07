#!/usr/bin/env python3
"""Add geo-SEO content to service pages: metro in titles, descriptions, JSON-LD, footer."""
import json, re

SERVICE_DIR = "/Users/igor/brow/browlink-site-main/services"
SERVICES = [
    "laminirovanie-resnic.html",
    "laminirovanie-brovey.html",
    "oformlenie-brovey.html",
    "korrekciya-brovey.html",
    "laminirovanie-korrekciya-brovey.html",
]

ADDRESS_LINE = '                <div style="font-size:12px; color:var(--text-muted); margin-top:8px;">Москва, м. Белорусская / Маяковская, Тверская-Ямская ул., 25с2 · <a href="tel:+79637329466" style="color:var(--text-muted); text-decoration:underline;">+7 963 732-94-66</a></div>\n'

OPENING_HOURS_SPEC = {
    "@type": "OpeningHoursSpecification",
    "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "opens": "10:00",
    "closes": "21:00",
}

for fname in SERVICES:
    path = f"{SERVICE_DIR}/{fname}"
    with open(path, encoding="utf-8") as f:
        html = f.read()

    original = html

    # 1. Meta title: "в Москве" → "на Белорусской, Москва"
    html = re.sub(
        r'(<title>.*?) в Москве (.*?</title>)',
        r'\1 на Белорусской, Москва \2',
        html,
    )

    # 2. Meta description: keep as-is but add metro prefix if not present
    if "Белорусская" not in html[:html.index("</head>")]:
        html = re.sub(
            r'(<meta name="description" content=")',
            r'\1Рядом с м. Белорусская и Маяковская. ',
            html,
            count=1,
        )

    # 3. OG title
    html = re.sub(
        r'(<meta property="og:title" content=".*?) в Москве (.*?/>)',
        r'\1 на Белорусской, Москва \2',
        html,
    )

    # 4. JSON-LD: add streetAddress, openingHours to provider.address, add to areaServed
    # Find the JSON-LD script block
    ld_match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    if ld_match:
        ld_text = ld_match.group(1)
        ld = json.loads(ld_text)
        graph = ld.get("@graph", [ld])

        for item in graph:
            # Add openingHours to BeautySalonService or provider if BeautySalon
            if item.get("@type") in ("BeautySalonService", "BeautySalon"):
                # Add openingHours to provider
                provider = item.get("provider")
                if provider:
                    if "openingHoursSpecification" not in provider:
                        provider["openingHoursSpecification"] = OPENING_HOURS_SPEC
                    addr = provider.get("address", {})
                    if "streetAddress" not in addr:
                        addr["streetAddress"] = "Тверская-Ямская улица, 25 ст2"
                    if "neighborhood" not in addr:
                        addr["neighborhood"] = "Белорусская"

                # areaServed → add neighbourhood
                area = item.get("areaServed", {})
                if area.get("name") == "Москва" and "description" not in area:
                    area["description"] = "Рядом с метро Белорусская, Маяковская"

        new_ld = json.dumps(ld, ensure_ascii=False, indent=2)
        html = html.replace(ld_match.group(1), new_ld)

    # 5. h1: "в Москве:" → "в Москве, м. Белорусская:"
    html = re.sub(
        r'в Москве: ',
        'в Москве, м. Белорусская: ',
        html,
        count=1,
    )

    # 6. First hero-desc paragraph: add metro reference at end if not present
    if "Белорусская" not in html[html.index('<h1 class="page-title">'):html.index("</section>") if "<h1 class=\"page-title\">" in html else 0:]:
        pass  # h1 already has metro now

    # Add metro to footer-adjacent hero content if needed
    html = re.sub(
        r'(<p class="hero-desc".*?</p>)',
        lambda m: m.group(1).replace(
            '</p>',
            ' Студия находится в 5 минутах от метро Белорусская (выход №4) и Маяковская — в пешей доступности для жителей Тверского района и ЦАО.</p>',
        ) if m.group(1).count("Белорусская") == 0 else m.group(1),
        html,
        count=1,
    )

    # 7. Footer: add address line after copyright div
    html = html.replace(
        '<div class="footer-links" style="margin-top:10px;">',
        ADDRESS_LINE + '            <div class="footer-links" style="margin-top:10px;">',
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    changes = sum(1 for a, b in zip(original, html) if a != b)
    print(f"  {fname}: {changes} chars changed")

print("Done — all 5 service pages updated")
