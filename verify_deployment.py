import os
import sys

def check_file(path):
    exists = os.path.exists(path)
    print(f"[{'OK' if exists else 'MISSING'}] {path}")
    if not exists:
        return False
    try:
        # Check permissions (basic check)
        if not os.access(path, os.R_OK):
            print(f"  [WARNING] File exists but is not readable!")
    except Exception as e:
        print(f"  [ERROR] checking permissions for {path}: {e}")
    return True

def check_import(module_name):
    try:
        __import__(module_name)
        print(f"[OK] Import {module_name}")
        return True
    except ImportError as e:
        print(f"[FAIL] Import {module_name}: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] Import {module_name} (unexpected error): {e}")
        return False

print("--- Deployment Verification ---")
print(f"CWD: {os.getcwd()}")
print(f"Python path: {sys.path}")

critical_files = [
    "main.py",
    "services/__init__.py",
    "services/garden_service.py",
    "database.py",
    "settings.py"
]

all_files_ok = True
for f in critical_files:
    if not check_file(f):
        all_files_ok = False

if all_files_ok:
    print("\n--- Testing Imports ---")
    if check_import("services.garden_service"):
        print("\nDeployment looks good! Try restarting the bot service.")
    else:
        print("\nImport failed despite file existing. Check python path or __init__.py.")
else:
    print("\nMissing files! Please ensure you have pulled the latest changes (git pull).")
