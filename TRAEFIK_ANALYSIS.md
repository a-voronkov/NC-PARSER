# 🔍 АНАЛИЗ КОНФИГУРАЦИИ TRAEFIK

## 🚨 НАЙДЕННАЯ ПРОБЛЕМА

Анализируя ваш `docker-compose.yml`, я вижу потенциальную проблему:

### ❌ Проблема с middleware
```yaml
- "traefik.http.routers.nextcloud.middlewares=hsts"
```

**HSTS middleware может вызывать проблемы с перенаправлениями!**

### ❌ Проблема с сетью
```yaml
- "traefik.docker.network=nc-rag_backend"
```

Но Traefik подключен к двум сетям: `web` и `backend`. Возможен конфликт.

## 🚀 ИСПРАВЛЕНИЯ

### 1. ОТКЛЮЧИТЬ HSTS MIDDLEWARE (временно)
```bash
cd /srv/docker/nc-rag

# Остановить сервисы
docker compose down

# Изменить docker-compose.yml - убрать HSTS middleware
sed -i 's/traefik.http.routers.nextcloud.middlewares=hsts/# traefik.http.routers.nextcloud.middlewares=hsts/' docker-compose.yml

# Проверить изменение
grep "middlewares=hsts" docker-compose.yml

# Запустить без HSTS
docker compose up -d
sleep 60

# Тест без HSTS
COOKIE_JAR="/tmp/no_hsts.txt"
rm -f "$COOKIE_JAR"

LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)

echo "CSRF (без HSTS): ${CSRF_TOKEN:0:30}..."

RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \
    -d "user=admin" \
    -d "password=$NEXTCLOUD_PASSWORD" \
    -d "requesttoken=$CSRF_TOKEN" \
    -w "URL:%{url_effective}\n" \
    "https://ncrag.voronkov.club/login")

FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)
echo "URL без HSTS: $FINAL_URL"

if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ ВСЕ ЕЩЕ НЕ РАБОТАЕТ"
else
    echo "✅ УСПЕХ! HSTS БЫЛА ПРОБЛЕМОЙ!"
fi

rm -f "$COOKIE_JAR"
```

### 2. ИСПРАВИТЬ СЕТЕВУЮ КОНФИГУРАЦИЮ
```bash
# Если HSTS не помогло, попробуйте исправить сеть
cd /srv/docker/nc-rag
docker compose down

# Изменить сетевую конфигурацию Traefik
# Убрать web сеть, оставить только backend
sed -i '/- web/d' docker-compose.yml

# Или наоборот - изменить traefik.docker.network
sed -i 's/traefik.docker.network=nc-rag_backend/# traefik.docker.network=nc-rag_backend/' docker-compose.yml

docker compose up -d
sleep 60

# Тест с исправленной сетью
```

### 3. ДОБАВИТЬ СПЕЦИАЛЬНЫЕ ЗАГОЛОВКИ ДЛЯ NEXTCLOUD
```bash
# Если проблема в заголовках, добавьте специальный middleware
cd /srv/docker/nc-rag
docker compose down

# Добавить новые labels для Nextcloud в docker-compose.yml
# Добавьте эти строки в labels секцию nextcloud:
```

## 🔧 ИСПРАВЛЕННАЯ КОНФИГУРАЦИЯ NEXTCLOUD

Замените labels секцию nextcloud на:

```yaml
labels:
  - "traefik.enable=true"
  # Убираем проблемный HSTS middleware
  # - "traefik.http.routers.nextcloud.middlewares=hsts"
  - "traefik.http.routers.nextcloud.rule=Host(`${NEXTCLOUD_DOMAIN:-ncrag.voronkov.club}`) && !PathPrefix(`/webhooks/nextcloud`)"
  - "traefik.http.routers.nextcloud.entrypoints=websecure"
  - "traefik.http.routers.nextcloud.tls.certresolver=le"
  - "traefik.http.routers.nextcloud.priority=100"
  # Добавляем специальные заголовки для Nextcloud
  - "traefik.http.middlewares.nextcloud-headers.headers.customRequestHeaders.X-Forwarded-Proto=https"
  - "traefik.http.middlewares.nextcloud-headers.headers.customRequestHeaders.X-Forwarded-Host=ncrag.voronkov.club"
  - "traefik.http.routers.nextcloud.middlewares=nextcloud-headers"
  - "traefik.docker.network=nc-rag_backend"
  - "traefik.http.services.nextcloud.loadbalancer.server.port=80"
```

## 🚀 ПОЛНОЕ ИСПРАВЛЕНИЕ

```bash
cd /srv/docker/nc-rag

# 1. Остановить сервисы
docker compose down

# 2. Создать исправленный docker-compose.yml
cat > docker-compose.yml.fixed << 'EOF'
# [Вставьте полную исправленную конфигурацию]
EOF

# 3. Заменить конфигурацию
cp docker-compose.yml docker-compose.yml.broken
mv docker-compose.yml.fixed docker-compose.yml

# 4. Запустить с исправленной конфигурацией
docker compose up -d
sleep 60

# 5. Настроить Nextcloud для работы с Traefik
docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 0 --value='172.19.0.8'
docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'
docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'
docker exec -u www-data nextcloud php occ config:system:set overwrite.cli.url --value='https://ncrag.voronkov.club'

# 6. Тест с исправленной конфигурацией
COOKIE_JAR="/tmp/fixed_config.txt"
rm -f "$COOKIE_JAR"

LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)

RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \
    -d "user=admin" \
    -d "password=$NEXTCLOUD_PASSWORD" \
    -d "requesttoken=$CSRF_TOKEN" \
    -w "URL:%{url_effective}\n" \
    "https://ncrag.voronkov.club/login")

FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)
echo "URL с исправленной конфигурацией: $FINAL_URL"
```

## 📋 МОЯ ГИПОТЕЗА

**HSTS middleware** может вызывать конфликты с перенаправлениями Nextcloud. 

**Попробуйте сначала просто отключить HSTS middleware** - это самое простое исправление!

Выполните команды и сообщите результат!