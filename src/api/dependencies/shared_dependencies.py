from src.core.config.settings import ApplicationSettings, settings
from src.core.utilities.file_fetcher_utility import FileFetcherUtility
from src.core.utilities.video_generator_utility import VideoGenerationTaskProcessor


def get_settings() -> ApplicationSettings:
    """
    Dependency to provide application settings.
    """
    return settings


def get_file_fetcher() -> FileFetcherUtility:
    """
    Dependency to provide an instance of FileFetcherUtility.
    """
    return FileFetcherUtility(temp_directory=settings.TEMP_DIR)


def get_video_processor() -> VideoGenerationTaskProcessor:
    """
    Dependency to provide an instance of VideoGenerationTaskProcessor.
    """
    return VideoGenerationTaskProcessor(fps=settings.DEFAULT_FPS)
