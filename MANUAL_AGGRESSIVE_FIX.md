# 🔥 AGGRESSIVE MANUAL FIX

## Проблема
Постоянный редирект на `https://ncrag.voronkov.club/login?direct=1&user=admin`

## 🚀 НЕМЕДЛЕННЫЕ КОМАНДЫ

```bash
ssh alfred361@ncrag.voronkov.club
cd /srv/docker/nc-rag
```

### 1. Получить IP Traefik контейнера
```bash
docker inspect traefik | grep '"IPAddress"' | head -1
# Запомните IP адрес
```

### 2. ПОЛНЫЙ СБРОС всех proxy настроек
```bash
docker exec -u www-data nextcloud php occ config:system:delete trusted_proxies
docker exec -u www-data nextcloud php occ config:system:delete forwarded_for_headers
docker exec -u www-data nextcloud php occ config:system:delete overwritehost
docker exec -u www-data nextcloud php occ config:system:delete overwriteprotocol
docker exec -u www-data nextcloud php occ config:system:delete overwrite.cli.url
```

### 3. КОМПЛЕКСНАЯ настройка proxy (замените TRAEFIK_IP на реальный IP)
```bash
# Доверенные прокси - несколько подходов
docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 0 --value='172.19.0.0/16'
docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 1 --value='172.18.0.0/16'
docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 2 --value='TRAEFIK_IP'

# Overwrite настройки
docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'
docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'
docker exec -u www-data nextcloud php occ config:system:set overwrite.cli.url --value='https://ncrag.voronkov.club'

# Forwarded headers
docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 0 --value='HTTP_X_FORWARDED_FOR'
docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 1 --value='HTTP_X_REAL_IP'

# Принудительный HTTPS
docker exec -u www-data nextcloud php occ config:system:set forcessl --value=true --type=boolean
```

### 4. ЯДЕРНЫЙ ПЕРЕЗАПУСК
```bash
# Очистить все кэши
docker exec nc-redis redis-cli FLUSHALL

# Перезапустить и Nextcloud и Traefik
docker restart nextcloud traefik

# Подождать 30 секунд
sleep 30
```

### 5. ТЕСТ с разными подходами
```bash
COOKIE_JAR="/tmp/test_aggressive.txt"
rm -f "$COOKIE_JAR"

# Попробовать прямой доступ к дашборду
echo "=== ПРЯМОЙ ДОСТУП К ФАЙЛАМ ==="
curl -s -c "$COOKIE_JAR" -w "STATUS:%{http_code}\nURL:%{url_effective}\n" "https://ncrag.voronkov.club/index.php/apps/files"

# Обычный логин
echo -e "\n=== ОБЫЧНЫЙ ЛОГИН ==="
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)

echo "CSRF Token: ${CSRF_TOKEN:0:30}..."

# Логин БЕЗ следования редиректам
echo -e "\n=== ЛОГИН БЕЗ РЕДИРЕКТОВ ==="
curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
    -d "user=admin" \
    -d "password=$NEXTCLOUD_PASSWORD" \
    -d "requesttoken=$CSRF_TOKEN" \
    -w "STATUS:%{http_code}\nURL:%{url_effective}\n" \
    "https://ncrag.voronkov.club/login"

# Логин С следованием редиректам
echo -e "\n=== ЛОГИН С РЕДИРЕКТАМИ ==="
RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \
    -d "user=admin" \
    -d "password=$NEXTCLOUD_PASSWORD" \
    -d "requesttoken=$CSRF_TOKEN" \
    -w "STATUS:%{http_code}\nURL:%{url_effective}\n" \
    "https://ncrag.voronkov.club/login")

echo "$RESPONSE" | tail -2

FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)
if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ ВСЕ ЕЩЕ РЕДИРЕКТ НА ЛОГИН"
else
    echo "✅ УСПЕХ: $FINAL_URL"
fi
```

## 🔍 ЕСЛИ ВСЕ ЕЩЕ НЕ РАБОТАЕТ

### Проверить Traefik маршрутизацию
```bash
# Посмотреть все Traefik правила
grep -A 10 "traefik.http.routers.nextcloud" docker-compose.yml

# Проверить логи Traefik во время логина
docker logs traefik --tail 20 -f &
# Попробуйте войти и посмотрите логи
```

### Проверить конфликты маршрутов
```bash
# Найти все HTTP роутеры
grep "traefik.http.routers" docker-compose.yml
```

### Альтернативное решение - отключить Traefik
```bash
# Временно обойти Traefik (ТОЛЬКО ДЛЯ ТЕСТА!)
docker stop traefik
docker run -d --name temp_proxy -p 80:80 -p 443:443 --network nc-rag_backend nginx:alpine

# Попробовать прямое подключение к Nextcloud
curl -H "Host: ncrag.voronkov.club" "http://172.19.0.X:80/login"
```

## 🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ

После этих исправлений:
1. ✅ Nextcloud должен доверять Traefik как прокси
2. ✅ URL должны генерироваться правильно
3. ✅ Редирект после логина должен вести на дашборд

## 📞 ЕСЛИ НИЧЕГО НЕ ПОМОГАЕТ

Возможные глубинные проблемы:
1. **Конфликт в docker-compose.yml** - несколько сервисов на одном домене
2. **SSL/TLS проблемы** - неправильные сертификаты
3. **Баг в Nextcloud 31** - попробуйте понизить версию
4. **Проблема с базой данных** - сессии не сохраняются корректно

Попробуйте эти команды и сообщите результат!