try:
    import uvicorn
except ImportError:
    uvicorn = None
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from api.endpoints.video_generation_endpoint import router as video_router
from core.config.settings import settings

from contextlib import asynccontextmanager
import shutil
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Clean up temp and output directories
    print("Startup: Cleaning up temporary and output directories...")
    try:
        if settings.TEMP_DIR.exists():
            shutil.rmtree(settings.TEMP_DIR)
        if settings.OUTPUT_DIR.exists():
            for filename in os.listdir(settings.OUTPUT_DIR):
                file_path = settings.OUTPUT_DIR / filename
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
        
        # Re-create directories
        settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print("Startup: Cleanup complete.")
    except Exception as e:
        print(f"Startup: Cleanup failed: {e}")
    
    yield
    
    # Shutdown: (Optional) could clean again, but usually we keep outputs
    pass

def create_application() -> FastAPI:
    """
    Factory function to create and configure the FastAPI application.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="An automated API for generating slideshow videos from images and audio.",
        lifespan=lifespan
    )

    # Configure CORS (Cross-Origin Resource Sharing)
    # Allows requests from different domains, useful for frontend integrations
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify actual domains
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routers
    app.include_router(video_router)

    # Mount static assets
    app.mount("/assets", StaticFiles(directory="demo-frontend/assets"), name="assets")

    @app.get("/api/info", tags=["Health Check"])
    async def api_info():
        """
        Simple health check endpoint.
        """
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "online"
        }

    @app.get("/", tags=["UI"])
    async def serve_frontend():
        """
        Serve the frontend UI.
        """
        return FileResponse("demo-frontend/index.html")

    return app

# The app instance to be used by the ASGI server (uvicorn)
app = create_application()

if __name__ == "__main__" and uvicorn:
    # Start the application manually for debugging
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
