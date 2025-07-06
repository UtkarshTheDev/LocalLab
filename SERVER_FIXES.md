# LocalLab Server Fixes

## Problems Fixed

### 1. Qwen2.5-VL Model Loading Error
The server was failing to load Qwen2.5-VL models (like `Qwen/Qwen2.5-VL-3B-Instruct`) with the error:

```
Unrecognized configuration class <class 'transformers.models.qwen2_5_vl.configuration_qwen2_5_vl.Qwen2_5_VLConfig'> for this kind of AutoModel: AutoModelForCausalLM.
```

### 2. Disk Offloading Error
Models were failing to load with the error:

```
You are trying to offload the whole model to the disk. Please use the `disk_offload` function instead.
```

### 3. Repeated Startup Callbacks
The server was repeatedly triggering startup callbacks every 30 seconds, causing log spam:

```
2025-07-03 11:18:58,857 - locallab.server - INFO - Server startup callback triggered
2025-07-03 11:19:28,957 - locallab.server - INFO - Server startup callback triggered
2025-07-03 11:19:59,055 - locallab.server - INFO - Server startup callback triggered
```

### 4. Incorrect Processor Loading
Text-only models (like microsoft/phi-2) were incorrectly attempting to load as processors:

```
2025-07-03 11:17:39,901 - locallab - INFO - Loaded microsoft/phi-2 processor successfully
```

## Root Causes
- **Qwen2.5-VL Issue**: Vision-language models require a specific model class (`Qwen2_5_VLForConditionalGeneration`) instead of the generic `AutoModelForCausalLM`
- **Disk Offloading Issue**: Using `device_map: "auto"` caused Transformers to try offloading entire models to disk when GPU memory was insufficient
- **Startup Loop**: The startup callback wasn't marking itself as complete, causing repeated triggers
- **Processor Logic**: All models were trying to load as processors first, even text-only models

## Solutions Applied

### 1. Smart Device Mapping Strategy
Implemented intelligent device mapping in `locallab/model_manager.py`:
- **GPU Memory Detection**: Checks available GPU memory before deciding device placement
- **Safe Device Mapping**: Uses specific device (`cuda:0` or `cpu`) instead of `device_map: "auto"`
- **CPU Fallback**: Automatically falls back to CPU if GPU memory is insufficient (<4GB)
- **Disk Offloading Prevention**: Avoids configurations that trigger disk offloading

### 2. Enhanced Model Class Detection with Error Recovery
Updated the model loading logic to:
- Added fallback logic to try multiple model classes in order:
  1. `AutoModelForCausalLM` (for regular text models)
  2. `AutoModel` (generic fallback)
  3. `Qwen2_5_VLForConditionalGeneration` (for Qwen2.5-VL models)
  4. `AutoModelForVision2Seq` (for other vision models)
- **CPU Retry Logic**: If disk offloading errors occur, automatically retry with CPU-only configuration
- **Error Detection**: Detects disk offloading errors and triggers appropriate fallback

### 3. Smart Processor/Tokenizer Loading
- Only attempt `AutoProcessor` for vision-language models (detected by "vl", "vision", or "qwen2.5-vl" in model name)
- Fall back to `AutoTokenizer` for all other models
- This ensures both text-only and multimodal models work correctly

### 4. Fixed Startup Callback Loop
- Added `startup_complete[0] = True` flag to prevent repeated startup callbacks
- The callback now marks itself as complete immediately after being triggered

### 5. Updated Dependencies
- Updated `transformers` requirement from `>=4.0.0` to `>=4.49.0` (minimum version for Qwen2.5-VL support)
- Updated both `requirements.txt` and `setup.py`

## Files Modified

### 1. `locallab/model_manager.py`
- **Lines 75-111**: Added `_get_safe_device_map()` method for intelligent device selection
- **Lines 113-187**: Updated `_get_quantization_config()` to use safe device mapping
- **Lines 290-315**: Enhanced processor/tokenizer loading logic for registry models
- **Lines 355-389**: Added CPU fallback logic for AutoModelForCausalLM (registry models)
- **Lines 385-417**: Added CPU fallback logic for Qwen2_5_VLForConditionalGeneration (registry models)
- **Lines 1390-1412**: Enhanced processor/tokenizer loading logic for custom models
- **Lines 1484-1518**: Added CPU fallback logic for AutoModelForCausalLM (custom models)
- **Lines 1493-1525**: Added CPU fallback logic for Qwen2_5_VLForConditionalGeneration (custom models)

### 2. `locallab/server.py`
- **Line 815**: Added `startup_complete[0] = True` to prevent repeated callbacks

### 3. `requirements.txt`
- Updated transformers version requirement to `>=4.49.0`

### 4. `setup.py`
- Updated transformers version requirement to `>=4.49.0`

## Testing Results

### ✅ Dependencies Verified
- Transformers 4.52.4 installed (sufficient for Qwen2.5-VL)
- `Qwen2_5_VLForConditionalGeneration` imports successfully
- `AutoProcessor` imports successfully

### ✅ Device Mapping Fixed
- Smart device detection prevents disk offloading errors
- CPU fallback works when GPU memory is insufficient
- Error detection correctly identifies disk offloading issues
- CPU retry logic successfully loads models when GPU fails

### ✅ Startup Callback Fixed
- Callback now only triggers once instead of repeatedly
- No more 30-second interval spam in logs

### ✅ Model Loading Logic
- Vision-language models use appropriate processor and model classes
- Text-only models use tokenizers (not processors)
- Fallback logic handles various model types gracefully
- CPU-only retry prevents complete loading failures

## Usage

After applying these fixes, you can now:

### Load Qwen2.5-VL Models
```bash
# Start the server
python -m locallab.server

# Use the API to load a Qwen2.5-VL model
curl -X POST "http://localhost:8000/models/load" \
     -H "Content-Type: application/json" \
     -d '{"model_id": "Qwen/Qwen2.5-VL-3B-Instruct"}'
```

### Expected Log Output
```
2025-07-03 11:17:32,864 - locallab - INFO - Loading tokenizer for Qwen/Qwen2.5-VL-3B-Instruct...
2025-07-03 11:17:39,901 - locallab - INFO - Loaded Qwen/Qwen2.5-VL-3B-Instruct processor successfully
2025-07-03 11:18:58,851 - locallab - INFO - Model weights loaded successfully
```

### For Text-Only Models
```
2025-07-03 11:17:32,864 - locallab - INFO - Loading tokenizer for microsoft/phi-2...
2025-07-03 11:17:39,901 - locallab - INFO - Loaded microsoft/phi-2 tokenizer successfully
```

## Backward Compatibility
- ✅ All existing text-only models continue to work
- ✅ No breaking changes to API
- ✅ Maintains all existing functionality
- ✅ Graceful fallback for unsupported model types
