# YouTube Video Automation API

A production-ready FastAPI application for generating automated slideshow videos with cinematic zoom effects using MoviePy 2.x.

## Features

- **Asynchronous Generation**: Long-running video generation tasks are handled in the background.
- **Flexible Inputs**: Accepts audio and images either as local file uploads or remote URLs.
- **Styles & Effects**: Choose from 5 cinematic styles including Zoom, Pan, Scroll, and Dynamic Mix.
- **Custom Orientation**: Generate videos in Landscape (16:9) or Portrait (9:16) modes.
- **Dynamic Timing**: Customize slide duration or auto-sync to audio length.
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
- `audio`: (File or URL String)
- `images`: (Multiple Files or URL Strings)
- `style`: (Integer) Style ID (1-5)
  - 1: Classic Zoom
  - 2: Cinematic Pan
  - 3: Vertical Scroll
  - 4: Static
  - 5: Dynamic Mix
- `orientation`: (String) "landscape" or "portrait"
- `image_duration`: (Float) Seconds per image (optional)

**Response:**
```json
{
  "task_id": "uuid-string",
  "status": "pending",
  "poll_url": "/video/status/uuid-string",
  "download_url": null
}
```

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