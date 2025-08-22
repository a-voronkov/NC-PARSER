# 🚀 ПРИМЕНЕНИЕ BEST PRACTICES КОНФИГУРАЦИИ

## 🎯 Ключевые улучшения в новой конфигурации:

1. **Правильные заголовки прокси** для Nextcloud
2. **Четкое разделение сетей** (web для внешних, backend для внутренних)
3. **Health checks** для всех сервисов
4. **Правильные middleware** с безопасными заголовками
5. **Оптимизированные настройки** производительности
6. **Убран проблемный HSTS middleware**

## 🔧 ПРИМЕНЕНИЕ НОВОЙ КОНФИГУРАЦИИ

```bash
cd /srv/docker/nc-rag

# 1. Создать бэкап текущей конфигурации
cp docker-compose.yml docker-compose.yml.backup.$(date +%Y%m%d_%H%M%S)

# 2. Остановить все сервисы
docker compose down

# 3. Заменить на новую конфигурацию
# Скопируйте содержимое из /workspace/docker-compose-best-practices.yml
# и замените им текущий docker-compose.yml

# 4. Создать директорию для конфигурации Nextcloud
mkdir -p ./nextcloud-config

# 5. Проверить .env файл
echo "=== ПРОВЕРКА .ENV ==="
cat .env | grep -E "(NEXTCLOUD_|POSTGRES_|REDIS_)"

# Убедитесь, что пароли правильные:
echo "NEXTCLOUD_PASS должен быть: $NEXTCLOUD_PASSWORD"
echo "NEXTCLOUD_ADMIN_PASSWORD должен быть: $NEXTCLOUD_PASSWORD"

# 6. Обновить .env с правильными паролями
sed -i "s/NEXTCLOUD_PASS=.*/NEXTCLOUD_PASS=$NEXTCLOUD_PASSWORD/" .env
sed -i "s/NEXTCLOUD_ADMIN_PASSWORD=.*/NEXTCLOUD_ADMIN_PASSWORD=$NEXTCLOUD_PASSWORD/" .env

# 7. Запустить с новой конфигурацией
echo "=== ЗАПУСК С НОВОЙ КОНФИГУРАЦИЕЙ ==="
docker compose up -d

# 8. Подождать полной инициализации
echo "Ожидание инициализации (2 минуты)..."
sleep 120

# 9. Проверить статус всех сервисов
echo "=== СТАТУС СЕРВИСОВ ==="
docker compose ps

# 10. Проверить health checks
echo "=== HEALTH CHECKS ==="
docker ps --format "table {{.Names}}\t{{.Status}}"

# 11. Настроить Nextcloud для работы с новой конфигурацией прокси
echo "=== НАСТРОЙКА NEXTCLOUD ==="

# Получить точный IP Traefik в web сети
TRAEFIK_WEB_IP=$(docker inspect traefik | grep -A 20 '"nc-rag_web"' | grep '"IPAddress"' | grep -oP '\d+\.\d+\.\d+\.\d+')
echo "Traefik Web IP: $TRAEFIK_WEB_IP"

# Настроить trusted proxies
docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 0 --value="$TRAEFIK_WEB_IP"
docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 1 --value='172.20.0.0/16'

# Настроить домены и overwrite параметры
docker exec -u www-data nextcloud php occ config:system:set trusted_domains 0 --value='ncrag.voronkov.club'
docker exec -u www-data nextcloud php occ config:system:set trusted_domains 1 --value='localhost'
docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'
docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'
docker exec -u www-data nextcloud php occ config:system:set overwrite.cli.url --value='https://ncrag.voronkov.club'

# Настроить forwarded headers
docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 0 --value='HTTP_X_FORWARDED_FOR'
docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 1 --value='HTTP_X_REAL_IP'

# Настроить Redis кэширование (опционально)
docker exec -u www-data nextcloud php occ config:system:set memcache.distributed --value='\OC\Memcache\Redis'
docker exec -u www-data nextcloud php occ config:system:set memcache.locking --value='\OC\Memcache\Redis'

# 12. Проверить статус Nextcloud
echo "=== СТАТУС NEXTCLOUD ==="
docker exec -u www-data nextcloud php occ status

# 13. ТЕСТ ЛОГИНА
echo "=== ТЕСТ ЛОГИНА ==="
COOKIE_JAR="/tmp/best_practices_test.txt"
rm -f "$COOKIE_JAR"

# Проверить доступность
echo "1. Проверка доступности..."
MAIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://ncrag.voronkov.club/")
LOGIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://ncrag.voronkov.club/login")
echo "Главная страница: $MAIN_STATUS"
echo "Страница логина: $LOGIN_STATUS"

# Получить CSRF токен
echo "2. Получение CSRF токена..."
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)

if [ -z "$CSRF_TOKEN" ]; then
    echo "❌ Не удалось получить CSRF токен"
    echo "Проверим содержимое страницы:"
    echo "$LOGIN_PAGE" | head -20
else
    echo "✅ CSRF Token: ${CSRF_TOKEN:0:40}..."
    
    # Тест логина
    echo "3. Тест логина..."
    RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \
        -d "user=admin" \
        -d "password=$NEXTCLOUD_PASSWORD" \
        -d "requesttoken=$CSRF_TOKEN" \
        -w "STATUS:%{http_code}\nURL:%{url_effective}\n" \
        "https://ncrag.voronkov.club/login")
    
    STATUS=$(echo "$RESPONSE" | grep "STATUS:" | cut -d: -f2)
    FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)
    
    echo "HTTP Status: $STATUS"
    echo "Final URL: $FINAL_URL"
    
    if [[ "$FINAL_URL" == *"/login"* ]]; then
        echo "❌ ВСЕ ЕЩЕ РЕДИРЕКТ НА ЛОГИН"
        echo "Попробуйте verbose диагностику..."
        
        # Verbose тест
        curl -v -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
            -d "user=admin" \
            -d "password=$NEXTCLOUD_PASSWORD" \
            -d "requesttoken=$CSRF_TOKEN" \
            "https://ncrag.voronkov.club/login" 2>&1 | grep -E "(< HTTP|< Location|< Set-Cookie)"
            
    elif echo "$RESPONSE" | grep -q "files\|dashboard\|apps"; then
        echo "✅ УСПЕХ! ЛОГИН РАБОТАЕТ!"
        echo "Best practices конфигурация успешно применена!"
    else
        echo "⚠️ НЕЯСНЫЙ РЕЗУЛЬТАТ"
        echo "Первые строки ответа:"
        echo "$RESPONSE" | head -10
    fi
fi

rm -f "$COOKIE_JAR"
```

## 🔍 КЛЮЧЕВЫЕ ОСОБЕННОСТИ НОВОЙ КОНФИГУРАЦИИ

### 1. **Правильные заголовки прокси:**
```yaml
- "traefik.http.middlewares.nextcloud-headers.headers.customRequestHeaders.X-Forwarded-Proto=https"
- "traefik.http.middlewares.nextcloud-headers.headers.customRequestHeaders.X-Forwarded-Host=ncrag.voronkov.club"
- "traefik.http.middlewares.nextcloud-headers.headers.hostsProxyHeaders=X-Forwarded-Host"
```

### 2. **Четкое разделение сетей:**
- **web**: Для внешнего доступа (Traefik ↔ Nextcloud, Node-RED)
- **backend**: Для внутреннего взаимодействия (База данных, Redis, etc.)

### 3. **Health checks:**
- Все сервисы имеют health checks для надежности
- Зависимости настроены правильно

### 4. **Безопасность:**
- Правильные security headers
- Внутренняя сеть изолирована
- Минимальные права доступа

## 📋 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ

После применения best practices:
1. ✅ **Правильные заголовки** от Traefik к Nextcloud
2. ✅ **Корректные перенаправления** после логина
3. ✅ **Стабильная работа** всех сервисов
4. ✅ **Безопасная конфигурация** с изоляцией сетей

**Примените новую конфигурацию и сообщите результат!**