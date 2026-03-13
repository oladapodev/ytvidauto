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
            return 30.0  # Fallback default

    def generate_video_from_audio_and_images(
        self,
        audio_path: str,
        image_paths: List[str],
        output_path: str,
        style_id: int = 1,
        orientation: str = "landscape",
        image_duration: float = 0.0,
        image_durations: List[float] = None,
        offsets: List[dict] = None
    ) -> str:
        """
        Generates video by creating individual video segments for each image and concatenating them.
        """
        segment_files = []
        concat_list_path = os.path.join(settings.TEMP_DIR, f"concat_list_{uuid.uuid4()}.txt")
        unique_run_id = str(uuid.uuid4())[:8]

        try:
            if not hasattr(subprocess, "run"):
                raise RuntimeError("Subprocess (FFmpeg) not supported on Cloudflare Workers.")

            total_audio_duration = self.get_audio_duration(audio_path)

            # --- Duration & Offset Logic ---
            final_image_durations = []
            final_offsets = []

            if image_durations and len(image_durations) == len(image_paths):
                final_image_durations = image_durations
            else:
                auto_dur = total_audio_duration / len(image_paths) if total_audio_duration > 0 else 3.0
                final_image_durations = [auto_dur] * len(image_paths)

            if offsets and len(offsets) == len(image_paths):
                final_offsets = offsets
            else:
                final_offsets = [{"x": 0, "y": 0, "scale": 1.0}] * len(image_paths)

            if orientation.lower() == "portrait":
                width, height = 1080, 1920
            else:
                width, height = 1920, 1080

            scale_factor = 1.25
            inter_w = int(width * scale_factor)
            inter_h = int(height * scale_factor)

            for i, img_path in enumerate(image_paths):
                current_duration = final_image_durations[i]
                total_frames = int(current_duration * self.fps)
                if total_frames < 1:
                    total_frames = 1

                off = final_offsets[i]
                x_off = off.get("x", 0)
                y_off = off.get("y", 0)
                scale = off.get("scale", 1.0)

                segment_path = os.path.join(settings.TEMP_DIR, f"seg_{unique_run_id}_{i}.mp4")
                zoompan_filter = get_style_filter(style_id, total_frames, self.fps, i, width, height)

                # Apply the manual offset and scale
                s_w = int(inter_w * scale)
                s_h = int(inter_h * scale)

                pos_filter = f"scale={s_w}:{s_h}:force_original_aspect_ratio=increase,crop={width}:{height}:{s_w/2+x_off}:{s_h/2+y_off}"

                cmd = [
                    'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
                    '-threads', '1', '-loop', '1', '-i', img_path,
                    '-vf', f"{pos_filter},format=yuv420p,{zoompan_filter},setsar=1",
                    '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
                    '-pix_fmt', 'yuv420p', '-t', str(current_duration),
                    segment_path
                ]

                subprocess.run(cmd, check=True)
                segment_files.append(segment_path)

            with open(concat_list_path, 'w') as f:
                for seg in segment_files:
                    f.write(f"file '{seg}'\n")

            final_cmd = [
                'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
                '-threads', '1', '-f', 'concat', '-safe', '0', '-i', concat_list_path,
                '-i', audio_path, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k',
            ]

            if not (image_durations or image_duration > 0):
                final_cmd.append('-shortest')

            final_cmd.append(output_path)
            subprocess.run(final_cmd, check=True)
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
