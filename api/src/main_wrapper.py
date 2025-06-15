"""Wrapper for main.py that handles imports correctly for uvicorn."""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Now import with absolute imports
from core.config import settings
from routers.debug import router as debug_router
from routers.development import router as dev_router
from routers.openai_compatible import router as openai_router
from routers.web_player import router as web_router
from services.temp_manager import temp_manager
from inference.model_manager import model_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event manager"""
    # Startup
    logger.info("Starting Kokoro-FastAPI server...")
    logger.info(f"Server version: 0.4.0")
    logger.info(f"Model directory: {settings.model_dir}")
    logger.info(f"Voices directory: {settings.voices_dir}")
    logger.info(f"Device type: {'GPU' if settings.use_gpu else 'CPU'}")
    
    # Initialize model manager
    logger.info("Loading TTS model and voice packs...")
    
    model_path = f"{settings.model_version}/kokoro-{settings.model_version}.pth"
    try:
        device, model, voicepack_count = await model_manager.initialize_with_warmup(
            model_path=model_path
        )
        
        logger.info(f"Model loaded successfully on {device}")
        logger.info(f"Available voice packs: {voicepack_count}")
        
        # Initialize temp manager
        temp_manager.set_model_manager(model_manager)
        temp_manager.start_cleanup_task()
        
    except Exception as e:
        logger.error(f"Failed to initialize model: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down server...")
    temp_manager.stop_cleanup_task()
    model_manager.unload()
    
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()


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
if settings.debug_mode:
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