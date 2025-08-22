#!/usr/bin/env python3
import subprocess
import os
import sys

def run_ssh_command(command):
    """Execute command on remote server"""
    ssh_cmd = [
        'sshpass', '-p', os.environ.get('SSH_PASSWORD', ''),
        'ssh', '-o', 'StrictHostKeyChecking=no',
        f"{os.environ.get('SSH_USER', '')}@{os.environ.get('SSH_SERVER', '')}",
        command
    ]
    
    print(f"Executing: {command}")
    result = subprocess.run(ssh_cmd, capture_output=True, text=True)
    print(f"Exit code: {result.returncode}")
    if result.stdout:
        print(f"Output:\n{result.stdout}")
    if result.stderr:
        print(f"Error:\n{result.stderr}")
    print("-" * 80)
    return result.returncode == 0

# Read the remote fix script
with open('/workspace/remote_fix.sh', 'r') as f:
    script_content = f.read()

# Upload and execute the script
upload_command = f"cat > /tmp/remote_fix.sh << 'EOF'\n{script_content}\nEOF"
run_ssh_command(upload_command)
run_ssh_command("chmod +x /tmp/remote_fix.sh")
run_ssh_command("/tmp/remote_fix.sh")

print("Fix script execution completed!")