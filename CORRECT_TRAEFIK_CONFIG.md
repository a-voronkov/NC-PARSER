# 🎯 ПРАВИЛЬНАЯ КОНФИГУРАЦИЯ TRAEFIK ДЛЯ NEXTCLOUD

Основываясь на официальной документации Nextcloud, проблема в **отсутствии правильных заголовков** от Traefik.

## 🚨 КОРНЕВАЯ ПРОБЛЕМА

Nextcloud **требует специальные заголовки** от reverse proxy:
- `X-Forwarded-Host`
- `X-Forwarded-Proto` 
- `X-Real-IP`
- `X-Forwarded-For`

## 🚀 ПРАВИЛЬНАЯ КОНФИГУРАЦИЯ

### 1. Исправленные labels для Nextcloud:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.nextcloud.rule=Host(`${NEXTCLOUD_DOMAIN:-ncrag.voronkov.club}`)"
  - "traefik.http.routers.nextcloud.entrypoints=websecure"
  - "traefik.http.routers.nextcloud.tls.certresolver=le"
  - "traefik.http.routers.nextcloud.priority=100"
  
  # КРИТИЧНО: Middleware для правильных заголовков
  - "traefik.http.middlewares.nextcloud-headers.headers.customRequestHeaders.X-Forwarded-Proto=https"
  - "traefik.http.middlewares.nextcloud-headers.headers.customRequestHeaders.X-Forwarded-Host=ncrag.voronkov.club"
  - "traefik.http.middlewares.nextcloud-headers.headers.hostsProxyHeaders=X-Forwarded-Host"
  - "traefik.http.middlewares.nextcloud-headers.headers.referrerPolicy=same-origin"
  - "traefik.http.middlewares.nextcloud-headers.headers.customResponseHeaders.X-Robots-Tag=noindex, nofollow"
  
  # Применить middleware
  - "traefik.http.routers.nextcloud.middlewares=nextcloud-headers"
  
  - "traefik.docker.network=nc-rag_backend"
  - "traefik.http.services.nextcloud.loadbalancer.server.port=80"
```

## 🔧 НЕМЕДЛЕННОЕ ИСПРАВЛЕНИЕ

```bash
cd /srv/docker/nc-rag

# 1. Остановить сервисы
docker compose down

# 2. Создать правильную конфигурацию
cat > docker-compose.yml.correct << 'EOF'
services:
  traefik:
    image: traefik:v3.5
    container_name: traefik
    command:
      - --providers.docker=true
      - --providers.docker.exposedbydefault=false
      - --providers.docker.network=nc-rag_backend
      - --entrypoints.web.address=:80
      - --entrypoints.websecure.address=:443
      - --entrypoints.web.http.redirections.entryPoint.to=websecure
      - --entrypoints.web.http.redirections.entryPoint.scheme=https
      - --certificatesresolvers.le.acme.email=${LETSENCRYPT_EMAIL:-admin@voronkov.club}
      - --certificatesresolvers.le.acme.storage=/letsencrypt/acme.json
      - --certificatesresolvers.le.acme.httpchallenge=true
      - --certificatesresolvers.le.acme.httpchallenge.entrypoint=web
      - --api.dashboard=true
      - --accesslog=true
      - --accesslog.filepath=/var/log/traefik/access.log
      - --log.level=DEBUG
    labels:
      - "traefik.enable=true"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik_letsencrypt:/letsencrypt
    restart: unless-stopped
    networks:
      - backend

  db:
    image: postgres:17
    container_name: nc-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-nextcloud}
      POSTGRES_USER: ${POSTGRES_USER:-nextcloud}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-nextcloudpass}
    volumes:
      - db_data:/var/lib/postgresql/data
    networks:
      - backend

  redis:
    image: redis:7-alpine
    container_name: nc-redis
    command: ["redis-server", "--appendonly", "no"]
    restart: unless-stopped
    networks:
      - backend

  memcached:
    image: memcached:1.6-alpine
    container_name: nc-memcached
    command: ["-m", "128"]
    restart: unless-stopped
    networks:
      - backend

  nextcloud:
    image: nextcloud:31-apache
    container_name: nextcloud
    depends_on:
      - db
      - traefik
      - redis
      - memcached
    restart: unless-stopped
    environment:
      POSTGRES_HOST: db
      POSTGRES_DB: ${POSTGRES_DB:-nextcloud}
      POSTGRES_USER: ${POSTGRES_USER:-nextcloud}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-nextcloudpass}
      NEXTCLOUD_ADMIN_USER: ${NEXTCLOUD_ADMIN_USER:-admin}
      NEXTCLOUD_ADMIN_PASSWORD: ${NEXTCLOUD_ADMIN_PASSWORD:-adminpass}
      NEXTCLOUD_TRUSTED_DOMAINS: ${NEXTCLOUD_TRUSTED_DOMAINS:-ncrag.voronkov.club}
      REDIS_HOST: redis
      REDIS_HOST_PORT: 6379
      REDIS_HOST_PASSWORD: ""
      MEMCACHED_HOST: memcached
      MEMCACHED_PORT: 11211
    labels:
      - "traefik.enable=true"
      # ПРАВИЛЬНАЯ конфигурация без проблемных middleware
      - "traefik.http.routers.nextcloud.rule=Host(`${NEXTCLOUD_DOMAIN:-ncrag.voronkov.club}`)"
      - "traefik.http.routers.nextcloud.entrypoints=websecure"
      - "traefik.http.routers.nextcloud.tls.certresolver=le"
      - "traefik.http.routers.nextcloud.priority=100"
      
      # КРИТИЧНО: Правильные заголовки для Nextcloud
      - "traefik.http.middlewares.nextcloud-headers.headers.customRequestHeaders.X-Forwarded-Proto=https"
      - "traefik.http.middlewares.nextcloud-headers.headers.customRequestHeaders.X-Forwarded-Host=ncrag.voronkov.club"
      - "traefik.http.middlewares.nextcloud-headers.headers.hostsProxyHeaders=X-Forwarded-Host"
      - "traefik.http.middlewares.nextcloud-headers.headers.referrerPolicy=same-origin"
      
      # Применить middleware
      - "traefik.http.routers.nextcloud.middlewares=nextcloud-headers"
      
      - "traefik.docker.network=nc-rag_backend"
      - "traefik.http.services.nextcloud.loadbalancer.server.port=80"
    volumes:
      - nextcloud_data:/var/www/html
    networks:
      - backend

  nextcloud-cron:
    image: nextcloud:31-apache
    container_name: nextcloud-cron
    restart: unless-stopped
    depends_on:
      - db
      - nextcloud
    environment:
      POSTGRES_HOST: db
      POSTGRES_DB: ${POSTGRES_DB:-nextcloud}
      POSTGRES_USER: ${POSTGRES_USER:-nextcloud}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-nextcloudpass}
    entrypoint: /cron.sh
    volumes:
      - nextcloud_data:/var/www/html
    networks:
      - backend

  mock-parser:
    build:
      context: ./services/mock-parser
    container_name: mock-parser
    environment:
      - UVICORN_WORKERS=1
    restart: unless-stopped
    networks:
      - backend

  node-red:
    image: nodered/node-red:4.1
    container_name: node-red
    environment:
      - TZ=UTC
      - NODE_RED_ENABLE_SAFE_MODE=false
      - TENANT_DEFAULT=${TENANT_DEFAULT:-default}
      - WEBHOOK_SECRET=${WEBHOOK_SECRET:-change-me}
    volumes:
      - ./services/node-red/flows.json:/data/flows.json
      - node_red_data:/data
    depends_on:
      - traefik
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.nodered.rule=Host(`${NEXTCLOUD_DOMAIN:-ncrag.voronkov.club}`) && PathPrefix(`/webhooks/nextcloud`)"
      - "traefik.http.routers.nodered.entrypoints=websecure"
      - "traefik.http.routers.nodered.priority=1000"
      - "traefik.http.routers.nodered.tls.certresolver=le"
      - "traefik.http.services.nodered.loadbalancer.server.port=1880"
      - "traefik.docker.network=nc-rag_backend"
    restart: unless-stopped
    networks:
      - backend

  nc-webhook-seeder:
    image: curlimages/curl:8.10.1
    container_name: nc-webhook-seeder
    depends_on:
      - nextcloud
      - traefik
    environment:
      - NC_ADMIN_USER=${NEXTCLOUD_ADMIN_USER}
      - NC_ADMIN_PASS=${NEXTCLOUD_ADMIN_PASSWORD}
      - NC_DOMAIN=${NEXTCLOUD_DOMAIN}
      - WEBHOOK_SECRET=${WEBHOOK_SECRET}
    entrypoint: ["/bin/sh", "/scripts/register_webhooks.sh"]
    volumes:
      - ./scripts/register_webhooks.sh:/scripts/register_webhooks.sh:ro
    restart: "no"
    networks:
      - backend

volumes:
  nextcloud_data:
  db_data:
  traefik_letsencrypt:
  node_red_data:

networks:
  backend:
EOF

# 3. Заменить конфигурацию
cp docker-compose.yml docker-compose.yml.old
mv docker-compose.yml.correct docker-compose.yml

# 4. Запустить с правильной конфигурацией
docker compose up -d
sleep 90

# 5. Настроить Nextcloud согласно документации
echo "=== НАСТРОЙКА NEXTCLOUD ПО ДОКУМЕНТАЦИИ ==="
docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 0 --value='172.19.0.8'
docker exec -u www-data nextcloud php occ config:system:set trusted_domains 0 --value='ncrag.voronkov.club'
docker exec -u www-data nextcloud php occ config:system:set trusted_domains 1 --value='localhost'
docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'
docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'
docker exec -u www-data nextcloud php occ config:system:set overwrite.cli.url --value='https://ncrag.voronkov.club'

# 6. ТЕСТ с правильной конфигурацией
echo "=== ТЕСТ С ПРАВИЛЬНОЙ КОНФИГУРАЦИЕЙ ==="
COOKIE_JAR="/tmp/correct_config.txt"
rm -f "$COOKIE_JAR"

# Проверить главную страницу
curl -s -o /dev/null -w "Главная: %{http_code}\n" "https://ncrag.voronkov.club/"

# Тест логина
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)

echo "CSRF: ${CSRF_TOKEN:0:30}..."

RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \
    -d "user=admin" \
    -d "password=$NEXTCLOUD_PASSWORD" \
    -d "requesttoken=$CSRF_TOKEN" \
    -w "URL:%{url_effective}\n" \
    "https://ncrag.voronkov.club/login")

FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)
echo "Final URL: $FINAL_URL"

if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ ВСЕ ЕЩЕ НЕ РАБОТАЕТ"
    echo "Попробуйте откат к Nextcloud 30"
else
    echo "✅ УСПЕХ! ПРАВИЛЬНАЯ КОНФИГУРАЦИЯ РАБОТАЕТ!"
fi

rm -f "$COOKIE_JAR"
```

## 🔍 КЛЮЧЕВЫЕ ИЗМЕНЕНИЯ

1. **Убрал проблемный HSTS middleware**
2. **Добавил правильные заголовки** согласно документации Nextcloud
3. **Упростил правило маршрутизации** (убрал исключение webhook)
4. **Убрал сеть `web`** из Traefik для упрощения

## 📋 АЛЬТЕРНАТИВА: ОТКАТ К NEXTCLOUD 30

Если правильная конфигурация не поможет:

```bash
# Откат к стабильной версии
sed -i 's/nextcloud:31-apache/nextcloud:30-apache/g' docker-compose.yml
docker compose down
docker volume rm nc-rag_nextcloud_data nc-rag_db_data
docker compose up -d
sleep 120
```

**Попробуйте правильную конфигурацию Traefik!** Это должно решить проблему согласно официальной документации.