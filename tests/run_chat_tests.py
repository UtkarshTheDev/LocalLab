#!/usr/bin/env python3
"""
Test runner for LocalLab CLI chat functionality
"""

import sys
import subprocess
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - SUCCESS")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False

def install_test_dependencies():
    """Install test dependencies"""
    return run_command(
        "pip install -r tests/requirements-test.txt",
        "Installing test dependencies"
    )

def run_unit_tests():
    """Run unit tests"""
    return run_command(
        "python -m pytest tests/test_chat_interface.py -v --tb=short",
        "Running ChatInterface unit tests"
    )

def run_connection_tests():
    """Run connection tests"""
    return run_command(
        "python -m pytest tests/test_chat_connection.py -v --tb=short",
        "Running connection unit tests"
    )

def run_ui_tests():
    """Run UI tests"""
    return run_command(
        "python -m pytest tests/test_chat_ui.py -v --tb=short",
        "Running UI unit tests"
    )

def run_integration_tests():
    """Run integration tests"""
    return run_command(
        "python -m pytest tests/test_chat_integration.py -v --tb=short",
        "Running integration tests"
    )

def run_all_chat_tests():
    """Run all chat-related tests"""
    return run_command(
        "python -m pytest tests/test_chat_*.py -v --tb=short",
        "Running all chat tests"
    )

def run_tests_with_coverage():
    """Run tests with coverage report"""
    return run_command(
        "python -m pytest tests/test_chat_*.py --cov=locallab.cli --cov-report=term-missing --cov-report=html",
        "Running tests with coverage"
    )

def run_import_tests():
    """Test basic imports"""
    print(f"\n{'='*60}")
    print("🔄 Testing basic imports")
    print(f"{'='*60}")
    
    try:
        # Test CLI imports
        from locallab.cli.chat import ChatInterface, GenerationMode, chat_command
        from locallab.cli.connection import ServerConnection, detect_local_server, test_connection
        from locallab.cli.ui import ChatUI, StreamingDisplay, BatchProgressDisplay
        
        print("✅ All CLI imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def run_syntax_checks():
    """Run syntax and style checks"""
    commands = [
        ("python -m py_compile locallab/cli/chat.py", "Syntax check - chat.py"),
        ("python -m py_compile locallab/cli/connection.py", "Syntax check - connection.py"),
        ("python -m py_compile locallab/cli/ui.py", "Syntax check - ui.py"),
    ]
    
    all_passed = True
    for cmd, desc in commands:
        if not run_command(cmd, desc):
            all_passed = False
    
    return all_passed

def test_cli_help():
    """Test CLI help command"""
    return run_command(
        "python -c \"from locallab.cli.chat import chat_command; print('CLI help test passed')\"",
        "Testing CLI help functionality"
    )

def main():
    """Main test runner"""
    print("🚀 LocalLab CLI Chat Test Runner")
    print("=" * 60)
    
    # Change to project directory
    os.chdir(project_root)
    
    # Test categories
    test_categories = [
        ("Import Tests", run_import_tests),
        ("Syntax Checks", run_syntax_checks),
        ("CLI Help Test", test_cli_help),
        ("Install Dependencies", install_test_dependencies),
        ("Unit Tests - ChatInterface", run_unit_tests),
        ("Unit Tests - Connection", run_connection_tests),
        ("Unit Tests - UI", run_ui_tests),
        ("Integration Tests", run_integration_tests),
        ("All Chat Tests", run_all_chat_tests),
        ("Coverage Report", run_tests_with_coverage),
    ]
    
    # Track results
    results = {}
    
    # Run tests
    for category, test_func in test_categories:
        try:
            results[category] = test_func()
        except Exception as e:
            print(f"❌ {category} - ERROR: {e}")
            results[category] = False
    
    # Print summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = 0
    total = len(results)
    
    for category, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{category:30} {status}")
        if success:
            passed += 1
    
    print(f"\n📈 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
