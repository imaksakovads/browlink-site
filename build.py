#!/usr/bin/env python3
"""
Статический сборщик блога OSTIN KOSMO.
Конвертирует Markdown-статьи → SEO-оптимизированные HTML-страницы
в стиле основного сайта (Tailwind CDN + Oswald/Manrope + монохром).

Запуск:
    python3 build.py                           # собрать все статьи
    python3 build.py --check                   # только проверка статей
    python3 build.py --deploy                  # сборка + копирование на сайт
    python3 build.py --new "Заголовок"          # создать новую статью
    python3 build.py --import "$(pbpaste)"     # импорт из буфера обмена (Gemini)
    python3 build.py --watch                   # следить за изменениями (dev)

Требования:
    pip install markdown

Структура статьи (content/*.md):
    ---
    title: "Ламинирование бровей: полный гид 2025"
    description: "Мета-описание 140-160 символов с ключами"
    date: 2025-06-29
    author: Kate Ostin
    category: brow-lamination
    tags: ламинирование, брови, уход, кератин
    image: https://i.postimg.cc/xxx/cover.jpg
    image_alt: Ламинирование бровей до и после
    ---
    ## Контент статьи в Markdown...
"""

import re
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from html import escape


# ═══════════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════════

ROOT = Path(__file__).resolve().parent
CONTENT_DIR = ROOT / "content"
TEMPLATES_DIR = ROOT / "templates"
OUTPUT_DIR = ROOT / "output"

SITE_URL = "https://ostinkosmo.ru"
BLOG_URL = f"{SITE_URL}/blog"
SITE_NAME = "OSTIN KOSMO"

# Humanizer API (должен быть запущен на порту 8000)
HUMANIZER_API_URL = "http://localhost:8000/humanize"
AUTHOR_DEFAULT = "Kate Ostin"
AUTHOR_TELEGRAM = "https://t.me/KateOstin666"
AUTHOR_DESCRIPTION = (
    "Основатель студии OSTIN KOSMO. "
    "Специалист по ламинированию ресниц и архитектуре бровей. "
    "Более 1000 довольных клиентов с 2021 года."
)

# Средняя скорость чтения русского текста (слов/мин)
READING_SPEED_WPM = 180

# Расширения Markdown
MD_EXTENSIONS = [
    "markdown.extensions.toc",
    "markdown.extensions.codehilite",
    "markdown.extensions.fenced_code",
    "markdown.extensions.tables",
    "markdown.extensions.attr_list",
    "markdown.extensions.smarty",
]
MD_EXTENSION_CONFIGS = {
    "markdown.extensions.toc": {
        "permalink": False,
        "baselevel": 2,
        "title": "Содержание",
    },
}


# ═══════════════════════════════════════════════════════════════════
# ИНСТРУМЕНТЫ
# ═══════════════════════════════════════════════════════════════════

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """
    Разбирает YAML-подобный frontmatter из начала файла.

    Возвращает (метаданные: dict, тело_статьи: str).
    """
    if not text.startswith("---\n"):
        return {}, text

    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return {}, text

    meta = {}
    raw_meta = parts[1].strip()

    for line in raw_meta.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ": " in line:
            key, _, value = line.partition(": ")
            value = value.strip().strip('"').strip("'")
            meta[key.strip()] = value
        elif ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip('"').strip("'")

    body = parts[2].strip()
    return meta, body


# Допустимые поля frontmatter (для детекта опечаток)
_KNOWN_META_FIELDS: frozenset[str] = frozenset({
    "title", "description", "date", "author", "category",
    "tags", "image", "image_alt", "slug",
})


def validate_frontmatter(meta: dict, filename: str = "") -> list[str]:
    """
    Проверяет метаданные статьи на соответствие SEO-правилам.

    Возвращает список строк-предупреждений (пустой если всё ок).
    """
    warnings: list[str] = []
    prefix = f"  [{filename}] " if filename else ""

    # title обязателен
    if not meta.get("title", "").strip():
        warnings.append(f"{prefix}title пуст или отсутствует")
        return warnings

    title = meta["title"].strip()

    # description: обязательно, 100-160 символов
    desc = meta.get("description", "").strip()
    if not desc:
        warnings.append(f"{prefix}description отсутствует (нужно 100-160 символов)")
    elif len(desc) < 100:
        warnings.append(
            f"{prefix}description: {len(desc)} символов (минимум 100)"
        )
    elif len(desc) > 160:
        warnings.append(
            f"{prefix}description: {len(desc)} символов (максимум 160)"
        )

    # date: валидный ISO-формат YYYY-MM-DD
    date_str = meta.get("date", "").strip()
    if not date_str:
        warnings.append(f"{prefix}date отсутствует (нужен формат YYYY-MM-DD)")
    else:
        try:
            datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            warnings.append(
                f"{prefix}date «{date_str}» не в формате YYYY-MM-DD"
            )

    # Неизвестные поля (вероятная опечатка)
    for key in meta:
        if key.startswith("_"):
            continue
        if key not in _KNOWN_META_FIELDS:
            suggestions = [
                f for f in _KNOWN_META_FIELDS
                if len(f) == len(key) and sum(1 for a, b in zip(f, key) if a != b) <= 2
            ]
            hint = f" → возможно «{suggestions[0]}»" if suggestions else ""
            warnings.append(f"{prefix}неизвестное поле «{key}»{hint}")

    # slug: если задан вручную — проверить отсутствие кириллицы и пробелов
    manual_slug = meta.get("slug", "").strip()
    if manual_slug:
        if any(ord("а") <= ord(ch) <= ord("я") or ch == "ё" for ch in manual_slug.lower()):
            warnings.append(f"{prefix}slug содержит кириллицу «{manual_slug}»")
        if " " in manual_slug:
            warnings.append(f"{prefix}slug содержит пробелы «{manual_slug}»")

    return warnings


_TRANSLIT_TABLE = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e",
    "ё": "yo", "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k",
    "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "",
    "э": "e", "ю": "yu", "я": "ya",
}

# Стоп-слова, которые отбрасываются при генерации слага
_STOP_WORDS: frozenset[str] = frozenset({
    "как", "о", "в", "на", "и", "или", "для", "от", "что", "это",
    "не", "по", "с", "к", "из", "за", "у", "но", "то", "так",
    "бы", "ли", "же", "до", "под", "при", "без", "над", "об",
    "про", "со", "во", "ко", "а", "он", "она", "они", "мы",
    "вы", "его", "её", "их", "всё", "еще", "уже", "только",
    "лишь", "чем", "все", "вся", "весь",
})

# Максимальная длина генерируемого слага
_SLUG_MAX_LEN = 60
# Минимальное количество значимых слов в слаге (если меньше — не фильтруем)
_SLUG_MIN_WORDS = 3

_WORD_SPLIT = re.compile(r"[^а-яёa-z0-9]+")


def _transliterate_word(word: str) -> str:
    """Транслитерирует одно слово (русский → латиница)."""
    result: list[str] = []
    for ch in word:
        if ch in _TRANSLIT_TABLE:
            tr = _TRANSLIT_TABLE[ch]
            if tr:
                result.append(tr)
        elif ch.isalnum():
            result.append(ch)
    return "".join(result)


def slugify(text: str, max_len: int = _SLUG_MAX_LEN) -> str:
    """
    Генерирует URL-safe slug из заголовка.

    Алгоритм:
    1. Разбить заголовок на слова, отбросить стоп-слова.
    2. Если значимых слов < _SLUG_MIN_WORDS — использовать все слова.
    3. Транслитерировать каждое слово.
    4. Брать слова по одному, пока суммарная длина ≤ max_len.
    5. Склеить дефисами, почистить повторы.
    """
    text = text.lower().strip()
    words = [w for w in _WORD_SPLIT.split(text) if w]

    # Отбрасываем стоп-слова
    significant = [w for w in words if w not in _STOP_WORDS]

    # Если значимых слов слишком мало — используем все слова
    if len(significant) < _SLUG_MIN_WORDS:
        significant = words

    # Транслитерация
    latin_words = [_transliterate_word(w) for w in significant]
    latin_words = [w for w in latin_words if w]  # убрать пустые (только стоп-символы)

    if not latin_words:
        # Совсем ничего не осталось — fallback на первый символ
        return slugify(text, max_len) if text else "post"

    # Набираем слова, пока влезаем в max_len
    chosen: list[str] = []
    length = 0
    for w in latin_words:
        added = len(chosen)  # дефисы между словами
        if length + added + len(w) > max_len:
            break
        chosen.append(w)
        length += len(w)

    # Минимум одно слово
    if not chosen:
        chosen = [latin_words[0][:max_len]]

    slug = "-".join(chosen)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def calc_reading_time(text: str) -> int:
    """Время чтения в минутах (русский текст: ~180 слов/мин)."""
    words = len(text.split())
    return max(1, round(words / READING_SPEED_WPM))


def format_date(date_str: str, fmt: str = "%d.%m.%Y") -> str:
    """Форматирует дату в читаемый русский формат."""
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime(fmt)
    except (ValueError, TypeError):
        return date_str


def to_iso_date(date_str: str) -> str:
    """Возвращает ISO-дату для JSON-LD."""
    try:
        return datetime.fromisoformat(date_str).isoformat()
    except (ValueError, TypeError):
        return date_str


# ═══════════════════════════════════════════════════════════════════
# ШАБЛОНИЗАТОР
# ═══════════════════════════════════════════════════════════════════

def load_template(name: str) -> str:
    """Загружает HTML-шаблон."""
    path = TEMPLATES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Шаблон не найден: {path}")
    return path.read_text(encoding="utf-8")


def render(template: str, **kwargs) -> str:
    """Простая замена {{переменных}} в шаблоне."""
    result = template
    for key, value in kwargs.items():
        placeholder = "{{" + key + "}}"
        result = result.replace(placeholder, str(value) if value is not None else "")
    return result


# ═══════════════════════════════════════════════════════════════════
# ОГЛАВЛЕНИЕ (Table of Contents)
# ═══════════════════════════════════════════════════════════════════

_H_PATTERN = re.compile(
    r'<h([23])\s+id="([^"]+)"[^>]*>(.*?)</h[23]>',
    re.IGNORECASE,
)
_TAG_STRIP = re.compile(r"<[^>]+>")


def extract_headings(html: str) -> list[dict]:
    """
    Извлекает h2/h3 из HTML для построения оглавления.

    Возвращает: [{"level": 2, "id": "...", "text": "..."}, ...]
    """
    headings: list[dict] = []
    for match in _H_PATTERN.finditer(html):
        level = int(match.group(1))
        hid = match.group(2)
        text = _TAG_STRIP.sub("", match.group(3)).strip()
        headings.append({"level": level, "id": hid, "text": text})
    return headings


def build_toc_html(headings: list[dict]) -> str:
    """Строит HTML-навигацию оглавления."""
    if not headings:
        return ""

    lines = [
        '<nav class="toc mb-12 p-6 border border-gray-200 bg-gray-50/50" '
        'aria-label="Содержание статьи">',
        '<h2 class="font-display text-sm uppercase tracking-widest mb-4">'
        'Содержание</h2>',
        '<ul class="space-y-2 text-sm">',
    ]
    for h in headings:
        indent = "ml-4" if h["level"] == 3 else ""
        lines.append(
            f'<li class="{indent}">'
            f'<a href="#{h["id"]}" class="text-gray-600 hover:text-black transition">'
            f'{h["text"]}'
            f'</a></li>'
        )
    lines.append("</ul></nav>")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# JSON-LD ГЕНЕРАТОРЫ
# ═══════════════════════════════════════════════════════════════════

def build_jsonld_article(meta: dict, url: str) -> str:
    """JSON-LD типа BlogPosting для страницы статьи."""
    ld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": meta.get("title", ""),
        "description": meta.get("description", ""),
        "image": meta.get("image", ""),
        "datePublished": to_iso_date(meta.get("date", "")),
        "dateModified": to_iso_date(meta.get("date", "")),
        "author": {
            "@type": "Person",
            "name": meta.get("author", AUTHOR_DEFAULT),
            "url": AUTHOR_TELEGRAM,
        },
        "publisher": {
            "@type": "Organization",
            "name": SITE_NAME,
            "url": SITE_URL,
            "logo": {
                "@type": "ImageObject",
                "url": f"{SITE_URL}/apple-touch-icon.png",
            },
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": url,
        },
    }
    return json.dumps(ld, ensure_ascii=False, indent=2)


def build_jsonld_breadcrumbs(meta: dict, url: str) -> str:
    """JSON-LD BreadcrumbList."""
    ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Главная",
                "item": SITE_URL,
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": "Блог",
                "item": BLOG_URL,
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": meta.get("title", ""),
                "item": url,
            },
        ],
    }
    return json.dumps(ld, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════════════
# СБОРКА СТРАНИЦ
# ═══════════════════════════════════════════════════════════════════

# Паттерн для детекта H1 в теле статьи (# Заголовок, но не ##)
_H1_IN_BODY = re.compile(r"^# [^#]", re.MULTILINE)
# Паттерн для детекта пустых заголовков (## без текста)
_EMPTY_HEADING = re.compile(r"^#{2,6}\s*$", re.MULTILINE)
# Все заголовки в теле (h2-h6)
_ALL_HEADINGS = re.compile(r"^(#{2,6})\s+(.+)", re.MULTILINE)


def preprocess_markdown(body_md: str) -> tuple[str, list[str]]:
    """
    Автоисправление и валидация Markdown перед конвертацией в HTML.

    Автоисправления:
      - H1 (# Заголовок) в теле → H2 (## Заголовок)

    Предупреждения:
      - Пустые заголовки (## без текста)
      - Пропуск уровня (напр. h2 → h4 без h3)
      - Слишком глубокие заголовки (h5/h6)

    Возвращает: (исправленный_markdown, список_предупреждений)
    """
    warnings: list[str] = []

    # --- Автоисправление: H1 → H2 ---
    h1_matches = _H1_IN_BODY.findall(body_md)
    if h1_matches:
        body_md = _H1_IN_BODY.sub(lambda m: "##" + m.group(0)[1:], body_md)
        # Найдём номера строк с H1
        lines = body_md.split("\n")
        for i, line in enumerate(lines, 1):
            if re.match(r"^## [^#]", line) and "автоисправлен" not in str(warnings):
                pass
        # Считаем количество исправленных H1 по всем совпадениям
        warnings.append(
            f"H1 в теле статьи → автоисправлен на H2 "
            f"({len(h1_matches)} шт.)"
        )

    # --- Предупреждение: пустые заголовки ---
    empty = _EMPTY_HEADING.findall(body_md)
    if empty:
        warnings.append(
            f"пустые заголовки в теле ({len(empty)} шт.)"
        )

    # --- Предупреждение: пропуск уровня и глубокие заголовки ---
    heading_levels = []
    for line_num, match in enumerate(_ALL_HEADINGS.finditer(body_md), 1):
        level = len(match.group(1))
        text = match.group(2).strip()
        heading_levels.append((level, text))

    for i in range(1, len(heading_levels)):
        prev_level, _ = heading_levels[i - 1]
        curr_level, curr_text = heading_levels[i]
        if curr_level > prev_level + 1:
            warnings.append(
                f"пропуск уровня: h{prev_level} → h{curr_level} "
                f"(«{curr_text[:40]}…»)" if len(curr_text) > 40 else
                f"пропуск уровня: h{prev_level} → h{curr_level} «{curr_text}»"
            )

    # Глубокие заголовки
    deep = [lvl for lvl, _ in heading_levels if lvl >= 5]
    if deep:
        warnings.append(
            f"слишком глубокие заголовки h5/h6 ({len(deep)} шт.) — "
            f"редко нужны в блоге"
        )

    return body_md, warnings


def build_post(meta: dict, body_md: str, template: str) -> str:
    """
    Собирает финальную HTML-страницу статьи.

    Аргументы:
        meta     — метаданные из frontmatter
        body_md  — тело статьи в Markdown
        template — HTML-шаблон страницы статьи

    Возвращает:
        Готовый HTML-документ.
    """
    from markdown import markdown as md_convert

    slug = meta.get("slug") or slugify(meta["title"])
    url = f"{BLOG_URL}/{slug}.html"

    # Нормализация относительных URL изображений → абсолютные
    image = meta.get("image", "")
    if image and image.startswith("/"):
        image = SITE_URL + image
        meta = {**meta, "image": image}  # для build_jsonld_article и build_index

    # Препроцессинг Markdown (автоисправления + предупреждения)
    body_md, md_warnings = preprocess_markdown(body_md)
    if md_warnings:
        existing = meta.setdefault("_warnings", [])
        existing.extend(md_warnings)

    # Markdown → HTML
    body_html = md_convert(
        body_md,
        extensions=MD_EXTENSIONS,
        extension_configs=MD_EXTENSION_CONFIGS,
    )

    # Оглавление
    toc_html = build_toc_html(extract_headings(body_html))

    # Время чтения
    read_min = calc_reading_time(body_md)

    # Дата
    date_fmt = format_date(meta.get("date", ""))
    date_iso = to_iso_date(meta.get("date", ""))

    # Теги
    tags_raw = meta.get("tags", "")
    tag_list = [t.strip() for t in tags_raw.split(",") if t.strip()]
    tags_html = "".join(
        f'<a href="{BLOG_URL}/?tag={slugify(t)}" '
        f'class="text-xs border border-gray-300 px-3 py-1 rounded-full '
        f'hover:bg-black hover:text-white transition">{escape(t)}</a>'
        for t in tag_list
    )

    # JSON-LD
    jsonld_article = build_jsonld_article(meta, url)
    jsonld_bc = build_jsonld_breadcrumbs(meta, url)

    return render(
        template,
        # SEO
        title=escape(meta.get("title", "")),
        description=escape(meta.get("description", "")),
        canonical=url,
        og_image=meta.get("image", ""),
        og_image_alt=meta.get("image_alt", meta.get("title", "")),
        jsonld_article=jsonld_article,
        jsonld_breadcrumbs=jsonld_bc,
        # Контент
        article_date=date_fmt,
        article_date_iso=date_iso,
        article_author=meta.get("author", AUTHOR_DEFAULT),
        article_category=meta.get("category", ""),
        article_tags_html=tags_html,
        article_tags_raw=tags_raw,
        article_read_time=str(read_min),
        article_toc=toc_html,
        article_body=body_html,
        # Фиксированные
        site_url=SITE_URL,
        blog_url=BLOG_URL,
        site_name=SITE_NAME,
        author_description=AUTHOR_DESCRIPTION,
        author_telegram=AUTHOR_TELEGRAM,
        copyright_year=str(datetime.now().year),
    )


def build_index(posts: list[dict], template: str) -> str:
    """
    Собирает главную страницу блога — сетка карточек статей.

    Аргументы:
        posts    — список метаданных, отсортированный по дате (новые сверху)
        template — HTML-шаблон индексной страницы

    Возвращает:
        Готовый HTML-документ.
    """
    jsonld_blog = json.dumps({
        "@context": "https://schema.org",
        "@type": "Blog",
        "name": f"Блог {SITE_NAME}",
        "url": BLOG_URL,
        "description": "Блог о ламинировании ресниц и бровей, уходе и бьюти-трендах",
        "publisher": {
            "@type": "Organization",
            "name": SITE_NAME,
            "url": SITE_URL,
        },
    }, ensure_ascii=False, indent=2)

    cards: list[str] = []
    for meta in posts:
        slug = meta.get("slug") or slugify(meta["title"])
        url = f"{BLOG_URL}/{slug}.html"

        # Нормализация относительных URL изображений
        img_url = meta.get("image", "")
        if img_url.startswith("/"):
            img_url = SITE_URL + img_url
        date_fmt = format_date(meta.get("date", ""))
        date_iso = to_iso_date(meta.get("date", ""))
        read_min = calc_reading_time(meta.get("_body", ""))
        tags_list = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]
        tags_line = " · ".join(escape(t) for t in tags_list[:3]) if tags_list else ""

        card = f"""<article class="border border-gray-200 group hover:border-black transition duration-300 flex flex-col">
    <div class="h-56 overflow-hidden border-b border-gray-200">
        <img src="{img_url}" alt="{escape(meta.get('image_alt', meta.get('title', '')))}" class="w-full h-full object-cover group-hover:scale-105 transition duration-700" width="800" height="448" loading="lazy">
    </div>
    <div class="p-6 flex flex-col flex-1">
        <div class="flex items-center gap-3 mb-3">
            <time datetime="{date_iso}" class="font-mono text-xs text-gray-400">{date_fmt}</time>
            <span class="text-gray-300">·</span>
            <span class="font-mono text-xs text-gray-400">{read_min} мин чтения</span>
        </div>
        <h2 class="font-display text-xl uppercase mb-3 leading-tight">
            <a href="{url}" class="hover:text-gray-500 transition">{escape(meta.get('title', ''))}</a>
        </h2>
        <p class="text-gray-600 text-sm leading-relaxed mb-4 flex-1">{escape(meta.get('description', ''))}</p>
        <div class="font-mono text-xs text-gray-400">{tags_line}</div>
    </div>
</article>"""
        cards.append(card.strip())

    return render(
        template,
        title=f"Блог {SITE_NAME} — о ламинировании бровей и ресниц",
        description="Профессиональный блог о ламинировании бровей и ресниц, уходе, трендах и бьюти-советах от мастеров студии OSTIN KOSMO.",
        canonical=BLOG_URL,
        og_image="",
        og_image_alt="Блог OSTIN KOSMO",
        jsonld_article=jsonld_blog,
        jsonld_breadcrumbs="",
        jsonld_blog=jsonld_blog,
        article_cards="\n".join(cards) if cards else "",
        article_count=str(len(posts)),
        site_url=SITE_URL,
        blog_url=BLOG_URL,
        site_name=SITE_NAME,
        author_telegram=AUTHOR_TELEGRAM,
        copyright_year=str(datetime.now().year),
    )


# ═══════════════════════════════════════════════════════════════════
# ОСНОВНОЙ ЦИКЛ СБОРКИ
# ═══════════════════════════════════════════════════════════════════

def load_articles() -> list[tuple[dict, str]]:
    """
    Загружает все статьи из content/.
    Возвращает список (метаданные, markdown-тело), отсортированный по дате (новые сверху).
    """
    if not CONTENT_DIR.exists():
        CONTENT_DIR.mkdir(parents=True)
        print(f"📁 Создана папка {CONTENT_DIR}")
        return []

    articles: list[tuple[dict, str]] = []
    for md_file in sorted(CONTENT_DIR.glob("*.md"), reverse=True):
        text = md_file.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)

        if not meta.get("title"):
            print(f"⚠️  Пропущен {md_file.name}: нет title в frontmatter")
            continue

        if not meta.get("slug"):
            meta["slug"] = slugify(meta["title"])

        # Валидация frontmatter
        warnings = validate_frontmatter(meta, md_file.name)
        meta["_body"] = body
        meta["_source_file"] = md_file  # путь к исходному .md для инкрементальной сборки
        meta["_warnings"] = warnings
        articles.append((meta, body))

    articles.sort(key=lambda x: x[0].get("date", ""), reverse=True)
    return articles


def build_all(incremental: bool = False):
    """Главный метод сборки.

    Аргументы:
        incremental — если True: не очищает output, собирает только
                      новые/изменённые .md статьи, пересобирает index.
    """
    # Проверяем зависимость
    try:
        import markdown  # noqa: F401
    except ImportError:
        print("❌ Нужен markdown: pip install markdown")
        return

    print("🔨 OSTIN KOSMO Blog Builder\n")

    if incremental:
        print("⚡ Инкрементальный режим\n")
    else:
        print("🔄 Полная пересборка\n")

    # Шаблоны
    post_tpl = load_template("blog-post.html")
    index_tpl = load_template("blog-index.html")
    print("📄 Шаблоны загружены")

    # Статьи
    articles = load_articles()
    if not articles:
        print("\n⚠️  Нет статей в content/.\n")
        return

    print(f"📚 Статей: {len(articles)}")

    # Очистка output/
    if incremental:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Копирование только новой статики (не перезаписываем существующее)
        static_dir = ROOT / "static"
        if static_dir.exists():
            new_files = 0
            for f in static_dir.rglob("*"):
                if f.is_file():
                    relative = f.relative_to(static_dir)
                    dst = OUTPUT_DIR / relative
                    if dst.exists():
                        continue
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dst)
                    new_files += 1
            if new_files:
                print(f"📦 {new_files} новых файлов статики")
    else:
        if OUTPUT_DIR.exists():
            shutil.rmtree(OUTPUT_DIR)
        OUTPUT_DIR.mkdir(parents=True)

        # Копирование статики (только при полной пересборке)
        static_dir = ROOT / "static"
        if static_dir.exists():
            for f in static_dir.rglob("*"):
                if f.is_file():
                    relative = f.relative_to(static_dir)
                    dst = OUTPUT_DIR / relative
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dst)
            print(f"📦 Статика скопирована из {static_dir.name}/")

    # Сборка каждой статьи
    total_warnings = 0
    built_count = 0
    skipped_count = 0
    for meta, body in articles:
        slug = meta["slug"]
        output_path = OUTPUT_DIR / f"{slug}.html"
        short_title = meta['title'][:60]

        # Инкрементальная проверка: билдим только если .md новее .html
        if incremental and output_path.exists():
            src_md = meta.get("_source_file")
            if src_md and src_md.exists() and src_md.stat().st_mtime <= output_path.stat().st_mtime:
                print(f"  ➖ {slug}.html — без изменений")
                skipped_count += 1
                continue

        html = build_post(meta, body, post_tpl)
        output_path.write_text(html, encoding="utf-8")
        print(f"  ✅ {slug}.html — «{short_title}»")
        built_count += 1

        # Вывод предупреждений для этой статьи
        post_warnings = meta.get("_warnings", [])
        for w in post_warnings:
            print(f"     ⚠️  {w}")
        total_warnings += len(post_warnings)

    # Сборка индекса (всегда)
    posts_meta = [m for m, _ in articles]
    index_html = build_index(posts_meta, index_tpl)
    (OUTPUT_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print(f"  ✅ index.html — главная блога")

    # Итоговая сводка
    summary_parts = []
    if incremental:
        summary_parts.append(f"⚡ {built_count} новых, {skipped_count} пропущено")
    if total_warnings > 0:
        summary_parts.append(f"⚠️  {total_warnings} предупреждений")
    summary_parts.append("сборка завершена успешно")
    print(f"\n{' — '.join(summary_parts)}")
    print(f"   Файлы в {OUTPUT_DIR}/")


# ═══════════════════════════════════════════════════════════════════
# СОЗДАНИЕ НОВЫХ СТАТЕЙ
# ═══════════════════════════════════════════════════════════════════

_TEMPLATE_PATH = CONTENT_DIR / ".template.md"

# Максимальная длина заголовка для --import (длиннее = абзац, не заголовок)
_TITLE_MAX_LEN = 100

# Паттерны для --import: детект заголовка и начала текста
_TITLE_CANDIDATE = re.compile(
    r"^(?:\*\*)?([А-ЯЁA-Z].{10,120})(?:\*\*)?$", re.MULTILINE
)
_FRONTMATTER_LINE = re.compile(r"^(\w[\w\s]*?):\s*(.+)$")


def _build_template(title: str, description: str, tags: str = "") -> str:
    """Создаёт содержимое .md файла из шаблона."""
    if _TEMPLATE_PATH.exists():
        tpl = _TEMPLATE_PATH.read_text(encoding="utf-8")
    else:
        tpl = DEFAULT_TEMPLATE

    today = datetime.now().strftime("%Y-%m-%d")
    image_alt = title

    return (
        tpl.replace("{{TITLE}}", title)
        .replace("{{DESCRIPTION}}", description)
        .replace("{{DATE}}", today)
        .replace("{{TAGS}}", tags)
        .replace("{{IMAGE_ALT}}", image_alt)
        .replace("{{BODY}}", "")
    )


# Дефолтный шаблон (если .template.md отсутствует)
DEFAULT_TEMPLATE = """---
title: "{{TITLE}}"
description: "{{DESCRIPTION}}"
date: {{DATE}}
author: Kate Ostin
category: brow-lamination
tags: {{TAGS}}
image: https://i.postimg.cc/QtDtLm6Y/photo-2025-08-09-17-37-33.jpg
image_alt: {{IMAGE_ALT}}
---

{{BODY}}
"""


def create_article(title: str, description: str = "", tags: str = "") -> Path:
    """
    Создаёт новый .md файл статьи с готовым frontmatter.

    Аргументы:
        title       — заголовок статьи
        description — SEO-описание (если пусто — заглушка)
        tags        — теги через запятую

    Возвращает:
        Path к созданному файлу.
    """
    slug = slugify(title)
    filename = f"{slug}.md"
    filepath = CONTENT_DIR / filename

    if filepath.exists():
        raise FileExistsError(f"Файл уже существует: {filepath}")

    if not description:
        description = title  # временная заглушка, --check предупредит
    if not tags:
        tags = "брови, уход, OSTIN KOSMO"

    content = _build_template(title, description, tags)
    filepath.write_text(content, encoding="utf-8")

    print(f"\n📝 Статья создана: {filepath}")
    print(f"   Slug: {slug}")
    print(f"   Дата: сегодня")
    print(f"   Теги: {tags}")
    print(f"\n   Дальше:")
    print(f"   1. Открой GEMINI_PROMPT.md → скопируй в Gemini")
    print(f"   2. Замени [ВСТАВЬ ТЕМУ ЗДЕСЬ] на «{title}»")
    print(f"   3. Скопируй результат Gemini → вставь в {filename} после frontmatter")
    print(f"   4. python3 build.py --check")
    print(f"   5. python3 build.py --deploy\n")
    return filepath


def import_article(raw_text: str, tags: str = "") -> Path | None:
    """
    Импортирует статью из сырого текста (из Gemini / буфера обмена).

    Алгоритм:
    1. Ищет заголовок — первая строка, но НЕ длиннее 100 символов
    2. Если первая строка > 100 символов — берёт первое предложение
    3. Берёт первый содержательный абзац как основу для description
    4. Всё остальное — тело статьи
    5. Создаёт .md файл с правильным именем

    Аргументы:
        raw_text — сырой текст из Gemini
        tags     — теги через запятую (опционально)

    Возвращает:
        Path к созданному файлу, или None если не удалось извлечь заголовок.
    """
    raw_text = raw_text.strip()
    if not raw_text:
        print("❌ Пустой текст — нечего импортировать.")
        return None

    lines = raw_text.split("\n")

    # --- 1. Извлечение заголовка ---
    title = ""
    body_start = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        # Пропускаем явные frontmatter-строки (ключ: значение)
        if _FRONTMATTER_LINE.match(stripped):
            continue
        # Убираем Markdown-форматирование (**жирный**, *курсив*)
        clean = re.sub(r"[*_]{1,2}", "", stripped).strip()

        # Первая непустая строка → кандидат в заголовок
        if len(clean) >= 10:
            if len(clean) > _TITLE_MAX_LEN:
                # Слишком длинная строка — похоже на абзац, а не заголовок.
                # Берём первое предложение до точки/вопроса/воскл.
                sentence_match = re.match(
                    r"^([^.!?]+[.!?])", clean
                )
                if sentence_match:
                    title = sentence_match.group(1).strip()
                    if len(title) < 10:
                        # Первое предложение слишком короткое — берём первые _TITLE_MAX_LEN симв
                        title = clean[:_TITLE_MAX_LEN].rsplit(" ", 1)[0] + "…"
                else:
                    # Нет знаков препинания — обрезаем до _TITLE_MAX_LEN по пробелу
                    title = clean[:_TITLE_MAX_LEN].rsplit(" ", 1)[0] + "…"
                print(f"   ⚠️  Заголовок обрезан до {len(title)} символов (было {len(clean)}).")
                print(f"   Если не устраивает — поправь вручную в .md файле.")
                # Тело начинается с этой же строки (обрезанной части)
                body_start = i  # не i+1 — обработаем эту строку как тело
            else:
                title = clean
                body_start = i + 1
            break

    if not title:
        print("❌ Не удалось найти заголовок в тексте.")
        print("   Заголовок должен быть первой строкой (минимум 10 символов).")
        return None

    print(f"   Заголовок: «{title}»")

    # --- 2. Генерация description из первого абзаца ---
    description = ""
    body_lines: list[str] = []

    # Если заголовок был обрезан из длинной строки — добавляем остаток этой строки в тело
    if body_start == 0:
        # Заголовок из первой строки, тело со второй
        pass

    for i in range(body_start, len(lines)):
        stripped = lines[i].strip()
        # Пропускаем разделители и пустые строки в поиске первого абзаца
        if not stripped or stripped in ("---", "***", "___", "—"):
            if body_lines:
                continue
            else:
                body_lines.append("")
                continue
        # Убираем **жирный** из строки, но сохраняем текст
        clean_line = re.sub(r"[*_]{1,2}", "", stripped).strip()
        # Пропускаем строки, похожие на мета-данные
        if _FRONTMATTER_LINE.match(clean_line):
            continue
        # Если это та же строка, из которой взяли заголовок — берём остаток после заголовка
        if i == body_start and title in clean_line:
            after_title = clean_line[clean_line.find(title) + len(title):].strip()
            if after_title:
                body_lines.append(after_title)
            continue
        body_lines.append(clean_line)

    # Ищем первый содержательный абзац для description
    paragraph_parts: list[str] = []
    for line in body_lines:
        if not line:
            if paragraph_parts:
                break
            continue
        paragraph_parts.append(line)

    if paragraph_parts:
        raw_desc = " ".join(paragraph_parts)
        # Чистим Markdown
        raw_desc = re.sub(r"[*_#>\[\]()]+", "", raw_desc).strip()
        description = raw_desc[:157] + ("..." if len(raw_desc) > 157 else "")
        print(f"   Description: {len(description)} символов")

    if not description:
        description = title
        print(f"   Description: заглушка (не удалось извлечь из текста)")

    # --- 3. Тело статьи ---
    body = "\n".join(body_lines).strip()

    # --- 4. Создание файла ---
    slug = slugify(title)
    filename = f"{slug}.md"
    filepath = CONTENT_DIR / filename

    if filepath.exists():
        # Не перезаписываем — добавляем суффикс
        import time
        ts = int(time.time()) % 100000
        filename = f"{slug}-{ts}.md"
        filepath = CONTENT_DIR / filename

    content = _build_template(title, description, tags)
    # Вставляем тело статьи
    content = content.replace("{{BODY}}", body)

    filepath.write_text(content, encoding="utf-8")

    print(f"\n📝 Статья импортирована: {filepath}")
    print(f"   Slug: {slug}")
    print(f"   Проверь: python3 build.py --check")
    print(f"   Собери: python3 build.py --deploy\n")
    return filepath


# ═══════════════════════════════════════════════════════════════════
# Генерация статьи через Humanizer
# ═══════════════════════════════════════════════════════════════════

def generate_article(title: str, tags: str = "") -> Path:
    """
    Генерирует статью через Humanizer API и сохраняет как .md.

    Пайплайн:
      1. create_article() — создаёт .md с frontmatter
      2. Отправляет промпт в Humanizer (порт 8000)
      3. Humanizer применяет 16 фильтров (запрет тире, риторич. вопросов,
         списков, сбитый ритм, асимметричные абзацы и т.д.)
      4. Обновляет description и вставляет тело статьи

    Аргументы:
        title — заголовок/тема статьи
        tags  — теги через запятую

    Возвращает:
        Path к созданному файлу.
    """
    # Шаг 1: создаём файл с frontmatter
    filepath = create_article(title, tags=tags)
    print(f"   Шаг 1: файл создан")

    # Шаг 2: формируем промпт для генерации статьи
    prompt = (
        f"Напиши статью для бьюти-блога на тему: {title}. "
        f"Это информационная статья для девушек 25-45 лет, "
        f"которые интересуются бьюти-услугами.\n\n"
        f"Структура:\n"
        f"- Лид-абзац без заголовка (сразу с новой строки)\n"
        f"- Разделы с заголовками ## H2\n"
        f"- В конце естественное завершение, без рекламы\n\n"
        f"Формат: чистый Markdown, без frontmatter (он уже есть), "
        f"без H1, короткие абзацы по 2-4 предложения, "
        f"прямая польза для читателя."
    )

    # Шаг 3: вызываем Humanizer
    print(f"   Шаг 2: отправляю в Humanizer...")
    print(f"   Humanizer применяет 16 фильтров: детокс AI-клише, "
          f"запрет тире/списков/риторич.вопросов, сбитый ритм...")

    import httpx
    try:
        with httpx.Client(timeout=120) as client:
            resp = client.post(
                HUMANIZER_API_URL,
                json={"content": prompt, "max_tokens": 4096},
            )
        if not resp.is_success:
            print(f"\n❌ Humanizer API ошибка {resp.status_code}: {resp.text[:300]}")
            print(f"   Запусти сервер: uvicorn api:app --port 8000")
            print(f"   Или вставь текст вручную из Gemini в {filepath.name}")
            return filepath
        data = resp.json()
        article_body = data.get("text", "")
        duration = data.get("duration_ms", 0)
        if not article_body or article_body.startswith("[Ошибка"):
            print(f"\n❌ Humanizer вернул ошибку: {article_body[:200]}")
            return filepath
        print(f"   ✅ Humanizer ответил за {duration/1000:.1f}с "
              f"({len(article_body)} симв)")
    except httpx.ConnectError:
        print(f"\n❌ Не удалось подключиться к Humanizer (порт 8000)")
        print(f"   Запусти: cd text/ && uvicorn api:app --port 8000")
        print(f"   Или вставь текст вручную из Gemini в {filepath.name}")
        return filepath

    # Шаг 4: description оставляем заглушкой — финальный редактируется вручную
    description = title

    # Шаг 5: собираем финальный .md
    # Читаем файл, созданный create_article, и вставляем тело после frontmatter
    raw = filepath.read_text(encoding="utf-8")
    # Ищем границу frontmatter: вторая строка с ---
    parts = raw.split("---\n")
    if len(parts) >= 3:
        # parts[0] = "", parts[1] = frontmatter, parts[2] = тело (пустое)
        frontmatter = parts[1].strip()
        # Обновляем description в frontmatter
        desc_line = f'description: "{description}"'
        frontmatter = re.sub(r'description: ".*"', desc_line, frontmatter)
        # Собираем заново
        new_content = f"---\n{frontmatter}\n---\n\n{article_body.strip()}\n"
        filepath.write_text(new_content, encoding="utf-8")
    else:
        # Fallback: просто дописываем
        filepath.write_text(raw.rstrip() + "\n\n" + article_body.strip() + "\n", encoding="utf-8")

    print(f"\n📝 Статья сгенерирована: {filepath}")
    print(f"   Тема: {title}")
    print(f"   Длина: {len(article_body)} символов")
    print(f"   Humanizer: 16 фильтров применены")
    print(f"\n   Дальше:")
    print(f"   1. Открой {filepath.name} — проверь текст")
    print(f"   2. python3 build.py --check")
    print(f"   3. python3 build.py --deploy\n")
    return filepath


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════

DEPLOY_TARGET = Path("/Users/igor/brow/browlink-site-main/blog")


def check_all() -> int:
    """
    Режим проверки: валидация всех статей без сборки.
    Возвращает количество предупреждений (0 = всё идеально).
    """
    try:
        import markdown  # noqa: F401
    except ImportError:
        print("❌ Нужен markdown: pip install markdown")
        return 1

    print("🔍 OSTIN KOSMO Blog Checker\n")

    articles = load_articles()
    if not articles:
        print("⚠️  Нет статей в content/.")
        return 1

    print(f"📚 Статей: {len(articles)}\n")

    total_warnings = 0
    for meta, body in articles:
        slug = meta["slug"]
        short_title = meta['title'][:60]

        # Frontmatter warnings (уже собраны в load_articles)
        fm_warnings = meta.get("_warnings", [])

        # Markdown warnings (препроцессинг, но без сборки HTML)
        _, md_warnings = preprocess_markdown(body)

        all_w = fm_warnings + md_warnings
        total_warnings += len(all_w)

        if all_w:
            print(f"  📄 {slug}.html — «{short_title}»")
            for w in all_w:
                print(f"     ⚠️  {w}")
        else:
            print(f"  ✅ {slug}.html — «{short_title}»")

    print()
    if total_warnings > 0:
        print(f"⚠️  {total_warnings} предупреждений — проверь перед сборкой")
    else:
        print("🎉 Всё чисто! Можно собирать: python3 build.py")

    return total_warnings


def deploy_output() -> None:
    """Копирует собранные файлы из output/ на сайт."""
    if not DEPLOY_TARGET.exists():
        print(f"❌ Папка назначения не найдена: {DEPLOY_TARGET}")
        print(f"   Убедись, что основной сайт существует по этому пути.")
        return

    files = list(OUTPUT_DIR.rglob("*"))
    if not files:
        print("❌ Нет файлов в output/. Сначала запусти сборку: python3 build.py")
        return

    copied = 0
    for src in files:
        if src.is_dir():
            continue
        rel = src.relative_to(OUTPUT_DIR)
        dst = DEPLOY_TARGET / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1

    print(f"\n📦 Скопировано {copied} файлов → {DEPLOY_TARGET}/")
    print(f"   Деплой через Git: cd {DEPLOY_TARGET.parent} && git add blog/ && git commit -m 'blog: deploy' && git push")


def main():
    parser = argparse.ArgumentParser(
        description="OSTIN KOSMO Blog Builder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python3 build.py                          Собрать все статьи
  python3 build.py --check                  Только проверка (без сборки)
  python3 build.py --deploy                 Сборка + копирование на сайт
  python3 build.py --new "Мой заголовок"    Создать новую статью
  python3 build.py --import "$(pbpaste)"    Импорт из буфера обмена
  python3 build.py --generate "Тема"        Сгенерировать через Humanizer
  python3 build.py --watch                  Dev-режим
""",
    )
    parser.add_argument(
        "--incremental", action="store_true",
        help="Инкрементальная сборка: только новые/изменённые статьи + пересборка индекса",
    )
    parser.add_argument(
        "--watch", action="store_true",
        help="Следить за изменениями (dev-режим)",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Только валидация статей, без сборки",
    )
    parser.add_argument(
        "--deploy", action="store_true",
        help="Сборка + копирование output/ на сайт",
    )
    parser.add_argument(
        "--new", metavar="TITLE", type=str, default=None,
        help="Создать новую статью с указанным заголовком",
    )
    parser.add_argument(
        "--generate", metavar="TITLE", type=str, default=None,
        help="Сгенерировать статью через Humanizer (16 фильтров). Нужен сервер на порту 8000",
    )
    parser.add_argument(
        "--import", metavar="TEXT", type=str, default=None, dest="import_text",
        help="Импортировать статью из сырого текста (Gemini / буфер обмена). "
             "Используйте --import - для чтения из stdin.",
    )
    parser.add_argument(
        "--tags", type=str, default="",
        help="Теги через запятую (для --new и --import)",
    )
    args = parser.parse_args()

    # --new: создать новую статью
    if args.new:
        create_article(args.new, tags=args.tags)
        return

    # --generate: генерация через Humanizer
    if args.generate:
        generate_article(args.generate, tags=args.tags)
        return

    # --import: импорт статьи
    if args.import_text is not None:
        text = args.import_text
        if text == "-":
            # Читаем из stdin
            import sys
            text = sys.stdin.read()
        if not text.strip():
            print("❌ Пустой текст — нечего импортировать.")
            print("   Использование: python3 build.py --import \"$(pbpaste)\"")
            raise SystemExit(1)
        result = import_article(text, tags=args.tags)
        if result is None:
            raise SystemExit(1)
        return

    # --check: только валидация
    if args.check:
        exit_code = check_all()
        raise SystemExit(exit_code)

    # --watch: dev-режим
    if args.watch:
        print("👀 Watch-режим активирован\n")
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class RebuildHandler(FileSystemEventHandler):
                def on_any_event(self, event):
                    if event.src_path.endswith((".md", ".html")):
                        print(f"\n🔄 Изменения: {Path(event.src_path).name}")
                        try:
                            build_all()
                        except Exception as e:
                            print(f"❌ Ошибка: {e}")

            observer = Observer()
            observer.schedule(RebuildHandler(), str(CONTENT_DIR), recursive=True)
            observer.schedule(RebuildHandler(), str(TEMPLATES_DIR), recursive=True)
            observer.start()

            build_all(incremental=args.incremental)

            try:
                import time
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
                print("\n👋 Готово.")
            observer.join()
            return
        except ImportError:
            print("⚠️  Для --watch нужен watchdog: pip install watchdog")
            build_all()
            return

    # Обычная сборка
    build_all(incremental=args.incremental)

    # --deploy: сборка + копирование
    if args.deploy:
        deploy_output()


if __name__ == "__main__":
    main()
