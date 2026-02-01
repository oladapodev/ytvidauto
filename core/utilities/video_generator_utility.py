import os
import subprocess
import uuid
from typing import List
from core.config.settings import settings
from core.config.video_styles import get_style_filter


class VideoGenerationTaskProcessor:
    """
    High-performance video generation utility using raw FFmpeg.
    Uses intermediate segment generation to ensure robust slideshow timing.
    """

    def __init__(self, fps: int = settings.DEFAULT_FPS):
        self.fps = fps

    def get_audio_duration(self, audio_path: str) -> float:
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', audio_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            return float(result.stdout.strip())
        except ValueError:
            return 30.0 # Fallback default

    def generate_video_from_audio_and_images(
        self, 
        audio_path: str, 
        image_paths: List[str], 
        output_path: str, 
        style_id: int = 1,
        orientation: str = "landscape",
        image_duration: float = 0.0
    ) -> str:
        """
        Generates video by creating individual video segments for each image and concatenating them.
        This approach is significantly more stable than complex filtergraphs for slideshows.
        """
        segment_files = []
        concat_list_path = os.path.join(settings.TEMP_DIR, f"concat_list_{uuid.uuid4()}.txt")
        unique_run_id = str(uuid.uuid4())[:8]
        
        try:
            # Check for subprocess availability (not available in Cloudflare Workers Pyodide)
            if not hasattr(subprocess, "run"):
                raise RuntimeError("Subprocess (FFmpeg) not supported on Cloudflare Workers. Use a traditional server environment.")

            total_duration = self.get_audio_duration(audio_path)

            if image_duration > 0:
                # Use user-specified duration (seconds per slide)
                duration_per_image = image_duration
                # Note: If duration_per_image * count > audio duration, audio loops or stops?
                # For this implementation, we will match audio length in final step if possible, 
                # OR if user specified explicit duration, we might want video to define length.
                # Let's keep existing logic: 'shortest' will cut video if audio is shorter.
                # Ideally, if user sets duration, they want that duration.
                # We'll handle this in the final concat command.
            else:
                # Calculate based on audio duration
                if total_duration < len(image_paths):
                    total_duration = float(len(image_paths))
                duration_per_image = total_duration / len(image_paths)

            total_frames = int(duration_per_image * self.fps)
            
            # Determine resolution based on orientation
            if orientation.lower() == "portrait":
                width, height = 1080, 1920
                scale_crop_filter = f"scale={width*2}:{height*2}:force_original_aspect_ratio=increase,crop={width*2}:{height*2}" # High-res intermediate
            else:
                # Default Landscape
                width, height = 1920, 1080
                scale_crop_filter = f"scale={width*2}:{height*2}:force_original_aspect_ratio=increase,crop={width*2}:{height*2}"

            print(f"DEBUG: Generating {len(image_paths)} segments. Duration per img: {duration_per_image}s. Dim: {width}x{height}")

            # 1. Generate a video segment for each image
            for i, img_path in enumerate(image_paths):
                segment_path = os.path.join(settings.TEMP_DIR, f"seg_{unique_run_id}_{i}.mp4")
                
                # Get the filter string based on the selected style and dimensions
                zoompan_filter = get_style_filter(style_id, total_frames, self.fps, i, width, height)

                
                cmd = [
                    'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
                    '-loop', '1', '-i', img_path,
                    '-vf', (
                        f"{scale_crop_filter}," # High-res pre-process
                        f"format=yuv420p,"
                        f"{zoompan_filter},"
                        f"setsar=1"
                    ),
                    '-c:v', 'libx264',
                    '-preset', 'ultrafast', # Max speed for intermediate segments
                    '-pix_fmt', 'yuv420p',
                    '-t', str(duration_per_image),
                    segment_path
                ]
                
                subprocess.run(cmd, check=True)
                segment_files.append(segment_path)
                print(f"DEBUG: Generated segment {i+1}/{len(image_paths)}")

            # 2. Create concatenation list file
            with open(concat_list_path, 'w') as f:
                for seg in segment_files:
                    # FFmpeg concat requires absolute paths in a specific format
                    f.write(f"file '{seg}'\n")

            # 3. Concatenate segments and add audio
            print(f"DEBUG: Concatenating segments to {output_path}")
            
            final_cmd = [
                'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
                '-f', 'concat', '-safe', '0', '-i', concat_list_path,
                '-i', audio_path,
                '-c:v', 'copy', # Stream copy the video (super fast, no re-encode)
                '-c:a', 'aac', '-b:a', '192k',
            ]
            
            # Logic: If user specified image duration, we respect that length for video.
            # Audio behavior:
            # If audio > video: video ends (or black? -shortest means stop at shortest input).
            # If audio < video: audio silence (unless -shortest is used, then video cuts).
            
            # Implementation Strategy: 
            # If explicit duration used: Don't use -shortest (let video run full length, audio cuts or silence).
            # If auto duration (based on audio): Use -shortest (video matches audio).
            
            if image_duration <= 0.0:
                final_cmd.append('-shortest')
                
            final_cmd.append(output_path)

            
            subprocess.run(final_cmd, check=True)
            print("DEBUG: Final video ready.")
            
            return output_path

        except subprocess.CalledProcessError as e:
            print(f"FFmpeg Error: {e}")
            if os.path.exists(output_path):
                os.remove(output_path)
            raise e
        except Exception as e:
            raise e
        finally:
            # Cleanup intermediate files
            if os.path.exists(concat_list_path):
                try:
                    os.remove(concat_list_path)
                except OSError:
                    pass
            for seg in segment_files:
                if os.path.exists(seg):
                    try:
                        os.remove(seg)
                    except OSError:
                        pass
