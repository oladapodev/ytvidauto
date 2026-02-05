from pathlib import Path
import shutil
import os
from contextlib import asynccontextmanager

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

# Robust Path Resolution for Docker and Local
BASE_PATH = Path(__file__).resolve().parent
ASSETS_PATH = BASE_PATH / "demo-frontend" / "assets"
INDEX_PATH = BASE_PATH / "demo-frontend" / "index.html"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Clean up temp and output directories
    print("Startup: Cleaning up temporary and output directories...")
    try:
        # Re-create directories using settings paths
        settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Cleanup logic
        for path in [settings.TEMP_DIR, settings.OUTPUT_DIR]:
            for filename in os.listdir(path):
                file_path = path / filename
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception:
                    pass
        print("Startup: Cleanup complete.")
    except Exception as e:
        print(f"Startup: Cleanup failed: {e}")
    
    yield

def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Automated Video Slideshow API",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(video_router)

    # Static Files Mounting
    if ASSETS_PATH.exists():
        app.mount("/assets", StaticFiles(directory=str(ASSETS_PATH)), name="assets")
    else:
        # Fallback for Docker environments where CWD might be different
        docker_assets = Path("/app/demo-frontend/assets")
        if docker_assets.exists():
            app.mount("/assets", StaticFiles(directory=str(docker_assets)), name="assets")

    @app.get("/api/info")
    async def api_info():
        return {"app": settings.APP_NAME, "status": "online"}

    @app.get("/")
    async def serve_frontend():
        # Prefer the resolved INDEX_PATH
        if INDEX_PATH.exists():
            return FileResponse(str(INDEX_PATH))
        # Fallback
        docker_index = Path("/app/demo-frontend/index.html")
        if docker_index.exists():
            return FileResponse(str(docker_index))
        return {"error": "Frontend index.html not found"}

    return app

app = create_application()

if __name__ == "__main__" and uvicorn:
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
