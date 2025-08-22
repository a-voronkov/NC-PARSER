# 🔧 Manual Fix for Traefik/Domain Configuration Issues

## Analysis of the Problem

Based on your logs:
```
POST /login HTTP/1.1" 303 1396  -> Redirect after login attempt
GET /login?direct=1&user=admin HTTP/1.1" 200 10104  -> Back to login page
```

This is a **classic proxy/domain configuration issue**, not a password problem!

## Root Cause
The issue is likely one of these:
1. **Trusted proxies not configured** - Nextcloud doesn't trust Traefik
2. **Overwrite settings missing** - Nextcloud generates wrong URLs behind proxy
3. **Trusted domains mismatch** - Domain validation failing

## 🚀 IMMEDIATE FIX COMMANDS

Connect to your server and run these commands:

```bash
ssh alfred361@ncrag.voronkov.club
cd /srv/docker/nc-rag
```

### Step 1: Fix Trusted Proxies (CRITICAL)
```bash
# Set trusted proxy network (Traefik container network)
docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 0 --value='172.19.0.0/16'

# Alternative: Set specific Traefik container IP
docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 0 --value='172.19.0.6'
```

### Step 2: Fix Overwrite Settings (CRITICAL)
```bash
# Set overwrite host (must match your domain exactly)
docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'

# Set overwrite protocol
docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'

# Set CLI URL
docker exec -u www-data nextcloud php occ config:system:set overwrite.cli.url --value='https://ncrag.voronkov.club'
```

### Step 3: Fix Trusted Domains
```bash
# Ensure trusted domains are correct
docker exec -u www-data nextcloud php occ config:system:set trusted_domains 0 --value='localhost'
docker exec -u www-data nextcloud php occ config:system:set trusted_domains 1 --value='ncrag.voronkov.club'
```

### Step 4: Set Forwarded Headers
```bash
# Set forwarded headers for proxy detection
docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 0 --value='HTTP_X_FORWARDED_FOR'
docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 1 --value='HTTP_X_REAL_IP'
```

### Step 5: Restart and Test
```bash
# Restart Nextcloud to apply changes
docker restart nextcloud

# Wait for restart
sleep 15

# Test login immediately
curl -c /tmp/cookies.txt "https://ncrag.voronkov.club/login" > /tmp/login.html
grep -o 'data-requesttoken="[^"]*"' /tmp/login.html | head -1
```

## 🔍 Verification Commands

After applying fixes, verify configuration:

```bash
# Check trusted proxies
docker exec -u www-data nextcloud php occ config:system:get trusted_proxies

# Check overwrite settings
docker exec -u www-data nextcloud php occ config:system:get overwritehost
docker exec -u www-data nextcloud php occ config:system:get overwriteprotocol

# Check trusted domains
docker exec -u www-data nextcloud php occ config:system:get trusted_domains
```

## 🧪 Test Login Flow

```bash
# Complete login test
COOKIE_JAR="/tmp/test_cookies.txt"
rm -f "$COOKIE_JAR"

# Get login page
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\K[^"]+' | head -1)

echo "CSRF Token: ${CSRF_TOKEN:0:30}..."

# Submit login
RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \
    -d "user=admin" \
    -d "password=$NEXTCLOUD_PASSWORD" \
    -d "requesttoken=$CSRF_TOKEN" \
    -w "STATUS:%{http_code}\nURL:%{url_effective}\n" \
    "https://ncrag.voronkov.club/login")

echo "$RESPONSE" | tail -2

# Check final URL
FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)
if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ Still redirecting to login"
else
    echo "✅ SUCCESS: Redirected to $FINAL_URL"
fi
```

## 🔧 If Still Not Working

### Check Traefik Labels
Verify the Traefik configuration in docker-compose.yml:

```bash
cd /srv/docker/nc-rag
grep -A 10 "traefik.http.routers.nextcloud" docker-compose.yml
```

Should look like:
```yaml
- "traefik.http.routers.nextcloud.rule=Host(`ncrag.voronkov.club`)"
- "traefik.http.routers.nextcloud.entrypoints=websecure"
- "traefik.http.routers.nextcloud.tls.certresolver=le"
```

### Check Network Configuration
```bash
# Verify containers are on same network
docker network ls | grep nc-rag
docker inspect nextcloud | grep NetworkMode
docker inspect traefik | grep NetworkMode
```

### Debug Traefik Routing
```bash
# Check Traefik logs during login attempt
docker logs traefik --tail 20 -f &
# Then try to log in and watch the logs
```

## 📋 Expected Results

After applying these fixes:
1. **Trusted proxies** will allow Nextcloud to trust requests from Traefik
2. **Overwrite settings** will generate correct URLs behind the proxy
3. **Login should redirect to dashboard** instead of back to login page

## 🎯 Why This Fixes the Issue

The `303` redirect you saw means:
- Nextcloud **accepted** the login credentials
- But when generating the redirect URL, it used the wrong host/protocol
- This caused the redirect to fail or loop back to login

The proxy settings fix this by telling Nextcloud:
- Trust the proxy (Traefik)
- Use the correct external domain/protocol for URLs
- Handle forwarded headers properly

Try these fixes and let me know the results!