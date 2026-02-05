import uuid
import os
from pathlib import Path
from typing import Union, List

import httpx
from fastapi import UploadFile
from core.config.settings import settings


class FileFetcherUtility:
    """
    Utility class for handling file inputs. Supports both local file uploads
    (FastAPI UploadFile) and remote URLs. Files are saved to a temporary directory
    for processing by the video generation utility.
    """

    def __init__(self, temp_directory: Union[str, Path] = settings.TEMP_DIR):
        """
        Initialize the utility with a target temporary directory.
        """
        self.temp_dir = Path(temp_directory)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_and_save_resource(self, input_source: Union[str, UploadFile]) -> str:
        """
        Process a single resource input. If the input is a URL (string starting with http),
        it downloads the content using httpx. If it's an UploadFile, it saves the uploaded
        stream to a temporary file.

        Args:
            input_source: Either a URL string or a FastAPI UploadFile object.

        Returns:
            str: The absolute path to the saved temporary file.

        Raises:
            Exception: If the URL fetch fails or file writing encounters an error.
        """
        # Generate a unique filename to avoid collisions
        unique_filename = f"{uuid.uuid4()}"
        
        MAX_SIZE = 10 * 1024 * 1024  # 10MB limit for edge workers environment
        
        if isinstance(input_source, str):
            if input_source.startswith("http://") or input_source.startswith("https://"):
                # Case: Input is a URL
                file_extension = input_source.split(".")[-1].split("?")[0]
                if len(file_extension) > 5:
                    file_extension = "tmp"
                
                target_path = self.temp_dir / f"{unique_filename}.{file_extension}"
                
                try:
                    async with httpx.AsyncClient(timeout=settings.HTTP_FETCH_TIMEOUT_SECONDS) as client:
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        }
                        # Stream the download to check size
                        async with client.stream("GET", input_source, headers=headers, follow_redirects=True) as response:
                            response.raise_for_status()
                            
                            content_length = response.headers.get("Content-Length")
                            if content_length and int(content_length) > MAX_SIZE:
                                raise ValueError(f"Remote file exceeds size limit of {MAX_SIZE/1e6}MB")

                            downloaded_size = 0
                            with open(target_path, "wb") as buffer:
                                async for chunk in response.aiter_bytes():
                                    downloaded_size += len(chunk)
                                    if downloaded_size > MAX_SIZE:
                                        raise ValueError(f"Remote file exceeds size limit of {MAX_SIZE/1e6}MB")
                                    buffer.write(chunk)
                except httpx.HTTPError as e:
                    raise RuntimeError(f"Failed to fetch remote resource: {str(e)}")
                
                return str(target_path.absolute())
            else:
                 # Case: String represents a local path or invalid input
                detail = f"Type: {type(input_source)}, Value: {str(input_source)[:100]}"
                raise ValueError(f"URL must start with http/https or be an UploadFile. Received: {detail}")

        else:
            # Case: Input is likely an Upload-like object (FastAPI/Starlette UploadFile)
            filename = getattr(input_source, "filename", "unnamed.tmp")
            extension = Path(filename).suffix if filename else ""
            target_path = self.temp_dir / f"{unique_filename}{extension}"
            
            # Optimization: Stream the file to disk in chunks instead of await input_source.read()
            # which loads the entire file into RAM.
            downloaded_size = 0
            try:
                with open(target_path, "wb") as buffer:
                    while True:
                        chunk = await input_source.read(1024 * 1024) # 1MB chunks
                        if not chunk:
                            break
                        downloaded_size += len(chunk)
                        if downloaded_size > MAX_SIZE:
                            raise ValueError(f"Uploaded file exceeds size limit of {MAX_SIZE/1e6}MB")
                        buffer.write(chunk)
            except Exception as e:
                if os.path.exists(target_path):
                    os.remove(target_path)
                raise e
            
            return str(target_path.absolute())

    async def process_multiple_resources(self, resource_list: List[Union[str, UploadFile]]) -> List[str]:
        """
        Process a list of resources (e.g., multiple images for a slideshow).

        Args:
            resource_list: A list containing URL strings or UploadFile objects.

        Returns:
            List[str]: A list of absolute paths to the saved temporary files.
        """
        saved_paths = []
        for resource in resource_list:
            path = await self.fetch_and_save_resource(resource)
            saved_paths.append(path)
        return saved_paths
