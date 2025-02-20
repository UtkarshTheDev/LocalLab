#!/bin/bash

# Install test dependencies
pip install -r tests/requirements-test.txt

# Run tests with coverage
pytest tests/ \
    --cov=server.locallab \
    --cov-report=term-missing \
    --cov-report=html \
    -v 