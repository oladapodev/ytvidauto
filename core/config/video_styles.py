from typing import Callable

class VideoStyle:
    def __init__(self, id: int, name: str, description: str, filter_generator: Callable):
        self.id = id
        self.name = name
        self.description = description
        self.filter_generator = filter_generator

def style_zoom_in_out(total_frames: int, fps: int, index: int, width: int = 1280, height: int = 720) -> str:
    """Style 1: Alternating Zoom In and Zoom Out"""
    is_zoom_in = (index % 2 == 0)
    if is_zoom_in:
        # Smooth zoom in
        z_val = "min(zoom+0.0015,1.25)"
    else:
        # Smooth zoom out from 1.25x
        z_val = f"1.25-(0.25*on/{total_frames})"
    
    return (
        f"zoompan=z='{z_val}':d={total_frames}:s={width}x{height}:fps={fps}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    )

def style_pan_horizontal(total_frames: int, fps: int, index: int, width: int = 1280, height: int = 720) -> str:
    """Style 2: Alternating Horizontal Pan (Left -> Right, Right -> Left)"""
    is_left_to_right = (index % 2 == 0)
    
    if is_left_to_right:
        x_val = f"(1-on/{total_frames})*(iw-iw/zoom)"
    else:
        x_val = f"(on/{total_frames})*(iw-iw/zoom)"
        
    return (
        f"zoompan=z=1.2:d={total_frames}:s={width}x{height}:fps={fps}:"
        f"x='{x_val}':y='ih/2-(ih/zoom/2)'"
    )

def style_pan_vertical(total_frames: int, fps: int, index: int, width: int = 1280, height: int = 720) -> str:
    """Style 3: Alternating Vertical Pan (Top -> Bottom, Bottom -> Top)"""
    is_top_to_bottom = (index % 2 == 0)
    
    if is_top_to_bottom:
        y_val = f"(on/{total_frames})*(ih-ih/zoom)"
    else:
        y_val = f"(1-on/{total_frames})*(ih-ih/zoom)"

    return (
        f"zoompan=z=1.2:d={total_frames}:s={width}x{height}:fps={fps}:"
        f"x='iw/2-(iw/zoom/2)':y='{y_val}'"
    )

def style_static_fit(total_frames: int, fps: int, index: int, width: int = 1280, height: int = 720) -> str:
    """Style 4: Static image (No movement)"""
    return (
        f"zoompan=z=1:d={total_frames}:s={width}x{height}:fps={fps}:"
        f"x=0:y=0"
    )

def style_dynamic_mix(total_frames: int, fps: int, index: int, width: int = 1280, height: int = 720) -> str:
    """Style 5: Mix of all styles based on index"""
    cycle = index % 3
    if cycle == 0:
        return style_zoom_in_out(total_frames, fps, index, width, height)
    elif cycle == 1:
        return style_pan_horizontal(total_frames, fps, index, width, height)
    else:
        return style_pan_vertical(total_frames, fps, index, width, height)


# Registry of available styles
AVAILABLE_STYLES = {
    1: VideoStyle(1, "Classic Zoom", "Alternating gentle zoom in and out", style_zoom_in_out),
    2: VideoStyle(2, "Cinematic Pan", "Horizontal panning across images", style_pan_horizontal),
    3: VideoStyle(3, "Vertical Scroll", "Vertical panning up and down", style_pan_vertical),
    4: VideoStyle(4, "Static", "No motion, simple slideshow", style_static_fit),
    5: VideoStyle(5, "Dynamic Mix", "Randomized mix of pans and zooms", style_dynamic_mix),
}

def get_style_filter(style_id: int, total_frames: int, fps: int, index: int, width: int = 1280, height: int = 720) -> str:
    """Helper to get the filter string for a given style ID"""
    style = AVAILABLE_STYLES.get(style_id)
    if not style:
        # Default to style 1 if invalid ID
        style = AVAILABLE_STYLES[1]
    
    return style.filter_generator(total_frames, fps, index, width, height)
