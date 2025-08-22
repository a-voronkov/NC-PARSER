# 🔍 ГЛУБОКАЯ ДИАГНОСТИКА ПРОБЛЕМЫ

Раз стандартные исправления не помогли, проверим более глубокие причины.

## 🚀 КОМАНДЫ ДЛЯ ВЫПОЛНЕНИЯ

```bash
ssh alfred361@ncrag.voronkov.club
cd /srv/docker/nc-rag

# 1. Проверить текущую конфигурацию Nextcloud
echo "=== ТЕКУЩАЯ КОНФИГУРАЦИЯ ==="
docker exec -u www-data nextcloud php occ config:system:get trusted_proxies
docker exec -u www-data nextcloud php occ config:system:get overwritehost
docker exec -u www-data nextcloud php occ config:system:get overwriteprotocol
docker exec -u www-data nextcloud php occ config:system:get trusted_domains

# 2. VERBOSE тест логина для видения заголовков
echo -e "\n=== VERBOSE ЛОГИН ТЕСТ ==="
COOKIE_JAR="/tmp/verbose.txt"
rm -f "$COOKIE_JAR"

# Получить страницу логина
curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login" > /tmp/login.html
CSRF_TOKEN=$(grep -oP 'data-requesttoken="\K[^"]+' /tmp/login.html | head -1)
echo "CSRF Token: ${CSRF_TOKEN:0:40}..."

# Отправить логин с verbose выводом
echo -e "\n=== ЗАГОЛОВКИ ОТВЕТА ==="
curl -v -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
    -d "user=admin" \
    -d "password=$NEXTCLOUD_PASSWORD" \
    -d "requesttoken=$CSRF_TOKEN" \
    "https://ncrag.voronkov.club/login" 2>&1 | grep -E "(< HTTP|< Location|< Set-Cookie|> POST|> Host)"

rm -f "$COOKIE_JAR" /tmp/login.html
```

## 🧪 ТЕСТ БЕЗ REDIS

```bash
# Отключить Redis кэширование
echo "=== ОТКЛЮЧЕНИЕ REDIS ==="
docker exec -u www-data nextcloud php occ config:system:delete memcache.distributed
docker exec -u www-data nextcloud php occ config:system:delete memcache.locking
docker restart nextcloud
sleep 15

# Тест без Redis
echo -e "\n=== ТЕСТ БЕЗ REDIS ==="
COOKIE_JAR="/tmp/no_redis.txt"
rm -f "$COOKIE_JAR"

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
echo "Final URL без Redis: $FINAL_URL"

if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ ВСЕ ЕЩЕ РЕДИРЕКТ (Redis не причина)"
else
    echo "✅ УСПЕХ БЕЗ REDIS!"
fi

rm -f "$COOKIE_JAR"
```

## 🔍 ПРОВЕРКА CONFIG.PHP

```bash
# Проверить прямо config.php файл
echo "=== CONFIG.PHP ==="
docker exec nextcloud cat /var/www/html/config/config.php | grep -E "(trusted_proxies|overwrite|trusted_domains)" -A 2 -B 1
```

## 🧪 АЛЬТЕРНАТИВНЫЕ ТЕСТЫ

### Тест 1: HTTP вместо HTTPS
```bash
# Временно переключиться на HTTP
docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='http'
docker exec -u www-data nextcloud php occ config:system:set overwrite.cli.url --value='http://ncrag.voronkov.club'
docker restart nextcloud
sleep 15

# Тест через HTTP
curl -L "http://ncrag.voronkov.club/login"
```

### Тест 2: Прямое подключение к контейнеру
```bash
# Найти IP Nextcloud контейнера
NEXTCLOUD_IP=$(docker inspect nextcloud | grep '"IPAddress"' | head -1 | grep -oP '\d+\.\d+\.\d+\.\d+')
echo "Nextcloud IP: $NEXTCLOUD_IP"

# Тест прямого подключения
curl -H "Host: ncrag.voronkov.club" "http://$NEXTCLOUD_IP/login"
```

### Тест 3: Проверка базы данных
```bash
# Проверить сессии в базе данных
docker exec nc-db psql -U nextcloud -d nextcloud -c "SELECT * FROM oc_sessions LIMIT 5;"

# Проверить пользователей
docker exec nc-db psql -U nextcloud -d nextcloud -c "SELECT uid, password FROM oc_users WHERE uid='admin';"
```

## 📋 ВОЗМОЖНЫЕ ПРИЧИНЫ

Если все вышеперечисленное не помогает, проблема может быть в:

1. **Баг в Nextcloud 31** - попробуйте понизить версию
2. **Проблема с базой данных** - сессии не сохраняются
3. **SSL/TLS проблемы** - неправильные сертификаты
4. **Конфликт в Apache конфигурации** внутри контейнера
5. **Проблема с файловой системой** - права доступа

## 🚨 КРИТИЧЕСКИЙ ТЕСТ

Выполните все команды выше и сообщите:
1. **Результат verbose curl** - какие заголовки Location возвращаются
2. **Работает ли без Redis**
3. **Что показывает config.php**
4. **Результат прямого подключения к контейнеру**

Это поможет точно определить источник проблемы!