#!/usr/bin/env python3
"""
Test script to verify the LocalLab structure and logger module.
This script performs basic import checks to ensure the refactored 
code structure works correctly.
"""

import os
import sys
import importlib.util
from colorama import Fore, Style, init
init(autoreset=True)

# Test results
passed = []
failed = []
skipped = []

# Check if torch is available
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print(f"{Fore.YELLOW}Warning: PyTorch is not installed. Skipping torch-dependent tests.{Style.RESET_ALL}")

def print_header(text):
    """Print a formatted header"""
    print(f"\n{Fore.CYAN}======== {text} ========{Style.RESET_ALL}")

def test_import(module_name, component=None, requires_torch=False):
    """Test importing a module and optionally a specific component"""
    # Skip torch-dependent tests if torch is not available
    if requires_torch and not TORCH_AVAILABLE:
        test_name = f"{module_name}{f'.{component}' if component else ''}"
        print(f"{Fore.YELLOW}⚠ Skipped import of {test_name} (requires torch){Style.RESET_ALL}")
        skipped.append(test_name)
        return True
        
    try:
        if component:
            # Import specific component from module
            exec(f"from {module_name} import {component}")
            print(f"{Fore.GREEN}✓ Successfully imported {component} from {module_name}{Style.RESET_ALL}")
            passed.append(f"{module_name}.{component}")
        else:
            # Import entire module
            exec(f"import {module_name}")
            print(f"{Fore.GREEN}✓ Successfully imported {module_name}{Style.RESET_ALL}")
            passed.append(module_name)
        return True
    except Exception as e:
        print(f"{Fore.RED}✗ Failed to import {module_name}{' - ' + component if component else ''}: {str(e)}{Style.RESET_ALL}")
        failed.append(module_name + (f".{component}" if component else ""))
        return False

def main():
    """Run the tests"""
    print_header("LocalLab Structure Test")
    print(f"Python version: {sys.version}")
    print(f"PyTorch available: {TORCH_AVAILABLE}")
    
    # Ensure we're in the project root
    if not os.path.exists("locallab"):
        print(f"{Fore.RED}Error: This script must be run from the project root directory{Style.RESET_ALL}")
        sys.exit(1)
    
    # Test core package imports
    print_header("Testing Core Imports")
    test_import("locallab", requires_torch=True)
    test_import("locallab", "__version__", requires_torch=True)
    test_import("locallab", "start_server", requires_torch=True)
    
    # Test logger module
    print_header("Testing Logger Module")
    test_import("locallab.logger", requires_torch=False)
    test_import("locallab.logger", "get_logger", requires_torch=False)
    test_import("locallab.logger.logger", requires_torch=False)
    test_import("locallab.logger.logger", "log_request", requires_torch=False)
    test_import("locallab.logger.logger", "set_server_status", requires_torch=False)
    
    # Test core components
    print_header("Testing Core Components")
    test_import("locallab.core.app", requires_torch=True)
    test_import("locallab.model_manager", requires_torch=True)
    test_import("locallab.server", requires_torch=True)
    
    # Test UI components
    print_header("Testing UI Components")
    test_import("locallab.ui.banners", requires_torch=False)
    test_import("locallab.ui.banners", "print_initializing_banner", requires_torch=False)
    test_import("locallab.ui.banners", "print_running_banner", requires_torch=False)
    
    # Test routes
    print_header("Testing Routes")
    test_import("locallab.routes.models", requires_torch=True)
    test_import("locallab.routes.generate", requires_torch=True)
    test_import("locallab.routes.system", requires_torch=True)
    
    # Test utils
    print_header("Testing Utils")
    test_import("locallab.utils.networking", requires_torch=False)
    test_import("locallab.utils.networking", "is_port_in_use", requires_torch=False)
    
    # Summary
    print_header("Test Summary")
    print(f"Passed: {len(passed)} tests")
    print(f"Failed: {len(failed)} tests")
    print(f"Skipped: {len(skipped)} tests (torch dependency)")
    
    if failed:
        print("\nFailed imports:")
        for f in failed:
            print(f"  - {f}")
            
    if skipped:
        print("\nSkipped imports (torch dependency):")
        for s in skipped:
            print(f"  - {s}")
        
    if not failed:
        print(f"\n{Fore.GREEN}All non-skipped tests passed!{Style.RESET_ALL}")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main()) 