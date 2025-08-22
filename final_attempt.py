import os
import time

# Execute fix commands
os.system(f'sshpass -p "{os.environ["SSH_PASSWORD"]}" ssh -o StrictHostKeyChecking=no {os.environ["SSH_USER"]}@{os.environ["SSH_SERVER"]} "cd /srv/docker/nc-rag && docker exec -e OC_PASS=\'{os.environ["NEXTCLOUD_PASSWORD"]}\' -u www-data nextcloud php occ user:resetpassword admin --password-from-env"')

os.system(f'sshpass -p "{os.environ["SSH_PASSWORD"]}" ssh -o StrictHostKeyChecking=no {os.environ["SSH_USER"]}@{os.environ["SSH_SERVER"]} "cd /srv/docker/nc-rag && docker restart nextcloud"')

time.sleep(20)

print("Done! Test at https://ncrag.voronkov.club")
print(f"Username: admin")
print(f"Password: {os.environ['NEXTCLOUD_PASSWORD']}")