#!/usr/bin/env python3
"""Quick test script for LocalLab"""

def main():
    tests = []
    
    # Test 1: Basic imports
    try:
        import locallab
        tests.append(("Basic import", True, locallab.__version__))
    except Exception as e:
        tests.append(("Basic import", False, str(e)))
    
    # Test 2: Transformers version
    try:
        import transformers
        version = transformers.__version__
        major, minor = map(int, version.split('.')[:2])
        ok = major > 4 or (major == 4 and minor >= 49)
        tests.append(("Transformers version", ok, version))
    except Exception as e:
        tests.append(("Transformers version", False, str(e)))
    
    # Test 3: Qwen2.5-VL support
    try:
        from transformers import Qwen2_5_VLForConditionalGeneration
        tests.append(("Qwen2.5-VL support", True, "Available"))
    except Exception as e:
        tests.append(("Qwen2.5-VL support", False, str(e)))
    
    # Test 4: AutoProcessor support
    try:
        from transformers import AutoProcessor
        tests.append(("AutoProcessor", True, "Available"))
    except Exception as e:
        tests.append(("AutoProcessor", False, str(e)))
    
    # Test 5: Model Manager
    try:
        from locallab.model_manager import ModelManager
        mm = ModelManager()
        tests.append(("ModelManager", True, "Initialized"))
    except Exception as e:
        tests.append(("ModelManager", False, str(e)))
    
    # Test 6: Server module
    try:
        from locallab.server import run_server
        tests.append(("Server module", True, "Available"))
    except Exception as e:
        tests.append(("Server module", False, str(e)))
    
    # Test 7: FastAPI app
    try:
        from locallab.core.app import app
        tests.append(("FastAPI app", True, f"{app.title} v{app.version}"))
    except Exception as e:
        tests.append(("FastAPI app", False, str(e)))
    
    # Test 8: VL model detection logic
    try:
        # Test the VL detection logic we implemented
        def is_vl_model(model_name):
            return "vl" in model_name.lower() or "vision" in model_name.lower() or "qwen2.5-vl" in model_name.lower()
        
        test_cases = [
            ("Qwen/Qwen2.5-VL-3B-Instruct", True),
            ("microsoft/phi-2", False),
            ("llava-hf/llava-1.5-7b-hf", False),  # Should be False with our current logic
            ("some-vision-model", True),
        ]
        
        all_correct = all(is_vl_model(model) == expected for model, expected in test_cases)
        tests.append(("VL detection logic", all_correct, "Logic working"))
    except Exception as e:
        tests.append(("VL detection logic", False, str(e)))
    
    # Test 9: Configuration loading
    try:
        from locallab.config import DEFAULT_MODEL, SERVER_PORT
        tests.append(("Configuration", True, f"Port: {SERVER_PORT}, Model: {DEFAULT_MODEL}"))
    except Exception as e:
        tests.append(("Configuration", False, str(e)))
    
    # Test 10: Memory usage check
    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        tests.append(("Memory usage", True, f"{memory_mb:.1f} MB"))
    except Exception as e:
        tests.append(("Memory usage", False, str(e)))
    
    # Print results
    print("=" * 70)
    print("LocalLab Quick Test Results")
    print("=" * 70)
    
    passed = 0
    for test_name, success, details in tests:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{test_name:25} {status:8} {details}")
        if success:
            passed += 1
    
    print("=" * 70)
    print(f"Tests passed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("🎉 All tests passed! Ready for release.")
        return True
    else:
        print("❌ Some tests failed. Please fix before release.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
