from pathlib import Path
from pydantic_settings import BaseSettings


class ApplicationSettings(BaseSettings):
    """
    Application-wide configuration settings managed via Pydantic BaseSettings.
    Values can be overridden using environment variables (e.g., APP_NAME=MyAPI).
    """

    # Application Metadata
    APP_NAME: str = "YouTube Video Automation API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Directory Configurations
    # Base directory of the project (ytvidauto/)
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    
    # Directory for temporary file storage
    TEMP_DIR: Path = BASE_DIR / "temp"
    
    # Directory for final video outputs
    OUTPUT_DIR: Path = BASE_DIR / "outputs"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"INFO: Settings initialized. Base: {self.BASE_DIR}")
        print(f"INFO: Temp Dir: {self.TEMP_DIR}")
        print(f"INFO: Output Dir: {self.OUTPUT_DIR}")

    # API Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Utility Limits
    HTTP_FETCH_TIMEOUT_SECONDS: int = 60  # Timeout for fetching remote URLs
    MAX_IMAGE_COUNT: int = 50             # Reasonable limit for sliding images
    DEFAULT_FPS: int = 24                # Required FPS for the final video

    model_config = {
        "case_sensitive": True,
        "env_file": ".env"
    }


# Instantiate settings for global use across the application
settings = ApplicationSettings()

# Ensure necessary directories exist on startup
settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
