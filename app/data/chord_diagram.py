import json
import os
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional

import cairosvg
import fretboard

from app.data.chord_defaults import (
    get_default_version,
    get_chord_defaults_path,
    load_defaults,
    save_defaults,
    set_default_version,
)


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
    chord_name: str,
    output_dir: Optional[Path] = None,
    version: Optional[int] = None,
) -> Optional[str]:
    """Generate a chord diagram image.

    Args:
        chord_name: The chord name (e.g., "C", "Cmaj7", "C/E")
        output_dir: Directory to save the diagram (default: cache dir)
        version: Specific version to use (1-indexed). If None, uses default.

    Returns:
        Path to the generated PNG file, or None if failed
    """
    if output_dir is None:
        output_dir = get_diagram_cache_dir()

    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    sanitized = sanitize_chord_name(chord_name)

    # Determine which version to use
    if version is None:
        version = get_default_version(chord_name)

    # Use version in filename
    png_path = output_dir / f"{sanitized}_v{version}.png"

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

        # Use specified version or default (1-indexed, convert to 0-indexed)
        version = version if version is not None else 1
        pos_index = version - 1 if version > 0 else 0
        if pos_index >= len(positions):
            pos_index = 0  # Fallback to first position if version not found

        pos = positions[pos_index]
        frets = pos.get("frets", [])
        fingers = pos.get("fingers", [])
        base_fret = pos.get("baseFret", 1)

        # Do NOT adjust frets - they are already relative to the nut
        # baseFret just tells us which fret to start the diagram from
        adjusted_frets = frets  # frets are already correct

        # Create a custom style for the desired size
        custom_style = {
            "drawing": {
                "height": 150,
                "width": 150,
                "font_size": 11,
                "spacing": 15,
            },
            "string": {
                "size": 2,
            },
            "nut": {
                "size": 5,
            },
            "fret": {
                "size": 1,
            },
            "marker": {
                "radius": 7,
                "stroke_width": 1,
            },
        }

        frets_str = "".join([str(f) if f >= 0 else "x" for f in adjusted_frets])
        fingers_str = "".join([str(f) if f > 0 else "-" for f in fingers])

        chord = fretboard.Chord(
            positions=frets_str, fingers=fingers_str, style=custom_style
        )

        # Create the fretboard first (needed to initialize style)
        chord.draw()

        # If base_fret > 1, create a custom fretboard that shows the base fret indicator
        if base_fret > 1:
            # Fretboard frets parameter: (start, end) where start is displayed as "start fr"
            # The Fretboard internally subtracts 1, so pass (base_fret + 1, base_fret + 5)
            chord.fretboard = fretboard.Fretboard(
                strings=6, frets=(base_fret + 1, base_fret + 5), style=chord.style
            )
            # Add markers - the original frets are relative to nut, add base_fret - 1 to get
            # position on the custom fretboard which starts at base_fret
            for i, (fret, finger) in enumerate(zip(frets, fingers)):
                if fret > 0:
                    # Position on custom fretboard = original fret + base_fret - 1
                    display_fret = fret + base_fret - 1
                    if display_fret >= base_fret:
                        finger_char = str(finger) if finger > 0 else None
                        chord.fretboard.add_marker(
                            string=i, fret=display_fret, label=finger_char
                        )
            # Call draw() to render the fret labels on the custom fretboard
            chord.fretboard.draw()

        svg_path = output_dir / f"{sanitized}_v{version}.svg"

        # Use fretboard.render directly to avoid chord.draw() being called again
        # which would overwrite our custom fretboard
        output = StringIO()
        chord.fretboard.render(output)
        with open(svg_path, "w") as f:
            f.write(output.getvalue())

        with open(svg_path, "rb") as f:
            svg_data = f.read()

        cairosvg.svg2png(bytestring=svg_data, write_to=str(png_path))

        if svg_path.exists():
            svg_path.unlink()

        return str(png_path)

    except Exception as e:
        print(f"Error generating diagram for {chord_name}: {e}")
        return None


def generate_chord_diagram_for_version(
    chord_name: str,
    version: int,
    output_dir: Optional[Path] = None,
) -> Optional[str]:
    """Generate a chord diagram for a specific version.

    Args:
        chord_name: The chord name (e.g., "C", "Cmaj7")
        version: Specific version to use (1-indexed)
        output_dir: Directory to save the diagram (default: cache dir)

    Returns:
        Path to the generated PNG file, or None if failed
    """
    return generate_chord_diagram(chord_name, output_dir, version)


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

    base_suffix = suffix.split("/")[0] if "/" in suffix else suffix
    for chord in chord_list:
        if chord.get("suffix") == base_suffix:
            return chord

    return None


def parse_chord_name(chord_name: str) -> tuple:
    """Parse chord name into key and suffix.

    Args:
        chord_name: e.g., "Cmaj7", "C/E", "C#m", "Bm7b5/A"

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
        "m7": "m7",
        "m9": "m9",
        "m11": "m11",
        "m6": "m6",
        "m7b5": "m7b5",
        "7": "7",
        "9": "9",
        "11": "11",
        "13": "13",
        "6": "6",
        "add9": "add9",
        "add11": "add11",
        "sus": "sus",
    }

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

    bass_note = None
    main_chord = chord_name

    if "/" in chord_name:
        parts = chord_name.split("/", 1)
        main_chord = parts[0]
        bass_note = parts[1]

    keys = ["C#", "Db", "Bb", "Eb", "Ab", "F#", "C", "D", "E", "F", "G", "A", "B"]

    key = None
    suffix = "major"

    for k in keys:
        if main_chord.startswith(k):
            key = k
            suffix = main_chord[len(k) :]
            break

    if key is None:
        return chord_name, "major"

    if not suffix:
        suffix = "major"
    elif suffix in suffix_map:
        suffix = suffix_map[suffix]
    elif suffix.startswith("m"):
        for suff in sorted(suffix_map.keys(), key=len, reverse=True):
            if suffix == suff or suffix.startswith(suff):
                suffix = suffix_map[suff]
                break

    if bass_note:
        suffix = suffix + "/" + bass_note

    lookup_key = key_map.get(key, key)
    return lookup_key, suffix


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


def generate_all_chord_diagrams_with_versions(
    chord_names: list,
) -> Dict[str, List[str]]:
    """Generate diagrams for all versions of chord names.

    Args:
        chord_names: List of unique chord names

    Returns:
        Dictionary mapping chord names to list of diagram file paths (one per version)
    """
    results = {}
    for chord_name in chord_names:
        if chord_name and chord_name != "N":
            versions = get_chord_versions_count(chord_name)
            paths = []
            for v in range(1, versions + 1):
                path = generate_chord_diagram(chord_name, version=v)
                if path:
                    paths.append(path)
            if paths:
                results[chord_name] = paths
    return results


def get_chord_versions_count(chord_name: str) -> int:
    """Get the number of available versions for a chord.

    Args:
        chord_name: The chord name (e.g., "C", "Cmaj7")

    Returns:
        Number of available versions
    """
    chord_data = get_chord_data(chord_name)
    if not chord_data:
        return 0
    return len(chord_data.get("positions", []))
