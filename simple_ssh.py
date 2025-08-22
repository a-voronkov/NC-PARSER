import os
import subprocess

# Get environment variables
ssh_server = os.getenv('SSH_SERVER', 'ncrag.voronkov.club')
ssh_user = os.getenv('SSH_USER', 'alfred361')
ssh_password = os.getenv('SSH_PASSWORD', '')

print(f"Server: {ssh_server}")
print(f"User: {ssh_user}")

# Simple test
cmd = ['sshpass', '-p', ssh_password, 'ssh', '-o', 'StrictHostKeyChecking=no', f'{ssh_user}@{ssh_server}', 'echo "SSH works"; date']
result = subprocess.run(cmd, capture_output=True, text=True)
print("SSH test result:")
print(result.stdout)
if result.stderr:
    print("Error:", result.stderr)

# Check containers
cmd2 = ['sshpass', '-p', ssh_password, 'ssh', '-o', 'StrictHostKeyChecking=no', f'{ssh_user}@{ssh_server}', 'cd /srv/docker/nc-rag && docker ps']
result2 = subprocess.run(cmd2, capture_output=True, text=True)
print("Docker containers:")
print(result2.stdout)

# Test Redis
cmd3 = ['sshpass', '-p', ssh_password, 'ssh', '-o', 'StrictHostKeyChecking=no', f'{ssh_user}@{ssh_server}', 'cd /srv/docker/nc-rag && docker exec nc-redis redis-cli ping']
result3 = subprocess.run(cmd3, capture_output=True, text=True)
print("Redis test:")
print(result3.stdout)

print("Done!")