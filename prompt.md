You are an AI coding agent tasked with building a complete, production-ready Python project for a YouTube automation API. This API accepts audio and images either as file uploads or URLs (fetching them if URLs are provided) via a POST endpoint, generates a video by animating the images (slideshow with effects like zoom in/out) synced to the audio using MoviePy, and handles long-running generations asynchronously with FastAPI's BackgroundTasks. The project must follow strict separation of concerns, a highly readable folder structure, intention-driven descriptive class and function names (no abbreviations or short names—e.g., use VideoGenerationTaskProcessor instead of VidGen), comprehensive comments explaining what each part does and why, and adhere to the latest best practices in Python, FastAPI, and MoviePy as of January 2026.
Important Rules—Strictly Follow These, Do Not Skip or Deviate:

Do not try to be smart, optimize prematurely, or add features not specified. Follow instructions exactly, step by step, one task before the next. Do not combine tasks.
Break your work into sequential tasks as listed below. Complete one fully before moving to the next. Output progress after each task.
Use the latest versions: uv 0.9.27 for project setup, FastAPI 0.128.0, MoviePy 2.2.1, Uvicorn 0.40.0, Pillow 12.1.0, python-multipart 0.0.22, Pydantic 2.12.5, httpx 0.27.0 (for fetching URLs).
For dev: pytest 9.0.2, ruff 0.14.13.
Code must prioritize readability: Use type hints everywhere, follow PEP 8 with Ruff for linting (integrate Ruff via uv), add docstrings to all classes/functions, and inline comments for complex logic.
Best practices:
FastAPI: Use async endpoints where possible, dependencies for shared logic, Pydantic for models, HTTPException for errors, BackgroundTasks for async video generation.
MoviePy: Handle resources properly (close clips), use resize for zooms, ensure FPS=24, codec=libx264.
General: Use tempfile for uploads/fetched files, store outputs temporarily and return download paths, add basic error handling for URL fetching.
Testing: Include pytest setup with basic tests.

Folder structure (separation of concerns):textproject_root/
├── src/
│   ├── api/
│   │   ├── endpoints/
│   │   │   └── video_generation_endpoint.py  # API routes
│   │   ├── models/
│   │   │   └── request_response_models.py  # Pydantic schemas
│   │   └── dependencies/
│   │       └── shared_dependencies.py  # FastAPI deps if needed
│   ├── core/
│   │   ├── config/
│   │   │   └── settings.py  # App configs
│   │   └── utilities/
│   │       ├── video_generator_utility.py  # MoviePy logic
│   │       └── file_fetcher_utility.py  # Logic to handle file/URL inputs
│   └── main.py  # FastAPI app entry
├── tests/
│   └── test_video_generation.py  # Pytest files
├── .gitignore
├── pyproject.toml  # Managed by uv
└── README.md  # Instructions to run
Use uv for all setup: uv init, uv add <package>, uv sync, uv run.

Sequential Tasks—Complete One by One:

Project Initialization: Use uv 0.9.27 to create a new project named "yt-video-automation-api". Run uv init yt-video-automation-api --app to set up pyproject.toml and basic structure. Then cd into it and use uv python pin 3.12 for Python 3.12. Add .gitignore with standard Python ignores plus temp files.
Add Dependencies: Use uv add to install: fastapi==0.128.0, uvicorn==0.40.0, moviepy==2.2.1, pillow==12.1.0, python-multipart==0.0.22, pydantic==2.12.5, httpx==0.27.0. For dev: uv add --dev pytest==9.0.2, ruff==0.14.13. Run uv sync to create lockfile and venv.
Configure Settings: In src/core/config/settings.py, create a Settings class using Pydantic's BaseSettings. Include any necessary configs like TEMP_DIR or timeouts. Add comments explaining each.
File Fetcher Utility: In src/core/utilities/file_fetcher_utility.py, create a class FileFetcherUtility with async methods to handle inputs: fetch_and_save_if_url(input: Union[str, UploadFile], temp_dir: str) -> str. If str (URL), use httpx to async get and save to temp file; if UploadFile, save directly. Handle lists for images. Fully comment logic.
Video Generation Utility: In src/core/utilities/video_generator_utility.py, create a class VideoGeneratorUtility with a method generate_video_from_audio_and_images(audio_path: str, image_paths: list[str], output_path: str). Use MoviePy to load audio, calculate durations, create ImageClips with alternating zoom in/out using resize lambda (e.g., 1.0 to 1.2 and back), concatenate, set audio, write_videofile with fps=24, codec='libx264', audio_codec='aac'. Add error handling, resource cleanup. Fully comment logic.
API Models: In src/api/models/request_response_models.py, use Pydantic to define VideoGenerationRequest (audio: Union[UploadFile, str], images: List[Union[UploadFile, str]] ) and VideoGenerationResponse (task_id: str, status: str, poll_url: str, download_url: Optional[str]).
API Dependencies: In src/api/dependencies/shared_dependencies.py, create any needed dependencies, like for settings.
API Endpoints: In src/api/endpoints/video_generation_endpoint.py, create a FastAPI router. Add async POST /generate-video using models, BackgroundTasks. Use FileFetcherUtility to get paths from inputs in temp dir, add background task to call VideoGeneratorUtility, store status in in-memory dict (task_id -> status/file), return response with task_id. Add /status/{task_id} to check status and if done, provide download URL. Add /download/{task_id} to serve FileResponse if done.
Main App Entry: In src/main.py, create FastAPI app, include the router, add middleware for logging/security if needed (basic CORS).
Testing Setup: In tests/test_video_generation.py, add pytest fixtures for app/client, mock background tasks, test endpoint returns accepted, status checks.
README and Final Polish: Write README.md with setup (uv sync, uv run uvicorn src.main:app), usage. Run ruff check/lint, pytest. Ensure everything is commented and readable.

After each task, output: "Task X completed. Proceeding to Task Y." When all done, output the full codebase. Do not generate code outside these tasks. Start with Task 1.