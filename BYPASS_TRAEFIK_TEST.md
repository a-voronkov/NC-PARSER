# 🔥 ТЕСТ БЕЗ TRAEFIK - НАЙТИ КОРЕНЬ ПРОБЛЕМЫ

Раз даже отключение HSTS не помогло, давайте проверим, работает ли Nextcloud вообще без Traefik.

## 🚀 ТЕСТ 1: ПРЯМОЕ ПОДКЛЮЧЕНИЕ К NEXTCLOUD

```bash
cd /srv/docker/nc-rag

# 1. Найти IP адрес Nextcloud контейнера
NEXTCLOUD_IP=$(docker inspect nextcloud | grep '"IPAddress"' | grep '172.19' | head -1 | grep -oP '\d+\.\d+\.\d+\.\d+')
echo "Nextcloud IP: $NEXTCLOUD_IP"

# 2. Тест прямого подключения (обход Traefik)
echo "=== ПРЯМОЕ ПОДКЛЮЧЕНИЕ К NEXTCLOUD ==="
curl -H "Host: ncrag.voronkov.club" -I "http://$NEXTCLOUD_IP/login"

# 3. Полный тест логина напрямую
DIRECT_COOKIE="/tmp/direct_nextcloud.txt"
rm -f "$DIRECT_COOKIE"

echo "Получение страницы логина напрямую..."
DIRECT_LOGIN=$(curl -s -c "$DIRECT_COOKIE" -H "Host: ncrag.voronkov.club" "http://$NEXTCLOUD_IP/login")
DIRECT_CSRF=$(echo "$DIRECT_LOGIN" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)

if [ -z "$DIRECT_CSRF" ]; then
    echo "❌ Не удалось получить CSRF токен при прямом подключении"
    echo "Первые строки ответа:"
    echo "$DIRECT_LOGIN" | head -10
else
    echo "CSRF (прямое): ${DIRECT_CSRF:0:30}..."
    
    echo "Тест логина напрямую..."
    DIRECT_RESPONSE=$(curl -s -b "$DIRECT_COOKIE" -c "$DIRECT_COOKIE" -L \
        -H "Host: ncrag.voronkov.club" \
        -d "user=admin" \
        -d "password=$NEXTCLOUD_PASSWORD" \
        -d "requesttoken=$DIRECT_CSRF" \
        -w "URL:%{url_effective}\n" \
        "http://$NEXTCLOUD_IP/login")
    
    DIRECT_URL=$(echo "$DIRECT_RESPONSE" | grep "URL:" | cut -d: -f2-)
    echo "Прямое подключение URL: $DIRECT_URL"
    
    if [[ "$DIRECT_URL" == *"/login"* ]]; then
        echo "❌ ДАЖЕ ПРЯМОЕ ПОДКЛЮЧЕНИЕ НЕ РАБОТАЕТ!"
        echo "Проблема в самом Nextcloud!"
    else
        echo "✅ ПРЯМОЕ ПОДКЛЮЧЕНИЕ РАБОТАЕТ!"
        echo "Проблема в Traefik конфигурации!"
    fi
fi

rm -f "$DIRECT_COOKIE"
```

## 🔥 ТЕСТ 2: ВРЕМЕННО ОТКЛЮЧИТЬ TRAEFIK

```bash
cd /srv/docker/nc-rag

# 1. Остановить Traefik
echo "=== ОСТАНОВКА TRAEFIK ==="
docker stop traefik

# 2. Временно проксировать через простой nginx
echo "=== ВРЕМЕННЫЙ NGINX PROXY ==="
docker run -d --name temp_nginx \
    -p 80:80 -p 443:443 \
    --network nc-rag_backend \
    -v /tmp/nginx.conf:/etc/nginx/nginx.conf:ro \
    nginx:alpine

# Создать простую конфигурацию nginx
cat > /tmp/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}
http {
    upstream nextcloud {
        server nextcloud:80;
    }
    server {
        listen 80;
        server_name ncrag.voronkov.club;
        location / {
            proxy_pass http://nextcloud;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

# 3. Перезапустить nginx с конфигурацией
docker cp /tmp/nginx.conf temp_nginx:/etc/nginx/nginx.conf
docker restart temp_nginx

# 4. Тест через nginx (HTTP)
echo "=== ТЕСТ ЧЕРЕЗ NGINX ==="
NGINX_COOKIE="/tmp/nginx_test.txt"
rm -f "$NGINX_COOKIE"

NGINX_LOGIN=$(curl -s -c "$NGINX_COOKIE" "http://ncrag.voronkov.club/login")
NGINX_CSRF=$(echo "$NGINX_LOGIN" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)

echo "CSRF (nginx): ${NGINX_CSRF:0:30}..."

NGINX_RESPONSE=$(curl -s -b "$NGINX_COOKIE" -c "$NGINX_COOKIE" -L \
    -d "user=admin" \
    -d "password=$NEXTCLOUD_PASSWORD" \
    -d "requesttoken=$NGINX_CSRF" \
    -w "URL:%{url_effective}\n" \
    "http://ncrag.voronkov.club/login")

NGINX_URL=$(echo "$NGINX_RESPONSE" | grep "URL:" | cut -d: -f2-)
echo "Nginx proxy URL: $NGINX_URL"

if [[ "$NGINX_URL" == *"/login"* ]]; then
    echo "❌ ДАЖЕ NGINX НЕ РАБОТАЕТ"
else
    echo "✅ NGINX РАБОТАЕТ! Проблема в Traefik!"
fi

# 5. Очистка
docker stop temp_nginx
docker rm temp_nginx
rm -f "$NGINX_COOKIE" /tmp/nginx.conf

# 6. Запустить Traefik обратно
docker start traefik
```

## 🧪 ТЕСТ 3: ОТКАТ К NEXTCLOUD 30

```bash
cd /srv/docker/nc-rag

# 1. Откат к версии 30
echo "=== ОТКАТ К NEXTCLOUD 30 ==="
docker compose down
sed -i 's/nextcloud:31-apache/nextcloud:30-apache/g' docker-compose.yml

# Проверить изменение
grep "image.*nextcloud" docker-compose.yml

# 2. Удалить данные и пересоздать
docker volume rm nc-rag_nextcloud_data nc-rag_db_data

# 3. Запустить Nextcloud 30
docker compose up -d
sleep 120

# 4. Проверить версию
docker exec -u www-data nextcloud php occ status

# 5. Тест с Nextcloud 30
COOKIE_JAR="/tmp/nextcloud30.txt"
rm -f "$COOKIE_JAR"

LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)

echo "CSRF (NC 30): ${CSRF_TOKEN:0:30}..."

RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \
    -d "user=admin" \
    -d "password=$NEXTCLOUD_PASSWORD" \
    -d "requesttoken=$CSRF_TOKEN" \
    -w "URL:%{url_effective}\n" \
    "https://ncrag.voronkov.club/login")

FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)
echo "Nextcloud 30 URL: $FINAL_URL"

if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ NEXTCLOUD 30 ТОЖЕ НЕ РАБОТАЕТ"
else
    echo "✅ NEXTCLOUD 30 РАБОТАЕТ! Проблема в версии 31!"
fi

rm -f "$COOKIE_JAR"
```

## 📋 КРИТИЧЕСКИЕ ВОПРОСЫ

**Выполните все 3 теста по порядку:**

1. **Прямое подключение** - работает ли Nextcloud без прокси?
2. **Nginx proxy** - работает ли с простым прокси?
3. **Nextcloud 30** - работает ли со старой версией?

Это точно покажет:
- **Проблема в Nextcloud** (если прямое подключение не работает)
- **Проблема в Traefik** (если nginx работает, а Traefik нет)
- **Баг в версии 31** (если NC 30 работает)

**Выполните все тесты и сообщите результаты каждого!**