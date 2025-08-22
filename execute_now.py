import subprocess
import os

# Execute bash script directly
subprocess.call(['bash', '/workspace/simple_fix.sh'], env=os.environ)