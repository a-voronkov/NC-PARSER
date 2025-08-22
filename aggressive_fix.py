#!/usr/bin/env python3
import subprocess
import os
import time

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

print("🔥 AGGRESSIVE FIX FOR PERSISTENT REDIRECT")
print("=" * 50)

# 1. Get Traefik container IP
print("1. Getting Traefik container IP...")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker inspect traefik | grep '\"IPAddress\"' | head -1")
traefik_ip = ""
if code == 0 and out:
    import re
    match = re.search(r'"IPAddress":\s*"([^"]+)"', out)
    if match:
        traefik_ip = match.group(1)
        print(f"✅ Traefik IP: {traefik_ip}")
    else:
        print("⚠️ Could not extract Traefik IP")

# 2. Completely reset all proxy-related settings
print("\n2. Completely resetting proxy settings...")

# Clear existing settings
reset_commands = [
    "docker exec -u www-data nextcloud php occ config:system:delete trusted_proxies",
    "docker exec -u www-data nextcloud php occ config:system:delete forwarded_for_headers", 
    "docker exec -u www-data nextcloud php occ config:system:delete overwritehost",
    "docker exec -u www-data nextcloud php occ config:system:delete overwriteprotocol",
    "docker exec -u www-data nextcloud php occ config:system:delete overwrite.cli.url",
    "docker exec -u www-data nextcloud php occ config:system:delete overwritecondaddr",
    "docker exec -u www-data nextcloud php occ config:system:delete overwritewebroot"
]

for cmd in reset_commands:
    code, out, err = ssh_command(f"cd /srv/docker/nc-rag && {cmd}")
    print(f"Reset: {cmd.split()[-1]} -> {'✅' if code == 0 else '❌'}")

# 3. Set comprehensive proxy configuration
print("\n3. Setting comprehensive proxy configuration...")

proxy_commands = [
    # Trusted proxies - multiple approaches
    "docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 0 --value='172.19.0.0/16'",
    "docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 1 --value='172.18.0.0/16'",
    "docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 2 --value='10.0.0.0/8'",
]

# Add specific Traefik IP if found
if traefik_ip:
    proxy_commands.append(f"docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 3 --value='{traefik_ip}'")

proxy_commands.extend([
    # Overwrite settings
    "docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'",
    "docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'",
    "docker exec -u www-data nextcloud php occ config:system:set overwrite.cli.url --value='https://ncrag.voronkov.club'",
    "docker exec -u www-data nextcloud php occ config:system:set overwritewebroot --value=''",
    
    # Forwarded headers - comprehensive list
    "docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 0 --value='HTTP_X_FORWARDED_FOR'",
    "docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 1 --value='HTTP_X_REAL_IP'",
    "docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 2 --value='HTTP_CF_CONNECTING_IP'",
    "docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 3 --value='HTTP_X_FORWARDED'",
    
    # Force HTTPS
    "docker exec -u www-data nextcloud php occ config:system:set forcessl --value=true --type=boolean",
    
    # Trusted domains (ensure correct)
    "docker exec -u www-data nextcloud php occ config:system:set trusted_domains 0 --value='localhost'",
    "docker exec -u www-data nextcloud php occ config:system:set trusted_domains 1 --value='ncrag.voronkov.club'",
    "docker exec -u www-data nextcloud php occ config:system:set trusted_domains 2 --value='127.0.0.1'"
])

for cmd in proxy_commands:
    code, out, err = ssh_command(f"cd /srv/docker/nc-rag && {cmd}")
    setting_name = cmd.split()[-3] if '--value' in cmd else 'unknown'
    print(f"Set {setting_name}: {'✅' if code == 0 else '❌'}")

# 4. Try alternative session configuration
print("\n4. Setting alternative session configuration...")
session_commands = [
    "docker exec -u www-data nextcloud php occ config:system:set session_lifetime --value=86400 --type=integer",
    "docker exec -u www-data nextcloud php occ config:system:set remember_login_cookie_lifetime --value=86400 --type=integer",
    "docker exec -u www-data nextcloud php occ config:system:set auto_logout --value=false --type=boolean"
]

for cmd in session_commands:
    code, out, err = ssh_command(f"cd /srv/docker/nc-rag && {cmd}")
    print(f"Session setting: {'✅' if code == 0 else '❌'}")

# 5. Clear all caches and restart everything
print("\n5. Nuclear restart - clearing everything...")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec nc-redis redis-cli FLUSHALL")
print(f"Redis flush: {'✅' if code == 0 else '❌'}")

code, out, err = ssh_command("cd /srv/docker/nc-rag && docker restart nextcloud traefik")
print(f"Container restart: {'✅' if code == 0 else '❌'}")

print("\n6. Waiting 30 seconds for full restart...")
time.sleep(30)

# 7. Test with different approach - check if we can bypass the redirect
print("\n7. Testing with direct dashboard access...")
test_cmd = '''
cd /srv/docker/nc-rag
COOKIE_JAR="/tmp/aggressive_test.txt"
rm -f "$COOKIE_JAR"

# Try to access dashboard directly first
echo "=== TESTING DIRECT DASHBOARD ACCESS ==="
DIRECT_RESPONSE=$(curl -s -c "$COOKIE_JAR" -w "STATUS:%{http_code}\\nURL:%{url_effective}\\n" "https://ncrag.voronkov.club/index.php/apps/files")
echo "$DIRECT_RESPONSE" | tail -2

echo -e "\n=== NORMAL LOGIN FLOW ==="
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\\K[^"]+' | head -1)

if [ -n "$CSRF_TOKEN" ]; then
    echo "CSRF Token: ${CSRF_TOKEN:0:30}..."
    
    # Try login without following redirects first
    echo -e "\n=== LOGIN WITHOUT REDIRECT FOLLOWING ==="
    NO_REDIRECT=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" \\
        -d "user=admin" \\
        -d "password=$NEXTCLOUD_PASSWORD" \\
        -d "requesttoken=$CSRF_TOKEN" \\
        -w "STATUS:%{http_code}\\nURL:%{url_effective}\\n" \\
        "https://ncrag.voronkov.club/login")
    echo "$NO_REDIRECT" | tail -2
    
    # Now try with redirect following
    echo -e "\n=== LOGIN WITH REDIRECT FOLLOWING ==="
    WITH_REDIRECT=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \\
        -d "user=admin" \\
        -d "password=$NEXTCLOUD_PASSWORD" \\
        -d "requesttoken=$CSRF_TOKEN" \\
        -w "STATUS:%{http_code}\\nURL:%{url_effective}\\n" \\
        "https://ncrag.voronkov.club/login")
    echo "$WITH_REDIRECT" | tail -2
    
    FINAL_URL=$(echo "$WITH_REDIRECT" | grep "URL:" | cut -d: -f2-)
    if [[ "$FINAL_URL" == *"/login"* ]]; then
        echo "❌ Still redirecting to login"
    else
        echo "✅ SUCCESS: Redirected to $FINAL_URL"
    fi
else
    echo "❌ No CSRF token found"
fi

rm -f "$COOKIE_JAR"
'''

code, out, err = ssh_command(test_cmd)
print(out)

# 8. Final configuration check
print("\n8. Final configuration verification:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:get trusted_proxies")
print(f"Final trusted proxies: {out.strip()}")

code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:get overwritehost")
print(f"Final overwrite host: {out.strip()}")

print("\n" + "=" * 50)
print("🔥 AGGRESSIVE FIX COMPLETE")
print("\nIf this doesn't work, the issue might be:")
print("1. Traefik routing configuration in docker-compose.yml")
print("2. SSL/TLS certificate issues")  
print("3. Application-level session handling bug")
print("4. Need to check Nextcloud application logs for specific errors")