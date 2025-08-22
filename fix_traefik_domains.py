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

print("🔧 FIXING TRAEFIK AND DOMAIN CONFIGURATION")
print("=" * 50)

# 1. Check current configuration first
print("1. Current Nextcloud configuration:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:list system")
if code == 0:
    print("✅ Nextcloud config accessible")
else:
    print("❌ Cannot access Nextcloud config")
    print(err)

# 2. Fix trusted domains
print("\n2. Setting trusted domains...")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set trusted_domains 0 --value='localhost'")
print(f"Set localhost: {out}")

code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set trusted_domains 1 --value='ncrag.voronkov.club'")
print(f"Set domain: {out}")

# 3. Fix overwrite settings - CRITICAL for proxy setup
print("\n3. Fixing overwrite settings for proxy...")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set overwrite.cli.url --value='https://ncrag.voronkov.club'")
print(f"CLI URL: {out}")

code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'")
print(f"Overwrite host: {out}")

code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'")
print(f"Overwrite protocol: {out}")

# 4. Set proxy settings - VERY IMPORTANT for Traefik
print("\n4. Setting proxy configuration...")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 0 --value='172.19.0.0/16'")
print(f"Trusted proxies: {out}")

# 5. Disable forwarded headers if causing issues
print("\n5. Setting forwarded headers...")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 0 --value='HTTP_X_FORWARDED_FOR'")
print(f"Forwarded headers: {out}")

# 6. Check if there's a specific Traefik issue with routing
print("\n6. Checking Traefik routing...")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker logs traefik --tail 10")
print("Recent Traefik logs:")
print(out)

# 7. Restart Nextcloud to apply changes
print("\n7. Restarting Nextcloud...")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker restart nextcloud")
print(f"Restart result: {code}")

# 8. Wait and test
print("\n8. Waiting 15 seconds for restart...")
import time
time.sleep(15)

# 9. Test the login flow again
print("\n9. Testing login flow...")
test_cmd = '''
cd /srv/docker/nc-rag
COOKIE_JAR="/tmp/test_$(date +%s).txt"
rm -f "$COOKIE_JAR"

echo "Getting login page..."
LOGIN_RESPONSE=$(curl -s -c "$COOKIE_JAR" -w "STATUS:%{http_code}\\nURL:%{url_effective}\\n" "https://ncrag.voronkov.club/login")
echo "$LOGIN_RESPONSE" | tail -2

echo "Extracting CSRF token..."
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\\K[^"]+' | head -1)

if [ -z "$CSRF_TOKEN" ]; then
    echo "❌ No CSRF token found"
    exit 1
fi

echo "CSRF token: ${CSRF_TOKEN:0:30}..."

echo "Testing POST login..."
POST_RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \\
    -d "user=admin" \\
    -d "password=$NEXTCLOUD_PASSWORD" \\
    -d "requesttoken=$CSRF_TOKEN" \\
    -w "STATUS:%{http_code}\\nURL:%{url_effective}\\n" \\
    "https://ncrag.voronkov.club/login")

echo "POST response:"
echo "$POST_RESPONSE" | tail -2

FINAL_URL=$(echo "$POST_RESPONSE" | grep "URL:" | cut -d: -f2-)
if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ Still redirecting to login"
else
    echo "✅ Redirected away from login - SUCCESS!"
fi
'''

code, out, err = ssh_command(test_cmd)
print(out)

# 10. Additional debugging
print("\n10. Additional debugging info:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:get trusted_domains")
print(f"Final trusted domains: {out}")

code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:get overwritehost")
print(f"Final overwrite host: {out}")

print("\n" + "=" * 50)
print("🔧 TRAEFIK/DOMAIN FIX COMPLETE")
print("\nIf still not working, the issue might be:")
print("1. Traefik routing configuration in docker-compose.yml")
print("2. SSL certificate issues")
print("3. Network connectivity between containers")
print("4. Browser cache (try incognito mode)")