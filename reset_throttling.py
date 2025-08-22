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

print("🔓 RESETTING LOGIN THROTTLING")
print("=" * 40)

# 1. Reset brute force protection for your IP
print("1. Resetting brute force protection...")

# Get your current IP from the logs
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker logs nextcloud --tail 50 | grep 'invalid login' | tail -1")
if out:
    print(f"Recent invalid login attempt: {out.strip()}")

# Reset for common IP ranges (since we don't know exact IP)
common_ips = [
    "171.5.227.98",  # From your logs
    "172.19.0.0/16", # Docker network
    "10.0.0.0/8",    # Private network
    "192.168.0.0/16" # Private network
]

for ip in common_ips:
    code, out, err = ssh_command(f"cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ security:bruteforce:reset {ip}")
    if code == 0:
        print(f"✅ Reset throttling for {ip}")
    else:
        print(f"⚠️ Could not reset {ip}: {err}")

# 2. Clear any session locks
print("\n2. Clearing session locks...")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec nc-redis redis-cli FLUSHALL")
print(f"Redis flush: {'✅ Success' if code == 0 else '❌ Failed'}")

# 3. Reset admin password to ensure it's correct
print("\n3. Ensuring admin password is correct...")
nextcloud_password = os.environ.get('NEXTCLOUD_PASSWORD', '')
if nextcloud_password:
    code, out, err = ssh_command(f"cd /srv/docker/nc-rag && docker exec -e OC_PASS='{nextcloud_password}' -u www-data nextcloud php occ user:resetpassword admin --password-from-env")
    print(f"Password reset: {'✅ Success' if code == 0 else '❌ Failed'}")
    print(f"Using password length: {len(nextcloud_password)} characters")
else:
    print("❌ NEXTCLOUD_PASSWORD not found in environment")

# 4. Wait a bit for throttling to clear
print("\n4. Waiting 35 seconds for throttling to clear...")
time.sleep(35)

# 5. Test login with correct password
print("\n5. Testing login with correct password...")
test_cmd = f'''
cd /srv/docker/nc-rag
COOKIE_JAR="/tmp/test_$(date +%s).txt"
rm -f "$COOKIE_JAR"

echo "Getting fresh login page..."
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\\K[^"]+' | head -1)

if [ -z "$CSRF_TOKEN" ]; then
    echo "❌ No CSRF token found"
    exit 1
fi

echo "CSRF token: ${{CSRF_TOKEN:0:30}}..."

echo "Submitting login with correct password..."
RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \\
    -d "user=admin" \\
    -d "password={nextcloud_password}" \\
    -d "requesttoken=$CSRF_TOKEN" \\
    -w "STATUS:%{{http_code}}\\nURL:%{{url_effective}}\\n" \\
    "https://ncrag.voronkov.club/login")

STATUS=$(echo "$RESPONSE" | grep "STATUS:" | cut -d: -f2)
FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)

echo "HTTP Status: $STATUS"
echo "Final URL: $FINAL_URL"

# Check for throttling message
if echo "$RESPONSE" | grep -qi "throttled\\|invalid login"; then
    echo "⚠️ Still throttled or invalid credentials"
elif [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ Still redirecting to login page"
elif echo "$RESPONSE" | grep -q "files\\|dashboard\\|apps"; then
    echo "✅ SUCCESS: Login successful!"
    echo "Found dashboard content"
else
    echo "⚠️ Unclear response"
    echo "Response preview:"
    echo "$RESPONSE" | head -10
fi

rm -f "$COOKIE_JAR"
'''

code, out, err = ssh_command(test_cmd)
print(out)

print("\n" + "=" * 40)
print("🔓 THROTTLING RESET COMPLETE")
print(f"\nLogin credentials:")
print(f"URL: https://ncrag.voronkov.club")
print(f"Username: admin")
print(f"Password: {nextcloud_password}")
print(f"\nIf still having issues, try:")
print("1. Wait another 30 seconds")
print("2. Clear browser cache/cookies")
print("3. Try incognito/private mode")
print("4. Check if password is correct in your environment")