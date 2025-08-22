# 🔍 ПРОВЕРКА КОНФЛИКТОВ МАРШРУТИЗАЦИИ

## Гипотеза
Возможно, есть конфликт между маршрутами Nextcloud и Node-RED в Traefik.

## 🚀 КОМАНДЫ ДЛЯ ПРОВЕРКИ

```bash
ssh alfred361@ncrag.voronkov.club
cd /srv/docker/nc-rag

# 1. Найти ВСЕ сервисы на домене ncrag.voronkov.club
echo "=== ВСЕ СЕРВИСЫ НА ДОМЕНЕ ==="
grep -n "ncrag.voronkov.club" docker-compose.yml

# 2. Проверить Nextcloud маршруты
echo -e "\n=== NEXTCLOUD МАРШРУТЫ ==="
grep -A 10 -B 2 "traefik.http.routers.nextcloud" docker-compose.yml

# 3. Проверить Node-RED маршруты  
echo -e "\n=== NODE-RED МАРШРУТЫ ==="
grep -A 10 -B 2 "traefik.http.routers.nodered" docker-compose.yml

# 4. Проверить приоритеты
echo -e "\n=== ПРИОРИТЕТЫ МАРШРУТОВ ==="
grep -n "priority" docker-compose.yml

# 5. Проверить правила маршрутизации
echo -e "\n=== ПРАВИЛА МАРШРУТИЗАЦИИ ==="
grep "traefik.http.routers.*rule" docker-compose.yml
```

## 🧪 ТЕСТ БЕЗ NODE-RED

```bash
# Остановить Node-RED временно
echo "=== ОСТАНОВКА NODE-RED ==="
docker stop node-red

# Перезапустить Traefik
docker restart traefik
sleep 15

# Тест логина без Node-RED
echo -e "\n=== ТЕСТ ЛОГИНА БЕЗ NODE-RED ==="
COOKIE_JAR="/tmp/no_nodered.txt"
rm -f "$COOKIE_JAR"

LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)

echo "CSRF: ${CSRF_TOKEN:0:30}..."

RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \
    -d "user=admin" \
    -d "password=$NEXTCLOUD_PASSWORD" \
    -d "requesttoken=$CSRF_TOKEN" \
    -w "STATUS:%{http_code}\nURL:%{url_effective}\n" \
    "https://ncrag.voronkov.club/login")

STATUS=$(echo "$RESPONSE" | grep "STATUS:" | cut -d: -f2)
FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)

echo "Status: $STATUS"
echo "Final URL: $FINAL_URL"

if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ ВСЕ ЕЩЕ РЕДИРЕКТ (Node-RED не причина)"
    
    # Вернуть Node-RED
    docker start node-red
    
elif echo "$RESPONSE" | grep -q "files\|dashboard"; then
    echo "✅ УСПЕХ БЕЗ NODE-RED!"
    echo "🎯 Node-RED вызывал конфликт маршрутов!"
    
    # Не запускаем Node-RED пока не исправим конфигурацию
    
else
    echo "⚠️ Неясный ответ:"
    echo "$RESPONSE" | head -10
fi

rm -f "$COOKIE_JAR"
```

## 🔧 ЕСЛИ NODE-RED ВЫЗЫВАЕТ КОНФЛИКТ

Если логин работает без Node-RED, то проблема в приоритетах маршрутов:

### Проверить текущие приоритеты:
```bash
grep -A 15 "traefik.http.routers" docker-compose.yml | grep -E "(rule|priority)"
```

### Исправить приоритеты в docker-compose.yml:

Nextcloud должен иметь **более низкий приоритет** (большее число):
```yaml
# Node-RED (высокий приоритет для специфического пути)
- "traefik.http.routers.nodered.priority=1000"
- "traefik.http.routers.nodered.rule=Host(`ncrag.voronkov.club`) && PathPrefix(`/webhooks/nextcloud`)"

# Nextcloud (низкий приоритет для общего домена)  
- "traefik.http.routers.nextcloud.priority=100"
- "traefik.http.routers.nextcloud.rule=Host(`ncrag.voronkov.club`) && !PathPrefix(`/webhooks/nextcloud`)"
```

## 🚀 АЛЬТЕРНАТИВНОЕ РЕШЕНИЕ

Если проблема не в Node-RED, попробуйте:

### 1. Проверить SSL сертификаты
```bash
# Проверить сертификат
openssl s_client -connect ncrag.voronkov.club:443 -servername ncrag.voronkov.club < /dev/null

# Проверить Traefik сертификаты
docker exec traefik ls -la /letsencrypt/
```

### 2. Попробовать HTTP вместо HTTPS (временно)
```bash
# Изменить overwrite protocol на HTTP для теста
docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='http'
docker exec -u www-data nextcloud php occ config:system:set overwrite.cli.url --value='http://ncrag.voronkov.club'
docker restart nextcloud

# Тест через HTTP
curl -L "http://ncrag.voronkov.club/login"
```

## 📋 ВЫПОЛНИТЕ КОМАНДЫ И СООБЩИТЕ:
1. Результат проверки маршрутов
2. Работает ли логин без Node-RED
3. Какие приоритеты у маршрутов
4. Результат теста