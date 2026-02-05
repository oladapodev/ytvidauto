from typing import List, Optional, Any
from pydantic import BaseModel, Field


class TimelineEntry(BaseModel):
    """
    Represents an individual item in the video timeline.
    """
    file_index: int = Field(..., description="The 0-based index of the image in the 'images' upload list.")
    duration: float = Field(..., description="Duration in seconds for this image segment.")
    x_offset: float = Field(0.0, description="Horizontal shift of the image on the canvas.")
    y_offset: float = Field(0.0, description="Vertical shift of the image on the canvas.")
    scale: float = Field(1.0, description="Scaling factor (zoom) for the image.")


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


class VideoGenerationRequest(BaseModel):
    """
    Schema for the video generation request parameters.
    Note: Standard Multipart form data is handled by Form() fields in the endpoint.
    """
    audio: Any = Field(..., description="URL string or an uploaded audio file.")
    images: List[Any] = Field(..., description="List of URL strings or uploaded image files.")
    style: int = Field(1, ge=1, le=5, description="Style ID (1: Zoom, 2: Pan, 3: Scroll, 4: Static, 5: Mix)")
    orientation: str = Field("landscape", description="Video aspect ratio: 'landscape' or 'portrait'")
    image_duration: float = Field(0.0, description="Fallback constant duration per image (ignored if timeline_data is used)")
    timeline_data: Optional[str] = Field(None, description="JSON string array of TimelineEntry objects.")