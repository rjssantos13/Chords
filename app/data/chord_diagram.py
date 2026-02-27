import json
import os
from pathlib import Path
from typing import Dict, Optional

import cairosvg
import fretboard


def get_diagram_cache_dir() -> Path:
    """Get the chord diagram cache directory."""
    from app.config import get_app_dir

    cache_dir = get_app_dir() / "chord_diagrams"
    if not cache_dir.exists():
        cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_chords_db_path() -> Path:
    """Get the chord database JSON path."""
    from app.config import get_app_dir

    db_path = get_app_dir() / "chords_db.json"
    if not db_path.exists():
        source_path = Path(__file__).parent.parent.parent / "Chords JSON database.txt"
        if source_path.exists():
            with open(source_path, "r") as f:
                data = json.load(f)
            with open(db_path, "w") as f:
                json.dump(data, f, indent=2)
    return db_path


def sanitize_chord_name(chord_name: str) -> str:
    """Sanitize chord name for use as filename."""
    result = chord_name.replace("/", "_")
    return result


def generate_chord_diagram(
    chord_name: str, output_dir: Optional[Path] = None
) -> Optional[str]:
    """Generate a chord diagram image.

    Args:
        chord_name: The chord name (e.g., "C", "Cmaj7", "C/E")
        output_dir: Directory to save the diagram (default: cache dir)

    Returns:
        Path to the generated PNG file, or None if failed
    """
    if output_dir is None:
        output_dir = get_diagram_cache_dir()

    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    sanitized = sanitize_chord_name(chord_name)
    png_path = output_dir / f"{sanitized}.png"

    if png_path.exists():
        return str(png_path)

    try:
        chord_data = get_chord_data(chord_name)
        if not chord_data:
            print(f"No chord data found for: {chord_name}")
            return None

        positions = chord_data.get("positions", [])
        if not positions:
            print(f"No positions found for: {chord_name}")
            return None

        pos = positions[0]
        frets = pos.get("frets", [])
        fingers = pos.get("fingers", [])

        frets_str = "".join([str(f) if f >= 0 else "x" for f in frets])
        fingers_str = "".join([str(f) if f > 0 else "-" for f in fingers])

        chord = fretboard.Chord(positions=frets_str, fingers=fingers_str)

        svg_path = output_dir / f"{sanitized}.svg"
        chord.save(str(svg_path))

        with open(svg_path, "rb") as f:
            svg_data = f.read()

        cairosvg.svg2png(bytestring=svg_data, write_to=str(png_path))

        if svg_path.exists():
            svg_path.unlink()

        return str(png_path)

    except Exception as e:
        print(f"Error generating diagram for {chord_name}: {e}")
        return None


def get_chord_data(chord_name: str) -> Optional[Dict]:
    """Get chord data from the JSON database.

    Args:
        chord_name: The chord name (e.g., "C", "Cmaj7", "C/E")

    Returns:
        Chord data dict or None if not found
    """
    db_path = get_chords_db_path()
    if not db_path.exists():
        return None

    with open(db_path, "r") as f:
        data = json.load(f)

    chords_db = data.get("chords", {})

    key, suffix = parse_chord_name(chord_name)

    if key not in chords_db:
        return None

    chord_list = chords_db[key]
    for chord in chord_list:
        if chord.get("suffix") == suffix:
            return chord

    return None


def parse_chord_name(chord_name: str) -> tuple:
    """Parse chord name into key and suffix.

    Args:
        chord_name: e.g., "Cmaj7", "C/E", "C#m"

    Returns:
        Tuple of (key, suffix) e.g., ("C", "maj7")
    """
    chord_name = chord_name.strip()

    key_map = {
        "C#": "Csharp",
        "F#": "Fsharp",
        "G#": "Gsharp",
    }

    suffix_map = {
        "m": "minor",
        "maj": "major",
        "maj7": "maj7",
        "maj9": "maj9",
        "maj11": "maj11",
        "maj13": "maj13",
        "dim": "dim",
        "dim7": "dim7",
        "aug": "aug",
        "aug7": "aug7",
        "sus2": "sus2",
        "sus4": "sus4",
        "7sus4": "7sus4",
    }

    if "/" in chord_name:
        parts = chord_name.split("/")
        key = parts[0]
        suffix = "/" + "/".join(parts[1:])
        # Extract just the root note from compound keys like "C7", "Cmaj7"
        root_notes = [
            "C",
            "C#",
            "Db",
            "D",
            "D#",
            "Eb",
            "E",
            "F",
            "F#",
            "Gb",
            "G",
            "G#",
            "Ab",
            "A",
            "A#",
            "Bb",
            "B",
        ]
        for root in root_notes:
            if key.startswith(root):
                key = root
                break
        key = key_map.get(key, key)
        return key, suffix

    keys = ["C#", "Bb", "Eb", "Ab", "F#", "C", "D", "E", "F", "G", "A", "B"]

    for key in keys:
        if chord_name.startswith(key):
            suffix = chord_name[len(key) :]
            if not suffix:
                suffix = "major"
            elif suffix in suffix_map:
                suffix = suffix_map[suffix]
            lookup_key = key_map.get(key, key)
            return lookup_key, suffix

    return chord_name, "major"


def generate_all_chord_diagrams(chord_names: list) -> Dict[str, str]:
    """Generate diagrams for a list of chord names.

    Args:
        chord_names: List of unique chord names

    Returns:
        Dictionary mapping chord names to diagram file paths
    """
    results = {}
    for chord_name in chord_names:
        if chord_name and chord_name != "N":
            path = generate_chord_diagram(chord_name)
            if path:
                results[chord_name] = path
    return results
