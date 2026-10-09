# OSTIN KOSMO — VK-прокси заявок (Cloudflare Worker)

Прокси для отправки заявок с сайта в **личные сообщения группы ВК**.
Заявка летит с браузера на этот Worker, а он от имени сообщества
отправляет её методом `messages.send` — токен ВК не светится в HTML.

## Почему так, а не напрямую из браузера
- VK API (api.vk.com) не даёт CORS на клиентскую отправку ЛС.
- Токен с правом `messages` нельзя класть в публичный HTML/JS — это утечка.
- Прокси решает обе проблемы.

## Требуемые переменные окружения Worker'а
| Переменная | Что это |
|------------|---------|
| `VK_TOKEN`  | Access-токен сообщества с правом `messages` |
| `VK_GROUP`  | Числовой id сообщества ВК |
| `VK_PEER`   | id получателя заявки (ЛС мастеру/владельцу) |

Целевое сообщество: **ostin_kosmo_msk** (id `216964714`).
Получатель заявок: владелец группы id **`11249666`** (@katespanjen).
Групповой токен имеет право `messages` — проверено тестовой отправкой (message_id дошёл).

⚠️ Никогда не коммитьте реальный `VK_TOKEN` в публичный репозиторий.
Задавайте его секретом в Cloudflare.

## Деплой (один раз)
```bash
npm install -g wrangler
cd vk-proxy
npx wrangler login
npx wrangler secret put VK_TOKEN     # ввести токен
npx wrangler secret put VK_GROUP     # или vars в Dashboard
npx wrangler secret put VK_PEER
npx wrangler deploy
```
Рабочий URL Worker'а: **`https://ostinkosmo-vk-proxy.ostinkosmo.workers.dev`** (workers.dev subdomain `ostinkosmo`).
Этот URL вписывается в `index.html` в обработчик VK-канала.

## Локальная проверка
```bash
cd vk-proxy
npx wrangler dev   # запустит локально, покажет URL
# POST http://localhost:8787 с телом:
# {"phone":"+7 (900) 000-00-00","service":"Ламинирование ресниц"}
```

## Как вписать в форму (index.html)
В `submitContactForm()` при `channel === 'vk'` слать на Worker вместо Telegram:
```js
fetch('https://<worker-url>', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ phone: fullPhone, service: svcName, date: modalState.date, channel: chName })
});
```
См. `src/worker.js` — он принимает те же поля.
