#!/usr/bin/env python
"""Kokoro server entry point with proper imports."""

import os
import sys
from pathlib import Path

# Set up paths
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import FastAPI and other dependencies
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import with absolute paths
from core.config import settings
from routers.openai_compatible import router as openai_router
from routers.web_player import router as web_router
from services.temp_manager import temp_manager
from inference.model_manager import model_manager

# Import optional routers
try:
    from routers.debug import router as debug_router
    from routers.development import router as dev_router
    HAS_DEBUG_ROUTERS = True
except ImportError:
    HAS_DEBUG_ROUTERS = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event manager"""
    # Startup
    print("Starting Kokoro-FastAPI server...")
    print(f"Model directory: {settings.model_dir}")
    print(f"Voices directory: {settings.voices_dir}")
    
    # Initialize model manager
    print("Loading TTS model and voice packs...")
    
    model_path = f"{settings.model_version}/kokoro-{settings.model_version}.pth"
    try:
        device, model, voicepack_count = await model_manager.initialize_with_warmup(
            model_path=model_path
        )
        
        print(f"Model loaded successfully on {device}")
        print(f"Available voice packs: {voicepack_count}")
        
        # Initialize temp manager
        temp_manager.set_model_manager(model_manager)
        temp_manager.start_cleanup_task()
        
    except Exception as e:
        print(f"Failed to initialize model: {e}")
        raise
    
    yield
    
    # Shutdown
    print("Shutting down server...")
    temp_manager.stop_cleanup_task()
    model_manager.unload()

# Create FastAPI app
app = FastAPI(
    title="Kokoro-FastAPI",
    description="FastAPI OpenAI Compatible TTS API",
    version="0.4.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(openai_router)
app.include_router(web_router)

# Conditionally include debug/dev routers
if HAS_DEBUG_ROUTERS and settings.debug_mode:
    app.include_router(debug_router, prefix="/debug", tags=["debug"])
    app.include_router(dev_router, prefix="/dev", tags=["development"])

# Health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "ok",
        "version": "0.4.0",
        "model_loaded": model_manager.is_loaded
    }

if __name__ == "__main__":
    import uvicorn
    
    # Get config from environment
    host = os.environ.get("KOKORO_HOST", "0.0.0.0")
    port = int(os.environ.get("KOKORO_PORT", "8880"))
    
    # Run the server
    uvicorn.run(app, host=host, port=port)