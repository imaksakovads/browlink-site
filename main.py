"""
OSTIN KOSMO — VK booking form proxy (Yandex Cloud Function)
-----------------------------------------------------------
Принимает заявку с формы записи → отправляет в ЛС группы VK
методом messages.send от имени сообщества.

Схема:
  Браузер (index.html)  →  POST <apigw>.apigw.yandexcloud.net/vk-lead
                        →  Function  →  api.vk.com/method/messages.send

Почему не напрямую из браузера: api.vk.com не отдаёт CORS
(Access-Control-Allow-Origin), а токен с правом messages нельзя
светить в публичном HTML. Функция живёт на инфраструктуре Яндекса
(*.yandexcloud.net), которая из РФ доступна без VPN — в отличие от
Cloudflare *.workers.dev.

Переменные окружения функции (VK_TOKEN, VK_PEER):
http-триггер передаёт их коде как env (event не нужен для самих чисел —
числа передаются через окружение функции).
"""
import json
import os
import time
import urllib.parse
import urllib.request

VK_TOKEN = os.environ.get("VK_TOKEN", "")
VK_PEER = os.environ.get("VK_PEER", "11249666")  # владелец группы (@katespanjen)

ALLOWED_ORIGINS = {"https://www.ostinkosmo.ru", "https://ostinkosmo.ru"}


def _cors(event):
    headers = event.get("headers") or {}
    origin = headers.get("Origin") or headers.get("origin") or ""
    allow_origin = origin if origin in ALLOWED_ORIGINS else "https://www.ostinkosmo.ru"
    return {
        "Access-Control-Allow-Origin": allow_origin,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Max-Age": "86400",
    }


def _resp(status, payload, cors):
    return {
        "statusCode": status,
        "headers": {**cors, "Content-Type": "application/json"},
        "body": json.dumps(payload),
        "isBase64Encoded": False,
    }


def handler(event, context):
    cors = _cors(event)
    method = (event.get("httpMethod") or "POST").upper()

    if method == "OPTIONS":  # CORS preflight от браузера
        return {"statusCode": 204, "headers": cors, "body": "", "isBase64Encoded": False}

    if method != "POST":
        return _resp(405, {"error": "Method not allowed"}, cors)

    # Тело запроса через API Gateway приходит как строка (или base64)
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64
        raw = base64.b64decode(raw).decode("utf-8", "ignore")
    try:
        body = json.loads(raw)
    except Exception:
        return _resp(400, {"error": "Invalid JSON"}, cors)

    phone = body.get("phone")
    service = body.get("service")
    date = body.get("date")
    channel = body.get("channel")
    name = body.get("name")
    text = body.get("text")

    if not phone and not text:
        return _resp(400, {"error": "Phone or text required"}, cors)

    if text:
        message = text
    else:
        lines = [
            "⚡ Новая заявка с сайта!",
            "Канал: " + (channel or "VK"),
            "Услуга: " + (service or "—"),
        ]
        if date:
            lines.append("Дата: " + date)
        if name:
            lines.append("Имя: " + name)
        lines.append("Телефон: " + phone)
        message = "\n".join(lines)

    # Отправка в VK
    data = urllib.parse.urlencode({
        "access_token": VK_TOKEN,
        "v": "5.199",
        "peer_id": VK_PEER,
        "random_id": str(int(time.time() * 1000)),
        "message": message,
        "dont_parse_links": "1",
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.vk.com/method/messages.send",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        vk = json.loads(urllib.request.urlopen(req, timeout=10).read().decode("utf-8"))
    except Exception as e:
        return _resp(502, {"ok": False, "error": "vk_unreachable", "msg": str(e)}, cors)

    if vk.get("error"):
        e = vk["error"]
        return _resp(502, {"ok": False, "error": "vk_error", "code": e.get("error_code"), "msg": e.get("error_msg")}, cors)

    return _resp(200, {"ok": True, "vk_message_id": vk.get("response")}, cors)