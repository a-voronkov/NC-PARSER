# 🔥 ЧИСТАЯ УСТАНОВКА NEXTCLOUD

## ⚠️ ПРЕДУПРЕЖДЕНИЕ
Это удалит ВСЕ данные Nextcloud! Убедитесь, что важных данных нет или они сохранены.

## 🗂️ ШАГ 1: СОЗДАНИЕ БЭКАПОВ (опционально)

```bash
cd /srv/docker/nc-rag

# Создать бэкап конфигурации (если нужно)
docker exec nextcloud tar -czf /tmp/nextcloud_config_backup.tar.gz /var/www/html/config
docker cp nextcloud:/tmp/nextcloud_config_backup.tar.gz ./config_backup_$(date +%Y%m%d).tar.gz

# Создать бэкап .env файла
cp .env .env.backup.$(date +%Y%m%d)

echo "✅ Бэкапы созданы"
```

## 🧹 ШАГ 2: ПОЛНАЯ ОЧИСТКА

```bash
cd /srv/docker/nc-rag

# 1. Остановить все сервисы
echo "=== ОСТАНОВКА СЕРВИСОВ ==="
docker compose down

# 2. Удалить volumes с данными
echo "=== УДАЛЕНИЕ VOLUMES ==="
docker volume rm nc-rag_nextcloud_data
docker volume rm nc-rag_db_data
docker volume rm nc-rag_node_red_data

# Опционально: удалить и SSL сертификаты для полной очистки
# docker volume rm nc-rag_traefik_letsencrypt

# 3. Очистить неиспользуемые образы и контейнеры
docker system prune -f

echo "✅ Очистка завершена"
```

## 🚀 ШАГ 3: ЧИСТАЯ УСТАНОВКА

```bash
cd /srv/docker/nc-rag

# 1. Проверить .env файл
echo "=== ПРОВЕРКА .ENV ==="
cat .env | grep -E "(NEXTCLOUD_|POSTGRES_)"

# Убедиться, что пароли правильные:
# NEXTCLOUD_PASS должен быть = $NEXTCLOUD_PASSWORD
# NEXTCLOUD_ADMIN_PASSWORD должен быть = $NEXTCLOUD_PASSWORD

# 2. Обновить .env с правильными паролями
echo "=== ОБНОВЛЕНИЕ .ENV ==="
sed -i "s/NEXTCLOUD_PASS=.*/NEXTCLOUD_PASS=$NEXTCLOUD_PASSWORD/" .env
sed -i "s/NEXTCLOUD_ADMIN_PASSWORD=.*/NEXTCLOUD_ADMIN_PASSWORD=$NEXTCLOUD_PASSWORD/" .env

# 3. Запустить сервисы заново
echo "=== ЗАПУСК СЕРВИСОВ ==="
docker compose up -d

# 4. Подождать инициализации (это займет время!)
echo "=== ОЖИДАНИЕ ИНИЦИАЛИЗАЦИИ ==="
echo "Ждем 2 минуты для полной инициализации..."
sleep 120

# 5. Проверить статус контейнеров
echo "=== СТАТУС КОНТЕЙНЕРОВ ==="
docker ps --format "table {{.Names}}\t{{.Status}}"

# 6. Проверить статус Nextcloud
echo "=== СТАТУС NEXTCLOUD ==="
docker exec -u www-data nextcloud php occ status

# 7. Проверить пользователя admin
echo "=== ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ ==="
docker exec -u www-data nextcloud php occ user:info admin
```

## 🧪 ШАГ 4: ТЕСТ ЧИСТОЙ УСТАНОВКИ

```bash
echo "=== ТЕСТ ЛОГИНА НА ЧИСТОЙ УСТАНОВКЕ ==="
COOKIE_JAR="/tmp/clean_install_test.txt"
rm -f "$COOKIE_JAR"

# Проверить доступность страницы
echo "1. Проверка доступности..."
SITE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://ncrag.voronkov.club/login")
echo "Статус сайта: $SITE_STATUS"

if [ "$SITE_STATUS" != "200" ]; then
    echo "❌ Сайт недоступен"
    exit 1
fi

# Получить страницу логина
echo "2. Получение страницы логина..."
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)

if [ -z "$CSRF_TOKEN" ]; then
    echo "❌ Не удалось получить CSRF токен"
    echo "Проверим содержимое страницы:"
    echo "$LOGIN_PAGE" | head -20
    exit 1
fi

echo "3. CSRF Token: ${CSRF_TOKEN:0:40}..."

# Попробовать логин
echo "4. Отправка данных логина..."
RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \
    -d "user=admin" \
    -d "password=$NEXTCLOUD_PASSWORD" \
    -d "requesttoken=$CSRF_TOKEN" \
    -w "STATUS:%{http_code}\nURL:%{url_effective}\n" \
    "https://ncrag.voronkov.club/login")

# Извлечь результаты
STATUS=$(echo "$RESPONSE" | grep "STATUS:" | cut -d: -f2)
FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)

echo "5. HTTP Status: $STATUS"
echo "6. Final URL: $FINAL_URL"

# Проверить результат
if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ ВСЕ ЕЩЕ РЕДИРЕКТ НА ЛОГИН"
    echo "Это может быть фундаментальная проблема с конфигурацией"
    
    # Показать первые строки ответа для диагностики
    echo "Первые строки ответа:"
    echo "$RESPONSE" | head -15
    
elif echo "$RESPONSE" | grep -q "files\|dashboard\|apps\|<title>Files"; then
    echo "✅ УСПЕХ! ЧИСТАЯ УСТАНОВКА РАБОТАЕТ!"
    echo "Логин успешен, найдено содержимое дашборда"
    
    # Настроить оптимальную конфигурацию для продакшена
    echo "Настройка оптимальной конфигурации..."
    docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 0 --value='172.19.0.8'
    docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'
    docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'
    docker exec -u www-data nextcloud php occ config:system:set memcache.distributed --value='\OC\Memcache\Redis'
    docker exec -u www-data nextcloud php occ config:system:set memcache.locking --value='\OC\Memcache\Redis'
    
else
    echo "⚠️ НЕЯСНЫЙ РЕЗУЛЬТАТ"
    echo "Статус: $STATUS"
    echo "URL: $FINAL_URL"
    echo "Первые строки ответа:"
    echo "$RESPONSE" | head -10
fi

rm -f "$COOKIE_JAR"
```

## 📋 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ

После чистой установки:
1. ✅ **Nextcloud инициализируется с нуля**
2. ✅ **Пользователь admin создается с правильным паролем**
3. ✅ **Никаких старых конфигураций или кэшей**
4. ✅ **Логин должен работать сразу**

## 🔄 ЕСЛИ ЧИСТАЯ УСТАНОВКА НЕ ПОМОЖЕТ

Тогда проблема может быть в:
1. **docker-compose.yml конфигурации**
2. **Traefik настройках**
3. **SSL сертификатах**
4. **Баге в Nextcloud 31**

**Выполните чистую установку и сообщите результат!**