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

def print_header(text):
    """Print a formatted header"""
    print(f"\n{Fore.CYAN}======== {text} ========{Style.RESET_ALL}")

def test_import(module_name, component=None):
    """Test importing a module and optionally a specific component"""
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
    
    # Ensure we're in the project root
    if not os.path.exists("locallab"):
        print(f"{Fore.RED}Error: This script must be run from the project root directory{Style.RESET_ALL}")
        sys.exit(1)
    
    # Test core package imports
    print_header("Testing Core Imports")
    test_import("locallab")
    test_import("locallab", "__version__")
    test_import("locallab", "start_server")
    
    # Test logger module
    print_header("Testing Logger Module")
    test_import("locallab.logger")
    test_import("locallab.logger", "get_logger")
    test_import("locallab.logger.logger")
    test_import("locallab.logger.logger", "log_request")
    test_import("locallab.logger.logger", "set_server_status")
    
    # Test core components
    print_header("Testing Core Components")
    test_import("locallab.core.app")
    test_import("locallab.model_manager")
    test_import("locallab.server")
    
    # Test UI components
    print_header("Testing UI Components")
    test_import("locallab.ui.banners")
    test_import("locallab.ui.banners", "print_initializing_banner")
    test_import("locallab.ui.banners", "print_running_banner")
    
    # Test routes
    print_header("Testing Routes")
    test_import("locallab.routes.models")
    test_import("locallab.routes.generate")
    test_import("locallab.routes.system")
    
    # Test utils
    print_header("Testing Utils")
    test_import("locallab.utils.networking")
    test_import("locallab.utils.networking", "is_port_in_use")
    
    # Summary
    print_header("Test Summary")
    print(f"Passed: {len(passed)} tests")
    print(f"Failed: {len(failed)} tests")
    
    if failed:
        print("\nFailed imports:")
        for f in failed:
            print(f"  - {f}")
        return 1
    else:
        print(f"\n{Fore.GREEN}All tests passed!{Style.RESET_ALL}")
        return 0

if __name__ == "__main__":
    sys.exit(main()) 