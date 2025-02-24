# Google Colab Troubleshooting

## Common Issues

### Ngrok Connection Issues

**Issue:** Ngrok authentication error
```
ERROR: Failed to create ngrok tunnel: authentication failed
```
**Solution:**
1. Get a valid ngrok auth token from [ngrok dashboard](https://dashboard.ngrok.com)
2. Set the token correctly:
```python
import os
os.environ["NGROK_AUTH_TOKEN"] = "your_token_here"
```

### Memory Issues

**Issue:** Out of Memory (OOM) errors
```
RuntimeError: CUDA out of memory
```
**Solution:**
1. Enable memory optimizations:
```python
os.environ["LOCALLAB_ENABLE_QUANTIZATION"] = "true"
os.environ["LOCALLAB_QUANTIZATION_TYPE"] = "int8"
```
2. Use a smaller model:
```python
os.environ["HUGGINGFACE_MODEL"] = "microsoft/phi-2"  # Smaller model
```

### Connection Issues

**Issue:** Cannot connect to server
```
ConnectionError: Failed to connect to server
```
**Solution:**
1. Ensure you're using the correct URL:
   - For local connections within Colab: `http://localhost:8000`
   - For external connections: Use the ngrok URL shown in server logs
2. Check if server is running
3. Verify no firewall blocking

### Runtime Issues

**Issue:** Runtime disconnected
**Solution:**
1. Keep Colab tab active
2. Use "Connect to hosted runtime"
3. Restart kernel if needed

## Best Practices

1. **Memory Management**
   - Monitor memory usage
   - Use appropriate model size
   - Enable optimizations

2. **Connection Management**
   - Save ngrok URL
   - Handle reconnections
   - Check server status

3. **Error Recovery**
   ```python
   try:
       response = await client.generate("prompt")
   except Exception as e:
       if "out of memory" in str(e):
           # Switch to smaller model
           os.environ["HUGGINGFACE_MODEL"] = "microsoft/phi-2"
           await client.reload_model()
   ```

## Related Resources

- [Colab Guide](./README.md)
- [Performance Tips](../features/performance.md)
- [Model Management](../features/models.md)
