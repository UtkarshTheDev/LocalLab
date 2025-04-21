"""
Test script to verify imports.
"""

import os
import sys

# Print current directory and sys.path
print(f"Current directory: {os.getcwd()}")
print(f"sys.path: {sys.path}")

# Add the parent directory to the path
parent_dir = os.path.abspath(os.path.dirname(__file__))
print(f"Parent directory: {parent_dir}")
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    print(f"Added parent directory to sys.path")

# Try to import the client
try:
    print("\nTrying to import client.py...")
    import client
    print("Successfully imported client.py")
    print(f"client.__file__: {client.__file__}")
except ImportError as e:
    print(f"Failed to import client.py: {e}")

# Try to import the sync_wrapper
try:
    print("\nTrying to import sync_wrapper.py...")
    import sync_wrapper
    print("Successfully imported sync_wrapper.py")
    print(f"sync_wrapper.__file__: {sync_wrapper.__file__}")
except ImportError as e:
    print(f"Failed to import sync_wrapper.py: {e}")

# List files in the current directory
print("\nFiles in the current directory:")
for file in os.listdir(parent_dir):
    print(f"- {file}")
