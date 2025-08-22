# 🎯 ТОЧНОЕ ИСПРАВЛЕНИЕ с конкретными IP

## Сетевая информация
- **Traefik IP в backend**: `172.19.0.8`
- **Traefik IP в web**: `172.20.0.2`
- **Backend сеть**: `172.19.0.0/16`
- **Web сеть**: `172.20.0.0/16`

## 🚀 ТОЧНЫЕ КОМАНДЫ ИСПРАВЛЕНИЯ

```bash
ssh alfred361@ncrag.voronkov.club
cd /srv/docker/nc-rag

# 1. ТОЧНО настроить trusted_proxies с конкретными IP
docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 0 --value='172.19.0.8'
docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 1 --value='172.20.0.2'
docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 2 --value='172.19.0.0/16'
docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 3 --value='172.20.0.0/16'

# 2. КРИТИЧНО: Overwrite настройки
docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'
docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'
docker exec -u www-data nextcloud php occ config:system:set overwrite.cli.url --value='https://ncrag.voronkov.club'

# 3. Forwarded headers для Traefik
docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 0 --value='HTTP_X_FORWARDED_FOR'
docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 1 --value='HTTP_X_REAL_IP'
docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 2 --value='HTTP_X_FORWARDED_HOST'
docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 3 --value='HTTP_X_FORWARDED_PROTO'

# 4. Принудительный HTTPS
docker exec -u www-data nextcloud php occ config:system:set forcessl --value=true --type=boolean

# 5. ОЧИСТКА и ПЕРЕЗАПУСК
docker exec nc-redis redis-cli FLUSHALL
docker restart nextcloud traefik

# Подождать 30 секунд
sleep 30

# 6. Сбросить throttling для вашего IP
docker exec -u www-data nextcloud php occ security:bruteforce:reset 171.5.227.98
```

## 🧪 ТЕСТ ПОСЛЕ ИСПРАВЛЕНИЯ

```bash
# Проверить настройки
echo "=== ПРОВЕРКА НАСТРОЕК ==="
docker exec -u www-data nextcloud php occ config:system:get trusted_proxies
docker exec -u www-data nextcloud php occ config:system:get overwritehost
docker exec -u www-data nextcloud php occ config:system:get overwriteprotocol

# Тест логина
echo -e "\n=== ТЕСТ ЛОГИНА ==="
COOKIE_JAR="/tmp/exact_test.txt"
rm -f "$COOKIE_JAR"

LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)

echo "CSRF Token: ${CSRF_TOKEN:0:30}..."

# Попробовать логин
RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \
    -d "user=admin" \
    -d "password=$NEXTCLOUD_PASSWORD" \
    -d "requesttoken=$CSRF_TOKEN" \
    -w "STATUS:%{http_code}\nURL:%{url_effective}\n" \
    "https://ncrag.voronkov.club/login")

echo "$RESPONSE" | tail -2

FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)
echo "Final URL: $FINAL_URL"

if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ ВСЕ ЕЩЕ РЕДИРЕКТ"
    echo "Проверим verbose логин..."
    
    # Verbose тест для диагностики
    curl -v -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
        -d "user=admin" \
        -d "password=$NEXTCLOUD_PASSWORD" \
        -d "requesttoken=$CSRF_TOKEN" \
        "https://ncrag.voronkov.club/login" 2>&1 | grep -E "(Location:|HTTP/|Set-Cookie:)"
else
    echo "✅ УСПЕХ: $FINAL_URL"
fi

rm -f "$COOKIE_JAR"
```

## 🔍 ДОПОЛНИТЕЛЬНАЯ ДИАГНОСТИКА

Если проблема остается, проверьте:

### 1. Traefik правила маршрутизации
```bash
grep -A 15 "traefik.http.routers.nextcloud" docker-compose.yml
```

Должно быть примерно так:
```yaml
- "traefik.http.routers.nextcloud.rule=Host(`ncrag.voronkov.club`)"
- "traefik.http.routers.nextcloud.entrypoints=websecure"
- "traefik.http.routers.nextcloud.tls.certresolver=le"
```

### 2. Проверить конфликты маршрутов
```bash
# Найти все роутеры для этого домена
grep -n "ncrag.voronkov.club" docker-compose.yml
```

### 3. Проверить Node-RED маршрут
Я заметил в конфигурации, что Node-RED тоже использует тот же домен:
```yaml
traefik.http.routers.nodered.rule=Host(`ncrag.voronkov.club`) && PathPrefix(`/webhooks/nextcloud`)
```

Возможно, есть конфликт между маршрутами!

### 4. КРИТИЧЕСКАЯ ПРОВЕРКА: Приоритеты маршрутов
```bash
grep -A 5 -B 5 "priority" docker-compose.yml
```

## 🔥 ЕСЛИ ВСЕ ЕЩЕ НЕ РАБОТАЕТ

Попробуйте **временно отключить Node-RED маршрут**:

```bash
# Остановить Node-RED временно
docker stop node-red

# Перезапустить Traefik
docker restart traefik

# Попробовать логин снова
```

**Выполните точные команды выше и сообщите результат!**