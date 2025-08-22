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

print("🔍 ANALYZING DOCKER-COMPOSE CONFIGURATION")
print("=" * 60)

# 1. Get the current docker-compose.yml
print("1. Getting current docker-compose.yml...")
code, out, err = ssh_command("cd /srv/docker/nc-rag && cat docker-compose.yml")
if code != 0:
    print(f"❌ Failed to get docker-compose.yml: {err}")
    exit(1)

compose_content = out

# 2. Analyze Nextcloud service configuration
print("\n2. Nextcloud service configuration:")
lines = compose_content.split('\n')
in_nextcloud_section = False
nextcloud_config = []

for i, line in enumerate(lines):
    if 'nextcloud:' in line and 'image:' in lines[i+1] if i+1 < len(lines) else False:
        in_nextcloud_section = True
        nextcloud_config.append(f"{i+1}: {line}")
    elif in_nextcloud_section:
        if line.strip() and not line.startswith(' ') and ':' in line:
            # New service started
            break
        nextcloud_config.append(f"{i+1}: {line}")

for line in nextcloud_config[:30]:  # Limit output
    print(line)

# 3. Extract and analyze Traefik labels
print("\n3. Traefik labels analysis:")
traefik_labels = []
for line in nextcloud_config:
    if 'traefik.' in line:
        traefik_labels.append(line.split(': ', 1)[1] if ': ' in line else line)

for label in traefik_labels:
    print(f"  {label}")

# 4. Check for potential issues
print("\n4. Potential configuration issues:")

issues = []

# Check if rule has proper exclusion
nextcloud_rule = None
for label in traefik_labels:
    if 'traefik.http.routers.nextcloud.rule' in label:
        nextcloud_rule = label
        break

if nextcloud_rule:
    if '!PathPrefix' not in nextcloud_rule:
        issues.append("❌ Nextcloud rule doesn't exclude webhook path")
    else:
        issues.append("✅ Nextcloud rule properly excludes webhook path")
else:
    issues.append("❌ Nextcloud routing rule not found")

# Check priorities
has_nextcloud_priority = any('traefik.http.routers.nextcloud.priority' in label for label in traefik_labels)
if not has_nextcloud_priority:
    issues.append("❌ Nextcloud priority not set")
else:
    issues.append("✅ Nextcloud priority is set")

# Check entrypoints
has_websecure = any('entrypoints=websecure' in label for label in traefik_labels)
if not has_websecure:
    issues.append("❌ Nextcloud not using websecure entrypoint")
else:
    issues.append("✅ Nextcloud using websecure entrypoint")

# Check TLS
has_tls = any('tls.certresolver' in label for label in traefik_labels)
if not has_tls:
    issues.append("❌ No TLS certificate resolver")
else:
    issues.append("✅ TLS certificate resolver configured")

for issue in issues:
    print(f"  {issue}")

# 5. Create a corrected docker-compose.yml if needed
print("\n5. Creating corrected configuration...")

# Fix common issues
corrected_content = compose_content

# Ensure proper Nextcloud rule
if nextcloud_rule and '!PathPrefix' not in nextcloud_rule:
    old_rule = nextcloud_rule
    new_rule = old_rule.replace(')`"', ') && !PathPrefix(`/webhooks/nextcloud`)"')
    corrected_content = corrected_content.replace(old_rule, new_rule)
    print("✅ Fixed Nextcloud routing rule")

# Add missing priority if needed
if not has_nextcloud_priority:
    # Find the line with nextcloud rule and add priority after it
    rule_pattern = r'(- "traefik\.http\.routers\.nextcloud\.rule=[^"]*")'
    priority_addition = r'\1\n      - "traefik.http.routers.nextcloud.priority=100"'
    corrected_content = re.sub(rule_pattern, priority_addition, corrected_content)
    print("✅ Added Nextcloud priority")

# 6. Upload corrected configuration
print("\n6. Uploading corrected docker-compose.yml...")
upload_cmd = f'''
cd /srv/docker/nc-rag
cp docker-compose.yml docker-compose.yml.backup.$(date +%Y%m%d_%H%M%S)

cat > docker-compose.yml.new << 'EOF'
{corrected_content}
EOF

mv docker-compose.yml.new docker-compose.yml
echo "✅ docker-compose.yml updated"
'''

code, out, err = ssh_command(upload_cmd)
print(f"Upload result: {'✅ Success' if code == 0 else '❌ Failed'}")
if out:
    print(out)

print("\n" + "=" * 60)
print("🔍 ANALYSIS COMPLETE")
print("\nNext steps:")
print("1. Test with corrected docker-compose.yml")
print("2. Try Nextcloud 30 if still failing")
print("3. Test direct connection to bypass Traefik")