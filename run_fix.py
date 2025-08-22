import subprocess
import os

subprocess.run([
    'python3', '/workspace/direct_fix.py'
], env=os.environ)