# OSTIN KOSMO — VK-прокси заявок на Yandex Cloud (Functions + API Gateway)
#
# Обоснование: Cloudflare *.workers.dev блокируется в РФ (нужен VPN),
# а *.yandexcloud.net из РФ доступен без VPN. Поэтому прокси переносим
# с Cloudflare Worker на Yandex.
#
# Архитектура:
#   Браузер → https://<apigw-id>.apigw.yandexcloud.net/vk-lead
#           → API Gateway (публичный) → Function → api.vk.com/messages.send
#
# Почему API Gateway, а не прямой HTTP-триггер функций: прямое обращение
# к https://functions.yandexcloud.net/{id} требует IAM-токен (анонимный
# вызов недоступен). API Gateway делает endpoint публичным.

# ──────────────────────────────────────────────────────────────────────
# Шаг 0. Разово: инициализация CLI и каталога
# ──────────────────────────────────────────────────────────────────────
#   yc init                 # войти, выбрать/создать cloud и folder
#
# Запомнить folder-id (далее FOLDER_ID).

# ──────────────────────────────────────────────────────────────────────
# Шаг 1. Сервисный аккаунт (нужен API Gateway для вызова функции)
# ──────────────────────────────────────────────────────────────────────
#   SA_ID=$(yc iam service-account create --name ostinkosmo-vk \
#     --folder-id $FOLDER_ID --format json | jq -r .id)
#   yc resource-manager folder add-access-binding $FOLDER_ID \
#     --role functions.functionInvoker --service-account-id $SA_ID

# ──────────────────────────────────────────────────────────────────────
# Шаг 2. Функция + версия с кодом и секретами
# ──────────────────────────────────────────────────────────────────────
#   yc serverless function create --name ostinkosmo-vk-proxy \
#     --folder-id $FOLDER_ID
#   FN_ID=$(yc serverless function get ostinkosmo-vk-proxy --format json | jq -r .id)
#
#   yc serverless function version create \
#     --function-name ostinkosmo-vk-proxy \
#     --runtime python312 \
#     --entrypoint main.handler \
#     --source-path ./vk-proxy-yandex \
#     --memory 128m --execution-timeout 15s \
#     --environment VK_TOKEN='<token>',VK_PEER='11249666'

# ──────────────────────────────────────────────────────────────────────
# Шаг 3. API Gateway (публичный endpoint)
# ──────────────────────────────────────────────────────────────────────
# файл spec.yaml (рядом):
#   openapi: 3.0.0
#   info: {title: ostinkosmo-vk-proxy, version: 1.0.0}
#   paths:
#     /vk-lead:
#       post:
#         x-yc-apigateway-integration:
#           type: cloud_functions
#           function_id: <FN_ID>
#           service_account_id: <SA_ID>
#         responses: {'200': {description: ok}}
#       options:
#         x-yc-apigateway-integration:
#           type: cloud_functions
#           function_id: <FN_ID>
#           service_account_id: <SA_ID>
#         responses: {'200': {description: ok}}
#
#   yc serverless api-gateway create --name ostinkosmo-vk \
#     --spec spec.yaml --folder-id $FOLDER_ID
#   GW_ID=$(yc serverless api-gateway get ostinkosmo-vk --format json | jq -r .id)
#
# → публичный URL: https://$GW_ID.apigw.yandexcloud.net/vk-lead

# ──────────────────────────────────────────────────────────────────────
# Шаг 4. Проверка
# ──────────────────────────────────────────────────────────────────────
#   curl -s -X POST https://$GW_ID.apigw.yandexcloud.net/vk-lead \
#     -H 'Content-Type: application/json' \
#     -H 'Origin: https://www.ostinkosmo.ru' \
#     -d '{"text":"[ТЕСТ] проверка прокси Yandex"}'
#   # ожидание: {"ok": true, "vk_message_id": <n>}

# Шаг 5. index.html — заменить VK_PROXY_URL и URL квиза на
#   https://$GW_ID.apigw.yandexcloud.net/vk-lead