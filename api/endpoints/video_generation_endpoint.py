import uuid
import os
from typing import Dict, List

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, Request, Form
from fastapi.responses import FileResponse
from api.models.request_response_models import VideoGenerationResponse, TaskStatusModel
from api.dependencies.shared_dependencies import get_file_fetcher, get_video_processor, get_settings
from core.config.settings import ApplicationSettings
from core.utilities.file_fetcher_utility import FileFetcherUtility
from core.utilities.video_generator_utility import VideoGenerationTaskProcessor

router = APIRouter(prefix="/video", tags=["Video Generation"])

# In-memory store for task statuses (For production, use Redis or a database)
task_registry: Dict[str, TaskStatusModel] = {}


@router.get("/health")
async def health_check(request: Request):
    """
    Health check endpoint with deployment context.
    """
    is_workers = "env" in request.scope
    return {
        "status": "running on Cloudflare Workers" if is_workers else "running locally",
        "video_gen": "disabled" if is_workers else "enabled"
    }


async def run_video_generation_task(
    task_id: str,
    audio_path_or_url: str,
    image_paths_or_urls: List[str],
    file_fetcher: FileFetcherUtility,
    video_processor: VideoGenerationTaskProcessor,
    settings: ApplicationSettings,
    style_id: int = 1,
    orientation: str = "landscape",
    image_duration: float = 0.0
):
    """
    Background task to process files and generate the video.
    """
    print(f"DEBUG [Task {task_id}]: Starting generation task.")
    try:
        # Update status to processing
        task_registry[task_id].status = "processing"

        # 1. Resolve Audio Path
        print(f"DEBUG [Task {task_id}]: Resolving audio: {audio_path_or_url}")
        if os.path.isabs(audio_path_or_url) and os.path.exists(audio_path_or_url):
            final_audio_path = audio_path_or_url
            print(f"DEBUG [Task {task_id}]: Audio already exists at {final_audio_path}")
        else:
            print(f"DEBUG [Task {task_id}]: Audio not a local path. Attempting fetch/save.")
            final_audio_path = await file_fetcher.fetch_and_save_resource(audio_path_or_url)
            print(f"DEBUG [Task {task_id}]: Audio fetched and saved to {final_audio_path}")
        
        # 2. Resolve Image Paths
        final_image_paths = []
        for i, img in enumerate(image_paths_or_urls):
            print(f"DEBUG [Task {task_id}]: Resolving image {i}: {img}")
            if os.path.isabs(img) and os.path.exists(img):
                final_image_paths.append(img)
                print(f"DEBUG [Task {task_id}]: Image {i} already exists locally.")
            else:
                print(f"DEBUG [Task {task_id}]: Image {i} not local. Attempting fetch/save.")
                p = await file_fetcher.fetch_and_save_resource(img)
                final_image_paths.append(p)
                print(f"DEBUG [Task {task_id}]: Image {i} fetched and saved to {p}")

        # 3. Define output path
        output_filename = f"video_{task_id}.mp4"
        output_path = str(settings.OUTPUT_DIR / output_filename)
        print(f"DEBUG [Task {task_id}]: Final Output target: {output_path}")

        # 4. Generate the video
        print(f"DEBUG [Task {task_id}]: Calling FFmpeg processor...")
        video_processor.generate_video_from_audio_and_images(
            audio_path=final_audio_path,
            image_paths=final_image_paths,
            output_path=output_path,
            style_id=style_id,
            orientation=orientation,
            image_duration=image_duration
        )
        print(f"DEBUG [Task {task_id}]: FFmpeg processing finished successfully.")

        # 5. Update task registry on success
        task_registry[task_id].status = "completed"
        task_registry[task_id].output_path = output_path
        print(f"DEBUG [Task {task_id}]: Task marked COMPLETED.")

    except Exception as e:
        # Handle failures
        print(f"Task {task_id} failed: {str(e)}")
        task_registry[task_id].status = "failed"
        task_registry[task_id].error_message = str(e)


@router.post("/generate-video", response_model=VideoGenerationResponse)
async def generate_video(
    background_tasks: BackgroundTasks,
    request: Request,
    file_fetcher: FileFetcherUtility = Depends(get_file_fetcher),
    video_processor: VideoGenerationTaskProcessor = Depends(get_video_processor),
    settings: ApplicationSettings = Depends(get_settings),
    style: int = Form(1, description="Video style ID: 1=Zoom, 2=Pan, 3=Scroll, 4=Static, 5=Mix"),
    orientation: str = Form("landscape", description="Video orientation: 'landscape' or 'portrait'"),
    image_duration: float = Form(0.0, description="Duration per image in seconds (0 = sync to audio)")
):
    """
    Endpoint to initiate video generation. 
    Accepts audio and images as files or URLs in a multipart/form-data request.
    """
    # Cloudflare Workers Limitation Check
    if "env" in request.scope:
        return {
            "task_id": "mock_id_workers",
            "status": "not_implemented_on_edge",
            "message": "Video rendering exceeds Workers CPU limits and lacks FFmpeg binaries. Please use a full server environment."
        }

    form = await request.form()
    
    # Extract audio (either string URL or UploadFile)
    audio_input = form.get("audio")
    if not audio_input:
        raise HTTPException(status_code=422, detail="Audio input is required")
        
    # Extract images (multiple values)
    image_inputs = form.getlist("images")
    if not image_inputs:
        raise HTTPException(status_code=422, detail="At least one image is required")

    # Style, Orientation, and Duration are injected via Depends/Form above
    style_id = style



    task_id = str(uuid.uuid4())
    task_registry[task_id] = TaskStatusModel(task_id=task_id, status="pending")

    # Critical: UploadFiles MUST be read/saved before the request returns
    # because they are closed automatically when the endpoint finishes.
    processed_audio = ""
    # If it's a string, it's a URL. If not, we treat it as an UploadFile.
    if isinstance(audio_input, str):
        processed_audio = audio_input
    else:
        # It's an UploadFile object
        processed_audio = await file_fetcher.fetch_and_save_resource(audio_input)

    processed_images = []
    for img in image_inputs:
        if isinstance(img, str):
            processed_images.append(img)
        else:
            # It's an UploadFile object
            p = await file_fetcher.fetch_and_save_resource(img)
            processed_images.append(p)

    # Add generation to background tasks
    background_tasks.add_task(
        run_video_generation_task,
        task_id=task_id,
        audio_path_or_url=processed_audio,
        image_paths_or_urls=processed_images,
        file_fetcher=file_fetcher,
        video_processor=video_processor,
        settings=settings,
        style_id=style_id,
        orientation=orientation,
        image_duration=image_duration
    )

    # Return immediate response
    return VideoGenerationResponse(
        task_id=task_id,
        status="pending",
        poll_url=f"/video/status/{task_id}",
        download_url=None
    )


@router.get("/status/{task_id}", response_model=VideoGenerationResponse)
async def get_task_status(task_id: str):
    """
    Check the current status of a video generation task.
    """
    task = task_registry.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    download_url = f"/video/download/{task_id}" if task.status == "completed" else None
    
    return VideoGenerationResponse(
        task_id=task.task_id,
        status=task.status,
        poll_url=f"/video/status/{task_id}",
        download_url=download_url,
        error_message=task.error_message
    )


@router.get("/download/{task_id}")
async def download_video(task_id: str):
    """
    Download the generated video if the task is completed.
    """
    task = task_registry.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != "completed" or not task.output_path:
        raise HTTPException(status_code=400, detail="Video is not ready for download")

    if not os.path.exists(task.output_path):
        raise HTTPException(status_code=410, detail="File has been removed from temporary storage")

    return FileResponse(
        path=task.output_path,
        media_type="video/mp4",
        filename=f"generated_video_{task_id}.mp4"
    )
