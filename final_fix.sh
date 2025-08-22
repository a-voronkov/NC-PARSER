#!/bin/bash

echo "=== NEXTCLOUD LOGIN FIX ==="
echo "Target: $SSH_SERVER"
echo "User: $SSH_USER"

# Function to run SSH command
run_ssh() {
    local cmd="$1"
    local desc="$2"
    echo ">>> $desc"
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no "$SSH_USER@$SSH_SERVER" "$cmd"
    echo "---"
}

# Test connection
run_ssh "echo 'SSH OK'; date" "Testing connection"

# Check containers
run_ssh "cd /srv/docker/nc-rag && docker ps" "Checking containers"

# Test Redis
run_ssh "cd /srv/docker/nc-rag && docker exec nc-redis redis-cli ping" "Testing Redis"

# Configure Nextcloud
echo "Configuring Nextcloud..."
run_ssh "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set memcache.distributed --value='\\OC\\Memcache\\Redis'" "Setting memcache.distributed"
run_ssh "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set memcache.locking --value='\\OC\\Memcache\\Redis'" "Setting memcache.locking"
run_ssh "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set redis host --value='redis'" "Setting Redis host"
run_ssh "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set redis port --value=6379" "Setting Redis port"
run_ssh "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'" "Setting HTTPS protocol"

# Clear cache and restart
run_ssh "cd /srv/docker/nc-rag && docker exec nc-redis redis-cli FLUSHALL" "Clearing Redis cache"
run_ssh "cd /srv/docker/nc-rag && docker restart nextcloud" "Restarting Nextcloud"

echo "Waiting 20 seconds..."
sleep 20

# Test login
echo "Testing login..."
run_ssh 'COOKIE_JAR="/tmp/test_$(date +%s).txt"; rm -f "$COOKIE_JAR"; LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login"); CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP "data-requesttoken=\"\\K[^\"]+\" | head -1); echo "CSRF: ${CSRF_TOKEN:0:20}..."; RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L -d "user=admin" -d "password=G4z2j-sGXzM-C9Xbd-ZesDY-BZoFY" -d "requesttoken=$CSRF_TOKEN" -w "URL:%{url_effective}\\n" "https://ncrag.voronkov.club/login"); FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-); echo "Final URL: $FINAL_URL"; if [[ "$FINAL_URL" == *"/login"* ]]; then echo "LOGIN FAILED"; else echo "LOGIN SUCCESS"; fi' "Testing login flow"

echo "=== DONE ==="
echo "Please test at https://ncrag.voronkov.club"
echo "Username: admin"
echo "Password: G4z2j-sGXzM-C9Xbd-ZesDY-BZoFY"