#!/usr/bin/env python3
import subprocess
import os
import json
import sys
from datetime import datetime

# SSH connection details from environment
SSH_SERVER = os.getenv('SSH_SERVER')
SSH_USER = os.getenv('SSH_USER')
SSH_PASSWORD = os.getenv('SSH_PASSWORD')
NEXTCLOUD_PASSWORD = os.getenv('NEXTCLOUD_APP_PASSWORD', 'G4z2j-sGXzM-C9Xbd-ZesDY-BZoFY')

def run_ssh_command(command):
    """Run command on remote server via SSH"""
    full_command = [
        'sshpass', '-p', SSH_PASSWORD,
        'ssh', '-o', 'StrictHostKeyChecking=no',
        f'{SSH_USER}@{SSH_SERVER}',
        command
    ]
    try:
        result = subprocess.run(full_command, capture_output=True, text=True, timeout=30)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)

def check_containers():
    """Check Docker container status"""
    print("=== Checking Docker containers ===")
    code, out, err = run_ssh_command("cd /srv/docker/nc-rag && docker ps --format 'table {{.Names}}\t{{.Status}}'")
    if code == 0:
        print(out)
        return True
    else:
        print(f"Error: {err}")
        return False

def check_redis_connection():
    """Check Redis connectivity from Nextcloud"""
    print("\n=== Checking Redis connection ===")
    
    # Test Redis ping
    code, out, err = run_ssh_command("cd /srv/docker/nc-rag && docker exec nc-redis redis-cli ping")
    if code == 0:
        print(f"Redis ping: {out.strip()}")
    else:
        print(f"Redis ping failed: {err}")
        return False
    
    # Test PHP Redis extension
    code, out, err = run_ssh_command("cd /srv/docker/nc-rag && docker exec nextcloud php -m | grep -i redis")
    if code == 0:
        print(f"PHP Redis extension: {out.strip()}")
    else:
        print("PHP Redis extension not found")
        return False
    
    # Test Redis connection from PHP
    php_test = """
try {
    $redis = new Redis();
    $redis->connect('redis', 6379);
    echo 'Redis connection: SUCCESS\\n';
    $redis->set('test_key', 'test_value');
    echo 'Redis set/get: ' . $redis->get('test_key') . '\\n';
} catch (Exception $e) {
    echo 'Redis connection FAILED: ' . $e->getMessage() . '\\n';
}
"""
    code, out, err = run_ssh_command(f"cd /srv/docker/nc-rag && docker exec nextcloud php -r \"{php_test}\"")
    print(f"PHP Redis test: {out}")
    
    return "SUCCESS" in out

def check_nextcloud_config():
    """Check Nextcloud configuration"""
    print("\n=== Checking Nextcloud configuration ===")
    
    # Get system config
    code, out, err = run_ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:get redis")
    if code == 0:
        print(f"Redis config: {out}")
    else:
        print(f"Redis config error: {err}")
    
    # Check memcache settings
    code, out, err = run_ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:get memcache.distributed")
    if code == 0:
        print(f"Memcache distributed: {out}")
    
    code, out, err = run_ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:get memcache.locking")
    if code == 0:
        print(f"Memcache locking: {out}")
    
    # Check overwrite settings
    code, out, err = run_ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:get overwriteprotocol")
    if code == 0:
        print(f"Overwrite protocol: {out}")
    
    code, out, err = run_ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:get overwritehost")
    if code == 0:
        print(f"Overwrite host: {out}")

def check_logs():
    """Check recent logs"""
    print("\n=== Checking recent logs ===")
    
    # Nextcloud logs
    code, out, err = run_ssh_command("cd /srv/docker/nc-rag && docker exec nextcloud tail -10 /var/www/html/data/nextcloud.log")
    if code == 0:
        print("Recent Nextcloud logs:")
        for line in out.strip().split('\n'):
            if line.strip():
                try:
                    log_entry = json.loads(line)
                    print(f"  {log_entry.get('time', 'N/A')} [{log_entry.get('level', 'N/A')}] {log_entry.get('message', 'N/A')}")
                except:
                    print(f"  {line}")
    
    # Container logs
    code, out, err = run_ssh_command("cd /srv/docker/nc-rag && docker logs nextcloud --tail 10")
    if code == 0:
        print(f"\nNextcloud container logs:\n{out}")

def test_login_flow():
    """Test login flow with curl"""
    print("\n=== Testing login flow ===")
    
    # Create test script on server
    test_script = f'''#!/bin/bash
COOKIE_JAR="/tmp/nc_test_cookies.txt"
LOGIN_URL="https://ncrag.voronkov.club/login"
USERNAME="admin"
PASSWORD="{NEXTCLOUD_PASSWORD}"

rm -f "$COOKIE_JAR"

echo "1. Getting login page..."
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "$LOGIN_URL" 2>/dev/null)
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
echo "CSRF Token found: ${{CSRF_TOKEN:0:20}}..."

echo "3. Submitting login..."
RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \\
    -d "user=$USERNAME" \\
    -d "password=$PASSWORD" \\
    -d "requesttoken=$CSRF_TOKEN" \\
    -w "HTTPSTATUS:%{{http_code}}\\nFINAL_URL:%{{url_effective}}\\n" \\
    "$LOGIN_URL" 2>/dev/null)

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTPSTATUS" | cut -d: -f2)
FINAL_URL=$(echo "$RESPONSE" | grep "FINAL_URL" | cut -d: -f2-)

echo "HTTP Status: $HTTP_STATUS"
echo "Final URL: $FINAL_URL"

if [[ "$FINAL_URL" == *"/login"* ]]; then
    echo "RESULT: FAILED - Still on login page"
    exit 1
elif echo "$RESPONSE" | grep -q "files\\|dashboard\\|apps"; then
    echo "RESULT: SUCCESS - Login successful"
    exit 0
else
    echo "RESULT: UNCLEAR - Unexpected response"
    exit 1
fi
'''
    
    # Write script to server
    code, out, err = run_ssh_command(f"cat > /tmp/test_login.sh << 'EOF'\n{test_script}\nEOF")
    if code != 0:
        print(f"Failed to create test script: {err}")
        return False
    
    # Make executable and run
    code, out, err = run_ssh_command("chmod +x /tmp/test_login.sh && /tmp/test_login.sh")
    print(f"Login test result:\n{out}")
    if err:
        print(f"Login test errors:\n{err}")
    
    return code == 0

def main():
    print(f"=== Nextcloud Login Diagnosis Started at {datetime.now()} ===")
    print(f"Target server: {SSH_SERVER}")
    print(f"Target site: https://ncrag.voronkov.club")
    
    if not all([SSH_SERVER, SSH_USER, SSH_PASSWORD]):
        print("ERROR: SSH credentials not found in environment")
        sys.exit(1)
    
    # Run diagnostics
    containers_ok = check_containers()
    if not containers_ok:
        print("ERROR: Containers are not running properly")
        return
    
    redis_ok = check_redis_connection()
    check_nextcloud_config()
    check_logs()
    login_ok = test_login_flow()
    
    print(f"\n=== Summary ===")
    print(f"Containers: {'✅' if containers_ok else '❌'}")
    print(f"Redis: {'✅' if redis_ok else '❌'}")
    print(f"Login: {'✅' if login_ok else '❌'}")
    
    if not redis_ok:
        print("\n🔧 Redis connection issues detected. Recommended fixes:")
        print("1. Restart Redis and Nextcloud containers")
        print("2. Check Redis configuration in Nextcloud")
        print("3. Verify network connectivity between containers")
    
    if not login_ok:
        print("\n🔧 Login issues detected. Recommended fixes:")
        print("1. Check session configuration")
        print("2. Verify CSRF token handling")
        print("3. Check trusted domains and HTTPS settings")

if __name__ == "__main__":
    main()