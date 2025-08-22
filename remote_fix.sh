#!/bin/bash

echo "=== Nextcloud Remote Fix Script ==="
echo "Running on: $(hostname)"
echo "Date: $(date)"

cd /srv/docker/nc-rag

echo "1. Checking containers..."
docker ps --format "table {{.Names}}\t{{.Status}}"

echo -e "\n2. Testing Redis connection..."
docker exec nc-redis redis-cli ping

echo -e "\n3. Checking PHP Redis extension..."
docker exec nextcloud php -m | grep -i redis

echo -e "\n4. Testing Redis from PHP..."
docker exec nextcloud php -r "
try {
    \$redis = new Redis();
    \$redis->connect('redis', 6379);
    echo 'Redis connection: SUCCESS\n';
    \$redis->set('test_key', 'test_value');
    echo 'Redis set/get: ' . \$redis->get('test_key') . '\n';
} catch (Exception \$e) {
    echo 'Redis connection FAILED: ' . \$e->getMessage() . '\n';
}
"

echo -e "\n5. Checking Nextcloud Redis configuration..."
docker exec -u www-data nextcloud php occ config:system:get redis

echo -e "\n6. Fixing Redis configuration..."
docker exec -u www-data nextcloud php occ config:system:set memcache.distributed --value='\OC\Memcache\Redis'
docker exec -u www-data nextcloud php occ config:system:set memcache.locking --value='\OC\Memcache\Redis'
docker exec -u www-data nextcloud php occ config:system:set redis host --value='redis'
docker exec -u www-data nextcloud php occ config:system:set redis port --value=6379
docker exec -u www-data nextcloud php occ config:system:set redis password --value=''

echo -e "\n7. Setting HTTPS configuration..."
docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'
docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'

echo -e "\n8. Clearing Redis cache..."
docker exec nc-redis redis-cli FLUSHALL

echo -e "\n9. Restarting Nextcloud..."
docker restart nextcloud

echo "Waiting 15 seconds for restart..."
sleep 15

echo -e "\n10. Testing login..."
COOKIE_JAR="/tmp/test_cookies_$(date +%s).txt"
rm -f "$COOKIE_JAR"

# Get login page
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)

if [ -z "$CSRF_TOKEN" ]; then
    echo "❌ FAILED: Could not get CSRF token"
    exit 1
fi

echo "CSRF token: ${CSRF_TOKEN:0:20}..."

# Submit login
RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \
    -d "user=admin" \
    -d "password=G4z2j-sGXzM-C9Xbd-ZesDY-BZoFY" \
    -d "requesttoken=$CSRF_TOKEN" \
    -w "STATUS:%{http_code}\nURL:%{url_effective}\n" \
    "https://ncrag.voronkov.club/login")

HTTP_STATUS=$(echo "$RESPONSE" | grep "STATUS:" | cut -d: -f2)
FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)

echo "HTTP Status: $HTTP_STATUS"
echo "Final URL: $FINAL_URL"

if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ LOGIN STILL FAILING"
    
    # Check recent logs
    echo -e "\nRecent Nextcloud logs:"
    docker exec nextcloud tail -5 /var/www/html/data/nextcloud.log | while read line; do
        echo "  $line"
    done
    
    echo -e "\nTrying alternative fix..."
    # Try disabling Redis temporarily
    docker exec -u www-data nextcloud php occ config:system:delete memcache.distributed
    docker exec -u www-data nextcloud php occ config:system:delete memcache.locking
    docker restart nextcloud
    sleep 10
    
    echo "Testing without Redis..."
    RESPONSE2=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \
        -d "user=admin" \
        -d "password=G4z2j-sGXzM-C9Xbd-ZesDY-BZoFY" \
        -d "requesttoken=$CSRF_TOKEN" \
        -w "URL:%{url_effective}\n" \
        "https://ncrag.voronkov.club/login")
    
    FINAL_URL2=$(echo "$RESPONSE2" | grep "URL:" | cut -d: -f2-)
    echo "Without Redis URL: $FINAL_URL2"
    
    if [[ "$FINAL_URL2" == *"/login"* ]]; then
        echo "❌ Still failing without Redis - deeper issue"
    else
        echo "✅ Works without Redis - Redis configuration issue"
    fi
    
else
    echo "✅ LOGIN SUCCESS!"
fi

echo -e "\n=== Fix Complete ==="
echo "Please test login at: https://ncrag.voronkov.club"
echo "Username: admin"
echo "Password: G4z2j-sGXzM-C9Xbd-ZesDY-BZoFY"