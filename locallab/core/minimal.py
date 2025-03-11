"""
Minimal FastAPI app for fallback when the main app fails to load.
This provides basic functionality to indicate that the server is running
but in a degraded state.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

# Create a minimal FastAPI app
app = FastAPI(
    title="LocalLab (Minimal Mode)",
    description="LocalLab server running in minimal mode due to initialization errors",
    version="0.4.18"
)

class StatusResponse(BaseModel):
    status: str
    message: str
    version: str

@app.get("/", response_model=StatusResponse)
async def root():
    """Root endpoint that returns basic server status."""
    return {
        "status": "minimal",
        "message": "LocalLab server is running in minimal mode due to initialization errors. Check logs for details.",
        "version": "0.4.18"
    }

@app.get("/health", response_model=StatusResponse)
async def health():
    """Health check endpoint."""
    return {
        "status": "minimal",
        "message": "LocalLab server is running in minimal mode. Limited functionality available.",
        "version": "0.4.18"
    }

@app.get("/status", response_model=StatusResponse)
async def status():
    """Status endpoint that provides more detailed information."""
    return {
        "status": "minimal",
        "message": "LocalLab server is running in minimal mode. The main application failed to initialize. Check server logs for details.",
        "version": "0.4.18"
    }

class ErrorResponse(BaseModel):
    error: str
    message: str

@app.get("/generate", response_model=ErrorResponse)
async def generate():
    """Generate endpoint that returns an error message."""
    raise HTTPException(
        status_code=503,
        detail="Text generation is not available in minimal mode. Server is running with limited functionality due to initialization errors."
    )

@app.get("/models", response_model=Dict[str, List[str]])
async def models():
    """Models endpoint that returns an empty list."""
    return {
        "models": [],
        "message": "Model information is not available in minimal mode."
    }

@app.get("/system", response_model=Dict[str, Any])
async def system():
    """System endpoint that returns minimal system information."""
    import platform
    import psutil
    
    try:
        return {
            "status": "minimal",
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "cpu_count": psutil.cpu_count(),
            "memory_percent": psutil.virtual_memory().percent,
            "message": "Server is running in minimal mode with limited functionality."
        }
    except Exception:
        return {
            "status": "minimal",
            "message": "System information is not available in minimal mode."
        } 