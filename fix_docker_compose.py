#!/usr/bin/env python3
import subprocess
import os
import re

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

print("🔧 FIXING DOCKER-COMPOSE ROUTING PRIORITIES")
print("=" * 50)

# 1. Download current docker-compose.yml
print("1. Getting current docker-compose.yml...")
code, out, err = ssh_command("cd /srv/docker/nc-rag && cat docker-compose.yml")
if code != 0:
    print(f"❌ Failed to get docker-compose.yml: {err}")
    exit(1)

docker_compose_content = out

# 2. Check current routing rules
print("\n2. Current routing configuration:")
nextcloud_rules = []
nodered_rules = []

for line_num, line in enumerate(docker_compose_content.split('\n'), 1):
    if 'traefik.http.routers.nextcloud' in line:
        nextcloud_rules.append(f"{line_num}: {line.strip()}")
    elif 'traefik.http.routers.nodered' in line:
        nodered_rules.append(f"{line_num}: {line.strip()}")

print("Nextcloud rules:")
for rule in nextcloud_rules:
    print(f"  {rule}")

print("Node-RED rules:")
for rule in nodered_rules:
    print(f"  {rule}")

# 3. Create fixed docker-compose.yml
print("\n3. Creating fixed docker-compose.yml...")

# Fix the routing rules to avoid conflicts
fixed_content = docker_compose_content

# Ensure Nextcloud has the correct rule with exclusion
nextcloud_rule_pattern = r'(- "traefik\.http\.routers\.nextcloud\.rule=Host\(`[^`]+`\))[^"]*(")'
nextcloud_rule_replacement = r'\1 && !PathPrefix(`/webhooks/nextcloud`)\2'

if re.search(nextcloud_rule_pattern, fixed_content):
    fixed_content = re.sub(nextcloud_rule_pattern, nextcloud_rule_replacement, fixed_content)
    print("✅ Updated Nextcloud rule to exclude /webhooks/nextcloud")
else:
    print("⚠️ Could not find Nextcloud rule pattern")

# Ensure priorities are set correctly
if 'traefik.http.routers.nextcloud.priority' not in fixed_content:
    # Add priority after the Nextcloud rule
    nextcloud_section_pattern = r'(- "traefik\.http\.routers\.nextcloud\.rule=[^"]*")'
    nextcloud_priority_add = r'\1\n      - "traefik.http.routers.nextcloud.priority=100"'
    fixed_content = re.sub(nextcloud_section_pattern, nextcloud_priority_add, fixed_content)
    print("✅ Added Nextcloud priority=100")

if 'traefik.http.routers.nodered.priority' not in fixed_content:
    # Add priority after the Node-RED rule
    nodered_section_pattern = r'(- "traefik\.http\.routers\.nodered\.rule=[^"]*")'
    nodered_priority_add = r'\1\n      - "traefik.http.routers.nodered.priority=1000"'
    fixed_content = re.sub(nodered_section_pattern, nodered_priority_add, fixed_content)
    print("✅ Added Node-RED priority=1000")

# 4. Upload fixed docker-compose.yml
print("\n4. Uploading fixed docker-compose.yml...")

# Create a script to write the file
upload_script = f'''cat > /srv/docker/nc-rag/docker-compose.yml.new << 'EOF'
{fixed_content}
EOF

# Backup original
cp /srv/docker/nc-rag/docker-compose.yml /srv/docker/nc-rag/docker-compose.yml.backup.$(date +%Y%m%d_%H%M%S)

# Replace with new version
mv /srv/docker/nc-rag/docker-compose.yml.new /srv/docker/nc-rag/docker-compose.yml

echo "✅ docker-compose.yml updated"
'''

code, out, err = ssh_command(upload_script)
print(f"Upload result: {'✅ Success' if code == 0 else '❌ Failed'}")
if out:
    print(out)

# 5. Restart services with new configuration
print("\n5. Restarting services with new configuration...")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker compose down && docker compose up -d")
print(f"Service restart: {'✅ Success' if code == 0 else '❌ Failed'}")

print("\n6. Waiting 30 seconds for services to start...")
import time
time.sleep(30)

# 7. Test login with fixed configuration
print("\n7. Testing login with fixed routing...")
test_cmd = '''
cd /srv/docker/nc-rag
COOKIE_JAR="/tmp/fixed_routing_test.txt"
rm -f "$COOKIE_JAR"

LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\\K[^"]+' | head -1)

echo "CSRF: ${CSRF_TOKEN:0:30}..."

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
    echo "❌ STILL REDIRECTING"
elif echo "$RESPONSE" | grep -q "files\\|dashboard"; then
    echo "✅ SUCCESS: LOGIN WORKING!"
else
    echo "⚠️ Unclear response"
fi

rm -f "$COOKIE_JAR"
'''

code, out, err = ssh_command(test_cmd)
print(out)

print("\n" + "=" * 50)
print("🔧 DOCKER-COMPOSE FIX COMPLETE")
print("\nIf this fixed it, the issue was routing priority conflicts!")
print("If not, we may need to check SSL certificates or other issues.")