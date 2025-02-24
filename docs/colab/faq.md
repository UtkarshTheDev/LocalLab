# LocalLab FAQ for Google Colab

Frequently asked questions about using LocalLab in Google Colab environments.

## 📚 Table of Contents

1. [General Questions](#general-questions)
2. [Setup & Installation](#setup--installation)
3. [Model Management](#model-management)
4. [Performance](#performance)
5. [Troubleshooting](#troubleshooting)

## General Questions

### Q: What is LocalLab and why use it in Google Colab?

LocalLab is a framework for running large language models locally. Using it in Google Colab provides:

- Free access to GPU resources
- Easy setup and installation
- Collaborative environment
- Integration with popular ML tools

### Q: What models are supported in Colab?

The following models are supported based on runtime:

- Free Tier:
  - Models up to 7B parameters
  - Recommended: qwen-0.5b, phi-2
- Pro Tier:
  - Models up to 13B parameters
  - All supported models

### Q: How long can I run LocalLab in Colab?

- Free Tier: Up to 12 hours per session
- Pro Tier: Up to 24 hours per session
- Use `keep_alive` function to maintain connection:
  ```python
  from IPython.display import Javascript
  display(Javascript('''
      function ClickConnect(){
          console.log("Maintaining connection...");
          document.querySelector("colab-connect-button").click()
      }
      setInterval(ClickConnect, 60000)
  '''))
  ```

## Setup & Installation

### Q: How do I install LocalLab in Colab?

```python
# Install LocalLab
!pip install locallab

# Import and initialize
from locallab import LocalLabClient
client = LocalLabClient("http://localhost:8000")
```

### Q: How do I check GPU availability?

```python
import torch
print(f"GPU Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU Model: {torch.cuda.get_device_name(0)}")
```

### Q: How do I select the right runtime?

1. Click "Runtime" in the menu
2. Select "Change runtime type"
3. Choose:
   - "GPU" for model inference
   - "High-RAM" for large models
   - "TPU" for specific optimizations

## Model Management

### Q: How do I load models efficiently?

```python
# Best practice for model loading
async def load_model_efficiently():
    try:
        # Check available memory
        import psutil
        available_memory = psutil.virtual_memory().available / (1024 ** 3)  # GB

        if available_memory > 14:
            model = "mistral-7b"
        elif available_memory > 6:
            model = "phi-2"
        else:
            model = "qwen-0.5b"

        await client.load_model(
            model,
            quantization="int8",
            device_map="auto"
        )
    except Exception as e:
        print(f"Error loading model: {e}")
```

### Q: How do I manage multiple models?

```python
# Model switching utility
class ModelSwitcher:
    def __init__(self, client):
        self.client = client
        self.current_model = None

    async def switch_model(self, model_name: str):
        if self.current_model != model_name:
            await self.client.unload_model()
            await self.client.load_model(model_name)
            self.current_model = model_name

# Usage
switcher = ModelSwitcher(client)
await switcher.switch_model("qwen-0.5b")
```

### Q: How do I handle model quantization?

```python
# Quantization helper
async def load_quantized_model(
    model_name: str,
    quantization: str = "int8"
):
    try:
        await client.load_model(
            model_name,
            quantization=quantization,
            device_map="auto"
        )
    except Exception as e:
        print(f"Quantization failed: {e}")
        # Try without quantization
        await client.load_model(model_name)
```

## Performance

### Q: How do I optimize memory usage?

```python
# Memory optimization utility
class MemoryOptimizer:
    @staticmethod
    def optimize():
        # Clear PyTorch cache
        torch.cuda.empty_cache()

        # Clear Python garbage
        import gc
        gc.collect()

        # Clear IPython output
        from IPython.display import clear_output
        clear_output()

# Usage
MemoryOptimizer.optimize()
```

### Q: How do I monitor resource usage?

```python
# Resource monitor
def monitor_resources():
    while True:
        # CPU Usage
        cpu_percent = psutil.cpu_percent()

        # Memory Usage
        memory = psutil.virtual_memory()

        # GPU Memory
        if torch.cuda.is_available():
            gpu_memory = torch.cuda.memory_allocated() / 1e9

        print(f"CPU: {cpu_percent}%")
        print(f"RAM: {memory.percent}%")
        print(f"GPU Memory: {gpu_memory:.2f}GB")

        time.sleep(5)
```

### Q: How do I handle batch processing efficiently?

```python
# Efficient batch processing
async def process_batch_efficiently(
    prompts: List[str],
    batch_size: int = 4
):
    results = []
    for i in range(0, len(prompts), batch_size):
        batch = prompts[i:i + batch_size]
        responses = await client.batch_generate(batch)
        results.extend(responses)
        # Allow system to stabilize
        await asyncio.sleep(0.1)
    return results
```

## Troubleshooting

### Q: How do I handle common errors?

1. **Out of Memory Error**

   ```python
   try:
       await client.generate("prompt")
   except Exception as e:
       if "out of memory" in str(e).lower():
           MemoryOptimizer.optimize()
           # Try with smaller model
           await client.load_model("qwen-0.5b")
   ```

2. **Runtime Disconnection**

   ```python
   # Auto-reconnect utility
   def setup_auto_reconnect():
       display(Javascript('''
           function checkConnection(){
               if (!google.colab.kernel.accessAllowed){
                   console.log("Reconnecting...");
                   document.querySelector("colab-connect-button").click()
               }
           }
           setInterval(checkConnection, 30000)
       '''))
   ```

3. **Model Loading Failures**
   ```python
   async def safe_model_load():
       try:
           await client.load_model("mistral-7b")
       except Exception as e:
           print(f"Failed to load model: {e}")
           # Try fallback model
           await client.load_model("qwen-0.5b")
   ```

### Q: How do I debug performance issues?

```python
# Performance debugger
class PerformanceDebugger:
    def __init__(self):
        self.metrics = []

    async def profile_generation(self, prompt: str):
        start_time = time.time()
        memory_start = torch.cuda.memory_allocated()

        try:
            response = await client.generate(prompt)

            self.metrics.append({
                "duration": time.time() - start_time,
                "memory_used": torch.cuda.memory_allocated() - memory_start,
                "success": True
            })

            return response
        except Exception as e:
            self.metrics.append({
                "duration": time.time() - start_time,
                "memory_used": torch.cuda.memory_allocated() - memory_start,
                "success": False,
                "error": str(e)
            })
            raise

# Usage
debugger = PerformanceDebugger()
response = await debugger.profile_generation("Hello")
```

### Q: How do I report issues?

1. Gather system information:

   ```python
   def get_system_info():
       return {
           "colab_runtime": os.getenv("COLAB_GPU"),
           "python_version": sys.version,
           "torch_version": torch.__version__,
           "gpu_available": torch.cuda.is_available(),
           "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
           "memory_total": psutil.virtual_memory().total / (1024 ** 3)
       }
   ```

2. Create minimal reproduction:

   ```python
   async def create_reproduction():
       info = get_system_info()

       try:
           await client.load_model("qwen-0.5b")
           response = await client.generate("Test prompt")

           return {
               "system_info": info,
               "reproduction_steps": [
                   "1. Load model",
                   "2. Generate text"
               ],
               "result": response
           }
       except Exception as e:
           return {
               "system_info": info,
               "error": str(e),
               "traceback": traceback.format_exc()
           }
   ```

## Additional Resources

- [Performance Guide](../features/performance.md)
- [Troubleshooting Guide](./troubleshooting.md)
- [Examples](./examples.md)
