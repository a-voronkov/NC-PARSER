# 🎯 ЗАВЕРШЕНИЕ ИСПРАВЛЕНИЯ

Отлично! Вы уже выполнили основные команды очистки. Теперь завершим процесс:

## 🚀 ЗАВЕРШАЮЩИЕ КОМАНДЫ

```bash
cd /srv/docker/nc-rag

# 1. Сбросить пароль админа
echo "=== СБРОС ПАРОЛЯ ==="
docker exec -e OC_PASS="$NEXTCLOUD_PASSWORD" -u www-data nextcloud php occ user:resetpassword admin --password-from-env

# 2. Очистить Redis кэш
echo "=== ОЧИСТКА REDIS ==="
docker exec nc-redis redis-cli FLUSHALL

# 3. Перезапустить Nextcloud
echo "=== ПЕРЕЗАПУСК ==="
docker restart nextcloud
sleep 20

# 4. Проверить статус
echo "=== ПРОВЕРКА СТАТУСА ==="
docker exec -u www-data nextcloud php occ status

# 5. Проверить текущую конфигурацию
echo "=== ТЕКУЩАЯ КОНФИГУРАЦИЯ ==="
docker exec -u www-data nextcloud php occ config:system:get trusted_domains
docker exec -u www-data nextcloud php occ config:system:get overwriteprotocol
docker exec -u www-data nextcloud php occ config:system:get trusted_proxies
```

## 🧪 ТЕСТ ЛОГИНА

```bash
echo "=== ТЕСТ ЛОГИНА ==="
COOKIE_JAR="/tmp/final_test.txt"
rm -f "$COOKIE_JAR"

# Получить страницу логина
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)

if [ -z "$CSRF_TOKEN" ]; then
    echo "❌ Не удалось получить CSRF токен"
    exit 1
fi

echo "CSRF Token: ${CSRF_TOKEN:0:40}..."

# Попробовать логин
echo "Отправка данных логина..."
RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \
    -d "user=admin" \
    -d "password=$NEXTCLOUD_PASSWORD" \
    -d "requesttoken=$CSRF_TOKEN" \
    -w "STATUS:%{http_code}\nURL:%{url_effective}\n" \
    "https://ncrag.voronkov.club/login")

# Извлечь результаты
STATUS=$(echo "$RESPONSE" | grep "STATUS:" | cut -d: -f2)
FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)

echo "HTTP Status: $STATUS"
echo "Final URL: $FINAL_URL"

# Проверить результат
if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ ВСЕ ЕЩЕ РЕДИРЕКТ НА ЛОГИН"
    echo "Попробуем verbose диагностику..."
    
    # Verbose тест для видения заголовков
    curl -v -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
        -d "user=admin" \
        -d "password=$NEXTCLOUD_PASSWORD" \
        -d "requesttoken=$CSRF_TOKEN" \
        "https://ncrag.voronkov.club/login" 2>&1 | grep -E "(< HTTP|< Location|< Set-Cookie)"
        
elif echo "$RESPONSE" | grep -q "files\|dashboard\|apps\|<title>Files"; then
    echo "✅ УСПЕХ! ЛОГИН РАБОТАЕТ!"
    echo "Найдено содержимое дашборда"
else
    echo "⚠️ НЕЯСНЫЙ РЕЗУЛЬТАТ"
    echo "Первые строки ответа:"
    echo "$RESPONSE" | head -10
fi

rm -f "$COOKIE_JAR"
```

## 🔍 ЕСЛИ ВСЕ ЕЩЕ НЕ РАБОТАЕТ

### Проверить таблицы сессий
```bash
# Посмотреть какие таблицы сессий есть
docker exec nc-db psql -U nextcloud -d nextcloud -c "\dt" | grep session

# Если есть другие таблицы сессий, очистить их
# docker exec nc-db psql -U nextcloud -d nextcloud -c "DELETE FROM oc_*session*;"
```

### Создать нового пользователя для теста
```bash
# Создать тестового пользователя
docker exec -e OC_PASS="$NEXTCLOUD_PASSWORD" -u www-data nextcloud php occ user:add testadmin --password-from-env --display-name="Test Admin"
docker exec -u www-data nextcloud php occ group:adduser admin testadmin

echo "Попробуйте войти как testadmin с паролем $NEXTCLOUD_PASSWORD"
```

### Проверить версию Nextcloud
```bash
docker exec -u www-data nextcloud php occ status
docker exec nextcloud cat /var/www/html/version.php
```

## 📋 СЛЕДУЮЩИЕ ШАГИ

**Выполните завершающие команды выше** и сообщите:

1. **Результат теста логина** - работает ли теперь?
2. **Вывод verbose curl** - если все еще редирект
3. **Статус Nextcloud** - версия и состояние
4. **Результат создания тестового пользователя**

Если ничего не поможет, возможно, придется **откатиться к Nextcloud 30** или **пересоздать контейнер полностью**.