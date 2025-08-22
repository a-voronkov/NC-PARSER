#!/bin/bash

# Nextcloud Login Fix Script
# This script fixes common login issues with Nextcloud

set -e

echo "🔧 Nextcloud Login Fix Script"
echo "============================="

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ] || [ ! -d "services" ]; then
    echo "❌ Error: This script must be run from the nc-rag project root directory"
    echo "Please run: cd /srv/docker/nc-rag && ./scripts/fix-nextcloud-login.sh"
    exit 1
fi

# Check if NEXTCLOUD_PASSWORD is set
if [ -z "$NEXTCLOUD_PASSWORD" ]; then
    echo "❌ Error: NEXTCLOUD_PASSWORD environment variable is not set"
    echo "This should contain the frontend login password (not the API token)"
    exit 1
fi

echo "✅ Environment check passed"
echo "Password length: ${#NEXTCLOUD_PASSWORD} characters"

# Step 1: Check containers
echo ""
echo "🐳 Checking Docker containers..."
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(nextcloud|redis)"

# Step 2: Reset admin password
echo ""
echo "🔑 Resetting admin password..."
docker exec -e OC_PASS="$NEXTCLOUD_PASSWORD" -u www-data nextcloud php occ user:resetpassword admin --password-from-env
echo "✅ Password reset successful"

# Step 3: Configure Redis for sessions
echo ""
echo "⚙️ Configuring Redis for sessions..."
docker exec -u www-data nextcloud php occ config:system:set memcache.distributed --value='\OC\Memcache\Redis'
docker exec -u www-data nextcloud php occ config:system:set memcache.locking --value='\OC\Memcache\Redis'
docker exec -u www-data nextcloud php occ config:system:set redis host --value='redis'
docker exec -u www-data nextcloud php occ config:system:set redis port --value=6379
docker exec -u www-data nextcloud php occ config:system:set redis password --value=''
echo "✅ Redis configuration updated"

# Step 4: Configure HTTPS settings
echo ""
echo "🔒 Configuring HTTPS settings..."
docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'
docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'
echo "✅ HTTPS settings updated"

# Step 5: Clear cache and restart
echo ""
echo "🔄 Clearing cache and restarting..."
docker exec nc-redis redis-cli FLUSHALL
docker restart nextcloud
echo "⏳ Waiting 20 seconds for Nextcloud to restart..."
sleep 20
echo "✅ Restart complete"

# Step 6: Update .env file
echo ""
echo "📝 Updating .env file..."
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
sed -i "s/NEXTCLOUD_PASS=.*/NEXTCLOUD_PASS=$NEXTCLOUD_PASSWORD/" .env
sed -i "s/NEXTCLOUD_ADMIN_PASSWORD=.*/NEXTCLOUD_ADMIN_PASSWORD=$NEXTCLOUD_PASSWORD/" .env
echo "✅ .env file updated (backup created)"

# Step 7: Test login
echo ""
echo "🧪 Testing login functionality..."

# Create temporary test script
TEST_SCRIPT=$(mktemp)
cat > "$TEST_SCRIPT" << 'EOF'
#!/bin/bash
COOKIE_JAR="/tmp/nc_test_cookies_$(date +%s).txt"
rm -f "$COOKIE_JAR"

echo "  → Getting login page..."
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login" 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "❌ Cannot access login page"
    exit 1
fi

echo "  → Extracting CSRF token..."
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)
if [ -z "$CSRF_TOKEN" ]; then
    echo "❌ Cannot extract CSRF token"
    exit 1
fi

echo "  → Submitting login credentials..."
RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \
    -d "user=admin" \
    -d "password=$NEXTCLOUD_PASSWORD" \
    -d "requesttoken=$CSRF_TOKEN" \
    -w "STATUS:%{http_code}\nURL:%{url_effective}\n" \
    "https://ncrag.voronkov.club/login" 2>/dev/null)

STATUS=$(echo "$RESPONSE" | grep "STATUS:" | cut -d: -f2)
FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)

echo "  → HTTP Status: $STATUS"
echo "  → Final URL: $FINAL_URL"

if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ LOGIN FAILED: Still redirected to login page"
    rm -f "$COOKIE_JAR"
    exit 1
elif echo "$RESPONSE" | grep -q "files\|dashboard\|apps\|<title>Files"; then
    echo "✅ LOGIN SUCCESS: Dashboard content found"
    rm -f "$COOKIE_JAR"
    exit 0
else
    echo "⚠️ LOGIN UNCLEAR: Unexpected response"
    rm -f "$COOKIE_JAR"
    exit 2
fi
EOF

chmod +x "$TEST_SCRIPT"
if "$TEST_SCRIPT"; then
    LOGIN_SUCCESS=true
else
    LOGIN_SUCCESS=false
fi

rm -f "$TEST_SCRIPT"

# Final status
echo ""
echo "=============================="
if [ "$LOGIN_SUCCESS" = true ]; then
    echo "🎉 SUCCESS! Nextcloud login has been fixed!"
    echo ""
    echo "You can now log in at:"
    echo "  URL: https://ncrag.voronkov.club"
    echo "  Username: admin"
    echo "  Password: $NEXTCLOUD_PASSWORD"
    echo ""
    echo "✅ All fixes have been applied successfully"
else
    echo "⚠️ Login test failed. Trying fallback without Redis..."
    
    # Fallback: disable Redis temporarily
    docker exec -u www-data nextcloud php occ config:system:delete memcache.distributed 2>/dev/null || true
    docker exec -u www-data nextcloud php occ config:system:delete memcache.locking 2>/dev/null || true
    docker restart nextcloud
    sleep 15
    
    echo "Testing without Redis..."
    if "$TEST_SCRIPT" 2>/dev/null; then
        echo "✅ SUCCESS WITH REDIS DISABLED!"
        echo "Redis was causing session issues. Login now works without Redis caching."
    else
        echo "❌ Login still failing. Manual troubleshooting required."
        echo ""
        echo "Troubleshooting steps:"
        echo "1. Check container logs: docker logs nextcloud --tail 20"
        echo "2. Verify password: echo \$NEXTCLOUD_PASSWORD"
        echo "3. Clear browser cache and try incognito mode"
        echo "4. Check Nextcloud logs: docker exec nextcloud tail -10 /var/www/html/data/nextcloud.log"
    fi
fi

echo ""
echo "Script completed at $(date)"