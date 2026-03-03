import os
import uuid
import httpx
import json
from typing import Optional
from core.config.settings import settings

class DeepgramSTTUtility:
    """
    Utility for generating ASS captions from an audio file using Deepgram JSON API.
    Supports Advanced SubStation Alpha formatting for custom animations like 'Typing' and 'Popping'.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPGRAM_API_KEY", getattr(settings, "DEEPGRAM_API_KEY", ""))
        self.api_url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&utterances=true"

    def format_ass_time(self, seconds: float) -> str:
        """Convert seconds into ASS format: h:mm:ss.cs"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int(round((seconds % 1) * 100))
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def generate_ass_file(self, utterances: list, caption_font: str, caption_style: str) -> str:
        """
        Takes raw Deepgram utterances and formats them into an ASS file with embedded styles.
        Styles supported: 'standard', 'typing', 'popping'.
        """
        font_name = caption_font if caption_font and caption_font.lower() != "none" else "Arial"
        ass_path = os.path.join(settings.TEMP_DIR, f"captions_{uuid.uuid4()}.ass")

        # ASS Header with forced FontName
        ass_header = f"""[Script Info]
ScriptType: v4.00+
ScaledBorderAndShadow: yes
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},72,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,2,2,10,10,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        lines = [ass_header]

        for utterance in utterances:
            start_time = self.format_ass_time(utterance['start'])
            end_time = self.format_ass_time(utterance['end'])
            words = utterance.get('words', [])

            if caption_style.lower() == "typing":
                # Karaokes: {\k<duration_in_centiseconds>} Word
                text_line = ""
                for word in words:
                    duration_cs = int(round((word['end'] - word['start']) * 100))
                    # Wait duration from end of last word to start of this word
                    # For simplicity, we just use the phonetic karaoke tag \k 
                    text_line += f"{{\\k{duration_cs}}}{word['punctuated_word']} "
                text_line = text_line.strip()

            elif caption_style.lower() == "popping":
                # Popping: Animate scale from 50 to 100 using {\t(start,end,\fscx100\fscy100)} per word
                # This requires calculating relative times for \t tags from the start of the line.
                line_start_ms = utterance['start'] * 1000
                text_line = ""
                for word in words:
                    start_ms = int((word['start'] * 1000) - line_start_ms)
                    end_ms = int((word['end'] * 1000) - line_start_ms)
                    pop_end_ms = start_ms + min(150, end_ms - start_ms) # Pop completes in 150ms or duration
                    
                    # Tag sequence: 
                    # 1. Reset scale to 0: {\fscx0\fscy0}
                    # 2. Time-based pop animation: {\t(start,pop_end,\fscx100\fscy100)}
                    text_line += f"{{\\fscx0\\fscy0\\t({start_ms},{pop_end_ms},\\fscx100\\fscy100)}}{word['punctuated_word']} "
                text_line = text_line.strip()

            else:
                # Standard
                text_line = utterance['transcript']
            
            # Write Dialogue Line
            lines.append(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text_line}\n")

        with open(ass_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
            
        return ass_path


    async def generate_srt(self, audio_path: str, caption_font: str = "Standard", caption_style: str = "standard") -> Optional[str]:
        """Backward compatible name, but now strictly returns ASS for styled capabilities"""
        if not self.api_key:
            print("No Deepgram API key found. Skipping captions.")
            return None
            
        print(f"Generating advanced {caption_style} captions for {audio_path}...")
        
        try:
            with open(audio_path, "rb") as audio_file:
                audio_data = audio_file.read()

            headers = {
                "Authorization": f"Token {self.api_key}",
                "Accept": "application/json"
            }

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    content=audio_data
                )

            if response.status_code == 200:
                data = response.json()
                utterances = data.get('results', {}).get('utterances', [])
                
                if not utterances:
                    return None
                    
                ass_path = self.generate_ass_file(utterances, caption_font, caption_style)
                print(f"ASS Captions generated successfully at {ass_path}")
                return ass_path
            else:
                print(f"Deepgram API Error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"Error during Deepgram transcription: {e}")
            return None

# Dependency accessor
deepgram_utility = DeepgramSTTUtility()

async def get_deepgram_stt() -> DeepgramSTTUtility:
    return deepgram_utility
