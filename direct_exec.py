import os

# Get environment variables
ssh_server = os.getenv('SSH_SERVER')
ssh_user = os.getenv('SSH_USER')
ssh_password = os.getenv('SSH_PASSWORD')
nextcloud_password = os.getenv('NEXTCLOUD_PASSWORD')

print(f"Server: {ssh_server}")
print(f"User: {ssh_user}")
print(f"Password length: {len(nextcloud_password)} chars")

# Execute commands using os.system
commands = [
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "echo Connected; date"',
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker ps"',
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -e OC_PASS=\'{nextcloud_password}\' -u www-data nextcloud php occ user:resetpassword admin --password-from-env"',
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set memcache.distributed --value=\'\\OC\\Memcache\\Redis\'"',
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set memcache.locking --value=\'\\OC\\Memcache\\Redis\'"',
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value=\'https\'"',
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec nc-redis redis-cli FLUSHALL"',
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker restart nextcloud"'
]

for i, cmd in enumerate(commands, 1):
    print(f"\n{i}. Executing: {cmd[:60]}...")
    result = os.system(cmd)
    print(f"Result: {result}")

print("\nWaiting 20 seconds...")
import time
time.sleep(20)

# Test login
test_cmd = f'''sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && COOKIE_JAR=\\"/tmp/test_\\$(date +%s).txt\\" && rm -f \\"\\$COOKIE_JAR\\" && LOGIN_PAGE=\\$(curl -s -c \\"\\$COOKIE_JAR\\" \\"https://ncrag.voronkov.club/login\\") && CSRF_TOKEN=\\$(echo \\"\\$LOGIN_PAGE\\" | grep -oP 'data-requesttoken=\\"\\\\K[^\\"]+' | head -1) && echo \\"CSRF: \\${{CSRF_TOKEN:0:20}}...\\" && RESPONSE=\\$(curl -s -b \\"\\$COOKIE_JAR\\" -c \\"\\$COOKIE_JAR\\" -L -d \\"user=admin\\" -d \\"password={nextcloud_password}\\" -d \\"requesttoken=\\$CSRF_TOKEN\\" -w \\"URL:%{{url_effective}}\\\\n\\" \\"https://ncrag.voronkov.club/login\\") && FINAL_URL=\\$(echo \\"\\$RESPONSE\\" | grep \\"URL:\\" | cut -d: -f2-) && echo \\"Final URL: \\$FINAL_URL\\" && if [[ \\"\\$FINAL_URL\\" == *\\"/login\\"* ]]; then echo \\"LOGIN FAILED\\"; else echo \\"LOGIN SUCCESS\\"; fi"'''

print("\nTesting login...")
os.system(test_cmd)

print("\nDone!")
print(f"Test login at: https://ncrag.voronkov.club")
print(f"Username: admin")
print(f"Password: {nextcloud_password}")