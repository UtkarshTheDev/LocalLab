"""
API routes for LocalLab
"""

# Import routers for easier access
from .models import router as models_router
from .generate import router as generate_router
from .system import router as system_router 