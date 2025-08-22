#!/usr/bin/env python3
import subprocess
import os

def run_ssh(cmd):
    """Run SSH command"""
    ssh_cmd = [
        'sshpass', '-p', os.environ['SSH_PASSWORD'],
        'ssh', '-o', 'StrictHostKeyChecking=no',
        f"{os.environ['SSH_USER']}@{os.environ['SSH_SERVER']}",
        cmd
    ]
    result = subprocess.run(ssh_cmd, capture_output=True, text=True)
    print(f"Command: {cmd}")
    print(f"Output: {result.stdout}")
    if result.stderr:
        print(f"Error: {result.stderr}")
    print("-" * 50)
    return result.returncode == 0

# Get password
password = os.environ.get('NEXTCLOUD_PASSWORD', '')
print(f"Using password: {password[:5]}...")

# Step 1: Test connection
run_ssh("echo 'Connected'; date")

# Step 2: Check containers
run_ssh("cd /srv/docker/nc-rag && docker ps")

# Step 3: Reset password
run_ssh(f"cd /srv/docker/nc-rag && docker exec -e OC_PASS='{password}' -u www-data nextcloud php occ user:resetpassword admin --password-from-env")

# Step 4: Configure Redis
run_ssh("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set memcache.distributed --value='\\OC\\Memcache\\Redis'")
run_ssh("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set memcache.locking --value='\\OC\\Memcache\\Redis'")
run_ssh("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set redis host --value='redis'")
run_ssh("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set redis port --value=6379")

# Step 5: Set HTTPS
run_ssh("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'")

# Step 6: Clear cache and restart
run_ssh("cd /srv/docker/nc-rag && docker exec nc-redis redis-cli FLUSHALL")
run_ssh("cd /srv/docker/nc-rag && docker restart nextcloud")

print("Waiting 20 seconds...")
import time
time.sleep(20)

# Step 7: Test login
test_cmd = f'''
COOKIE_JAR="/tmp/test_$(date +%s).txt"
rm -f "$COOKIE_JAR"
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\\K[^"]+' | head -1)
echo "CSRF: ${{CSRF_TOKEN:0:20}}..."
RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \\
    -d "user=admin" \\
    -d "password={password}" \\
    -d "requesttoken=$CSRF_TOKEN" \\
    -w "URL:%{{url_effective}}\\n" \\
    "https://ncrag.voronkov.club/login")
FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)
echo "Final URL: $FINAL_URL"
if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "LOGIN FAILED"
else
    echo "LOGIN SUCCESS"
fi
'''

run_ssh(test_cmd)

print("Done!")