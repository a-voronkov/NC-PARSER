#!/usr/bin/env python3
import subprocess
import os
import json

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

print("🔍 DEEP DEBUGGING: LOGIN REDIRECT ISSUE")
print("=" * 50)

# 1. Check current Nextcloud system config
print("1. Current Nextcloud system configuration:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:list system")
if code == 0:
    try:
        config = json.loads(out)
        system_config = config.get('system', {})
        print(f"✅ Trusted domains: {system_config.get('trusted_domains', 'Not set')}")
        print(f"✅ Overwrite host: {system_config.get('overwritehost', 'Not set')}")
        print(f"✅ Overwrite protocol: {system_config.get('overwriteprotocol', 'Not set')}")
        print(f"✅ CLI URL: {system_config.get('overwrite.cli.url', 'Not set')}")
        print(f"✅ Trusted proxies: {system_config.get('trusted_proxies', 'Not set')}")
        print(f"✅ Forwarded headers: {system_config.get('forwarded_for_headers', 'Not set')}")
    except:
        print("Raw config output:")
        print(out)
else:
    print(f"❌ Failed to get config: {err}")

# 2. Check Traefik labels in detail
print("\n2. Traefik labels for Nextcloud:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && grep -A 15 -B 5 'traefik.http.routers.nextcloud' docker-compose.yml")
print(out)

# 3. Check if there are conflicting routes
print("\n3. All Traefik routes in docker-compose:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && grep 'traefik.http.routers' docker-compose.yml")
print(out)

# 4. Test with verbose curl to see exact headers
print("\n4. Verbose curl test to see headers:")
test_cmd = '''
cd /srv/docker/nc-rag
COOKIE_JAR="/tmp/debug_cookies.txt"
rm -f "$COOKIE_JAR"

echo "=== GET LOGIN PAGE ==="
curl -v -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login" 2>&1 | head -30

echo -e "\n=== EXTRACT CSRF TOKEN ==="
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\\K[^"]+' | head -1)
echo "CSRF Token: ${CSRF_TOKEN:0:50}..."

echo -e "\n=== POST LOGIN (VERBOSE) ==="
curl -v -b "$COOKIE_JAR" -c "$COOKIE_JAR" \\
    -d "user=admin" \\
    -d "password=$NEXTCLOUD_PASSWORD" \\
    -d "requesttoken=$CSRF_TOKEN" \\
    "https://ncrag.voronkov.club/login" 2>&1 | head -40
'''

code, out, err = ssh_command(test_cmd)
print(out)

# 5. Check if there's a specific issue with session handling
print("\n5. Check session configuration:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:get session_lifetime")
print(f"Session lifetime: {out.strip()}")

# 6. Check if maintenance mode or other issues
print("\n6. Check maintenance mode and other status:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ status")
print(out)

# 7. Check PHP session settings
print("\n7. Check PHP session settings:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec nextcloud php -i | grep -A 10 'Session Support'")
print(out)

# 8. Check if there's an issue with the specific redirect
print("\n8. Testing direct access to redirect URL:")
code, out, err = ssh_command('curl -I "https://ncrag.voronkov.club/login?direct=1&user=admin"')
print(out)

# 9. Check container networking
print("\n9. Container network information:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker inspect nextcloud | grep -A 20 'Networks'")
print(out[:1000])  # Limit output

print("\n" + "=" * 50)
print("🔍 DEBUG COMPLETE")

# Analysis and recommendations
print("\n📋 ANALYSIS:")
print("Look for these issues in the output above:")
print("1. Trusted proxies not matching Traefik network")
print("2. Missing or incorrect overwrite settings")
print("3. Conflicting Traefik routes")
print("4. Session handling issues")
print("5. HTTP vs HTTPS redirect problems")