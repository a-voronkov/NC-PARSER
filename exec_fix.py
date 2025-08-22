#!/usr/bin/env python3

# Simple execution
exec("""
import os
import time

print("=== EXECUTING NEXTCLOUD FIX ===")

# Get environment variables
server = os.environ.get('SSH_SERVER')
user = os.environ.get('SSH_USER')
password = os.environ.get('SSH_PASSWORD')
nc_password = os.environ.get('NEXTCLOUD_PASSWORD')

print(f"Server: {server}")
print(f"User: {user}")
print(f"Password: {nc_password}")

# Reset password
cmd1 = f'sshpass -p "{password}" ssh -o StrictHostKeyChecking=no {user}@{server} "cd /srv/docker/nc-rag && docker exec -e OC_PASS=\\'{nc_password}\\' -u www-data nextcloud php occ user:resetpassword admin --password-from-env"'
print("Resetting password...")
result1 = os.system(cmd1)
print(f"Result: {result1}")

# Configure Redis
cmd2 = f'sshpass -p "{password}" ssh -o StrictHostKeyChecking=no {user}@{server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set memcache.distributed --value=\\'\\\\\\\\OC\\\\\\\\Memcache\\\\\\\\Redis\\'"'
print("Configuring Redis...")
result2 = os.system(cmd2)
print(f"Result: {result2}")

# Set HTTPS
cmd3 = f'sshpass -p "{password}" ssh -o StrictHostKeyChecking=no {user}@{server} "cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value=\\'https\\'"'
print("Setting HTTPS...")
result3 = os.system(cmd3)
print(f"Result: {result3}")

# Clear cache
cmd4 = f'sshpass -p "{password}" ssh -o StrictHostKeyChecking=no {user}@{server} "cd /srv/docker/nc-rag && docker exec nc-redis redis-cli FLUSHALL"'
print("Clearing cache...")
result4 = os.system(cmd4)
print(f"Result: {result4}")

# Restart Nextcloud
cmd5 = f'sshpass -p "{password}" ssh -o StrictHostKeyChecking=no {user}@{server} "cd /srv/docker/nc-rag && docker restart nextcloud"'
print("Restarting Nextcloud...")
result5 = os.system(cmd5)
print(f"Result: {result5}")

print("Waiting 20 seconds...")
time.sleep(20)

print("=== DONE ===")
print("Test login at: https://ncrag.voronkov.club")
print(f"Username: admin")
print(f"Password: {nc_password}")
""")