#!/usr/bin/env python3
"""Add booking buttons to footer + fix mobile menu VK styling on 4 service pages."""
from pathlib import Path

SITE = Path("/Users/igor/brow/browlink-site-main/services")
FILES = [
    "laminirovanie-brovey.html",
    "oformlenie-brovey.html",
    "laminirovanie-resnic.html",
    "korrekciya-brovey.html",
]

BOOKING_BUTTONS = """
        <!-- Кнопки записи -->
        <div style="display:flex; gap:12px; flex-wrap:wrap; margin-bottom:30px;">
            <a href="https://t.me/KateOstin666" onclick="reachGoal('zakaz_whatsapp')" target="_blank" rel="nofollow" style="display:inline-flex; align-items:center; justify-content:center; gap:8px; font-family:var(--font-title); font-size:13px; text-transform:uppercase; letter-spacing:1.5px; font-weight:500; cursor:pointer; border:2px solid var(--text-main); background:var(--text-main); color:#fff; padding:12px 24px; text-decoration:none; transition:opacity 0.2s;">Telegram / Запись</a>
            <a href="https://vk.com/katespanjen" onclick="reachGoal('booking_vk')" target="_blank" rel="nofollow" style="display:inline-flex; align-items:center; justify-content:center; gap:8px; font-family:var(--font-title); font-size:13px; text-transform:uppercase; letter-spacing:1.5px; font-weight:500; cursor:pointer; border:2px solid var(--text-main); background:#fff; color:var(--text-main); padding:12px 24px; text-decoration:none; transition:opacity 0.2s;">ВКонтакте / Запись</a>
        </div>
"""

OLD_FOOTER_MARKER = """    <!-- Подвал сайта -->
    <footer class="footer">
        <div class="container footer-inner">
            <div class="copyright">© 2026 OSTINKOSMO. Студия эстетики и моделирования.</div>
            <div class="footer-links">
                <a href="/privacy/">Политика конфиденциальности</a>
            </div>
        </div>
    </footer>"""

NEW_FOOTER = """    <!-- Подвал сайта -->
    <footer class="footer">
        <div class="container">
            <div style="display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:20px; margin-bottom:30px;">""" + BOOKING_BUTTONS + """
            <div class="footer-inner" style="flex:1; min-width:200px;">
                <div class="copyright">© 2026 OSTINKOSMO. Студия эстетики и моделирования.</div>
                <div class="footer-links" style="margin-top:10px;">
                    <a href="/privacy/">Политика конфиденциальности</a>
                </div>
            </div>
        </div>
    </footer>"""

# Mobile menu: fix VK link to match TG style (Oswald font, proper size)
OLD_VK_MOBILE = """        <a href="https://vk.com/katespanjen" onclick="reachGoal('booking_vk')" target="_blank" rel="nofollow" style="font-family:'Inter',sans-serif; font-size:13px; color:#999; text-decoration:none; transition:color 0.2s; padding:8px 0; display:block; text-align:center; text-transform:uppercase; letter-spacing:1px;">ВКонтакте Запись</a>"""

NEW_VK_MOBILE = """        <a href="https://vk.com/katespanjen" onclick="reachGoal('booking_vk')" target="_blank" rel="nofollow" style="font-family:var(--font-title); font-size:20px; text-transform:uppercase; letter-spacing:1px; color:var(--text-main); padding:12px 0; display:block; text-align:center; text-decoration:none; transition:opacity 0.2s;">ВКонтакте / Запись</a>"""

count = 0
for fname in FILES:
    path = SITE / fname
    text = path.read_text(encoding="utf-8")
    modified = False

    # 1. Replace footer
    if OLD_FOOTER_MARKER in text:
        text = text.replace(OLD_FOOTER_MARKER, NEW_FOOTER)
        modified = True
        print(f"  ✅ {fname}: footer updated")
    else:
        print(f"  ⚠️  {fname}: old footer not found")

    # 2. Replace mobile VK link
    if OLD_VK_MOBILE in text:
        text = text.replace(OLD_VK_MOBILE, NEW_VK_MOBILE)
        modified = True
        print(f"  ✅ {fname}: mobile VK link updated")
    else:
        print(f"  ⚠️  {fname}: old VK mobile link not found")

    if modified:
        path.write_text(text, encoding="utf-8")
        count += 1

print(f"\nDone — {count}/{len(FILES)} files updated")
