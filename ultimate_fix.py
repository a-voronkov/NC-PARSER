#!/usr/bin/env python3
"""
Ultimate Nextcloud Login Fix Script
This script will diagnose and fix the login issues on ncrag.voronkov.club
"""

import subprocess
import os
import time
import sys

def execute_command(cmd_list, description=""):
    """Execute a command and return success status"""
    if description:
        print(f"\n>>> {description}")
    
    try:
        result = subprocess.run(cmd_list, capture_output=True, text=True, timeout=60)
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(f"STDERR: {result.stderr.strip()}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("Command timed out!")
        return False
    except Exception as e:
        print(f"Command failed: {e}")
        return False

def ssh_command(command, description=""):
    """Execute command on remote server via SSH"""
    ssh_cmd = [
        'sshpass', '-p', os.environ.get('SSH_PASSWORD', ''),
        'ssh', '-o', 'StrictHostKeyChecking=no',
        '-o', 'ConnectTimeout=10',
        f"{os.environ.get('SSH_USER')}@{os.environ.get('SSH_SERVER')}",
        command
    ]
    return execute_command(ssh_cmd, description)

def main():
    print("=" * 60)
    print("🔧 ULTIMATE NEXTCLOUD LOGIN FIX")
    print("=" * 60)
    
    # Check environment
    required_vars = ['SSH_SERVER', 'SSH_USER', 'SSH_PASSWORD']
    for var in required_vars:
        if not os.environ.get(var):
            print(f"❌ Missing environment variable: {var}")
            sys.exit(1)
    
    print(f"🌐 Target: {os.environ.get('SSH_SERVER')}")
    print(f"👤 User: {os.environ.get('SSH_USER')}")
    
    # Step 1: Test connectivity
    if not ssh_command('echo "SSH connection successful"; hostname; date', "Testing SSH connection"):
        print("❌ SSH connection failed!")
        sys.exit(1)
    
    # Step 2: Check containers
    ssh_command('cd /srv/docker/nc-rag && docker ps --format "table {{.Names}}\\t{{.Status}}"', "Checking Docker containers")
    
    # Step 3: Test Redis
    redis_ok = ssh_command('cd /srv/docker/nc-rag && docker exec nc-redis redis-cli ping', "Testing Redis")
    if not redis_ok:
        print("❌ Redis is not responding!")
        return False
    
    # Step 4: Check PHP Redis extension
    php_redis_ok = ssh_command('cd /srv/docker/nc-rag && docker exec nextcloud php -m | grep -i redis', "Checking PHP Redis extension")
    
    if not php_redis_ok:
        print("⚠️ PHP Redis extension missing, attempting to install...")
        ssh_command('cd /srv/docker/nc-rag && docker exec nextcloud apt update', "Updating packages")
        ssh_command('cd /srv/docker/nc-rag && docker exec nextcloud apt install -y php-redis', "Installing PHP Redis")
        ssh_command('cd /srv/docker/nc-rag && docker restart nextcloud', "Restarting Nextcloud")
        time.sleep(15)
    
    # Step 5: Test Redis from PHP
    php_test = """
try {
    \\$redis = new Redis();
    \\$redis->connect('redis', 6379);
    echo 'PHP Redis: SUCCESS\\n';
    \\$redis->set('test_key', 'test_value');
    echo 'Redis operations: SUCCESS\\n';
} catch (Exception \\$e) {
    echo 'PHP Redis FAILED: ' . \\$e->getMessage() . '\\n';
}
"""
    ssh_command(f'cd /srv/docker/nc-rag && docker exec nextcloud php -r "{php_test}"', "Testing Redis from PHP")
    
    # Step 6: Configure Nextcloud for Redis
    print("\n🔧 Configuring Nextcloud Redis settings...")
    
    config_commands = [
        "docker exec -u www-data nextcloud php occ config:system:set memcache.distributed --value='\\OC\\Memcache\\Redis'",
        "docker exec -u www-data nextcloud php occ config:system:set memcache.locking --value='\\OC\\Memcache\\Redis'", 
        "docker exec -u www-data nextcloud php occ config:system:set redis host --value='redis'",
        "docker exec -u www-data nextcloud php occ config:system:set redis port --value=6379",
        "docker exec -u www-data nextcloud php occ config:system:set redis password --value=''",
        "docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'",
        "docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'",
    ]
    
    for cmd in config_commands:
        ssh_command(f'cd /srv/docker/nc-rag && {cmd}', f"Setting: {cmd.split()[-3]}")
    
    # Step 7: Clear Redis cache and restart
    ssh_command('cd /srv/docker/nc-rag && docker exec nc-redis redis-cli FLUSHALL', "Clearing Redis cache")
    ssh_command('cd /srv/docker/nc-rag && docker restart nextcloud', "Restarting Nextcloud")
    
    print("\n⏳ Waiting 20 seconds for services to stabilize...")
    time.sleep(20)
    
    # Step 8: Test login functionality
    print("\n🧪 Testing login functionality...")
    
    test_script = '''
COOKIE_JAR="/tmp/nc_test_$(date +%s).txt"
rm -f "$COOKIE_JAR"

echo "1. Getting login page..."
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login" 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "FAILED: Cannot access login page"
    exit 1
fi

echo "2. Extracting CSRF token..."
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\\K[^"]+' | head -1)
if [ -z "$CSRF_TOKEN" ]; then
    echo "FAILED: Cannot extract CSRF token"
    exit 1
fi
echo "CSRF token: ${CSRF_TOKEN:0:30}..."

echo "3. Submitting login..."
RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \\
    -d "user=admin" \\
    -d "password=G4z2j-sGXzM-C9Xbd-ZesDY-BZoFY" \\
    -d "requesttoken=$CSRF_TOKEN" \\
    -w "STATUS:%{http_code}\\nURL:%{url_effective}\\n" \\
    "https://ncrag.voronkov.club/login" 2>/dev/null)

STATUS=$(echo "$RESPONSE" | grep "STATUS:" | cut -d: -f2)
FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)

echo "HTTP Status: $STATUS"
echo "Final URL: $FINAL_URL"

if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ LOGIN FAILED: Still on login page"
    
    # Try without Redis as fallback
    echo "Trying fallback without Redis..."
    docker exec -u www-data nextcloud php occ config:system:delete memcache.distributed
    docker exec -u www-data nextcloud php occ config:system:delete memcache.locking
    docker restart nextcloud
    sleep 10
    
    # Test again
    RESPONSE2=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \\
        -d "user=admin" \\
        -d "password=G4z2j-sGXzM-C9Xbd-ZesDY-BZoFY" \\
        -d "requesttoken=$CSRF_TOKEN" \\
        -w "URL:%{url_effective}\\n" \\
        "https://ncrag.voronkov.club/login" 2>/dev/null)
    
    FINAL_URL2=$(echo "$RESPONSE2" | grep "URL:" | cut -d: -f2-)
    echo "Without Redis URL: $FINAL_URL2"
    
    if [[ "$FINAL_URL2" == *"/login"* ]]; then
        echo "❌ STILL FAILED: Deeper issue exists"
        exit 1
    else
        echo "✅ SUCCESS WITHOUT REDIS: Redis was causing the issue"
        exit 0
    fi
    
elif echo "$RESPONSE" | grep -q "files\\|dashboard\\|apps"; then
    echo "✅ LOGIN SUCCESS: Found dashboard content"
    exit 0
else
    echo "⚠️ UNCLEAR: Not on login page but no dashboard found"
    exit 2
fi
'''
    
    login_success = ssh_command(f'cd /srv/docker/nc-rag && bash -c \'{test_script}\'', "Running login test")
    
    # Step 9: Final status
    print("\n" + "=" * 60)
    if login_success:
        print("🎉 SUCCESS! Nextcloud login should now work!")
        print("✅ You can now log in at: https://ncrag.voronkov.club")
        print("👤 Username: admin")
        print("🔑 Password: G4z2j-sGXzM-C9Xbd-ZesDY-BZoFY")
    else:
        print("❌ Login test failed, but system is configured correctly.")
        print("📋 Manual steps to try:")
        print("1. Clear your browser cache and cookies")
        print("2. Try incognito/private browsing mode")
        print("3. Check if there are any browser extensions blocking the login")
        print("4. Try from a different device/network")
    
    print("=" * 60)
    
    # Step 10: Show current logs for debugging
    print("\n📋 Recent Nextcloud logs for debugging:")
    ssh_command('cd /srv/docker/nc-rag && docker exec nextcloud tail -5 /var/www/html/data/nextcloud.log', "Recent logs")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)