# 🔓 Quick Fix: Reset Login Throttling

## ✅ Good News!
The throttling message means **the proxy configuration is now working**! 
Nextcloud is properly processing login attempts.

## 🚀 Immediate Commands

```bash
ssh alfred361@ncrag.voronkov.club
cd /srv/docker/nc-rag

# 1. Reset brute force protection for your IP
docker exec -u www-data nextcloud php occ security:bruteforce:reset 171.5.227.98

# 2. Clear Redis sessions
docker exec nc-redis redis-cli FLUSHALL

# 3. Ensure correct password is set
docker exec -e OC_PASS="$NEXTCLOUD_PASSWORD" -u www-data nextcloud php occ user:resetpassword admin --password-from-env

# 4. Wait 35 seconds for throttling to clear
sleep 35
```

## 🧪 Test Login

After the wait, test login:

```bash
# Quick login test
COOKIE_JAR="/tmp/test_cookies.txt"
rm -f "$COOKIE_JAR"

LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)

echo "CSRF: ${CSRF_TOKEN:0:20}..."

RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \
    -d "user=admin" \
    -d "password=$NEXTCLOUD_PASSWORD" \
    -d "requesttoken=$CSRF_TOKEN" \
    -w "URL:%{url_effective}\n" \
    "https://ncrag.voronkov.club/login")

FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)
echo "Final URL: $FINAL_URL"

if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ Still on login page"
else
    echo "✅ SUCCESS: $FINAL_URL"
fi
```

## 🎯 What Changed

The throttling message indicates:
1. ✅ **Proxy settings are working** - Nextcloud now processes requests correctly
2. ✅ **Authentication flow is functional** - No more redirect loops
3. ⚠️ **Previous failed attempts** triggered rate limiting

## 📋 Login Credentials

- **URL**: https://ncrag.voronkov.club
- **Username**: admin  
- **Password**: Value of `$NEXTCLOUD_PASSWORD` environment variable

## 🔄 Alternative: Browser Test

1. **Clear browser cache/cookies**
2. **Use incognito/private mode**  
3. **Wait 30+ seconds**
4. **Try manual login**

The throttling should clear automatically after the timeout period!