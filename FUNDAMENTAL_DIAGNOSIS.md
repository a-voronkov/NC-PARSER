# 🚨 ФУНДАМЕНТАЛЬНАЯ ДИАГНОСТИКА

Если чистая установка не работает, проблема в базовой конфигурации!

## 🔍 КРИТИЧЕСКАЯ ДИАГНОСТИКА

```bash
cd /srv/docker/nc-rag

# 1. VERBOSE тест для видения ТОЧНЫХ заголовков
echo "=== VERBOSE CURL ДИАГНОСТИКА ==="
COOKIE_JAR="/tmp/fundamental_test.txt"
rm -f "$COOKIE_JAR"

# Получить CSRF токен
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)
echo "CSRF Token: ${CSRF_TOKEN:0:40}..."

# КРИТИЧНО: Посмотреть ВСЕ заголовки ответа
echo -e "\n=== ВСЕ ЗАГОЛОВКИ ОТВЕТА ==="
curl -v -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
    -d "user=admin" \
    -d "password=$NEXTCLOUD_PASSWORD" \
    -d "requesttoken=$CSRF_TOKEN" \
    "https://ncrag.voronkov.club/login" 2>&1

rm -f "$COOKIE_JAR"
```

## 🔧 ПРОВЕРКА DOCKER-COMPOSE.YML

```bash
# 2. Проверить Nextcloud конфигурацию в docker-compose
echo -e "\n=== NEXTCLOUD КОНФИГУРАЦИЯ ==="
grep -A 20 -B 5 "nextcloud:" docker-compose.yml

# 3. Проверить Traefik labels для Nextcloud
echo -e "\n=== TRAEFIK LABELS ==="
grep -A 15 "traefik.enable=true" docker-compose.yml | grep -A 15 -B 5 nextcloud

# 4. Проверить переменные окружения
echo -e "\n=== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ==="
grep -A 10 "environment:" docker-compose.yml | grep -A 10 -B 2 NEXTCLOUD
```

## 🚨 ПОПРОБУЙТЕ ОТКАТ К NEXTCLOUD 30

```bash
# 1. Остановить сервисы
docker compose down

# 2. Изменить версию в docker-compose.yml
echo "=== ОТКАТ К NEXTCLOUD 30 ==="
sed -i 's/nextcloud:31-apache/nextcloud:30-apache/g' docker-compose.yml

# Проверить изменение
grep "image.*nextcloud" docker-compose.yml

# 3. Запустить с Nextcloud 30
docker compose up -d

# 4. Подождать инициализации
sleep 120

# 5. Проверить версию
docker exec -u www-data nextcloud php occ status

# 6. Тест логина с Nextcloud 30
COOKIE_JAR="/tmp/nextcloud30_test.txt"
rm -f "$COOKIE_JAR"

LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)

echo "CSRF (NC 30): ${CSRF_TOKEN:0:40}..."

RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \
    -d "user=admin" \
    -d "password=$NEXTCLOUD_PASSWORD" \
    -d "requesttoken=$CSRF_TOKEN" \
    -w "URL:%{url_effective}\n" \
    "https://ncrag.voronkov.club/login")

FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)
echo "Final URL (NC 30): $FINAL_URL"

if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ NEXTCLOUD 30 ТОЖЕ НЕ РАБОТАЕТ"
else
    echo "✅ NEXTCLOUD 30 РАБОТАЕТ!"
fi

rm -f "$COOKIE_JAR"
```

## 🔍 ПРОВЕРКА ПРЯМОГО ПОДКЛЮЧЕНИЯ

```bash
# 7. Тест ПРЯМОГО подключения к контейнеру (обход Traefik)
echo -e "\n=== ПРЯМОЕ ПОДКЛЮЧЕНИЕ ==="

# Найти IP Nextcloud контейнера
NEXTCLOUD_IP=$(docker inspect nextcloud | grep '"IPAddress"' | grep '172.19' | head -1 | grep -oP '\d+\.\d+\.\d+\.\d+')
echo "Nextcloud IP: $NEXTCLOUD_IP"

# Тест прямого подключения
if [ -n "$NEXTCLOUD_IP" ]; then
    echo "Тест прямого подключения к $NEXTCLOUD_IP..."
    curl -H "Host: ncrag.voronkov.club" -I "http://$NEXTCLOUD_IP/login"
    
    # Попробовать логин напрямую
    DIRECT_COOKIE="/tmp/direct_test.txt"
    rm -f "$DIRECT_COOKIE"
    
    DIRECT_LOGIN=$(curl -s -c "$DIRECT_COOKIE" -H "Host: ncrag.voronkov.club" "http://$NEXTCLOUD_IP/login")
    DIRECT_CSRF=$(echo "$DIRECT_LOGIN" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)
    
    if [ -n "$DIRECT_CSRF" ]; then
        echo "Прямой CSRF: ${DIRECT_CSRF:0:30}..."
        
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
            echo "❌ ДАЖЕ ПРЯМОЕ ПОДКЛЮЧЕНИЕ НЕ РАБОТАЕТ"
            echo "Проблема в самом Nextcloud!"
        else
            echo "✅ ПРЯМОЕ ПОДКЛЮЧЕНИЕ РАБОТАЕТ"
            echo "Проблема в Traefik!"
        fi
    fi
    
    rm -f "$DIRECT_COOKIE"
else
    echo "❌ Не удалось найти IP Nextcloud"
fi
```

## 📋 СЛЕДУЮЩИЕ ШАГИ

**Выполните ВСЕ команды выше** и сообщите:

1. **Результат verbose curl** - какие точно заголовки Location
2. **Работает ли Nextcloud 30**
3. **Результат прямого подключения** - работает ли обход Traefik

Это точно покажет, где проблема:
- **В Nextcloud** (если прямое подключение не работает)
- **В Traefik** (если прямое подключение работает)
- **В версии** (если NC 30 работает, а 31 нет)

**Выполните диагностику и сообщите все результаты!**