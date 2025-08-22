# 🚨 ЯДЕРНЫЕ ОПЦИИ - КАРДИНАЛЬНЫЕ РЕШЕНИЯ

Раз стандартные исправления не работают, попробуем кардинальные методы.

## 🔥 ОПЦИЯ 1: ПЕРЕСОЗДАНИЕ NEXTCLOUD КОНТЕЙНЕРА

```bash
ssh alfred361@ncrag.voronkov.club
cd /srv/docker/nc-rag

# 1. Создать бэкап данных
echo "=== СОЗДАНИЕ БЭКАПА ==="
docker exec nextcloud tar -czf /tmp/nextcloud_backup.tar.gz /var/www/html/config /var/www/html/data
docker cp nextcloud:/tmp/nextcloud_backup.tar.gz ./nextcloud_backup_$(date +%Y%m%d).tar.gz
echo "✅ Бэкап создан"

# 2. Остановить и удалить Nextcloud контейнер
docker stop nextcloud nextcloud-cron
docker rm nextcloud nextcloud-cron

# 3. Удалить volume (ОСТОРОЖНО!)
# docker volume rm nc-rag_nextcloud_data  # ТОЛЬКО если готовы потерять данные

# 4. Пересоздать контейнеры
docker compose up -d nextcloud nextcloud-cron

# 5. Подождать инициализации
sleep 60

# 6. Восстановить конфигурацию
docker exec -u www-data nextcloud php occ maintenance:mode --off
docker exec -e OC_PASS="$NEXTCLOUD_PASSWORD" -u www-data nextcloud php occ user:resetpassword admin --password-from-env

# 7. Настроить proxy заново
docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 0 --value='172.19.0.8'
docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'
docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'
```

## 🔄 ОПЦИЯ 2: ОТКАТ К NEXTCLOUD 30

```bash
# 1. Изменить версию в docker-compose.yml
sed -i 's/nextcloud:31-apache/nextcloud:30-apache/g' docker-compose.yml

# 2. Пересоздать контейнеры
docker compose down
docker compose up -d

# 3. Подождать инициализации
sleep 60

# 4. Проверить версию
docker exec -u www-data nextcloud php occ status

# 5. Настроить заново
docker exec -e OC_PASS="$NEXTCLOUD_PASSWORD" -u www-data nextcloud php occ user:resetpassword admin --password-from-env
```

## 🛠️ ОПЦИЯ 3: АЛЬТЕРНАТИВНАЯ АУТЕНТИФИКАЦИЯ

```bash
# 1. Создать нового пользователя для теста
docker exec -u www-data nextcloud php occ user:add testuser --password-from-env --display-name="Test User" --group="admin"

# 2. Попробовать войти под тестовым пользователем
# (используйте тот же пароль из $NEXTCLOUD_PASSWORD)

# 3. Если работает, проблема с пользователем admin
```

## 🔍 ОПЦИЯ 4: ГЛУБОКАЯ ДИАГНОСТИКА APACHE

```bash
# 1. Проверить Apache конфигурацию внутри контейнера
docker exec nextcloud cat /etc/apache2/sites-available/000-default.conf

# 2. Проверить Apache модули
docker exec nextcloud apache2ctl -M | grep -E "(rewrite|headers|proxy)"

# 3. Проверить Apache логи
docker exec nextcloud tail -20 /var/log/apache2/access.log
docker exec nextcloud tail -20 /var/log/apache2/error.log

# 4. Проверить PHP конфигурацию
docker exec nextcloud php -i | grep -E "(session|cookie)"
```

## 🧪 ОПЦИЯ 5: ТЕСТ ПРЯМОГО ПОДКЛЮЧЕНИЯ К БАЗЕ

```bash
# 1. Проверить сессии в базе данных
docker exec nc-db psql -U nextcloud -d nextcloud -c "
SELECT 
    id, 
    uid, 
    login_name,
    substr(token, 1, 10) as token_start,
    last_activity 
FROM oc_authtoken 
WHERE uid='admin' 
ORDER BY last_activity DESC 
LIMIT 5;
"

# 2. Проверить активные сессии
docker exec nc-db psql -U nextcloud -d nextcloud -c "
SELECT COUNT(*) as session_count FROM oc_sessions;
"

# 3. Очистить все сессии и токены
docker exec nc-db psql -U nextcloud -d nextcloud -c "
DELETE FROM oc_sessions;
DELETE FROM oc_authtoken WHERE uid='admin';
"
```

## ⚡ ОПЦИЯ 6: МИНИМАЛЬНАЯ КОНФИГУРАЦИЯ

```bash
# 1. Сбросить ВСЮ конфигурацию к минимуму
docker exec -u www-data nextcloud php occ config:system:delete trusted_proxies
docker exec -u www-data nextcloud php occ config:system:delete forwarded_for_headers
docker exec -u www-data nextcloud php occ config:system:delete overwritehost
docker exec -u www-data nextcloud php occ config:system:delete overwriteprotocol
docker exec -u www-data nextcloud php occ config:system:delete overwrite.cli.url
docker exec -u www-data nextcloud php occ config:system:delete memcache.distributed
docker exec -u www-data nextcloud php occ config:system:delete memcache.locking
docker exec -u www-data nextcloud php occ config:system:delete forcessl

# 2. Установить ТОЛЬКО необходимый минимум
docker exec -u www-data nextcloud php occ config:system:set trusted_domains 0 --value='ncrag.voronkov.club'
docker exec -u www-data nextcloud php occ config:system:set trusted_domains 1 --value='localhost'

# 3. Перезапуск
docker restart nextcloud
sleep 20

# 4. Тест с минимальной конфигурацией
COOKIE_JAR="/tmp/minimal_test.txt"
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
echo "URL с минимальной конфигурацией: $FINAL_URL"
```

## 🚨 КРИТИЧЕСКИЙ ВЫБОР

Попробуйте **ОПЦИЮ 6 (минимальная конфигурация)** первой - она наименее разрушительная.

Если не поможет, переходите к **ОПЦИИ 1 (пересоздание контейнера)**.

**Какую опцию попробуете первой?**