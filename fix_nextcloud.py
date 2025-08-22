#!/usr/bin/env python3
import os
import subprocess
import time
import json

def execute_ssh(command):
    """Execute command via SSH"""
    ssh_cmd = [
        'sshpass', '-p', os.environ['SSH_PASSWORD'],
        'ssh', '-o', 'StrictHostKeyChecking=no',
        f"{os.environ['SSH_USER']}@{os.environ['SSH_SERVER']}",
        command
    ]
    result = subprocess.run(ssh_cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def main():
    print("=== Nextcloud Fix Script ===")
    
    # Step 1: Check current state
    print("1. Checking containers...")
    code, out, err = execute_ssh("cd /srv/docker/nc-rag && docker ps --format 'table {{.Names}}\t{{.Status}}'")
    if code == 0:
        print(out)
    else:
        print(f"Error: {err}")
        return
    
    # Step 2: Check Redis connection
    print("\n2. Testing Redis...")
    code, out, err = execute_ssh("cd /srv/docker/nc-rag && docker exec nc-redis redis-cli ping")
    print(f"Redis ping: {out.strip()}")
    
    # Step 3: Check PHP Redis extension
    print("\n3. Checking PHP Redis extension...")
    code, out, err = execute_ssh("cd /srv/docker/nc-rag && docker exec nextcloud php -m | grep -i redis")
    if code == 0:
        print(f"PHP Redis: {out.strip()}")
    else:
        print("PHP Redis extension not found!")
        
        # Install Redis extension
        print("Installing PHP Redis extension...")
        execute_ssh("cd /srv/docker/nc-rag && docker exec nextcloud apt update")
        execute_ssh("cd /srv/docker/nc-rag && docker exec nextcloud apt install -y php-redis")
        execute_ssh("cd /srv/docker/nc-rag && docker restart nextcloud")
        time.sleep(10)
    
    # Step 4: Test Redis from PHP
    print("\n4. Testing Redis from PHP...")
    php_test = """
try {
    \$redis = new Redis();
    \$redis->connect('redis', 6379);
    echo 'SUCCESS: Redis connected\\n';
    \$redis->set('test', 'value');
    echo 'SUCCESS: Redis set/get works\\n';
} catch (Exception \$e) {
    echo 'FAILED: ' . \$e->getMessage() . '\\n';
}
"""
    code, out, err = execute_ssh(f"cd /srv/docker/nc-rag && docker exec nextcloud php -r \"{php_test}\"")
    print(f"PHP Redis test: {out}")
    
    # Step 5: Fix Nextcloud configuration
    print("\n5. Fixing Nextcloud configuration...")
    
    # Set Redis as session handler
    execute_ssh("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set memcache.distributed --value='\\OC\\Memcache\\Redis'")
    execute_ssh("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set memcache.locking --value='\\OC\\Memcache\\Redis'")
    
    # Ensure proper Redis config
    execute_ssh("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set redis host --value='redis'")
    execute_ssh("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set redis port --value=6379")
    execute_ssh("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set redis password --value=''")
    
    # Set proper HTTPS settings
    execute_ssh("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value='https'")
    execute_ssh("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set overwritehost --value='ncrag.voronkov.club'")
    
    # Step 6: Clear sessions and restart
    print("\n6. Clearing sessions and restarting...")
    execute_ssh("cd /srv/docker/nc-rag && docker exec nc-redis redis-cli FLUSHALL")
    execute_ssh("cd /srv/docker/nc-rag && docker restart nextcloud")
    time.sleep(15)
    
    # Step 7: Test login
    print("\n7. Testing login...")
    test_script = '''
COOKIE_JAR="/tmp/test_cookies.txt"
rm -f "$COOKIE_JAR"

# Get login page
LOGIN_PAGE=$(curl -s -c "$COOKIE_JAR" "https://ncrag.voronkov.club/login")
CSRF_TOKEN=$(echo "$LOGIN_PAGE" | grep -oP 'data-requesttoken="\\K[^"]+' | head -1)

if [ -z "$CSRF_TOKEN" ]; then
    echo "FAILED: No CSRF token"
    exit 1
fi

# Submit login
RESPONSE=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -L \\
    -d "user=admin" \\
    -d "password=G4z2j-sGXzM-C9Xbd-ZesDY-BZoFY" \\
    -d "requesttoken=$CSRF_TOKEN" \\
    -w "STATUS:%{http_code}\\nURL:%{url_effective}\\n" \\
    "https://ncrag.voronkov.club/login")

echo "$RESPONSE" | tail -2
if echo "$RESPONSE" | grep -q "files\\|dashboard"; then
    echo "SUCCESS: Login working!"
else
    echo "FAILED: Still redirecting to login"
fi
'''
    
    code, out, err = execute_ssh(f"bash -c '{test_script}'")
    print(f"Login test result:\n{out}")
    
    print("\n=== Fix Complete ===")
    print("Try logging in at https://ncrag.voronkov.club")
    print("Username: admin")
    print("Password: G4z2j-sGXzM-C9Xbd-ZesDY-BZoFY")

if __name__ == "__main__":
    main()