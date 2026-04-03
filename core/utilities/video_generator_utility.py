import os
import subprocess
import uuid
from typing import List, Optional
from core.config.settings import settings
from core.config.video_styles import get_style_filter

# Common video file extensions
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.flv', '.wmv', '.ts'}


def is_video_file(path: str) -> bool:
    """Detect whether a file is a video based on its extension."""
    _, ext = os.path.splitext(path)
    return ext.lower() in VIDEO_EXTENSIONS


class VideoGenerationTaskProcessor:
    """
    High-performance video generation utility using raw FFmpeg.
    Supports both image and video clips as timeline segments.
    Images are looped and animated; videos are trimmed/scaled directly.
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

    def get_media_duration(self, path: str) -> float:
        """Get the duration of a video clip via ffprobe."""
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            return float(result.stdout.strip())
        except ValueError:
            return 3.0

    def _build_image_segment(
        self,
        img_path: str,
        segment_path: str,
        duration: float,
        style_id: int,
        width: int,
        height: int,
        inter_w: int,
        inter_h: int,
        x_off: float,
        y_off: float,
        scale: float,
        unique_run_id: str,
        index: int
    ):
        """Build a video segment from a static image using loop + zoompan filter."""
        total_frames = max(1, int(duration * self.fps))
        zoompan_filter = get_style_filter(style_id, total_frames, self.fps, index, width, height)

        s_w = int(inter_w * scale)
        s_h = int(inter_h * scale)
        pos_filter = (
            f"scale={s_w}:{s_h}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height}:{s_w / 2 + x_off}:{s_h / 2 + y_off}"
        )

        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
            '-threads', '1', '-loop', '1', '-i', img_path,
            '-vf', f"{pos_filter},format=yuv420p,{zoompan_filter},setsar=1",
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
            '-pix_fmt', 'yuv420p', '-t', str(duration),
            segment_path
        ]
        subprocess.run(cmd, check=True)

    def _build_video_segment(
        self,
        vid_path: str,
        segment_path: str,
        duration: float,
        width: int,
        height: int,
        x_off: float,
        y_off: float,
        scale: float
    ):
        """
        Build a video segment from a video clip.
        Scales the clip to fill the target resolution (with optional offset/scale),
        and trims it to `duration` seconds. If the clip is shorter, it loops it.
        """
        native_duration = self.get_media_duration(vid_path)

        # If user-specified duration exceeds native video length, loop the source
        if duration > native_duration:
            input_args = ['-stream_loop', '-1', '-i', vid_path]
        else:
            input_args = ['-i', vid_path]

        # Scale to fill canvas, apply offset
        vf = (
            f"scale={int(width * scale * 1.25)}:{int(height * scale * 1.25)}"
            f":force_original_aspect_ratio=increase,"
            f"crop={width}:{height}:"
            f"{int(width * scale * 1.25 / 2 + x_off)}:{int(height * scale * 1.25 / 2 + y_off)},"
            f"setsar=1,format=yuv420p"
        )

        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
            '-threads', '1',
        ] + input_args + [
            '-vf', vf,
            '-an',  # Strip audio from segment (mixed at the end)
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
            '-pix_fmt', 'yuv420p', '-t', str(duration),
            segment_path
        ]
        subprocess.run(cmd, check=True)

    def generate_video_from_audio_and_images(
        self,
        audio_path: str,
        image_paths: List[str],
        output_path: str,
        style_id: int = 1,
        orientation: str = "landscape",
        image_duration: float = 0.0,
        image_durations: List[float] = None,
        offsets: List[dict] = None,
        media_types: Optional[List[str]] = None  # 'image' | 'video' per clip
    ) -> str:
        """
        Generates video by creating individual video segments for each clip
        (image or video) and concatenating them with the audio track.
        """
        segment_files = []
        concat_list_path = os.path.join(settings.TEMP_DIR, f"concat_list_{uuid.uuid4()}.txt")
        unique_run_id = str(uuid.uuid4())[:8]

        try:
            if not hasattr(subprocess, "run"):
                raise RuntimeError("Subprocess (FFmpeg) not supported on Cloudflare Workers.")

            total_audio_duration = self.get_audio_duration(audio_path)

            # --- Duration & Offset Logic ---
            if image_durations and len(image_durations) == len(image_paths):
                final_image_durations = image_durations
            else:
                auto_dur = total_audio_duration / len(image_paths) if total_audio_duration > 0 else 3.0
                final_image_durations = [auto_dur] * len(image_paths)

            if offsets and len(offsets) == len(image_paths):
                final_offsets = offsets
            else:
                final_offsets = [{"x": 0, "y": 0, "scale": 1.0}] * len(image_paths)

            # Resolve media types — fall back to file-extension detection
            resolved_types = []
            for i, path in enumerate(image_paths):
                if media_types and i < len(media_types):
                    resolved_types.append(media_types[i])
                else:
                    resolved_types.append('video' if is_video_file(path) else 'image')

            if orientation.lower() == "portrait":
                width, height = 1080, 1920
            else:
                width, height = 1920, 1080

            scale_factor = 1.25
            inter_w = int(width * scale_factor)
            inter_h = int(height * scale_factor)

            for i, media_path in enumerate(image_paths):
                current_duration = final_image_durations[i]
                off = final_offsets[i]
                x_off = off.get("x", 0)
                y_off = off.get("y", 0)
                clip_scale = off.get("scale", 1.0)

                segment_path = os.path.join(settings.TEMP_DIR, f"seg_{unique_run_id}_{i}.mp4")
                clip_type = resolved_types[i]

                if clip_type == 'video':
                    self._build_video_segment(
                        vid_path=media_path,
                        segment_path=segment_path,
                        duration=current_duration,
                        width=width,
                        height=height,
                        x_off=x_off,
                        y_off=y_off,
                        scale=clip_scale
                    )
                else:
                    self._build_image_segment(
                        img_path=media_path,
                        segment_path=segment_path,
                        duration=current_duration,
                        style_id=style_id,
                        width=width,
                        height=height,
                        inter_w=inter_w,
                        inter_h=inter_h,
                        x_off=x_off,
                        y_off=y_off,
                        scale=clip_scale,
                        unique_run_id=unique_run_id,
                        index=i
                    )

                segment_files.append(segment_path)

            # Write concat list
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
            for path in [concat_list_path] + segment_files:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
