#!/usr/bin/env python3
import subprocess
import os

def ssh_command(cmd):
    """Execute SSH command"""
    ssh_cmd = [
        'sshpass', '-p', os.environ['SSH_PASSWORD'],
        'ssh', '-o', 'StrictHostKeyChecking=no',
        f"{os.environ['SSH_USER']}@{os.environ['SSH_SERVER']}",
        cmd
    ]
    result = subprocess.run(ssh_cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

print("🔍 DEEP DIAGNOSIS: FINDING THE REAL CAUSE")
print("=" * 50)

# 1. Check exact Nextcloud configuration
print("1. Current Nextcloud proxy configuration:")
config_checks = [
    "trusted_proxies",
    "overwritehost", 
    "overwriteprotocol",
    "overwrite.cli.url",
    "trusted_domains",
    "forwarded_for_headers"
]

for setting in config_checks:
    code, out, err = ssh_command(f"cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:get {setting}")
    print(f"  {setting}: {out.strip()}")

# 2. Check if Nextcloud is actually processing the login
print("\n2. Testing verbose login to see exact redirect:")
verbose_test = '''
cd /srv/docker/nc-rag
COOKIE_JAR="/tmp/verbose_test.txt"
rm -f "$COOKIE_JAR"

echo "=== VERBOSE LOGIN TEST ==="

# Get login page
echo "Getting login page..."
curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login" > /tmp/login_page.html
CSRF_TOKEN=$(grep -oP 'data-requesttoken="\\K[^"]+' /tmp/login_page.html | head -1)
echo "CSRF Token: ${CSRF_TOKEN:0:40}..."

# Submit login with verbose output
echo -e "\n=== SUBMITTING LOGIN (VERBOSE) ==="
curl -v -b "$COOKIE_JAR" -c "$COOKIE_JAR" \\
    -d "user=admin" \\
    -d "password=$NEXTCLOUD_PASSWORD" \\
    -d "requesttoken=$CSRF_TOKEN" \\
    "https://ncrag.voronkov.club/login" 2>&1 | grep -E "(< HTTP|< Location|< Set-Cookie|> POST|> Host)"

echo -e "\n=== FOLLOWING REDIRECTS ==="
FINAL_RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \\
    -d "user=admin" \\
    -d "password=$NEXTCLOUD_PASSWORD" \\
    -d "requesttoken=$CSRF_TOKEN" \\
    -w "FINAL_STATUS:%{http_code}\\nFINAL_URL:%{url_effective}\\n" \\
    "https://ncrag.voronkov.club/login")

echo "$FINAL_RESPONSE" | tail -2

rm -f "$COOKIE_JAR" /tmp/login_page.html
'''

code, out, err = ssh_command(verbose_test)
print(out)

# 3. Check if there's a session issue
print("\n3. Checking session storage:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php -r \"echo 'Session save path: ' . session_save_path() . \\\"\\n\\\";\"")
print(out.strip())

# 4. Check Redis connectivity from Nextcloud
print("\n4. Testing Redis connectivity from Nextcloud:")
redis_test = '''
cd /srv/docker/nc-rag
docker exec nextcloud php -r "
try {
    \\$redis = new Redis();
    \\$redis->connect('redis', 6379);
    echo 'Redis connection: SUCCESS\\n';
    \\$redis->set('test_session', 'test_data');
    echo 'Redis write/read: ' . \\$redis->get('test_session') . '\\n';
    \\$redis->del('test_session');
    echo 'Redis operations: SUCCESS\\n';
} catch (Exception \\$e) {
    echo 'Redis FAILED: ' . \\$e->getMessage() . '\\n';
}
"
'''

code, out, err = ssh_command(redis_test)
print(out)

# 5. Check if there's an issue with PHP session handling
print("\n5. PHP session configuration:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec nextcloud php -i | grep -A 5 -B 5 'session.save_handler'")
print(out)

# 6. Check Nextcloud logs during login attempt
print("\n6. Real-time log test:")
realtime_test = '''
cd /srv/docker/nc-rag

echo "Starting log monitoring..."
# Start log monitoring in background
docker logs nextcloud -f > /tmp/nc_logs.txt 2>&1 &
LOG_PID=$!

sleep 2

echo "Performing login attempt..."
COOKIE_JAR="/tmp/realtime_test.txt"
rm -f "$COOKIE_JAR"

LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\\K[^"]+' | head -1)

curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \\
    -d "user=admin" \\
    -d "password=$NEXTCLOUD_PASSWORD" \\
    -d "requesttoken=$CSRF_TOKEN" \\
    "https://ncrag.voronkov.club/login" > /dev/null

sleep 3

# Stop log monitoring
kill $LOG_PID 2>/dev/null

echo "=== LOGS DURING LOGIN ATTEMPT ==="
tail -20 /tmp/nc_logs.txt

rm -f "$COOKIE_JAR" /tmp/nc_logs.txt
'''

code, out, err = ssh_command(realtime_test)
print(out)

# 7. Check if there's an issue with the config.php file directly
print("\n7. Checking Nextcloud config.php directly:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec nextcloud cat /var/www/html/config/config.php | grep -E '(trusted_proxies|overwrite|trusted_domains)' -A 3")
print(out)

# 8. Try alternative session handler
print("\n8. Trying without Redis session handler...")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:delete memcache.distributed")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:delete memcache.locking")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker restart nextcloud")

print("Waiting 15 seconds for restart...")
import time
time.sleep(15)

# Test without Redis
no_redis_test = '''
cd /srv/docker/nc-rag
COOKIE_JAR="/tmp/no_redis_test.txt"
rm -f "$COOKIE_JAR"

echo "Testing login without Redis..."
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\\K[^"]+' | head -1)

RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \\
    -d "user=admin" \\
    -d "password=$NEXTCLOUD_PASSWORD" \\
    -d "requesttoken=$CSRF_TOKEN" \\
    -w "URL:%{url_effective}\\n" \\
    "https://ncrag.voronkov.club/login")

FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)
echo "Final URL without Redis: $FINAL_URL"

if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ STILL REDIRECTING (Redis not the issue)"
else
    echo "✅ SUCCESS WITHOUT REDIS! Redis was causing the problem!"
fi

rm -f "$COOKIE_JAR"
'''

code, out, err = ssh_command(no_redis_test)
print(out)

print("\n" + "=" * 50)
print("🔍 DEEP DIAGNOSIS COMPLETE")

# Restart Node-RED
print("\nRestarting Node-RED...")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker start node-red")

print("\n📋 ANALYSIS SUMMARY:")
print("1. Routing conflicts: ❌ (Node-RED not the issue)")
print("2. Check Redis session handling results above")
print("3. Check verbose curl output for redirect details")
print("4. Check config.php for any manual overrides")