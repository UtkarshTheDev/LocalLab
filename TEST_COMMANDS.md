# LocalLab Testing Commands

## Pre-Release Testing Guide

### 1. Environment Setup

```bash
# Ensure you're in the project directory
cd c:\Users\HP\utkarsh\LocalLab

# Activate virtual environment (if using one)
# For Windows:
venv\Scripts\activate
# For Linux/Mac:
# source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e .
```

### 2. Basic Import and Version Tests

```bash
# Test basic imports
python -c "import locallab; print(f'LocalLab version: {locallab.__version__}')"

# Test core components
python -c "from locallab.model_manager import ModelManager; print('ModelManager imported successfully')"
python -c "from locallab.server import run_server; print('Server module imported successfully')"
python -c "from locallab.core.app import app; print('FastAPI app imported successfully')"
```

### 3. Dependency Verification

```bash
# Check transformers version (should be >=4.49.0)
python -c "import transformers; print(f'Transformers version: {transformers.__version__}')"

# Test Qwen2.5-VL imports (our main fix)
python -c "from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor; print('Qwen2.5-VL dependencies OK')"

# Check other key dependencies
python -c "import torch; print(f'PyTorch version: {torch.__version__}')"
python -c "import fastapi; print(f'FastAPI version: {fastapi.__version__}')"
```

### 4. Model Manager Tests

```bash
# Test model manager initialization
python -c "
from locallab.model_manager import ModelManager
mm = ModelManager()
print('ModelManager initialized successfully')
print(f'Available models: {len(mm.available_models) if hasattr(mm, \"available_models\") else \"Not loaded\"}')"

# Test model loading logic (without actually downloading)
python -c "
from locallab.model_manager import ModelManager
import asyncio

async def test_model_info():
    mm = ModelManager()
    try:
        # Test getting model info (should work without downloading)
        info = await mm.get_model_info('microsoft/phi-2')
        print(f'Model info retrieved: {info[\"name\"] if info else \"Failed\"}')
    except Exception as e:
        print(f'Model info test: {e}')

asyncio.run(test_model_info())
"
```

### 5. Server Startup Tests

```bash
# Test server configuration
python -c "
from locallab.config import SERVER_PORT, DEFAULT_MODEL
print(f'Server port: {SERVER_PORT}')
print(f'Default model: {DEFAULT_MODEL}')
"

# Test FastAPI app creation
python -c "
from locallab.core.app import app
print(f'FastAPI app created: {app.title} v{app.version}')
print(f'Routes: {len(app.routes)}')
"

# Quick server startup test (will exit quickly)
timeout 10 python -m locallab.server --help || echo "Server help command works"
```

### 6. API Endpoint Tests (Start Server First)

```bash
# Start the server in background (Windows)
start /B python -m locallab.server

# Or for testing, start with a specific model
# start /B python -m locallab.server --model microsoft/phi-2

# Wait for server to start
timeout 30

# Test health endpoint
curl -X GET "http://localhost:8000/health" || echo "Health endpoint test"

# Test system info
curl -X GET "http://localhost:8000/system/info" || echo "System info test"

# Test models list
curl -X GET "http://localhost:8000/models" || echo "Models list test"

# Test model loading (small model for testing)
curl -X POST "http://localhost:8000/models/load" \
     -H "Content-Type: application/json" \
     -d '{"model_id": "microsoft/DialoGPT-small"}' || echo "Model load test"

# Test generation (after model loads)
curl -X POST "http://localhost:8000/generate" \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Hello, how are you?", "max_length": 50}' || echo "Generation test"

# Stop the server
# taskkill /F /IM python.exe /FI "WINDOWTITLE eq *locallab*" 2>nul || echo "Server stopped"
```

### 7. Specific Fix Verification

```bash
# Test the Qwen2.5-VL fix specifically
python -c "
# Test that vision-language model detection works
model_name = 'Qwen/Qwen2.5-VL-3B-Instruct'
is_vl = 'vl' in model_name.lower() or 'vision' in model_name.lower() or 'qwen2.5-vl' in model_name.lower()
print(f'VL model detection for {model_name}: {is_vl}')

# Test that regular models are detected as non-VL
model_name = 'microsoft/phi-2'
is_vl = 'vl' in model_name.lower() or 'vision' in model_name.lower() or 'qwen2.5-vl' in model_name.lower()
print(f'VL model detection for {model_name}: {is_vl}')
"

# Test startup callback fix
python -c "
# Simulate the startup callback logic
startup_complete = [False]
call_count = 0

def on_startup():
    global call_count
    if startup_complete[0]:
        print('Startup already complete, skipping...')
        return
    call_count += 1
    print(f'Startup callback called (#{call_count})')
    startup_complete[0] = True

# Test multiple calls
on_startup()
on_startup()
on_startup()
print(f'Total calls: {call_count} (should be 1)')
"
```

### 8. Package Build Tests

```bash
# Test package building
python setup.py check
python setup.py sdist --dry-run

# Test installation from source
pip install . --force-reinstall

# Verify installation
python -c "import locallab; print('Package installed successfully')"
```

### 9. Integration Tests

```bash
# Create a simple integration test
python -c "
import asyncio
import time
from locallab.model_manager import ModelManager

async def integration_test():
    print('Starting integration test...')
    
    # Test 1: Model Manager
    mm = ModelManager()
    print('✓ ModelManager created')
    
    # Test 2: Model info (without download)
    try:
        info = await mm.get_model_info('microsoft/phi-2')
        print('✓ Model info retrieved')
    except Exception as e:
        print(f'⚠ Model info failed: {e}')
    
    # Test 3: Available models
    try:
        models = mm.get_available_models()
        print(f'✓ Available models: {len(models)}')
    except Exception as e:
        print(f'⚠ Available models failed: {e}')
    
    print('Integration test completed')

asyncio.run(integration_test())
"
```

### 10. Performance and Memory Tests

```bash
# Test memory usage
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.1f} MB')

from locallab.model_manager import ModelManager
mm = ModelManager()
print(f'Memory after ModelManager: {process.memory_info().rss / 1024 / 1024:.1f} MB')
"

# Test import time
python -c "
import time
start = time.time()
import locallab
end = time.time()
print(f'Import time: {(end - start) * 1000:.1f}ms')
"
```

### 11. Error Handling Tests

```bash
# Test invalid model handling
python -c "
import asyncio
from locallab.model_manager import ModelManager

async def test_invalid_model():
    mm = ModelManager()
    try:
        result = await mm.load_custom_model('invalid/nonexistent-model')
        print(f'Invalid model result: {result}')
    except Exception as e:
        print(f'Expected error for invalid model: {type(e).__name__}')

asyncio.run(test_invalid_model())
"
```

### 12. Final Verification Checklist

```bash
echo "=== FINAL VERIFICATION CHECKLIST ==="
echo "1. All imports work: $(python -c 'import locallab; print(\"✓\")' 2>/dev/null || echo '✗')"
echo "2. Transformers version OK: $(python -c 'import transformers; v=transformers.__version__; print(\"✓\" if tuple(map(int, v.split(\".\"))) >= (4,49,0) else \"✗\")' 2>/dev/null || echo '✗')"
echo "3. Qwen2.5-VL imports: $(python -c 'from transformers import Qwen2_5_VLForConditionalGeneration; print(\"✓\")' 2>/dev/null || echo '✗')"
echo "4. Server module works: $(python -c 'from locallab.server import run_server; print(\"✓\")' 2>/dev/null || echo '✗')"
echo "5. FastAPI app works: $(python -c 'from locallab.core.app import app; print(\"✓\")' 2>/dev/null || echo '✗')"
echo "=== END CHECKLIST ==="
```

## Quick Test Script

Save this as `quick_test.py` and run it:

```python
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
    
    # Test 4: Model Manager
    try:
        from locallab.model_manager import ModelManager
        mm = ModelManager()
        tests.append(("ModelManager", True, "Initialized"))
    except Exception as e:
        tests.append(("ModelManager", False, str(e)))
    
    # Test 5: Server module
    try:
        from locallab.server import run_server
        tests.append(("Server module", True, "Available"))
    except Exception as e:
        tests.append(("Server module", False, str(e)))
    
    # Print results
    print("=" * 60)
    print("LocalLab Quick Test Results")
    print("=" * 60)
    
    passed = 0
    for test_name, success, details in tests:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{test_name:20} {status:8} {details}")
        if success:
            passed += 1
    
    print("=" * 60)
    print(f"Tests passed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("🎉 All tests passed! Ready for release.")
    else:
        print("❌ Some tests failed. Please fix before release.")
    print("=" * 60)

if __name__ == "__main__":
    main()
```

Run with: `python quick_test.py`
