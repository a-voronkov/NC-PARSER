# ⚡ БЫСТРОЕ ИСПРАВЛЕНИЕ

## 🚨 НАЙДЕНА ПРОБЛЕМА!

В вашем `docker-compose.yml` **все еще есть ссылка на HSTS middleware**:
```yaml
- "traefik.http.routers.nextcloud.middlewares=hsts"
```

Но **HSTS middleware закомментирован** в Traefik! Это создает 404 ошибку.

## 🚀 НЕМЕДЛЕННОЕ ИСПРАВЛЕНИЕ

```bash
cd /srv/docker/nc-rag

# 1. Остановить сервисы
docker compose down

# 2. УБРАТЬ ссылку на HSTS middleware из Nextcloud
sed -i 's/traefik.http.routers.nextcloud.middlewares=hsts/# traefik.http.routers.nextcloud.middlewares=hsts/' docker-compose.yml

# 3. Проверить, что изменение применилось
grep -n "middlewares=hsts" docker-compose.yml
# Должно показать закомментированную строку

# 4. Запустить без middleware
docker compose up -d
sleep 60

# 5. Настроить Nextcloud
docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 0 --value='172.19.0.8'
docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'
docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'

# 6. ТЕСТ
echo "=== ТЕСТ БЕЗ HSTS MIDDLEWARE ==="

# Проверить главную страницу (должна быть не 404)
curl -s -o /dev/null -w "Главная: %{http_code}\n" "https://ncrag.voronkov.club/"

# Тест логина
COOKIE_JAR="/tmp/quick_fix.txt"
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
    echo "❌ ВСЕ ЕЩЕ РЕДИРЕКТ"
    echo "Попробуйте другие тесты из BYPASS_TRAEFIK_TEST.md"
else
    echo "✅ УСПЕХ! ПРОБЛЕМА БЫЛА В HSTS MIDDLEWARE!"
fi

rm -f "$COOKIE_JAR"
```

## 📋 ЧТО ДОЛЖНО ИЗМЕНИТЬСЯ

После исправления:
1. ✅ **Главная страница**: не 404, а редирект на логин
2. ✅ **Логин**: должен работать нормально
3. ✅ **Никаких ошибок** в Traefik логах

**Попробуйте быстрое исправление первым!**

Если не поможет - выполните полную диагностику из `BYPASS_TRAEFIK_TEST.md`.