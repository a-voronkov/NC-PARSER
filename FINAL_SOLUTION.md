# 🎯 ФИНАЛЬНОЕ РЕШЕНИЕ ПРОБЛЕМЫ

Основываясь на исследовании, проблема может быть в **таблице bruteforce_attempts** или в **конкретном баге Nextcloud 31**.

## 🚀 РЕШЕНИЕ 1: ОЧИСТКА ТАБЛИЦЫ BRUTEFORCE

```bash
ssh alfred361@ncrag.voronkov.club
cd /srv/docker/nc-rag

# 1. Очистить таблицу попыток взлома в PostgreSQL
echo "=== ОЧИСТКА BRUTEFORCE ТАБЛИЦЫ ==="
docker exec nc-db psql -U nextcloud -d nextcloud -c "TRUNCATE oc_bruteforce_attempts RESTART IDENTITY;"

# 2. Очистить все сессии и токены
docker exec nc-db psql -U nextcloud -d nextcloud -c "DELETE FROM oc_sessions;"
docker exec nc-db psql -U nextcloud -d nextcloud -c "DELETE FROM oc_authtoken WHERE uid='admin';"

# 3. Сбросить к минимальной конфигурации
docker exec -u www-data nextcloud php occ config:system:delete trusted_proxies
docker exec -u www-data nextcloud php occ config:system:delete forwarded_for_headers
docker exec -u www-data nextcloud php occ config:system:delete overwritehost
docker exec -u www-data nextcloud php occ config:system:delete overwriteprotocol
docker exec -u www-data nextcloud php occ config:system:delete memcache.distributed
docker exec -u www-data nextcloud php occ config:system:delete memcache.locking

# 4. Установить только базовые настройки
docker exec -u www-data nextcloud php occ config:system:set trusted_domains 0 --value='ncrag.voronkov.club'
docker exec -u www-data nextcloud php occ config:system:set trusted_domains 1 --value='localhost'
docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'

# 5. Сбросить пароль
docker exec -e OC_PASS="$NEXTCLOUD_PASSWORD" -u www-data nextcloud php occ user:resetpassword admin --password-from-env

# 6. Перезапуск
docker restart nextcloud
sleep 20

# 7. Тест
COOKIE_JAR="/tmp/clean_test.txt"
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
echo "Final URL: $FINAL_URL"

if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ ВСЕ ЕЩЕ НЕ РАБОТАЕТ"
else
    echo "✅ УСПЕХ!"
fi
```

## 🔄 РЕШЕНИЕ 2: ОТКАТ К NEXTCLOUD 30

Если первое решение не поможет:

```bash
# 1. Изменить версию в docker-compose.yml
sed -i 's/nextcloud:31-apache/nextcloud:30-apache/g' docker-compose.yml

# 2. Пересоздать
docker compose down
docker compose up -d
sleep 60

# 3. Настроить
docker exec -e OC_PASS="$NEXTCLOUD_PASSWORD" -u www-data nextcloud php occ user:resetpassword admin --password-from-env
docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'

# 4. Тест
```

## 🛠️ РЕШЕНИЕ 3: СОЗДАНИЕ НОВОГО ПОЛЬЗОВАТЕЛЯ

```bash
# Создать тестового пользователя
docker exec -u www-data nextcloud php occ user:add testuser --password-from-env --display-name="Test User"
docker exec -u www-data nextcloud php occ group:adduser admin testuser

# Попробовать войти под testuser с тем же паролем
```

## 🔍 ДИАГНОСТИКА: ПРОВЕРКА VERBOSE CURL

Перед применением решений, выполните это для диагностики:

```bash
cd /srv/docker/nc-rag
COOKIE_JAR="/tmp/verbose.txt"
rm -f "$COOKIE_JAR"

# Получить CSRF
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)

# Verbose логин - ВАЖНО ПОСМОТРЕТЬ ЗАГОЛОВКИ
curl -v -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
    -d "user=admin" \
    -d "password=$NEXTCLOUD_PASSWORD" \
    -d "requesttoken=$CSRF_TOKEN" \
    "https://ncrag.voronkov.club/login" 2>&1 | grep -E "(< HTTP|< Location|< Set-Cookie)"

rm -f "$COOKIE_JAR"
```

**Сначала выполните диагностику verbose curl** - она покажет точные заголовки Location.

**Затем попробуйте РЕШЕНИЕ 1** (очистка bruteforce таблицы).

Сообщите результаты обеих команд!