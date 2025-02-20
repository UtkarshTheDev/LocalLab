# Troubleshooting Guide

This document provides solutions to common issues encountered while running LocalLab.

> **Note**: For Colab-specific issues, see [Colab Troubleshooting](./colab/troubleshooting.md)

## Model Loading and Inference

**Issue:** Insufficient VRAM  
- Make sure your machine meets the minimum VRAM requirements for the selected model.
- Consider switching to a model with a lower VRAM footprint if necessary.

**Issue:** Errors during model download or loading  
- Verify internet connectivity.
- Check that the model name in the registry is correct.
- Ensure sufficient system memory is available.

## API and System Health

**Issue:** Slow or unresponsive API  
- Use the /system_health endpoint to review resource utilization.
- Monitor GPU and CPU loads to identify potential bottlenecks.

## ngrok and Public URL Issues

**Issue:** Public URL not generated or accessible  
- Confirm that ngrok is correctly installed and that the authentication token is valid.
- Check console logs for any errors related to the ngrok connection.

## General Debugging Guidelines

- Enable and review detailed logging to capture error details.
- Refer to CONTRIBUTING.md for troubleshooting steps and best practices.
- Reach out to the community for further assistance if issues persist.

## Related Troubleshooting Resources
- [Colab Troubleshooting](./colab/troubleshooting.md)
- [FAQ](./colab/faq.md)
- [Performance Guide](./features/performance.md)
- [Deployment Guide](./DEPLOYMENT.md)
