"""Check indexing status via Google Search Console API + Yandex Webmaster API.

Usage:
    python3 check_seo.py google      # Google Search Console (after OAuth setup)
    python3 check_seo.py yandex      # Yandex Webmaster (after OAuth setup)
    python3 check_seo.py all         # both

First run:
    python3 check_seo.py google --setup    # opens browser for OAuth
    python3 check_seo.py yandex --setup    # opens browser for OAuth
"""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

TOKEN_DIR = Path(__file__).parent / ".seo_tokens"
TOKEN_DIR.mkdir(exist_ok=True)

SITE_URL = "https://ostinkosmo.ru"
OLD_SITE = "https://www.ostinkosmo.online"


# ─── Google Search Console ───────────────────────────────────────────────

def google_setup() -> None:
    """Открывает браузер для OAuth, сохраняет токен."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("[ERROR] Установи: pip3 install google-auth-oauthlib", file=sys.stderr)
        sys.exit(1)

    creds_path = TOKEN_DIR / "google_oauth.json"
    if not creds_path.exists():
        print("[ERROR] Нужен файл OAuth 2.0 Desktop Client credentials.")
        print(f"  1. Открой https://console.cloud.google.com/")
        print("  2. Создай проект или выбери существующий")
        print("  3. API и сервисы → Библиотека → Search Console API → Включить")
        print("  4. API и сервисы → Учётные данные → Создать → OAuth client ID")
        print("     (Тип приложения: Desktop application)")
        print(f"  5. Скачай JSON → сохрани как: {creds_path}")
        print("  6. Запусти снова: python3 check_seo.py google --setup")
        sys.exit(1)

    with open(creds_path) as f:
        client_config = json.load(f)

    SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)

    token_path = TOKEN_DIR / "google_token.json"
    with open(token_path, "w") as f:
        f.write(creds.to_json())
    print(f"[OK] Токен сохранён: {token_path}")


def google_check() -> None:
    """Проверяет статус в Google Search Console."""
    token_path = TOKEN_DIR / "google_token.json"
    if not token_path.exists():
        print("[WARN] Google не настроен. Запусти: python3 check_seo.py google --setup")
        print("       Или: python3 check_seo.py google --setup")
        return

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        print("[ERROR] Установи: pip3 install google-api-python-client google-auth")
        return

    creds = Credentials.from_authorized_user_file(str(token_path))
    if creds.expired:
        creds.refresh(Request())
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    service = build("searchconsole", "v1", credentials=creds)

    print(f"\n{'=' * 50}")
    print("GOOGLE SEARCH CONSOLE")
    print(f"{'=' * 50}")

    # 1. Site list
    print("\n--- Сайты в Search Console ---")
    try:
        sites = service.sites().list().execute()
        for s in sites.get("siteEntry", []):
            status = "✅" if s.get("permissionLevel", "").startswith("site") else "❌ no access"
            print(f"  {status} {s['siteUrl']} ({s.get('permissionLevel', 'N/A')})")
    except Exception as e:
        print(f"  [ERROR] Не удалось получить список сайтов: {e}")

    # 2. Sitemap status
    print("\n--- Sitemap статус ---")
    try:
        sm = service.sitemaps().list(siteUrl=SITE_URL).execute()
        for s in sm.get("sitemap", []):
            err = s.get("errors", 0)
            submitted = s.get("contents", [{}])[0].get("submitted", 0) if s.get("contents") else 0
            status = "⚠️" if err else "✅"
            print(f"  {status} {s['path']} → {submitted} URLs, errors: {err}")
    except Exception as e:
        print(f"  [ERROR] Sitemap: {e}")

    # 3. Index coverage (last 90 days)
    print("\n--- Индекс: покрытие ---")
    try:
        req = {
            "startDate": "2026-04-14",
            "endDate": "2026-07-14",
            "dimensions": ["searchAppearance"],
        }
        data = service.searchanalytics().query(siteUrl=SITE_URL, body=req).execute()
        total_clicks = sum(r.get("clicks", 0) for r in data.get("rows", []))
        total_impressions = sum(r.get("impressions", 0) for r in data.get("rows", []))
        print(f"  Кликов (90d): {total_clicks}")
        print(f"  Показов (90d): {total_impressions}")
    except Exception as e:
        print(f"  [ERROR] Coverage: {e}")

    print()


# ─── Yandex Webmaster ────────────────────────────────────────────────────

YANDEX_AUTH_URL = "https://oauth.yandex.ru/authorize"
YANDEX_TOKEN_URL = "https://oauth.yandex.ru/token"
YANDEX_API = "https://api.webmaster.yandex.net/v4"


def yandex_setup() -> None:
    """Интерактивное получение Yandex OAuth токена."""
    token_path = TOKEN_DIR / "yandex_token.json"
    creds_path = TOKEN_DIR / "yandex_oauth.json"

    if not creds_path.exists():
        print()
        print("=" * 60)
        print("РЕГИСТРАЦИЯ ПРИЛОЖЕНИЯ В ЯНДЕКСЕ")
        print("=" * 60)
        print()
        print("  1. Открой в браузере страницу создания приложения:")
        print("     https://oauth.yandex.ru/client/new")
        print()
        print("  2. Заполни форму:")
        print("     • Название: OSTIN KOSMO Checker")
        print("     • Иконка — пропусти")
        print("     • Платформа: ВЕБ-СЕРВИСЫ")
        print("     • Redirect URI: https://oauth.yandex.ru/verification_code")
        print("     • Доступы — выбери:")
        print("       - webmaster:hostinfo")
        print("       - webmaster:verify")
        print()
        print("  3. Нажми «Создать приложение»")
        print()
        print("  4. Скопируй ClientID (идентификатор) со страницы приложения")
        print()
        client_id = input("  Вставь ClientID сюда: ").strip()
        if not client_id:
            print("  ❌ ClientID не может быть пустым")
            sys.exit(1)

        creds_path.write_text(json.dumps({"client_id": client_id}, indent=2))
        print(f"  ✅ Сохранено в {creds_path}")
    else:
        with open(creds_path) as f:
            cfg = json.load(f)
        client_id = cfg["client_id"]

    print()
    print("=" * 60)
    print("ПОЛУЧЕНИЕ ТОКЕНА")
    print("=" * 60)
    print()
    auth_url = (
        f"{YANDEX_AUTH_URL}?response_type=token"
        f"&client_id={client_id}"
    )
    print("  Перейди по ссылке и разреши доступ:")
    print(f"  {auth_url}")
    print()
    print("  После подтверждения тебя перенаправят на страницу")
    print("  с адресом вида:")
    print("  https://oauth.yandex.ru/verification_code#access_token=XXXXX")
    print()
    token = input("  Вставь access_token из URL: ").strip()
    if not token:
        print("  ❌ Токен не может быть пустым")
        sys.exit(1)

    token_data = {
        "access_token": token,
        "expires_at": "6 месяцев",
    }
    token_path.write_text(json.dumps(token_data, indent=2))
    print(f"  ✅ Токен сохранён: {token_path}")
    print("  ⏳ Срок действия: 6 месяцев. После — повтори шаг.")


def yandex_check() -> None:
    """Проверяет статус в Яндекс.Вебмастере."""
    token_path = TOKEN_DIR / "yandex_token.json"
    if not token_path.exists():
        print("[WARN] Яндекс не настроен. Запусти: python3 check_seo.py yandex --setup")
        return

    import requests
    token_data = json.loads(token_path.read_text())
    headers = {
        "Authorization": f"OAuth {token_data['access_token']}",
        "Content-Type": "application/json",
    }

    print(f"\n{'=' * 50}")
    print("ЯНДЕКС ВЕБМАСТЕР")
    print(f"{'=' * 50}")

    # 1. Get user's hosts
    print("\n--- Хосты в Вебмастере ---")
    try:
        resp = requests.get(f"{YANDEX_API}/user", headers=headers)
        user_id = resp.json().get("user_id")
        print(f"  User ID: {user_id}")

        resp = requests.get(f"{YANDEX_API}/hosts", headers=headers)
        hosts = resp.json().get("hosts", [])
        for h in hosts:
            verified = "✅" if h.get("verified") else "❌ not verified"
            print(f"  {verified} {h['host_url']}")
    except Exception as e:
        print(f"  [ERROR] Хосты: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="SEO API Checker")
    parser.add_argument("service", choices=["google", "yandex", "all"], help="Сервис для проверки")
    parser.add_argument("--setup", action="store_true", help="OAuth setup flow")
    args = parser.parse_args()

    if args.setup:
        if args.service in ("google", "all"):
            google_setup()
        if args.service in ("yandex", "all"):
            yandex_setup()
        return

    if args.service in ("google", "all"):
        google_check()
    if args.service in ("yandex", "all"):
        yandex_check()


if __name__ == "__main__":
    main()
