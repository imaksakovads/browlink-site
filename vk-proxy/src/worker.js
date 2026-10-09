/**
 * OSTIN KOSMO — VK booking form proxy (Cloudflare Worker)
 * -------------------------------------------------------
 * Назначение: принимать заявку с формы записи → отправлять в ЛС
 * группы VK методом messages.send от имени сообщества.
 *
 * Схема:
 *   Браузер (index.html)  →  POST <worker-url>  →  api.vk.com/messages.send
 *
 * Важно: токен сообщества НЕ попадает в публичный HTML — он задаётся
 * секретом в окружении Worker'а (Secrets / vars).
 *
 * CORS: браузер шлёт кросс-доменный POST с Content-Type: application/json,
 * поэтому Worker обязан отвечать на предварительный OPTIONS-запрос и
 * возвращать заголовки Access-Control-Allow-*.
 *
 * Требуемые переменные окружения (Vars/Secrets в Cloudflare Worker):
 *   VK_TOKEN   — access_token сообщества с правом messages
 *   VK_GROUP   — числовой id сообщества (напр. 123456789)
 *   VK_PEER    — числовой id пользователя-получателя (например владельца)
 */

// Разрешённые источники (Origins). Для заявок достаточно "*", но список
// надёжнее — исключает случайное использование прокси с чужих доменов.
const ALLOWED_ORIGINS = ["https://www.ostinkosmo.ru", "https://ostinkosmo.ru"];

function corsHeaders(request) {
  const origin = request.headers.get("Origin") || "";
  // Локальная разработка (wrangler dev, file://) — Origin отсутствует или локальный.
  const allowOrigin =
    ALLOWED_ORIGINS.includes(origin) || origin.startsWith("http://localhost")
      ? origin
      : ALLOWED_ORIGINS[0];
  return {
    "Access-Control-Allow-Origin": allowOrigin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
  };
}

export default {
  async fetch(request, env) {
    const cors = corsHeaders(request);

    // Предварительный запрос (preflight) от браузера
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }

    // Разрешаем только POST
    if (request.method !== "POST") {
      return json({ error: "Method not allowed" }, 405, cors);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: "Invalid JSON" }, 400, cors);
    }

    const { phone, service, date, channel, name, text } = body;

    // Минимальная валидация
    if (!phone && !text) {
      return json({ error: "Phone or text required" }, 400, cors);
    }

    // Собираем текст заявки — формат похож на Telegram-версию.
    // Если пришёл готовый text (например из квиза) — используем его как есть.
    let message;
    if (text) {
      message = text;
    } else {
      const lines = [
        "⚡ Новая заявка с сайта!",
        "Канал: " + (channel || "VK"),
        "Услуга: " + (service || "—"),
      ];
      if (date) lines.push("Дата: " + date);
      if (name) lines.push("Имя: " + name);
      lines.push("Телефон: " + phone);
      message = lines.join("\n");
    }

    // Отправка в VK API
    const vkUrl = new URL("https://api.vk.com/method/messages.send");
    const form = new URLSearchParams({
      access_token: env.VK_TOKEN,
      v: "5.199",
      peer_id: env.VK_PEER,      // ЛС пользователя, которому падает заявка
      random_id: String(Date.now()),
      message: message,
      dont_parse_links: "1",
    });

    const vkResp = await fetch(vkUrl, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
    });
    const vkData = await vkResp.json();

    // VK API возвращает { response: N } при успехе, либо { error: {...} }
    if (vkData.error) {
      // Логируем детали ошибки (не раскрывая токен)
      const e = vkData.error;
      return json(
        {
          ok: false,
          error: "vk_error",
          code: e.error_code,
          msg: e.error_msg,
        },
        502,
        cors
      );
    }

    return json({ ok: true, vk_message_id: vkData.response }, 200, cors);
  },
};

function json(data, status, extraHeaders) {
  return new Response(JSON.stringify(data), {
    status: status || 200,
    headers: {
      "Content-Type": "application/json",
      ...(extraHeaders || {}),
    },
  });
}