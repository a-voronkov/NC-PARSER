#!/bin/bash
set -e

echo "=== NEXTCLOUD LOGIN FIX ==="
echo "Server: $SSH_SERVER"
echo "User: $SSH_USER"
echo "Password length: ${#NEXTCLOUD_PASSWORD} chars"

# Function to run SSH commands
ssh_run() {
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no "$SSH_USER@$SSH_SERVER" "$1"
}

echo "1. Testing SSH connection..."
ssh_run "echo 'Connected to:'; hostname; date"

echo "2. Checking containers..."
ssh_run "cd /srv/docker/nc-rag && docker ps --format 'table {{.Names}}\t{{.Status}}'"

echo "3. Resetting admin password..."
ssh_run "cd /srv/docker/nc-rag && docker exec -e OC_PASS='$NEXTCLOUD_PASSWORD' -u www-data nextcloud php occ user:resetpassword admin --password-from-env"

echo "4. Configuring Redis..."
ssh_run "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set memcache.distributed --value='\\OC\\Memcache\\Redis'"
ssh_run "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set memcache.locking --value='\\OC\\Memcache\\Redis'"
ssh_run "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set redis host --value='redis'"
ssh_run "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set redis port --value=6379"
ssh_run "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'"

echo "5. Clearing cache and restarting..."
ssh_run "cd /srv/docker/nc-rag && docker exec nc-redis redis-cli FLUSHALL"
ssh_run "cd /srv/docker/nc-rag && docker restart nextcloud"

echo "6. Waiting 20 seconds for restart..."
sleep 20

echo "7. Testing login..."
ssh_run "cd /srv/docker/nc-rag && COOKIE_JAR=\"/tmp/test_\$(date +%s).txt\" && rm -f \"\$COOKIE_JAR\" && LOGIN_PAGE=\$(curl -s -c \"\$COOKIE_JAR\" \"https://ncrag.voronkov.club/login\") && CSRF_TOKEN=\$(echo \"\$LOGIN_PAGE\" | grep -oP 'data-requesttoken=\"\\K[^\"]+' | head -1) && echo \"CSRF: \${CSRF_TOKEN:0:20}...\" && RESPONSE=\$(curl -s -b \"\$COOKIE_JAR\" -c \"\$COOKIE_JAR\" -L -d \"user=admin\" -d \"password=$NEXTCLOUD_PASSWORD\" -d \"requesttoken=\$CSRF_TOKEN\" -w \"URL:%{url_effective}\\n\" \"https://ncrag.voronkov.club/login\") && FINAL_URL=\$(echo \"\$RESPONSE\" | grep \"URL:\" | cut -d: -f2-) && echo \"Final URL: \$FINAL_URL\" && if [[ \"\$FINAL_URL\" == *\"/login\"* ]]; then echo \"❌ LOGIN FAILED\"; else echo \"✅ LOGIN SUCCESS\"; fi"

echo "8. Updating .env file..."
ssh_run "cd /srv/docker/nc-rag && sed -i 's/NEXTCLOUD_PASS=.*/NEXTCLOUD_PASS=$NEXTCLOUD_PASSWORD/' .env && sed -i 's/NEXTCLOUD_ADMIN_PASSWORD=.*/NEXTCLOUD_ADMIN_PASSWORD=$NEXTCLOUD_PASSWORD/' .env"

echo "=== DONE ==="
echo "Please test login at: https://ncrag.voronkov.club"
echo "Username: admin"
echo "Password: $NEXTCLOUD_PASSWORD"