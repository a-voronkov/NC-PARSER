#!/usr/bin/env python3
import os
import time

# Exact network information from your output
TRAEFIK_BACKEND_IP = "172.19.0.8"
TRAEFIK_WEB_IP = "172.20.0.2"
BACKEND_NETWORK = "172.19.0.0/16"
WEB_NETWORK = "172.20.0.0/16"

print("🎯 EXACT FIX WITH SPECIFIC IP ADDRESSES")
print("=" * 50)
print(f"Traefik Backend IP: {TRAEFIK_BACKEND_IP}")
print(f"Traefik Web IP: {TRAEFIK_WEB_IP}")

# Get credentials
ssh_server = os.environ.get('SSH_SERVER')
ssh_user = os.environ.get('SSH_USER')
ssh_password = os.environ.get('SSH_PASSWORD')
nextcloud_password = os.environ.get('NEXTCLOUD_PASSWORD')

print(f"\nServer: {ssh_server}")
print(f"User: {ssh_user}")
print(f"Password length: {len(nextcloud_password)} chars")

# Commands to execute
commands = [
    # 1. Set exact trusted proxies
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 0 --value=\'{TRAEFIK_BACKEND_IP}\'"',
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 1 --value=\'{TRAEFIK_WEB_IP}\'"',
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 2 --value=\'{BACKEND_NETWORK}\'"',
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set trusted_proxies 3 --value=\'{WEB_NETWORK}\'"',
    
    # 2. Overwrite settings
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set overwritehost --value=\'ncrag.voronkov.club\'"',
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value=\'https\'"',
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set overwrite.cli.url --value=\'https://ncrag.voronkov.club\'"',
    
    # 3. Forwarded headers
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 0 --value=\'HTTP_X_FORWARDED_FOR\'"',
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 1 --value=\'HTTP_X_REAL_IP\'"',
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 2 --value=\'HTTP_X_FORWARDED_HOST\'"',
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set forwarded_for_headers 3 --value=\'HTTP_X_FORWARDED_PROTO\'"',
    
    # 4. Force SSL
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set forcessl --value=true --type=boolean"',
    
    # 5. Clear cache and restart
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec nc-redis redis-cli FLUSHALL"',
    f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker restart nextcloud traefik"'
]

# Execute all commands
for i, cmd in enumerate(commands, 1):
    print(f"\n{i}. Executing...")
    result = os.system(cmd)
    if result == 0:
        print("✅ Success")
    else:
        print(f"❌ Failed (exit code: {result})")

print("\n⏳ Waiting 30 seconds for restart...")
time.sleep(30)

# Reset throttling
print("\n🔓 Resetting throttling...")
reset_cmd = f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ security:bruteforce:reset 171.5.227.98"'
os.system(reset_cmd)

# Test login
print("\n🧪 Testing login...")
test_cmd = f'''sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && COOKIE_JAR=\\"/tmp/exact_test.txt\\" && rm -f \\"\\$COOKIE_JAR\\" && LOGIN_PAGE=\\$(curl -s -c \\"\\$COOKIE_JAR\\" \\"https://ncrag.voronkov.club/login\\") && CSRF_TOKEN=\\$(echo \\"\\$LOGIN_PAGE\\" | grep -oP 'data-requesttoken=\\"\\\\K[^\\"]+' | head -1) && echo \\"CSRF: \\${{CSRF_TOKEN:0:30}}...\\" && RESPONSE=\\$(curl -s -b \\"\\$COOKIE_JAR\\" -c \\"\\$COOKIE_JAR\\" -L -d \\"user=admin\\" -d \\"password={nextcloud_password}\\" -d \\"requesttoken=\\$CSRF_TOKEN\\" -w \\"URL:%{{url_effective}}\\\\n\\" \\"https://ncrag.voronkov.club/login\\") && FINAL_URL=\\$(echo \\"\\$RESPONSE\\" | grep \\"URL:\\" | cut -d: -f2-) && echo \\"Final URL: \\$FINAL_URL\\" && if [[ \\"\\$FINAL_URL\\" == *\\"/login\\"* ]]; then echo \\"❌ STILL REDIRECTING\\"; else echo \\"✅ SUCCESS: \\$FINAL_URL\\"; fi"'''

os.system(test_cmd)

print(f"\n🎯 EXACT FIX COMPLETE!")
print(f"Test at: https://ncrag.voronkov.club")
print(f"Username: admin")
print(f"Password: {nextcloud_password}")

# Auto-execute when imported
if __name__ == "__main__":
    pass