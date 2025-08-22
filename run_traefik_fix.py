import os

# Execute the Traefik fix script
print("Executing Traefik configuration fix...")
result = os.system("python3 /workspace/fix_traefik_domains.py")
print(f"Fix completed with exit code: {result}")