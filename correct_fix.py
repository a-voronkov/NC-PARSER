#!/usr/bin/env python3
"""
Nextcloud Login Fix Script - Using correct password from NEXTCLOUD_PASSWORD
"""

import subprocess
import os
import time
import sys

def ssh_command(command, description=""):
    """Execute command on remote server via SSH"""
    ssh_cmd = [
        'sshpass', '-p', os.environ.get('SSH_PASSWORD', ''),
        'ssh', '-o', 'StrictHostKeyChecking=no',
        '-o', 'ConnectTimeout=10',
        f"{os.environ.get('SSH_USER')}@{os.environ.get('SSH_SERVER')}",
        command
    ]
    
    if description:
        print(f"\n>>> {description}")
    
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=60)
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(f"STDERR: {result.stderr.strip()}")
        return result.returncode == 0
    except Exception as e:
        print(f"Command failed: {e}")
        return False

def main():
    print("=" * 60)
    print("🔧 NEXTCLOUD LOGIN FIX - CORRECT PASSWORD")
    print("=" * 60)
    
    # Get the correct password
    frontend_password = os.environ.get('NEXTCLOUD_PASSWORD', '')
    api_token = os.environ.get('NEXTCLOUD_APP_PASSWORD', '')
    
    print(f"🌐 Target: {os.environ.get('SSH_SERVER')}")
    print(f"👤 User: {os.environ.get('SSH_USER')}")
    print(f"🔑 Frontend password length: {len(frontend_password)} chars")
    print(f"🎫 API token length: {len(api_token)} chars")
    
    if not frontend_password:
        print("❌ NEXTCLOUD_PASSWORD environment variable is empty!")
        sys.exit(1)
    
    # Step 1: Test SSH connection
    if not ssh_command('echo "SSH connection successful"; hostname; date', "Testing SSH connection"):
        print("❌ SSH connection failed!")
        sys.exit(1)
    
    # Step 2: Check containers
    ssh_command('cd /srv/docker/nc-rag && docker ps --format "table {{.Names}}\\t{{.Status}}"', "Checking Docker containers")
    
    # Step 3: Reset admin password to correct one
    print("\n🔑 Setting correct admin password...")
    reset_cmd = f"cd /srv/docker/nc-rag && docker exec -e OC_PASS='{frontend_password}' -u www-data nextcloud php occ user:resetpassword admin --password-from-env"
    if ssh_command(reset_cmd, "Resetting admin password"):
        print("✅ Password reset successful")
    else:
        print("❌ Password reset failed")
        return False
    
    # Step 4: Configure Redis properly
    print("\n🔧 Configuring Redis for sessions...")
    
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
        ssh_command(f'cd /srv/docker/nc-rag && {cmd}', f"Setting: {cmd.split()[-3] if len(cmd.split()) > 3 else 'config'}")
    
    # Step 5: Clear Redis cache and restart
    ssh_command('cd /srv/docker/nc-rag && docker exec nc-redis redis-cli FLUSHALL', "Clearing Redis cache")
    ssh_command('cd /srv/docker/nc-rag && docker restart nextcloud', "Restarting Nextcloud")
    
    print("\n⏳ Waiting 20 seconds for Nextcloud to restart...")
    time.sleep(20)
    
    # Step 6: Test login with correct password
    print("\n🧪 Testing login with correct password...")
    
    test_script = f'''
COOKIE_JAR="/tmp/nc_test_$(date +%s).txt"
rm -f "$COOKIE_JAR"
FRONTEND_PASS="{frontend_password}"

echo "1. Getting login page..."
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login" 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "❌ FAILED: Cannot access login page"
    exit 1
fi

echo "2. Extracting CSRF token..."
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\\K[^"]+' | head -1)
if [ -z "$CSRF_TOKEN" ]; then
    echo "❌ FAILED: Cannot extract CSRF token"
    exit 1
fi
echo "CSRF token: ${{CSRF_TOKEN:0:30}}..."

echo "3. Submitting login with correct password..."
RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \\
    -d "user=admin" \\
    -d "password=$FRONTEND_PASS" \\
    -d "requesttoken=$CSRF_TOKEN" \\
    -w "STATUS:%{{http_code}}\\nURL:%{{url_effective}}\\n" \\
    "https://ncrag.voronkov.club/login" 2>/dev/null)

STATUS=$(echo "$RESPONSE" | grep "STATUS:" | cut -d: -f2)
FINAL_URL=$(echo "$RESPONSE" | grep "URL:" | cut -d: -f2-)

echo "HTTP Status: $STATUS"
echo "Final URL: $FINAL_URL"

if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "❌ LOGIN FAILED: Still on login page"
    
    # Check for specific error indicators
    if echo "$RESPONSE" | grep -qi "wrong.*password\\|invalid.*credentials"; then
        echo "Error: Wrong credentials detected"
    elif echo "$RESPONSE" | grep -qi "too.*many.*attempts"; then
        echo "Error: Too many failed attempts"
    else
        echo "Error: Unknown login failure"
    fi
    
    exit 1
elif echo "$RESPONSE" | grep -q "files\\|dashboard\\|apps\\|<title>Files"; then
    echo "✅ LOGIN SUCCESS: Found dashboard/files content"
    exit 0
else
    echo "⚠️ UNCLEAR: Not on login page but no clear dashboard found"
    echo "Response contains: $(echo "$RESPONSE" | head -5)"
    exit 2
fi
'''
    
    login_success = ssh_command(f'cd /srv/docker/nc-rag && bash -c \'{test_script}\'', "Running login test")
    
    # Step 7: Final status
    print("\n" + "=" * 60)
    if login_success:
        print("🎉 SUCCESS! Nextcloud login is now working!")
        print("✅ You can now log in at: https://ncrag.voronkov.club")
        print("👤 Username: admin")
        print(f"🔑 Password: {frontend_password}")
        
        # Update .env file with correct password
        print("\n🔧 Updating .env file with correct password...")
        env_update_cmd = f"cd /srv/docker/nc-rag && sed -i 's/NEXTCLOUD_PASS=.*/NEXTCLOUD_PASS={frontend_password}/' .env && sed -i 's/NEXTCLOUD_ADMIN_PASSWORD=.*/NEXTCLOUD_ADMIN_PASSWORD={frontend_password}/' .env"
        ssh_command(env_update_cmd, "Updating .env file")
        
        return True
    else:
        print("❌ Login test failed")
        
        # Try fallback without Redis
        print("\n🔄 Trying fallback without Redis...")
        ssh_command('cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:delete memcache.distributed', "Removing Redis distributed cache")
        ssh_command('cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:delete memcache.locking', "Removing Redis locking cache")
        ssh_command('cd /srv/docker/nc-rag && docker restart nextcloud', "Restarting without Redis")
        
        time.sleep(15)
        
        fallback_success = ssh_command(f'cd /srv/docker/nc-rag && bash -c \'{test_script}\'', "Testing without Redis")
        
        if fallback_success:
            print("✅ SUCCESS WITHOUT REDIS! Redis was causing the issue")
            return True
        else:
            print("❌ Still failing - there may be a deeper issue")
            return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n📋 Next steps:")
            print("1. Test login manually at https://ncrag.voronkov.club")
            print("2. If working, consider updating repository with fixes")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)