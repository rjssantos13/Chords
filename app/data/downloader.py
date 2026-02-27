import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

import yt_dlp
from youtube_search import YoutubeSearch


def search_youtube(query: str, limit: int = 10) -> List[Dict]:
    """Search for videos on YouTube.

    Args:
        query: Search query string
        limit: Maximum number of results

    Returns:
        List of dictionaries with video info (title, link.)
    """
    search = YoutubeSearch(query, max_results=limit)
    results = search.to_dict()
    return results


def download_youtube_audio(
    url: str, output_folder: Path, progress_callback: Optional[callable] = None
) -> Optional[str]:
    """Download audio from YouTube video as MP3.

    Args:
        url: YouTube video URL
        output_folder: Directory to save the audio file
        progress_callback: Optional callback for progress updates

    Returns:
        Path to the downloaded MP3 file, or None if failed
    """
    if isinstance(output_folder, str):
        output_folder = Path(output_folder)

    if not output_folder.exists():
        output_folder.mkdir(parents=True, exist_ok=True)

    filename = "audio"
    filepath = os.path.join(str(output_folder), filename)

    cmd = [
        "yt-dlp",
        url,
        "-f",
        "bestaudio/best",
        "--extract-audio",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "192",
        "-o",
        os.path.join(str(output_folder), f"{filename}.%(ext)s"),
    ]

    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        out_lines = []

        for line in iter(proc.stdout.readline, ""):
            out_lines.append(line)
            if progress_callback:
                m = re.search(r"(\d{1,3}(?:\.\d+)?)%", line)
                if m:
                    try:
                        progress = float(m.group(1)) / 100.0
                        progress_callback("downloading", progress)
                    except Exception:
                        pass

        proc.stdout.close()
        proc.wait()

        if proc.returncode != 0:
            error_msg = "".join(out_lines)
            print(f"Download error: {error_msg}")
            return None

        mp3_file = os.path.join(str(output_folder), f"{filename}.mp3")
        if os.path.exists(mp3_file):
            return mp3_file

        for f in os.listdir(str(output_folder)):
            if f.endswith(".mp3"):
                return os.path.join(str(output_folder), f)

        return None

    except Exception as e:
        print(f"Download error: {e}")
        return None


def get_youtube_video_title(url: str) -> Optional[str]:
    """Get the title of a YouTube video.

    Args:
        url: YouTube video URL

    Returns:
        Video title or None if failed
    """
    ydl_opts = {
        "format": "bestaudio/best",
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("title")
    except Exception:
        return None
