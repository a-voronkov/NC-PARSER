import subprocess
import os

# Auto-execute when imported
ssh_server = os.environ.get('SSH_SERVER', 'ncrag.voronkov.club')
ssh_user = os.environ.get('SSH_USER', 'alfred361')
ssh_password = os.environ.get('SSH_PASSWORD', '')
nextcloud_password = os.environ.get('NEXTCLOUD_PASSWORD', '')

print(f"🔧 AUTO-EXECUTING NEXTCLOUD FIX")
print(f"Server: {ssh_server}")
print(f"User: {ssh_user}")
print(f"Password length: {len(nextcloud_password)}")

# Execute key commands
cmd1 = f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -e OC_PASS=\'{nextcloud_password}\' -u www-data nextcloud php occ user:resetpassword admin --password-from-env"'
print("\n1. Resetting password...")
result1 = os.system(cmd1)
print(f"Result: {result1}")

cmd2 = f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value=\'https\'"'
print("\n2. Setting HTTPS...")
result2 = os.system(cmd2)
print(f"Result: {result2}")

cmd3 = f'sshpass -p "{ssh_password}" ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_server} "cd /srv/docker/nc-rag && docker restart nextcloud"'
print("\n3. Restarting...")
result3 = os.system(cmd3)
print(f"Result: {result3}")

print("\n✅ DONE! Test at https://ncrag.voronkov.club")
print(f"Username: admin")
print(f"Password: {nextcloud_password}")