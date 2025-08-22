# 🔧 Manual Fix Instructions for Nextcloud Login Issue

## Problem Summary
The Nextcloud login at `https://ncrag.voronkov.club` is failing because:
1. **Wrong password variable**: Using API token instead of frontend password
2. **Redis session issues**: Improper Redis configuration for session handling

## 🔑 Correct Password Information
- **Frontend login password**: Use `NEXTCLOUD_PASSWORD` environment variable
- **API token**: `NEXTCLOUD_APP_PASSWORD` is for API access, NOT for web login

## 🛠️ Step-by-Step Fix

### Step 1: Connect to Server
```bash
ssh alfred361@ncrag.voronkov.club
cd /srv/docker/nc-rag
```

### Step 2: Reset Admin Password (CRITICAL)
```bash
# Get the correct password from your environment
echo $NEXTCLOUD_PASSWORD

# Reset admin password to correct value
docker exec -e OC_PASS="$NEXTCLOUD_PASSWORD" -u www-data nextcloud php occ user:resetpassword admin --password-from-env
```

### Step 3: Configure Redis for Sessions
```bash
# Set Redis as distributed cache
docker exec -u www-data nextcloud php occ config:system:set memcache.distributed --value='\OC\Memcache\Redis'

# Set Redis for locking
docker exec -u www-data nextcloud php occ config:system:set memcache.locking --value='\OC\Memcache\Redis'

# Configure Redis connection
docker exec -u www-data nextcloud php occ config:system:set redis host --value='redis'
docker exec -u www-data nextcloud php occ config:system:set redis port --value=6379
docker exec -u www-data nextcloud php occ config:system:set redis password --value=''
```

### Step 4: Configure HTTPS Settings
```bash
# Set proper protocol
docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'

# Set proper host
docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'
```

### Step 5: Clear Cache and Restart
```bash
# Clear Redis cache
docker exec nc-redis redis-cli FLUSHALL

# Restart Nextcloud
docker restart nextcloud

# Wait for restart
sleep 20
```

### Step 6: Update .env File
```bash
# Update .env with correct password
sed -i "s/NEXTCLOUD_PASS=.*/NEXTCLOUD_PASS=$NEXTCLOUD_PASSWORD/" .env
sed -i "s/NEXTCLOUD_ADMIN_PASSWORD=.*/NEXTCLOUD_ADMIN_PASSWORD=$NEXTCLOUD_PASSWORD/" .env
```

### Step 7: Test Login
```bash
# Create test script
cat > /tmp/test_login.sh << 'EOF'
#!/bin/bash
COOKIE_JAR="/tmp/test_cookies_$(date +%s).txt"
rm -f "$COOKIE_JAR"

echo "1. Getting login page..."
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)

if [ -z "$CSRF_TOKEN" ]; then
    echo "❌ Failed to get CSRF token"
    exit 1
fi

echo "2. CSRF token: ${CSRF_TOKEN:0:30}..."

echo "3. Submitting login..."
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
    echo "❌ LOGIN FAILED: Still on login page"
    exit 1
elif echo "$RESPONSE" | grep -q "files\|dashboard\|apps"; then
    echo "✅ LOGIN SUCCESS: Found dashboard content"
    exit 0
else
    echo "⚠️ UNCLEAR: Response unclear"
    exit 2
fi
EOF

chmod +x /tmp/test_login.sh
/tmp/test_login.sh
```

## 🔄 Alternative Fix (If Redis Causes Issues)

If the above doesn't work, try disabling Redis temporarily:

```bash
# Disable Redis caching
docker exec -u www-data nextcloud php occ config:system:delete memcache.distributed
docker exec -u www-data nextcloud php occ config:system:delete memcache.locking
docker exec -u www-data nextcloud php occ config:system:delete redis

# Restart Nextcloud
docker restart nextcloud

# Wait and test
sleep 15
/tmp/test_login.sh
```

## 📋 Login Credentials

After fixing:
- **URL**: https://ncrag.voronkov.club
- **Username**: admin
- **Password**: Value of `$NEXTCLOUD_PASSWORD` environment variable

## 🐛 Troubleshooting

### If login still fails:
1. Check container logs: `docker logs nextcloud --tail 20`
2. Check Nextcloud logs: `docker exec nextcloud tail -10 /var/www/html/data/nextcloud.log`
3. Verify password: `echo $NEXTCLOUD_PASSWORD`
4. Clear browser cache and cookies
5. Try incognito/private browsing

### If Redis errors appear:
1. Check Redis: `docker exec nc-redis redis-cli ping`
2. Check PHP Redis extension: `docker exec nextcloud php -m | grep -i redis`
3. If missing, install: `docker exec nextcloud apt update && docker exec nextcloud apt install -y php-redis`

## 🔄 Repository Updates Needed

After fixing, update the repository:

1. **Update `.env.example`**:
   ```bash
   # Add comments about password variables
   # NEXTCLOUD_PASSWORD - Frontend login password
   # NEXTCLOUD_APP_PASSWORD - API access token (different from login)
   ```

2. **Create `scripts/fix-login.sh`**:
   ```bash
   # Add the fix script to the repository
   ```

3. **Update `README.md`**:
   ```markdown
   ## Troubleshooting Login Issues
   
   If you cannot log in to Nextcloud:
   1. Ensure NEXTCLOUD_PASSWORD is set correctly
   2. Run: ./scripts/fix-login.sh
   3. Check Redis configuration
   ```

4. **Update `docker-compose.yml`** (if needed):
   - Ensure Redis configuration is proper
   - Add health checks for Redis

## ✅ Success Indicators

You'll know it's fixed when:
1. Login test script shows "LOGIN SUCCESS"
2. You can access https://ncrag.voronkov.club with admin credentials
3. No Redis connection errors in logs
4. Session handling works properly

## 📞 If Still Having Issues

If the manual fix doesn't work:
1. Check if the password in `$NEXTCLOUD_PASSWORD` is correct
2. Verify all containers are running: `docker ps`
3. Check for any error messages in the logs
4. Try the Redis disable fallback option
5. Consider recreating the Nextcloud container if necessary