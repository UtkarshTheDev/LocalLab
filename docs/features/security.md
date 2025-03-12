# LocalLab Security and Rate Limiting

This document describes the security features and how to configure rate limiting and request validation for LocalLab.

## Table of Contents

1. [Request Validation](#request-validation)
2. [Rate Limiting](#rate-limiting)
3. [Additional Security Settings](#additional-security-settings)

## Request Validation

LocalLab includes basic request validation to ensure that incoming requests follow the schema expected by each endpoint. By default, this is enabled.

```bash
export LOCALLAB_ENABLE_REQUEST_VALIDATION="true"
```

## Rate Limiting

To prevent abuse and ensure fair usage, LocalLab supports simple rate limiting. You can configure the maximum permitted requests per minute and the burst size with the following environment variables:

```bash
export LOCALLAB_RATE_LIMIT="60"         # Maximum requests per minute
export LOCALLAB_BURST_SIZE="10"         # Maximum burst size
```

## Additional Security Settings

You may also enable compression and other settings to guard against overuse of resources:

```bash
export LOCALLAB_ENABLE_COMPRESSION="true"
```

For more advanced security configurations (such as API key based authentication), please explore further customizations or open an issue on the [LocalLab GitHub repository](https://github.com/UtkarshTheDev/LocalLab/issues).
