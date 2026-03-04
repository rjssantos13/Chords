import json
from pathlib import Path
from typing import Dict, List, Optional


def get_chord_defaults_path() -> Path:
    """Get the path to the chord defaults file."""
    from app.config import get_app_dir

    return get_app_dir() / "chord_defaults.json"


def load_defaults() -> Dict[str, int]:
    """Load chord defaults from file.

    Returns:
        Dictionary mapping chord names to default versions (1-indexed)
    """
    defaults_path = get_chord_defaults_path()
    if defaults_path.exists():
        with open(defaults_path, "r") as f:
            return json.load(f)
    return {}


def save_defaults(defaults: Dict[str, int]) -> None:
    """Save chord defaults to file.

    Args:
        defaults: Dictionary mapping chord names to default versions
    """
    defaults_path = get_chord_defaults_path()
    with open(defaults_path, "w") as f:
        json.dump(defaults, f, indent=2)


def get_default_version(chord_name: str) -> int:
    """Get the default version for a chord.

    Args:
        chord_name: The chord name (e.g., "C", "Cmaj7")

    Returns:
        Default version (1-indexed), defaults to 1 if not set
    """
    defaults = load_defaults()
    return defaults.get(chord_name, 1)


def set_default_version(chord_name: str, version: int) -> None:
    """Set the default version for a chord.

    Args:
        chord_name: The chord name (e.g., "C", "Cmaj7")
        version: The version to set as default (1-indexed)
    """
    defaults = load_defaults()
    defaults[chord_name] = version
    save_defaults(defaults)


def get_all_chords_with_defaults() -> Dict[str, int]:
    """Get all chords that have defaults set.

    Returns:
        Dictionary mapping chord names to default versions
    """
    return load_defaults()


def get_all_available_chords() -> List[str]:
    """Get all chord names available in the chord database.

    Returns:
        List of chord names
    """
    from app.data.chord_diagram import get_chords_db_path, parse_chord_name

    db_path = get_chords_db_path()
    if not db_path.exists():
        return []

    with open(db_path, "r") as f:
        data = json.load(f)

    chords = []
    chords_db = data.get("chords", {})

    for key, chord_list in chords_db.items():
        for chord in chord_list:
            suffix = chord.get("suffix", "")
            # Convert suffix back to display format
            display_suffix = suffix
            if suffix == "major":
                display_suffix = ""
            elif suffix == "minor":
                display_suffix = "m"
            elif suffix == "dim7":
                display_suffix = "dim7"
            elif suffix == "sus2sus4":
                display_suffix = "sus2sus4"
            elif suffix == "7sus4":
                display_suffix = "7sus4"

            # Convert key back to display format
            display_key = key
            key_display_map = {
                "Csharp": "C#",
                "Dsharp": "D#",
                "Fsharp": "F#",
                "Gsharp": "G#",
                "Asharp": "A#",
            }
            if key in key_display_map:
                display_key = key_display_map[key]

            if display_suffix:
                chord_name = f"{display_key}{display_suffix}"
            else:
                chord_name = display_key

            chords.append(chord_name)

    return sorted(set(chords))


def get_chord_versions(chord_name: str) -> List[Dict]:
    """Get all available versions for a chord.

    Args:
        chord_name: The chord name (e.g., "C", "Cmaj7")

    Returns:
        List of dicts with version info, each containing:
        - version: 1-indexed version number
        - frets: list of fret positions
        - fingers: list of finger positions
    """
    from app.data.chord_diagram import get_chord_data

    chord_data = get_chord_data(chord_name)
    if not chord_data:
        return []

    positions = chord_data.get("positions", [])
    versions = []
    for i, pos in enumerate(positions):
        versions.append(
            {
                "version": i + 1,
                "frets": pos.get("frets", []),
                "fingers": pos.get("fingers", []),
                "baseFret": pos.get("baseFret", 1),
            }
        )

    return versions


def generate_all_version_diagrams(chord_name: str) -> List[str]:
    """Generate diagrams for all versions of a chord.

    Args:
        chord_name: The chord name (e.g., "C", "Cmaj7")

    Returns:
        List of paths to generated diagram files
    """
    from app.data.chord_diagram import generate_chord_diagram_for_version

    versions = get_chord_versions(chord_name)
    paths = []
    for v in versions:
        path = generate_chord_diagram_for_version(chord_name, v["version"])
        if path:
            paths.append(path)

    return paths
