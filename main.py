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

def create_application() -> FastAPI:
    """
    Factory function to create and configure the FastAPI application.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="An automated API for generating slideshow videos from images and audio."
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
