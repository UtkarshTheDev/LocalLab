#!/usr/bin/env python3
"""
Migration script to transition from monolithic to modular structure.
This script will backup the old main.py and logger.py files before removal.
"""

import os
import shutil
import datetime
import sys

# Get current date for backup filename
today = datetime.datetime.now().strftime("%Y%m%d")

# Create backup directory if it doesn't exist
backup_dir = "backups"
if not os.path.exists(backup_dir):
    os.makedirs(backup_dir)

# Files to backup
files_to_backup = [
    ("locallab/main.py", f"{backup_dir}/main_{today}.py.bak"),
    ("locallab/logger.py", f"{backup_dir}/logger_{today}.py.bak")
]

# Perform backups
backed_up = []
for src_path, backup_path in files_to_backup:
    if os.path.exists(src_path):
        print(f"Backing up {src_path} to {backup_path}...")
        shutil.copy2(src_path, backup_path)
        backed_up.append(src_path)
        print(f"Backup created successfully.")

if backed_up:
    print(f"\nMIGRATION COMPLETE: The following files have been backed up:")
    for path in backed_up:
        print(f"- {path}")
    print(f"\nYou can now safely remove them with: git rm {' '.join(backed_up)}")
    print(f"\nTo test the new modular structure, run: python3 -c 'from locallab import start_server; print(\"Successfully imported start_server\")'")
else:
    print("No files needed backup. The migration may have already been completed.")

# Add a warning if main.py still exists but logger.py has been removed
if os.path.exists("locallab/main.py") and not os.path.exists("locallab/logger.py"):
    print("\nWARNING: main.py still exists but logger.py has been removed.")
    print("Make sure to update any imports in main.py to use the new logger module.")

print("\nNOTE: Be sure to install all required dependencies (torch, fastapi, uvicorn, etc.)")
print("      before running the server with the new structure.\n")

# Check if the new structure is properly set up
required_dirs = ["locallab/core", "locallab/routes", "locallab/ui", "locallab/utils", "locallab/logger"]
missing_dirs = [d for d in required_dirs if not os.path.exists(d)]

if missing_dirs:
    print(f"\nWARNING: The following required directories are missing:")
    for d in missing_dirs:
        print(f"- {d}")
    print("\nPlease make sure to create these directories and their required files.")
    sys.exit(1)
else:
    print("\nNew directory structure is properly set up.")
    print("Migration successful! ✅") 