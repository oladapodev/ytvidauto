# YouTube Video Automation API

A production-ready FastAPI application for generating automated slideshow videos with cinematic zoom effects using MoviePy 2.x.

## Features

- **Asynchronous Generation**: Long-running video generation tasks are handled in the background.
- **Flexible Inputs**: Accepts audio and images either as local file uploads or remote URLs.
- **Cinematic Effects**: Automatically applies alternating zoom-in and zoom-out effects to images.
- **Auto-Sync**: Images are automatically timed to span the entire duration of the provided audio.
- **Clean Architecture**: Follows strict separation of concerns and descriptive naming conventions.

## Tech Stack

- **Python**: 3.12+
- **Framework**: FastAPI 0.128.0
- **Video Engine**: MoviePy 2.2.1
- **Management**: uv (Package/Environment Management)
- **Validation**: Pydantic 2.12.5
- **Networking**: httpx 0.27.0

## Getting Started

### Prerequisites

- [uv](https://github.com/astral-sh/uv) installed on your system.
- FFmpeg installed (required by MoviePy).

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
uv run uvicorn src.main:app --reload
```
The API will be available at `http://localhost:8000`. 
Interactive documentation is available at `http://localhost:8000/docs`.

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
├── src/
│   ├── api/
│   │   ├── endpoints/          # API routes (FastAPI)
│   │   ├── models/             # Pydantic schemas
│   │   └── dependencies/       # Dependency injection
│   ├── core/
│   │   ├── config/             # App settings (Pydantic-settings)
│   │   └── utilities/          # Core logic (MoviePy, File Fetching)
│   └── main.py                 # App entry point
├── tests/                      # Pytest suite
├── pyproject.toml              # uv configuration
└── README.md
```