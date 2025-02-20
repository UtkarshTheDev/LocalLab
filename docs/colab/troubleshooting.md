# LocalLab Troubleshooting Guide for Google Colab

A comprehensive guide to troubleshooting common issues when using LocalLab in Google Colab.

## 📚 Table of Contents

1. [Memory Issues](#memory-issues)
2. [Runtime Issues](#runtime-issues)
3. [Model Loading Issues](#model-loading-issues)
4. [Performance Issues](#performance-issues)
5. [Connection Issues](#connection-issues)
6. [Common Error Messages](#common-error-messages)

## Memory Issues

### Out of Memory (OOM) Errors

1. **Symptoms**

   - CUDA out of memory error
   - Runtime crash
   - Model loading failure

2. **Solutions**

```python
class MemoryTroubleshooter:
    @staticmethod
    async def handle_oom():
        # 1. Clear memory
        torch.cuda.empty_cache()
        gc.collect()

        # 2. Check available memory
        memory_info = torch.cuda.mem_get_info()
        available_memory = memory_info[0] / 1024**3  # GB

        # 3. Choose appropriate model
        if available_memory < 4:
            model = "qwen-0.5b"
        elif available_memory < 8:
            model = "phi-2"
        else:
            model = "mistral-7b"

        # 4. Load with optimizations
        await client.load_model(
            model,
            quantization="int8",
            device_map="auto"
        )

# Usage
troubleshooter = MemoryTroubleshooter()
await troubleshooter.handle_oom()
```

3. **Prevention**

```python
class MemoryMonitor:
    def __init__(self, threshold_gb: float = 0.5):
        self.threshold = threshold_gb * 1024**3

    def check_memory(self):
        memory_info = torch.cuda.mem_get_info()
        if memory_info[0] < self.threshold:
            self.cleanup()

    def cleanup(self):
        torch.cuda.empty_cache()
        gc.collect()

# Usage
monitor = MemoryMonitor(threshold_gb=1.0)
monitor.check_memory()
```

## Runtime Issues

### Runtime Disconnections

1. **Auto-Reconnect Solution**

```python
from IPython.display import Javascript

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

# Usage
setup_auto_reconnect()
```

2. **State Recovery**

```python
class StateManager:
    def __init__(self):
        self.state = {}

    def save_state(self, key: str, value: Any):
        self.state[key] = value

    def load_state(self, key: str) -> Any:
        return self.state.get(key)

    async def recover_state(self, client: LocalLabClient):
        if model := self.state.get("model"):
            await client.load_model(model)

# Usage
state_manager = StateManager()
state_manager.save_state("model", "qwen-0.5b")
```

### Runtime Crashes

1. **Crash Handler**

```python
class CrashHandler:
    @staticmethod
    async def recover():
        # 1. Reset CUDA
        torch.cuda.empty_cache()
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

        # 2. Reset Python state
        gc.collect()

        # 3. Reinitialize client
        client = LocalLabClient("http://localhost:8000")

        return client

# Usage
new_client = await CrashHandler.recover()
```

## Model Loading Issues

### Failed Model Loading

1. **Model Loading Troubleshooter**

```python
class ModelLoadingTroubleshooter:
    def __init__(self, client: LocalLabClient):
        self.client = client

    async def troubleshoot_loading(
        self,
        model_name: str,
        max_retries: int = 3
    ):
        for attempt in range(max_retries):
            try:
                # Try loading with different optimizations
                if attempt == 0:
                    # Try normal loading
                    await self.client.load_model(model_name)
                elif attempt == 1:
                    # Try with quantization
                    await self.client.load_model(
                        model_name,
                        quantization="int8"
                    )
                else:
                    # Try with minimal settings
                    await self.client.load_model(
                        model_name,
                        quantization="int8",
                        device_map="auto",
                        optimize_memory=True
                    )
                return True
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(1)

        # If all attempts fail, try fallback model
        try:
            await self.client.load_model("qwen-0.5b")
            return True
        except:
            return False

# Usage
troubleshooter = ModelLoadingTroubleshooter(client)
success = await troubleshooter.troubleshoot_loading("mistral-7b")
```

## Performance Issues

### Slow Generation

1. **Performance Analyzer**

```python
class PerformanceAnalyzer:
    def __init__(self):
        self.metrics = []

    async def analyze_performance(
        self,
        client: LocalLabClient,
        prompt: str
    ):
        start_time = time.time()
        memory_start = torch.cuda.memory_allocated()

        try:
            response = await client.generate(prompt)

            duration = time.time() - start_time
            memory_used = torch.cuda.memory_allocated() - memory_start

            self.metrics.append({
                "duration": duration,
                "memory_used": memory_used,
                "tokens": len(response.split())
            })

            return self.get_recommendations()
        except Exception as e:
            return f"Error during analysis: {e}"

    def get_recommendations(self):
        if not self.metrics:
            return "No metrics available"

        avg_duration = sum(m["duration"] for m in self.metrics) / len(self.metrics)
        avg_memory = sum(m["memory_used"] for m in self.metrics) / len(self.metrics)

        recommendations = []

        if avg_duration > 2.0:  # More than 2 seconds per generation
            recommendations.append("Consider using a smaller model or enabling optimizations")

        if avg_memory > 4e9:  # More than 4GB memory usage
            recommendations.append("High memory usage detected. Consider enabling memory optimizations")

        return recommendations

# Usage
analyzer = PerformanceAnalyzer()
recommendations = await analyzer.analyze_performance(client, "Test prompt")
```

## Connection Issues

### Connection Troubleshooter

```python
class ConnectionTroubleshooter:
    def __init__(self, client: LocalLabClient):
        self.client = client

    async def check_connection(self):
        try:
            # 1. Check basic connectivity
            await self.client.health_check()

            # 2. Check model loading
            await self.client.load_model("qwen-0.5b")

            # 3. Check generation
            response = await self.client.generate("Test")

            return "All systems operational"
        except Exception as e:
            return self.diagnose_error(e)

    def diagnose_error(self, error: Exception):
        error_str = str(error).lower()

        if "connection refused" in error_str:
            return "Server not running or wrong address"
        elif "timeout" in error_str:
            return "Connection timeout - check network"
        elif "authentication" in error_str:
            return "Authentication failed - check API key"
        else:
            return f"Unknown error: {error}"

# Usage
troubleshooter = ConnectionTroubleshooter(client)
diagnosis = await troubleshooter.check_connection()
```

## Common Error Messages

### Error Handler

```python
class ErrorHandler:
    @staticmethod
    def handle_error(error: Exception):
        error_str = str(error).lower()

        # Memory errors
        if "out of memory" in error_str:
            return {
                "type": "memory",
                "solution": "Clear cache and reduce model size",
                "action": lambda: torch.cuda.empty_cache()
            }

        # CUDA errors
        elif "cuda" in error_str:
            return {
                "type": "cuda",
                "solution": "Reset CUDA and restart runtime",
                "action": lambda: torch.cuda.reset_peak_memory_stats()
            }

        # Model errors
        elif "model" in error_str:
            return {
                "type": "model",
                "solution": "Try loading a different model",
                "action": lambda: client.load_model("qwen-0.5b")
            }

        # Connection errors
        elif "connection" in error_str:
            return {
                "type": "connection",
                "solution": "Check network and restart runtime",
                "action": lambda: None
            }

        # Unknown errors
        else:
            return {
                "type": "unknown",
                "solution": f"Unknown error: {error}",
                "action": lambda: None
            }

# Usage
try:
    await client.generate("prompt")
except Exception as e:
    handler = ErrorHandler()
    solution = handler.handle_error(e)
    print(f"Error type: {solution['type']}")
    print(f"Solution: {solution['solution']}")
    solution['action']()
```

## Additional Resources

- [FAQ Guide](./faq.md)
- [Performance Guide](./performance.md)
- [Advanced Features](./advanced.md)
- [Examples](./examples.md)
