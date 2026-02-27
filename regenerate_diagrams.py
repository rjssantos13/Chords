#!/usr/bin/env python
"""Script to regenerate missing chord diagrams for all songs."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.storage import regenerate_missing_diagrams

if __name__ == "__main__":
    print("Regenerating missing chord diagrams...")
    songs_updated, diagrams_generated = regenerate_missing_diagrams()
    print(
        f"Done! Updated {songs_updated} songs, generated {diagrams_generated} diagrams."
    )
