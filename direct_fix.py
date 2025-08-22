#!/usr/bin/env python3
import subprocess
import os

# Environment variables
ssh_server = os.environ.get('SSH_SERVER')
ssh_user = os.environ.get('SSH_USER')  
ssh_password = os.environ.get('SSH_PASSWORD')

print(f"Connecting to {ssh_user}@{ssh_server}")

# Commands to execute
commands = [
    "cd /srv/docker/nc-rag && docker ps --format 'table {{.Names}}\t{{.Status}}'",
    "cd /srv/docker/nc-rag && docker exec nc-redis redis-cli ping",
    "cd /srv/docker/nc-rag && docker exec nextcloud php -m | grep -i redis",
    "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set memcache.distributed --value='\\OC\\Memcache\\Redis'",
    "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set memcache.locking --value='\\OC\\Memcache\\Redis'",
    "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set redis host --value='redis'",
    "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set redis port --value=6379",
    "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'",
    "cd /srv/docker/nc-rag && docker exec nc-redis redis-cli FLUSHALL",
    "cd /srv/docker/nc-rag && docker restart nextcloud"
]

for cmd in commands:
    print(f"\n>>> {cmd}")
    ssh_cmd = ['sshpass', '-p', ssh_password, 'ssh', '-o', 'StrictHostKeyChecking=no', f'{ssh_user}@{ssh_server}', cmd]
    result = subprocess.run(ssh_cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"ERROR: {result.stderr}")

print("\nWaiting 15 seconds for restart...")
import time
time.sleep(15)

# Test login
print("\nTesting login...")
test_cmd = '''
COOKIE_JAR="/tmp/test_$(date +%s).txt"
rm -f "$COOKIE_JAR"
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\\K[^"]+' | head -1)
echo "CSRF: ${CSRF_TOKEN:0:20}..."
RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \\
    -d "user=admin" \\
    -d "password=G4z2j-sGXzM-C9Xbd-ZesDY-BZoFY" \\
    -d "requesttoken=$CSRF_TOKEN" \\
    -w "URL:%{url_effective}\\n" \\
    "https://ncrag.voronkov.club/login")
FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)
echo "Final URL: $FINAL_URL"
if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "LOGIN FAILED"
else
    echo "LOGIN SUCCESS"
fi
'''

ssh_cmd = ['sshpass', '-p', ssh_password, 'ssh', '-o', 'StrictHostKeyChecking=no', f'{ssh_user}@{ssh_server}', test_cmd]
result = subprocess.run(ssh_cmd, capture_output=True, text=True)
print(result.stdout)

print("\n=== DONE ===")
print("Please test at https://ncrag.voronkov.club")
print("Username: admin")
print("Password: G4z2j-sGXzM-C9Xbd-ZesDY-BZoFY")