import os
import subprocess
import sys

# Execute the bash script
result = subprocess.run(['bash', '/workspace/final_fix.sh'], env=os.environ, capture_output=True, text=True)

print("STDOUT:")
print(result.stdout)

if result.stderr:
    print("\nSTDERR:")
    print(result.stderr)

print(f"\nExit code: {result.returncode}")

if result.returncode == 0:
    print("\n✅ Script executed successfully!")
else:
    print("\n❌ Script failed!")

sys.exit(result.returncode)