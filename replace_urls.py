"""
Замена внешних URL изображений на локальные /images/*.webp во всех HTML.
"""
from pathlib import Path

SITE_ROOT = Path(__file__).parent

REPLACEMENTS = {
    # i.ibb.co — статьи блога
    "https://i.ibb.co/JWknsnnC/1274ccc8-6aee-431c-8f76-aa8f9c182a41.jpg": "/images/blog-lam-resnits.webp",
    "https://i.ibb.co/7d1VPP2f/image.jpg": "/images/blog-lam-brovey.webp",
    "https://i.ibb.co/fzdjy7xp/image.png": "/images/blog-simmetriya.webp",
    "https://i.ibb.co/Zpzy266W/11.jpg": "/images/blog-harakter-brovi.webp",
    "https://i.ibb.co/mrSRvgmB/image.jpg": "/images/blog-lomkie-brovi.webp",
    "https://i.ibb.co/35K8F7jb/2.jpg": "/images/blog-nauka-simmetriya.webp",
    "https://i.ibb.co/27QQgs5Q/12.jpg": "/images/blog-okruzh-char.webp",
    "https://i.ibb.co/KYbcN2g/22.jpg": "/images/blog-brow-22.webp",
    "https://i.ibb.co/XxYDkpSg/11-1-1.png": "/images/blog-brow-11-1.webp",
    # i.postimg.cc — отзывы
    "https://i.postimg.cc/QtDtLm6Y/photo-2025-08-09-17-37-33.jpg": "/images/review-default.webp",
    "https://i.postimg.cc/6pDqctCX/photo-2025-08-09-17-25-54-2.jpg": "/images/review-1.webp",
    "https://i.postimg.cc/7Y9QSL85/photo-2024-10-04-14-40-45-1.jpg": "/images/review-2.webp",
    "https://i.postimg.cc/7ZCbSfG9/photo-2025-08-09-22-22-30.jpg": "/images/review-3.webp",
    "https://i.postimg.cc/CRZTq1J2/photo-2024-10-04-14-34-27-1.jpg": "/images/review-4.webp",
    "https://i.postimg.cc/JhYLxQfB/photo-2024-11-20-17-18-02.jpg": "/images/review-5.webp",
    # GitHub assets
    "https://github.com/user-attachments/assets/0de0f77b-700d-41c3-9251-e9a6a0fe9d74": "/images/gh-screenshot-1.webp",
    "https://github.com/user-attachments/assets/315d3a42-3672-475f-a28b-1e925947572a": "/images/gh-screenshot-2.webp",
    "https://github.com/user-attachments/assets/5841e948-e141-4bb2-b9f8-af499387237c": "/images/gh-screenshot-3.webp",
    "https://github.com/user-attachments/assets/91bc0bd2-24fa-441e-badf-5c2b33effc5b": "/images/gh-screenshot-4.webp",
    "https://github.com/user-attachments/assets/f82e6fab-e2f8-4e73-9d67-4e3d0ee3ec5f": "/images/gh-screenshot-5.webp",
}

CHANGED_FILES = 0
TOTAL_REPLACEMENTS = 0

for html_path in sorted(SITE_ROOT.rglob("*.html")):
    content = html_path.read_text(encoding="utf-8")
    new_content = content
    file_changes = 0
    for old_url, new_local in REPLACEMENTS.items():
        count = new_content.count(old_url)
        if count > 0:
            new_content = new_content.replace(old_url, new_local)
            file_changes += count

    if file_changes > 0:
        html_path.write_text(new_content, encoding="utf-8")
        rel = html_path.relative_to(SITE_ROOT)
        print(f"  ✏️  {rel}: {file_changes} замен")
        CHANGED_FILES += 1
        TOTAL_REPLACEMENTS += file_changes

print(f"\n✅ Изменено файлов: {CHANGED_FILES}")
print(f"✅ Всего замен: {TOTAL_REPLACEMENTS}")
