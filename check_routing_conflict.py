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

print("🔍 CHECKING FOR TRAEFIK ROUTING CONFLICTS")
print("=" * 50)

# 1. Check all routes using the same domain
print("1. All services using ncrag.voronkov.club:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && grep -n 'ncrag.voronkov.club' docker-compose.yml")
print(out)

# 2. Check Nextcloud routing rules specifically
print("\n2. Nextcloud Traefik configuration:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && grep -A 10 -B 2 'traefik.http.routers.nextcloud' docker-compose.yml")
print(out)

# 3. Check Node-RED routing rules
print("\n3. Node-RED Traefik configuration:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && grep -A 10 -B 2 'traefik.http.routers.nodered' docker-compose.yml")
print(out)

# 4. Check priorities
print("\n4. Router priorities:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && grep -n 'priority' docker-compose.yml")
print(out)

# 5. Check if there are any middlewares
print("\n5. Traefik middlewares:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && grep -n 'middlewares' docker-compose.yml")
print(out)

# 6. Test direct access to Node-RED webhook path
print("\n6. Testing Node-RED webhook path:")
code, out, err = ssh_command('curl -I "https://ncrag.voronkov.club/webhooks/nextcloud"')
print(out)

# 7. Test if stopping Node-RED helps
print("\n7. Testing without Node-RED...")
print("Stopping Node-RED temporarily...")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker stop node-red")
print(f"Node-RED stop: {'✅' if code == 0 else '❌'}")

print("Restarting Traefik...")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker restart traefik")
print(f"Traefik restart: {'✅' if code == 0 else '❌'}")

print("Waiting 15 seconds...")
import time
time.sleep(15)

# Test login without Node-RED
print("\n8. Testing login without Node-RED:")
test_cmd = '''
cd /srv/docker/nc-rag
COOKIE_JAR="/tmp/no_nodered_test.txt"
rm -f "$COOKIE_JAR"

echo "Getting login page..."
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\\K[^"]+' | head -1)

if [ -z "$CSRF_TOKEN" ]; then
    echo "❌ No CSRF token"
    exit 1
fi

echo "CSRF: ${CSRF_TOKEN:0:30}..."

echo "Testing login without Node-RED..."
RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \\
    -d "user=admin" \\
    -d "password=$NEXTCLOUD_PASSWORD" \\
    -d "requesttoken=$CSRF_TOKEN" \\
    -w "STATUS:%{http_code}\\nURL:%{url_effective}\\n" \\
    "https://ncrag.voronkov.club/login")

STATUS=$(echo "$RESPONSE" | grep "STATUS:" | cut -d: -f2)
FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)

echo "Status: $STATUS"
echo "Final URL: $FINAL_URL"

if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ STILL REDIRECTING (Node-RED not the issue)"
elif echo "$RESPONSE" | grep -q "files\\|dashboard"; then
    echo "✅ SUCCESS WITHOUT NODE-RED!"
    echo "Node-RED was causing routing conflict!"
else
    echo "⚠️ Different response, checking content..."
    echo "$RESPONSE" | head -10
fi

rm -f "$COOKIE_JAR"
'''

code, out, err = ssh_command(test_cmd)
print(out)

# 9. Restart Node-RED if it wasn't the issue
if "SUCCESS" not in out:
    print("\n9. Node-RED wasn't the issue, restarting it...")
    code, out, err = ssh_command("cd /srv/docker/nc-rag && docker start node-red")
    print(f"Node-RED restart: {'✅' if code == 0 else '❌'}")

print("\n" + "=" * 50)
print("🔍 ROUTING CONFLICT CHECK COMPLETE")

# Final recommendations
print("\n📋 NEXT STEPS:")
print("1. If Node-RED was the issue: Fix routing priorities")
print("2. If not Node-RED: Check Traefik configuration")
print("3. Consider checking SSL certificate issues")
print("4. May need to modify docker-compose.yml routing rules")