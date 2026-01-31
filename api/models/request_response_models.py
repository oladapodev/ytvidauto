from typing import List, Optional, Any
from pydantic import BaseModel, Field


class VideoGenerationResponse(BaseModel):
    """
    Response model returned immediately after a video generation task is queued.
    """
    task_id: str = Field(..., description="Unique identifier for the video generation task.")
    status: str = Field(..., description="Current status of the task (e.g., 'pending', 'processing', 'completed', 'failed').")
    poll_url: str = Field(..., description="URL to poll for the current status of the task.")
    download_url: Optional[str] = Field(None, description="URL to download the video if completed.")
    error_message: Optional[str] = Field(None, description="Detailed error message if task failed.")


class TaskStatusModel(BaseModel):
    """
    Internal model to track task state.
    """
    task_id: str
    status: str
    output_path: Optional[str] = None
    error_message: Optional[str] = None


# Note: VideoGenerationRequest with Union[UploadFile, str] is tricky for standard Pydantic models
# because UploadFile is a FastAPI-specific class meant for Form data, not JSON bodies.
# We define it here for conceptual alignment with the requirements, but the endpoint
# will handle the actual parsing of Multipart/Form data.

class VideoGenerationRequest(BaseModel):
    """
    Conceptual model for the request. 
    In practice, FastAPI handles UploadFile via Form parameters.
    """
    audio: Any = Field(..., description="URL string or an uploaded audio file.")
    images: List[Any] = Field(..., description="List of URL strings or uploaded image files.")
