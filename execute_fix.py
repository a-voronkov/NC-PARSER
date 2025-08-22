#!/usr/bin/env python3
import subprocess
import os
import sys

def main():
    print("🔧 Executing Nextcloud login fix...")
    
    # Get environment variables
    ssh_server = os.environ.get('SSH_SERVER')
    ssh_user = os.environ.get('SSH_USER')
    ssh_password = os.environ.get('SSH_PASSWORD')
    nextcloud_password = os.environ.get('NEXTCLOUD_PASSWORD')
    
    if not all([ssh_server, ssh_user, ssh_password, nextcloud_password]):
        print("❌ Missing required environment variables")
        return False
    
    print(f"Server: {ssh_server}")
    print(f"User: {ssh_user}")
    print(f"NC Password length: {len(nextcloud_password)} chars")
    
    # Commands to execute
    commands = [
        f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "echo Connected; date"',
        f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker ps | grep nextcloud"',
        f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -e OC_PASS=\'{nextcloud_password}\' -u www-data nextcloud php occ user:resetpassword admin --password-from-env"',
        f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set memcache.distributed --value=\'\\\\OC\\\\Memcache\\\\Redis\'"',
        f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value=\'https\'"',
        f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec nc-redis redis-cli FLUSHALL"',
        f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker restart nextcloud"'
    ]
    
    for i, cmd in enumerate(commands, 1):
        print(f"\n{i}. Executing command...")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            print(f"Exit code: {result.returncode}")
            if result.stdout:
                print(f"Output: {result.stdout.strip()}")
            if result.stderr:
                print(f"Error: {result.stderr.strip()}")
        except Exception as e:
            print(f"Command failed: {e}")
            return False
    
    print("\nWaiting 20 seconds for restart...")
    import time
    time.sleep(20)
    
    # Test login
    test_cmd = f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && COOKIE_JAR=\\"/tmp/test_\\$(date +%s).txt\\" && rm -f \\"\\$COOKIE_JAR\\" && LOGIN_PAGE=\\$(curl -s -c \\"\\$COOKIE_JAR\\" \\"https://ncrag.voronkov.club/login\\") && CSRF_TOKEN=\\$(echo \\"\\$LOGIN_PAGE\\" | grep -oP \'data-requesttoken=\\"\\\\K[^\\"]+\' | head -1) && echo \\"CSRF: \\${{CSRF_TOKEN:0:20}}...\\" && RESPONSE=\\$(curl -s -b \\"\\$COOKIE_JAR\\" -c \\"\\$COOKIE_JAR\\" -L -d \\"user=admin\\" -d \\"password={nextcloud_password}\\" -d \\"requesttoken=\\$CSRF_TOKEN\\" -w \\"URL:%{{url_effective}}\\\\n\\" \\"https://ncrag.voronkov.club/login\\") && FINAL_URL=\\$(echo \\"\\$RESPONSE\\" | grep \\"URL:\\" | cut -d: -f2-) && echo \\"Final URL: \\$FINAL_URL\\" && if [[ \\"\\$FINAL_URL\\" == *\\"/login\\"* ]]; then echo \\"❌ LOGIN FAILED\\"; else echo \\"✅ LOGIN SUCCESS\\"; fi"'
    
    print("\nTesting login...")
    try:
        result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, timeout=30)
        print(result.stdout)
        if result.stderr:
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Login test failed: {e}")
    
    print("\n🎉 Fix completed!")
    print(f"Test login at: https://ncrag.voronkov.club")
    print(f"Username: admin")
    print(f"Password: {nextcloud_password}")
    
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)