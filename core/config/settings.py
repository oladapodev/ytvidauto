from pathlib import Path
from pydantic import BaseModel


class ApplicationSettings(BaseModel):
    """
    Application-wide configuration settings.
    Simplified for Cloudflare Workers compatibility by avoiding pydantic-settings.
    """

    # Application Metadata
    APP_NAME: str = "YouTube Video Automation API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Directory Configurations
    # On Cloudflare Workers, we use /tmp for ephemeral storage
    BASE_DIR: Path = Path("/tmp")
    TEMP_DIR: Path = Path("/tmp/temp")
    OUTPUT_DIR: Path = Path("/tmp/outputs")

    # API Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Utility Limits
    HTTP_FETCH_TIMEOUT_SECONDS: int = 60
    MAX_IMAGE_COUNT: int = 50
    DEFAULT_FPS: int = 24

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Attempt to create dirs, but don't crash if it fails (not supported on some edge envs)
        try:
            self.TEMP_DIR.mkdir(parents=True, exist_ok=True)
            self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass


# Instantiate settings for global use across the application
settings = ApplicationSettings()

# Ensure necessary directories exist on startup (if possible)
try:
    settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
