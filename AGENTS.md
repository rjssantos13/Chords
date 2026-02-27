# AGENTS.md - Chords Project

## Overview
A Python Kivy application for extracting and visualizing chord progressions from audio files (local or YouTube).

## Environment
- Python: 3.9.25
- Virtual Environment: `.venv39/`
- Dependencies: chord_extractor, librosa, numpy, scipy, soundfile, kivy, youtube-search, yt-dlp, just-playback

## Project Structure
```
Chords/
├── main.py                    # Entry point (runs the Kivy app)
├── chords.py                  # Chord extraction module
├── app/
│   ├── __init__.py
│   ├── main.py               # Kivy App class
│   ├── config.py             # App settings storage
│   ├── screens/
│   │   ├── __init__.py
│   │   ├── home_screen.py    # Song list screen
│   │   ├── add_song_screen.py # Local/YouTube song addition
│   │   ├── settings_screen.py # Storage folder settings
│   │   └── player_screen.py   # Chord grid player
│   ├── widgets/
│   │   └── __init__.py
│   └── data/
│       ├── __init__.py
│       ├── storage.py         # JSON persistence
│       └── downloader.py     # YouTube download
├── .venv39/                  # Virtual environment
└── AGENTS.md                 # This file
```

## Data Storage
- App config: `~/.chords_app/config.json`
- Songs database: `~/.chords_app/songs.json`
- Audio files: `~/.chords_app/downloads/` (configurable in Settings)

## Running the Application

### Prerequisites
The app requires a display (X11/Wayland) to run:
```bash
# On headless servers, use xvfb-run
xvfb-run python main.py

# On desktop with display
python main.py
```

### Development
```bash
# Activate virtual environment
source .venv39/bin/activate

# Run main.py (requires display)
python main.py
```

## Dependencies
- **kivy**: UI framework
- **youtube-search**: YouTube search without API key
- **yt-dlp**: YouTube audio download
- **just-playback**: Audio playback with position tracking
- **chord_extractor**: Chord extraction (Chordino algorithm)

Install all dependencies:
```bash
pip install kivy youtube-search yt-dlp just-playback
```

## Build/Lint/Test Commands

### Running the Application
```bash
# Activate virtual environment
source .venv39/bin/activate

# Run main.py
python main.py
```

### Running Tests
This project does not currently have tests configured. If tests are added:
```bash
# Run all tests
pytest

# Run a single test file
pytest tests/test_specific.py

# Run a single test function
pytest tests/test_specific.py::test_function_name

# Run tests matching a pattern
pytest -k "test_pattern"
```

### Linting
This project does not currently have linting configured. Recommended tools:
```bash
# Install linting tools
pip install ruff black mypy

# Run ruff (fast linter)
ruff check .

# Run ruff with auto-fix
ruff check --fix .

# Run black (formatter)
black .

# Run mypy (type checker)
mypy .

# Run all linters
ruff check . && black --check . && mypy .
```

### Type Checking
```bash
mypy .
```

## Code Style Guidelines

### General Principles
- Follow PEP 8 style guide
- Keep lines under 100 characters
- Use 4 spaces for indentation (no tabs)
- Use descriptive variable and function names

### Imports
- Standard library imports first
- Third-party imports second
- Local imports last
- Separate each group with a blank line
- Use explicit relative imports for local modules

```python
# Correct order
import os
import sys
from typing import Dict, List, Optional

import numpy as np
from chord_extractor.extractors import Chordino

from my_module import my_function
```

### Formatting
- Use Black for automatic formatting
- Add spaces around operators: `a + b`, not `a+b`
- Use spaces after commas: `func(a, b, c)`
- No trailing whitespace
- One blank line between top-level definitions

### Types
- Use type hints for all function arguments and return values
- Use `Optional[X]` instead of `Union[X, None]`
- Use concrete types when possible: `list` instead of `Iterable`

```python
def process_chords(chords: List[tuple], threshold: float) -> Dict[str, float]:
    """Process chord data with type hints."""
    result: Dict[str, float] = {}
    return result
```

### Naming Conventions
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private functions/variables: prefix with underscore

```python
MAX_CHORD_DURATION = 10.0  # constant

class ChordExtractor:  # class
    def __init__(self):
        self._private_var = None

    def extract_chords(self, file_path: str) -> List[str]:  # method
        pass
```

### Error Handling
- Use specific exceptions
- Always include meaningful error messages
- Use try/except sparingly and specifically

```python
# Good
try:
    result = chordino.extract(audio_file)
except FileNotFoundError as e:
    raise ChordExtractionError(f"Could not find audio file: {audio_file}") from e
```

### Documentation
- Use docstrings for all public functions and classes
- Follow Google-style or NumPy-style docstrings
- Include type hints in docstrings when not obvious

```python
def extract_chords(song_file: str) -> List[tuple]:
    """Extract chord progression from an audio file.

    Args:
        song_file: Path to the audio file (MP3, WAV, etc.)

    Returns:
        List of tuples (chord, start_time)

    Raises:
        ChordExtractionError: If extraction fails
    """
```

### Testing (when added)
- Place tests in `tests/` directory
- Use `pytest` as test runner
- Name test files `test_<module>.py`
- Name test functions `test_<description>`

```python
def test_extract_chords_valid_file():
    """Test chord extraction with valid audio file."""
    result = extract_chords("test_audio.mp3")
    assert len(result) > 0
```

### Project Structure
```
Chords/
├── main.py              # Entry point
├── chords.py            # Chord extraction module
├── app/
│   ├── __init__.py
│   ├── main.py         # Kivy App class
│   ├── config.py       # Settings storage
│   ├── screens/
│   │   ├── home_screen.py
│   │   ├── add_song_screen.py
│   │   ├── settings_screen.py
│   │   └── player_screen.py
│   ├── widgets/
│   │   └── __init__.py
│   └── data/
│       ├── storage.py
│       └── downloader.py
├── tests/               # Test files (when added)
│   └── test_main.py
├── .venv39/             # Virtual environment
└── AGENTS.md            # This file
```

### Dependencies
- Pin dependency versions in requirements.txt or pyproject.toml
- Keep dependencies minimal

### Git Practices
- Make meaningful commit messages
- Create feature branches for new features
- Run linters before committing
