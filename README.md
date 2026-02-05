# YouTube Video Automation API

[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?name=ytvidauto&type=git&repository=oladapodev%2Fytvidauto&branch=main&builder=dockerfile&instance_type=free&regions=fra&instances_min=0&autoscaling_sleep_idle_delay=3900)

A production-ready FastAPI application for generating automated slideshow videos with cinematic zoom effects using MoviePy 2.x.

## Features

- **Interactive Canvas Editor**:
  - **Precision Dragging**: Adjust image positioning directly on the 16:9/9:16 canvas.
  - **Scale Control**: Resize images using the mouse wheel or the sidebar slider to perfectly fit your composition.
  - **Real-time Synchronization**: Image durations automatically adjust to match audio length, with fluid resizing between neighbors.
- **Variable Timing**: Supports custom durations for every single image in the slideshow via the new `timeline_data` API parameter.
- **Low-Resource Optimized**: Engineered for 0.1 vCPU / 512MB RAM environments (like Koyeb Free) using optimized FFmpeg scaling (1.25x) and single-threaded processing.
- **Asynchronous Generation**: Long-running video generation tasks are handled in the background.
- **Flexible Inputs**: Accepts audio and images either as local file uploads or remote URLs.
- **Styles & Effects**: Choose from 5 cinematic styles including Zoom, Pan, Scroll, and Dynamic Mix.
- **Custom Orientation**: Generate videos in Landscape (16:9) or Portrait (9:16) modes.
- **Auto-Cleanup**: Automatically manages temporary files to keep storage clean.
- **Clean Architecture**: Follows strict separation of concerns and descriptive naming conventions.

## Tech Stack

- **Python**: 3.12+
- **Framework**: FastAPI 0.128.0
- **Video Engine**: FFmpeg (via subprocess)
- **Management**: uv (Package/Environment Management)
- **Validation**: Pydantic 2.12.5
- **Networking**: httpx 0.27.0

## Getting Started

### Prerequisites

- [uv](https://github.com/astral-sh/uv) installed on your system.
- FFmpeg installed and in your PATH.
- Docker (optional, for containerized run).

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd ytvidauto
   ```

2. Sync dependencies and set up the virtual environment:
   ```bash
   uv sync
   ```

### Running the Application

Start the FastAPI server:
```bash
uv run uvicorn main:app --reload
```
The API will be available at `http://localhost:8000`. 
Interactive documentation is available at `http://localhost:8000/docs`.

**Using Docker:**
```bash
docker build -t ytvidauto:latest .
docker run -p 8000:8000 ytvidauto:latest
```

### Running Tests

Execute the test suite using pytest:
```bash
uv run pytest
```

### Linting and Formatting

We use Ruff for linting and formatting:
```bash
uv run ruff check .
```

## API Usage Example

### 1. Initiate Video Generation
**POST** `/video/generate-video`

**Multipart Form Data:**
- `audio`: (File or URL String) **Required**.
- `images`: (Multiple Files or URL Strings) **Required**.
- `timeline_data`: (JSON String) **Optional**. Allows precise control over duration and order.
  - Format: `[{"file_index": 0, "duration": 5.0}, {"file_index": 1, "duration": 2.5}]`
  - `file_index` refers to the 0-based index of the file in the `images` array.
- `style`: (Integer) Style ID (1-5, Default: 1)
  - 1: Classic Zoom
  - 2: Cinematic Pan
  - 3: Vertical Scroll
  - 4: Static
  - 5: Dynamic Mix
- `orientation`: (String) "landscape" or "portrait" (Default: "landscape")
- `image_duration`: (Float) Global seconds per image. Ignored if `timeline_data` is provided.

**Response:**
```json
{
  "task_id": "uuid-string",
  "status": "pending",
  "poll_url": "/video/status/uuid-string",
  "download_url": null
}
```

## Performance Optimizations for Free Tiers (Koyeb/Heroku)

This application is specifically tuned for environments with limited RAM (512MB) and CPU (0.1 vCPU):
1. **Intermediate Scaling**: Uses 1.25x scaling for internal processing instead of 2x or 4K, drastically reducing memory pressure.
2. **Streaming Uploads**: Files are streamed to disk in 1MB chunks to avoid loading large images or audio files entirely into RAM.
3. **Single-Threaded FFmpeg**: Limits FFmpeg to `-threads 1` to prevent CPU throttling and OOM kills.
4. **Ultrafast Presets**: Prioritizes rendering speed to avoid timeout errors on cloud platforms.

### 2. Check Task Status
**GET** `/video/status/{task_id}`

**Response (Processing):**
```json
{
  "task_id": "uuid-string",
  "status": "processing",
  "poll_url": "/video/status/uuid-string",
  "download_url": null
}
```

### 3. Download Completed Video
**GET** `/video/download/{task_id}`

## Folder Structure

```text
ytvidauto/
├── api/
│   ├── endpoints/          # API routes (FastAPI)
│   ├── models/             # Pydantic schemas
│   └── dependencies/       # Dependency injection
├── core/
│   ├── config/             # App settings & Video Styles
│   └── utilities/          # Core logic (Video Generator, File Fetching)
├── demo-frontend/          # Web UI
├── main.py                 # App entry point
├── tests/                  # Pytest suite
├── Dockerfile              # Container config
├── pyproject.toml          # uv configuration
└── README.md
```