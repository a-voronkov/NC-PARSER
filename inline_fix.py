#!/usr/bin/env python3

# Import and execute immediately
import os
import time

# Get credentials
server = os.environ.get('SSH_SERVER')
user = os.environ.get('SSH_USER') 
password = os.environ.get('SSH_PASSWORD')
nc_password = os.environ.get('NEXTCLOUD_PASSWORD')

print(f"=== NEXTCLOUD FIX ===")
print(f"Server: {server}")
print(f"User: {user}")
print(f"NC Password: {nc_password[:5]}...")

# Commands to execute
cmd1 = f'sshpass -p "{password}" ssh -o StrictHostKeyChecking=no {user}@{server} "echo Connected; date"'
cmd2 = f'sshpass -p "{password}" ssh -o StrictHostKeyChecking=no {user}@{server} "cd /srv/docker/nc-rag && docker ps"'
cmd3 = f'sshpass -p "{password}" ssh -o StrictHostKeyChecking=no {user}@{server} "cd /srv/docker/nc-rag && docker exec -e OC_PASS=\'{nc_password}\' -u www-data nextcloud php occ user:resetpassword admin --password-from-env"'
cmd4 = f'sshpass -p "{password}" ssh -o StrictHostKeyChecking=no {user}@{server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set memcache.distributed --value=\'\\\\OC\\\\Memcache\\\\Redis\'"'
cmd5 = f'sshpass -p "{password}" ssh -o StrictHostKeyChecking=no {user}@{server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value=\'https\'"'
cmd6 = f'sshpass -p "{password}" ssh -o StrictHostKeyChecking=no {user}@{server} "cd /srv/docker/nc-rag && docker exec nc-redis redis-cli FLUSHALL"'
cmd7 = f'sshpass -p "{password}" ssh -o StrictHostKeyChecking=no {user}@{server} "cd /srv/docker/nc-rag && docker restart nextcloud"'

# Execute each command
for i, cmd in enumerate([cmd1, cmd2, cmd3, cmd4, cmd5, cmd6, cmd7], 1):
    print(f"\n{i}. Executing command...")
    result = os.system(cmd)
    print(f"Exit code: {result}")

print("\nWaiting 20 seconds...")
time.sleep(20)

# Test login
login_test = f'sshpass -p "{password}" ssh -o StrictHostKeyChecking=no {user}@{server} "COOKIE_JAR=\\"/tmp/test_\\$(date +%s).txt\\" && rm -f \\"\\$COOKIE_JAR\\" && LOGIN_PAGE=\\$(curl -s -c \\"\\$COOKIE_JAR\\" \\"https://ncrag.voronkov.club/login\\") && CSRF_TOKEN=\\$(echo \\"\\$LOGIN_PAGE\\" | grep -oP \'data-requesttoken=\\"\\\\K[^\\"]+\' | head -1) && echo \\"CSRF: \\${{CSRF_TOKEN:0:20}}...\\" && RESPONSE=\\$(curl -s -b \\"\\$COOKIE_JAR\\" -c \\"\\$COOKIE_JAR\\" -L -d \\"user=admin\\" -d \\"password={nc_password}\\" -d \\"requesttoken=\\$CSRF_TOKEN\\" -w \\"URL:%{{url_effective}}\\\\n\\" \\"https://ncrag.voronkov.club/login\\") && FINAL_URL=\\$(echo \\"\\$RESPONSE\\" | grep \\"URL:\\" | cut -d: -f2-) && echo \\"Final URL: \\$FINAL_URL\\" && if [[ \\"\\$FINAL_URL\\" == *\\"/login\\"* ]]; then echo \\"LOGIN FAILED\\"; else echo \\"LOGIN SUCCESS\\"; fi"'

print("\nTesting login...")
os.system(login_test)

print(f"\n=== COMPLETE ===")
print(f"Test at: https://ncrag.voronkov.club")
print(f"Username: admin")  
print(f"Password: {nc_password}")

# Execute immediately when imported
if __name__ == "__main__":
    pass