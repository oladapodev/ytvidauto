import uuid
import os
import json
from typing import Dict, List

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, Request, Form
from fastapi.responses import FileResponse
from api.models.request_response_models import VideoGenerationResponse, TaskStatusModel
from api.dependencies.shared_dependencies import get_file_fetcher, get_video_processor, get_settings
from core.config.settings import ApplicationSettings
from core.utilities.file_fetcher_utility import FileFetcherUtility
from core.utilities.video_generator_utility import VideoGenerationTaskProcessor

router = APIRouter(prefix="/video", tags=["Video Generation"])

# In-memory store for task statuses
task_registry: Dict[str, TaskStatusModel] = {}


@router.get("/health")
async def health_check(request: Request):
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
    image_duration: float = 0.0,
    timeline_durations: List[float] = None,
    timeline_offsets: List[dict] = None
):
    try:
        task_registry[task_id].status = "processing"

        # 1. Resolve Audio
        if os.path.isabs(audio_path_or_url) and os.path.exists(audio_path_or_url):
            final_audio_path = audio_path_or_url
        else:
            final_audio_path = await file_fetcher.fetch_and_save_resource(audio_path_or_url)
        
        # 2. Resolve Images
        final_image_paths = []
        for img in image_paths_or_urls:
            if os.path.isabs(img) and os.path.exists(img):
                final_image_paths.append(img)
            else:
                p = await file_fetcher.fetch_and_save_resource(img)
                final_image_paths.append(p)

        # 3. Output path
        output_filename = f"video_{task_id}.mp4"
        output_path = str(settings.OUTPUT_DIR / output_filename)

        # 4. Generate
        video_processor.generate_video_from_audio_and_images(
            audio_path=final_audio_path,
            image_paths=final_image_paths,
            output_path=output_path,
            style_id=style_id,
            orientation=orientation,
            image_duration=image_duration,
            image_durations=timeline_durations,
            offsets=timeline_offsets
        )

        task_registry[task_id].status = "completed"
        task_registry[task_id].output_path = output_path

    except Exception as e:
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
    style: int = Form(1, description="Style ID (1: Zoom, 2: Pan, 3: Scroll, 4: Static, 5: Mix)"),
    orientation: str = Form("landscape", description="Video aspect ratio: 'landscape' or 'portrait'"),
    image_duration: float = Form(0.0, description="Fallback constant duration per image (ignored if timeline_data is used)"),
    timeline_data: str = Form(None, description="JSON string array of timeline entries: [{'file_index': 0, 'duration': 5.0, 'x_offset': 0, 'y_offset': 0, 'scale': 1.0}, ...]")
):
    if "env" in request.scope:
        return {"task_id": "error", "status": "not_supported"}

    form = await request.form()
    audio_input = form.get("audio")
    image_inputs = form.getlist("images")

    if not audio_input or not image_inputs:
        raise HTTPException(status_code=422, detail="Missing audio or images")

    task_id = str(uuid.uuid4())
    task_registry[task_id] = TaskStatusModel(task_id=task_id, status="pending")

    # Initial save to avoid file closure
    processed_audio = audio_input if isinstance(audio_input, str) else await file_fetcher.fetch_and_save_resource(audio_input)
    temp_image_paths = []
    for img in image_inputs:
        p = img if isinstance(img, str) else await file_fetcher.fetch_and_save_resource(img)
        temp_image_paths.append(p)
    
    final_ordered_paths = []
    final_durations = []
    final_offsets = []
    
    if timeline_data:
        try:
            entries = json.loads(timeline_data)
            for entry in entries:
                idx = int(entry.get("file_index", -1))
                if 0 <= idx < len(temp_image_paths):
                    final_ordered_paths.append(temp_image_paths[idx])
                    final_durations.append(float(entry.get("duration", 3.0)))
                    final_offsets.append({
                        "x": float(entry.get("x_offset", 0)),
                        "y": float(entry.get("y_offset", 0)),
                        "scale": float(entry.get("scale", 1.0))
                    })
        except:
            final_ordered_paths = temp_image_paths
    else:
        final_ordered_paths = temp_image_paths

    background_tasks.add_task(
        run_video_generation_task,
        task_id=task_id,
        audio_path_or_url=processed_audio,
        image_paths_or_urls=final_ordered_paths,
        file_fetcher=file_fetcher,
        video_processor=video_processor,
        settings=settings,
        style_id=style,
        orientation=orientation,
        image_duration=image_duration,
        timeline_durations=final_durations,
        timeline_offsets=final_offsets
    )

    return VideoGenerationResponse(task_id=task_id, status="pending", poll_url=f"/video/status/{task_id}")


@router.get("/status/{task_id}", response_model=VideoGenerationResponse)
async def get_task_status(task_id: str):
    task = task_registry.get(task_id)
    if not task: raise HTTPException(status_code=404)
    return VideoGenerationResponse(
        task_id=task.task_id, status=task.status,
        poll_url=f"/video/status/{task_id}",
        download_url=f"/video/download/{task_id}" if task.status == "completed" else None,
        error_message=task.error_message
    )


@router.get("/download/{task_id}")
async def download_video(task_id: str):
    task = task_registry.get(task_id)
    if not task or task.status != "completed": raise HTTPException(status_code=404)
    return FileResponse(path=task.output_path, media_type="video/mp4", filename=f"video_{task_id}.mp4")