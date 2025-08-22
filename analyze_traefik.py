#!/usr/bin/env python3
import subprocess
import os
import json

def ssh_command(cmd):
    """Execute SSH command"""
    ssh_cmd = [
        'sshpass', '-p', os.environ['SSH_PASSWORD'],
        'ssh', '-o', 'StrictHostKeyChecking=no',
        f"{os.environ['SSH_USER']}@{os.environ['SSH_SERVER']}",
        cmd
    ]
    result = subprocess.run(ssh_cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

print("🔍 ANALYZING TRAEFIK CONFIGURATION")
print("=" * 50)

# 1. Check Traefik labels for Nextcloud
print("1. Nextcloud Traefik labels:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && grep -A 10 'traefik.http.routers.nextcloud' docker-compose.yml")
print(out)

# 2. Check .env file for domain settings
print("\n2. Domain configuration in .env:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && grep NEXTCLOUD_DOMAIN .env")
print(out)

# 3. Check Nextcloud trusted domains
print("\n3. Nextcloud trusted domains:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:get trusted_domains")
print(out)

# 4. Check overwrite settings
print("\n4. Nextcloud overwrite settings:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:get overwrite.cli.url")
print("CLI URL:", out.strip())

code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:get overwritehost")
print("Overwrite host:", out.strip())

code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:get overwriteprotocol")
print("Overwrite protocol:", out.strip())

# 5. Check if there are proxy settings
print("\n5. Proxy settings:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec -u www-data nextcloud php occ config:system:get trusted_proxies")
print("Trusted proxies:", out.strip())

# 6. Check Traefik network configuration
print("\n6. Docker networks:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker network ls | grep nc-rag")
print(out)

# 7. Check if containers are on correct network
print("\n7. Nextcloud network connections:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker inspect nextcloud | grep -A 5 -B 5 NetworkMode")
print(out)

# 8. Check Traefik routing rules
print("\n8. Current Traefik configuration:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && docker exec traefik cat /etc/traefik/traefik.yml 2>/dev/null || echo 'No static config'")
print(out)

# 9. Test domain resolution
print("\n9. Domain resolution test:")
code, out, err = ssh_command("nslookup ncrag.voronkov.club")
print(out)

# 10. Check for conflicting routes
print("\n10. All Traefik labels in docker-compose:")
code, out, err = ssh_command("cd /srv/docker/nc-rag && grep -n 'traefik\\.' docker-compose.yml")
print(out)

print("\n" + "=" * 50)
print("🔍 ANALYSIS COMPLETE")

# Recommendations based on common issues
print("\n📋 POTENTIAL ISSUES TO CHECK:")
print("1. Verify NEXTCLOUD_DOMAIN matches the actual domain")
print("2. Check if overwritehost is set correctly")
print("3. Ensure trusted_domains includes the correct domain")
print("4. Verify Traefik routing rules don't conflict")
print("5. Check if there are multiple routes for the same domain")