#!/usr/bin/env python3
"""Fix laminirovanie-korrekciya-brovey.html — the 5th service page missing all updates."""
from pathlib import Path

path = Path("/Users/igor/brow/browlink-site-main/services/laminirovanie-korrekciya-brovey.html")
text = path.read_text(encoding="utf-8")
modified = False

# 1. Header sidebar — add VK link + wrap in sidebar-links div
old_header = """            <div class="header-right">
                <a href="https://t.me/KateOstin666" onclick="reachGoal('zakaz_whatsapp')" class="telegram-link" target="_blank" rel="nofollow">Telegram</a>
                <a href="tel:+79637329466" onclick="reachGoal('zvonok_tel')" class="phone">+7 963 732 94 66</a>
            </div>"""

new_header = """            <div class="header-right">
                <div class="sidebar-links" style="display:flex; flex-direction:column; gap:8px;">
                    <a href="https://t.me/KateOstin666" onclick="reachGoal('zakaz_whatsapp')" class="telegram-link" target="_blank" rel="nofollow">Telegram</a>
                    <a href="https://vk.com/katespanjen" onclick="reachGoal('booking_vk')" target="_blank" rel="nofollow" class="telegram-link">ВКонтакте</a>
                    <a href="tel:+79637329466" onclick="reachGoal('zvonok_tel')" class="phone" style="margin-top:4px;">+7 963 732 94 66</a>
                </div>
            </div>"""

if old_header in text:
    text = text.replace(old_header, new_header)
    modified = True
    print("✅ Header: VK link added")
else:
    print("⚠️ Header: pattern not found")

# 2. Mobile menu — add VK link
old_mobile = """        <a href="https://t.me/KateOstin666" onclick="reachGoal('zakaz_whatsapp')" class="mobile-tg" target="_blank" rel="nofollow">Telegram Запись</a>
    </div>"""

new_mobile = """        <a href="https://t.me/KateOstin666" onclick="reachGoal('zakaz_whatsapp')" class="mobile-tg" target="_blank" rel="nofollow">Telegram / Запись</a>
        <a href="https://vk.com/katespanjen" onclick="reachGoal('booking_vk')" target="_blank" rel="nofollow" style="font-family:var(--font-title); font-size:20px; text-transform:uppercase; letter-spacing:1px; color:var(--text-main); padding:12px 0; display:block; text-align:center; text-decoration:none; transition:opacity 0.2s;">ВКонтакте / Запись</a>
    </div>"""

if old_mobile in text:
    text = text.replace(old_mobile, new_mobile)
    modified = True
    print("✅ Mobile menu: VK link added")
else:
    print("⚠️ Mobile menu: pattern not found")

# 3. Hero button — replace old single button with TG/VK pair
old_hero_btn = """                <a href="https://t.me/KateOstin666" onclick="reachGoal('zakaz_whatsapp')" class="btn-action" style="text-decoration:none;" target="_blank" rel="nofollow">Записаться <span>→</span></a>"""

new_hero_btns = """                <div style="display:flex; gap:12px; flex-wrap:wrap; padding-top:25px; border-top:1px solid var(--border-color); width:100%;">
                    <a href="https://t.me/KateOstin666" onclick="reachGoal('zakaz_whatsapp')" target="_blank" rel="nofollow" style="display:inline-flex; align-items:center; justify-content:center; gap:8px; font-family:var(--font-title); font-size:15px; text-transform:uppercase; letter-spacing:1.5px; font-weight:500; cursor:pointer; border:2px solid var(--text-main); background:var(--text-main); color:#fff; padding:14px 28px; text-decoration:none; transition:opacity 0.2s;">Telegram / Запись</a>
                    <a href="https://vk.com/katespanjen" onclick="reachGoal('booking_vk')" target="_blank" rel="nofollow" style="display:inline-flex; align-items:center; justify-content:center; gap:8px; font-family:var(--font-title); font-size:15px; text-transform:uppercase; letter-spacing:1.5px; font-weight:500; cursor:pointer; border:2px solid var(--text-main); background:#fff; color:var(--text-main); padding:14px 28px; text-decoration:none; transition:opacity 0.2s;">ВКонтакте / Запись</a>
                </div>"""

if old_hero_btn in text:
    text = text.replace(old_hero_btn, new_hero_btns)
    modified = True
    print("✅ Hero buttons: TG/VK pair added")
else:
    print("⚠️ Hero button: pattern not found")

# 4. Footer — add booking buttons
old_footer = """    <!-- Подвал сайта -->
    <footer class="footer">
        <div class="container footer-inner">
            <div class="copyright">© 2026 OSTINKOSMO. Студия эстетики и моделирования.</div>
            <div class="footer-links">
                <a href="/privacy/">Политика конфиденциальности</a>
            </div>
        </div>
    </footer>"""

new_footer = """    <!-- Подвал сайта -->
    <footer class="footer">
        <div class="container">
            <div style="display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:20px; margin-bottom:30px;">
                <!-- Кнопки записи -->
                <div style="display:flex; gap:12px; flex-wrap:wrap;">
                    <a href="https://t.me/KateOstin666" onclick="reachGoal('zakaz_whatsapp')" target="_blank" rel="nofollow" style="display:inline-flex; align-items:center; justify-content:center; gap:8px; font-family:var(--font-title); font-size:13px; text-transform:uppercase; letter-spacing:1.5px; font-weight:500; cursor:pointer; border:2px solid var(--text-main); background:var(--text-main); color:#fff; padding:12px 24px; text-decoration:none; transition:opacity 0.2s;">Telegram / Запись</a>
                    <a href="https://vk.com/katespanjen" onclick="reachGoal('booking_vk')" target="_blank" rel="nofollow" style="display:inline-flex; align-items:center; justify-content:center; gap:8px; font-family:var(--font-title); font-size:13px; text-transform:uppercase; letter-spacing:1.5px; font-weight:500; cursor:pointer; border:2px solid var(--text-main); background:#fff; color:var(--text-main); padding:12px 24px; text-decoration:none; transition:opacity 0.2s;">ВКонтакте / Запись</a>
                </div>
                <div class="footer-inner" style="flex:1; min-width:200px;">
                    <div class="copyright">© 2026 OSTINKOSMO. Студия эстетики и моделирования.</div>
                    <div class="footer-links" style="margin-top:10px;">
                        <a href="/privacy/">Политика конфиденциальности</a>
                    </div>
                </div>
            </div>
        </div>
    </footer>"""

if old_footer in text:
    text = text.replace(old_footer, new_footer)
    modified = True
    print("✅ Footer: booking buttons added")
else:
    print("⚠️ Footer: pattern not found")

if modified:
    path.write_text(text, encoding="utf-8")
    print("\n✅ File saved!")
else:
    print("\n⚠️ No changes were made")
