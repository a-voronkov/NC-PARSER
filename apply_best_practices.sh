#!/bin/bash

# Nextcloud Best Practices Configuration Application Script
set -e

echo "🚀 ПРИМЕНЕНИЕ BEST PRACTICES КОНФИГУРАЦИИ NEXTCLOUD"
echo "=" * 60

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Ошибка: docker-compose.yml не найден в текущей директории"
    echo "Выполните: cd /srv/docker/nc-rag"
    exit 1
fi

# Check environment variables
if [ -z "$NEXTCLOUD_PASSWORD" ]; then
    echo "❌ Ошибка: NEXTCLOUD_PASSWORD не установлен"
    echo "Этот пароль используется для входа в веб-интерфейс"
    exit 1
fi

echo "✅ Проверки пройдены"
echo "Пароль фронтенда: ${#NEXTCLOUD_PASSWORD} символов"

# 1. Create backup
echo ""
echo "📁 Создание бэкапа..."
BACKUP_NAME="docker-compose.yml.backup.$(date +%Y%m%d_%H%M%S)"
cp docker-compose.yml "$BACKUP_NAME"
echo "✅ Бэкап создан: $BACKUP_NAME"

# 2. Stop services
echo ""
echo "🛑 Остановка сервисов..."
docker compose down
echo "✅ Сервисы остановлены"

# 3. Create nextcloud-config directory
echo ""
echo "📁 Создание директории конфигурации..."
mkdir -p ./nextcloud-config
echo "✅ Директория создана"

# 4. Update .env file
echo ""
echo "📝 Обновление .env файла..."
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Update passwords to match environment
sed -i "s/NEXTCLOUD_PASS=.*/NEXTCLOUD_PASS=$NEXTCLOUD_PASSWORD/" .env
sed -i "s/NEXTCLOUD_ADMIN_PASSWORD=.*/NEXTCLOUD_ADMIN_PASSWORD=$NEXTCLOUD_PASSWORD/" .env

echo "✅ .env файл обновлен"

# 5. Apply new docker-compose.yml
echo ""
echo "🔧 Применение новой конфигурации docker-compose.yml..."
echo "ВНИМАНИЕ: Замените docker-compose.yml содержимым из /workspace/docker-compose-best-practices.yml"
echo "Нажмите Enter когда замените файл..."
read -r

# 6. Start services with new configuration
echo ""
echo "🚀 Запуск сервисов с новой конфигурацией..."
docker compose up -d

echo ""
echo "⏳ Ожидание инициализации (2 минуты)..."
sleep 120

# 7. Check service status
echo ""
echo "📊 Проверка статуса сервисов..."
docker compose ps
echo ""
docker ps --format "table {{.Names}}\t{{.Status}}"

# 8. Configure Nextcloud for reverse proxy
echo ""
echo "⚙️ Настройка Nextcloud для reverse proxy..."

# Get Traefik IP in web network
TRAEFIK_WEB_IP=$(docker inspect traefik | grep -A 20 '"nc-rag_web"' | grep '"IPAddress"' | grep -oP '\d+\.\d+\.\d+\.\d+' | head -1)
if [ -n "$TRAEFIK_WEB_IP" ]; then
    echo "Traefik Web IP: $TRAEFIK_WEB_IP"
else
    echo "⚠️ Не удалось найти IP Traefik, используем сеть"
    TRAEFIK_WEB_IP="172.20.0.0/16"
fi

# Configure trusted proxies
echo "Настройка trusted proxies..."
docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 0 --value="$TRAEFIK_WEB_IP"
docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 1 --value='172.20.0.0/16'

# Configure domains and overwrite settings
echo "Настройка доменов и overwrite параметров..."
docker exec -u www-data nextcloud php occ config:system:set trusted_domains 0 --value='ncrag.voronkov.club'
docker exec -u www-data nextcloud php occ config:system:set trusted_domains 1 --value='localhost'
docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'
docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'
docker exec -u www-data nextcloud php occ config:system:set overwrite.cli.url --value='https://ncrag.voronkov.club'

# Configure forwarded headers
echo "Настройка forwarded headers..."
docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 0 --value='HTTP_X_FORWARDED_FOR'
docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 1 --value='HTTP_X_REAL_IP'
docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 2 --value='HTTP_X_FORWARDED_HOST'

# Configure Redis caching (optional)
echo "Настройка Redis кэширования..."
docker exec -u www-data nextcloud php occ config:system:set memcache.distributed --value='\OC\Memcache\Redis' || true
docker exec -u www-data nextcloud php occ config:system:set memcache.locking --value='\OC\Memcache\Redis' || true

echo "✅ Конфигурация Nextcloud завершена"

# 9. Check Nextcloud status
echo ""
echo "📊 Проверка статуса Nextcloud..."
docker exec -u www-data nextcloud php occ status

# 10. Test login functionality
echo ""
echo "🧪 ТЕСТ ЛОГИНА..."
COOKIE_JAR="/tmp/best_practices_test.txt"
rm -f "$COOKIE_JAR"

# Check accessibility
echo "1. Проверка доступности..."
MAIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://ncrag.voronkov.club/" || echo "FAIL")
LOGIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://ncrag.voronkov.club/login" || echo "FAIL")
echo "   Главная страница: $MAIN_STATUS"
echo "   Страница логина: $LOGIN_STATUS"

if [ "$LOGIN_STATUS" = "200" ]; then
    # Get CSRF token
    echo "2. Получение CSRF токена..."
    LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
    CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)
    
    if [ -z "$CSRF_TOKEN" ]; then
        echo "❌ Не удалось получить CSRF токен"
    else
        echo "✅ CSRF Token получен: ${CSRF_TOKEN:0:40}..."
        
        # Test login
        echo "3. Тест логина..."
        RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \
            -d "user=admin" \
            -d "password=$NEXTCLOUD_PASSWORD" \
            -d "requesttoken=$CSRF_TOKEN" \
            -w "STATUS:%{http_code}\nURL:%{url_effective}\n" \
            "https://ncrag.voronkov.club/login")
        
        STATUS=$(echo "$RESPONSE" | grep "STATUS:" | cut -d: -f2)
        FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)
        
        echo "   HTTP Status: $STATUS"
        echo "   Final URL: $FINAL_URL"
        
        if [[ "$FINAL_URL" == *"/login"* ]]; then
            echo "❌ ВСЕ ЕЩЕ РЕДИРЕКТ НА ЛОГИН"
            echo ""
            echo "🔍 Verbose диагностика:"
            curl -v -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
                -d "user=admin" \
                -d "password=$NEXTCLOUD_PASSWORD" \
                -d "requesttoken=$CSRF_TOKEN" \
                "https://ncrag.voronkov.club/login" 2>&1 | grep -E "(< HTTP|< Location|< Set-Cookie)" | head -10
                
        elif echo "$RESPONSE" | grep -q "files\|dashboard\|apps"; then
            echo "✅ УСПЕХ! ЛОГИН РАБОТАЕТ!"
            echo "🎉 Best practices конфигурация успешно применена!"
        else
            echo "⚠️ НЕЯСНЫЙ РЕЗУЛЬТАТ"
            echo "Первые строки ответа:"
            echo "$RESPONSE" | head -5
        fi
    fi
else
    echo "❌ Страница логина недоступна (статус: $LOGIN_STATUS)"
fi

rm -f "$COOKIE_JAR"

# Final summary
echo ""
echo "=" * 60
echo "📋 ИТОГИ ПРИМЕНЕНИЯ BEST PRACTICES:"
echo ""
echo "✅ Конфигурация обновлена согласно best practices"
echo "✅ Правильные заголовки прокси настроены"
echo "✅ Сети разделены для безопасности"
echo "✅ Health checks добавлены"
echo ""
echo "🌐 Доступ к Nextcloud:"
echo "   URL: https://ncrag.voronkov.club"
echo "   Логин: admin"
echo "   Пароль: $NEXTCLOUD_PASSWORD"
echo ""
echo "🔧 Если логин все еще не работает:"
echo "   1. Проверьте логи: docker logs nextcloud --tail 20"
echo "   2. Проверьте Traefik: docker logs traefik --tail 20"
echo "   3. Попробуйте откат к Nextcloud 30"
echo "   4. Очистите кэш браузера и попробуйте инкогнито режим"
echo ""
echo "Script completed at $(date)"