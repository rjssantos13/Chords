import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.config import get_songs_path


class Song:
    """Represents a song with its chords."""

    def __init__(
        self,
        name: str,
        source: str,
        file_path: str,
        chords: List[Dict],
        duration: float,
        youtube_url: Optional[str] = None,
        song_id: Optional[str] = None,
        created_at: Optional[str] = None,
        tempo: Optional[float] = None,
        time_signature: Optional[str] = None,
    ):
        self.id = song_id or str(uuid.uuid4())
        self.name = name
        self.source = source
        self.file_path = file_path
        self.youtube_url = youtube_url
        self.chords = chords
        self.duration = duration
        self.created_at = created_at or datetime.now().isoformat()
        self.tempo = tempo
        self.time_signature = time_signature

    def to_dict(self) -> Dict:
        """Convert song to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "source": self.source,
            "file_path": self.file_path,
            "youtube_url": self.youtube_url,
            "chords": self.chords,
            "duration": self.duration,
            "created_at": self.created_at,
            "tempo": self.tempo,
            "time_signature": self.time_signature,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Song":
        """Create song from dictionary."""
        return cls(
            song_id=data.get("id"),
            name=data["name"],
            source=data["source"],
            file_path=data["file_path"],
            youtube_url=data.get("youtube_url"),
            chords=data["chords"],
            duration=data["duration"],
            created_at=data.get("created_at"),
            tempo=data.get("tempo"),
            time_signature=data.get("time_signature"),
        )


def load_songs() -> List[Song]:
    """Load all songs from storage."""
    songs_path = get_songs_path()
    if not songs_path.exists():
        return []

    with open(songs_path, "r") as f:
        data = json.load(f)
        songs_list = data.get("songs", [])
        return [Song.from_dict(song_data) for song_data in songs_list]


def save_song(song: Song) -> None:
    """Save a new song to storage."""
    songs = load_songs()
    songs.append(song)
    save_all_songs(songs)


def delete_song(song_id: str) -> None:
    """Delete a song from storage."""
    songs = load_songs()
    songs = [s for s in songs if s.id != song_id]
    save_all_songs(songs)


def update_song_chords(song_id: str, chords: List[Dict]) -> None:
    """Update a song's chords in storage."""
    songs = load_songs()
    for song in songs:
        if song.id == song_id:
            song.chords = chords
            break
    save_all_songs(songs)


def save_all_songs(songs: List[Song]) -> None:
    """Save all songs to storage."""
    songs_path = get_songs_path()
    data = {"songs": [song.to_dict() for song in songs]}
    with open(songs_path, "w") as f:
        json.dump(data, f, indent=2)


def get_song_by_id(song_id: str) -> Optional[Song]:
    """Get a song by its ID."""
    songs = load_songs()
    for song in songs:
        if song.id == song_id:
            return song
    return None


def regenerate_missing_diagrams() -> tuple:
    """Regenerate missing chord diagrams for all songs.

    Returns:
        Tuple of (songs_updated, diagrams_generated)
    """
    from app.data.chord_diagram import generate_all_chord_diagrams

    songs = load_songs()
    songs_updated = 0
    diagrams_generated = 0

    for song in songs:
        missing_chords = set()
        for chord in song.chords:
            chord_name = chord.get("CHORD")
            if chord_name and chord_name != "N":
                if not chord.get("DIAGRAM"):
                    missing_chords.add(chord_name)

        if missing_chords:
            diagram_paths = generate_all_chord_diagrams(list(missing_chords))
            for chord in song.chords:
                chord_name = chord.get("CHORD")
                if chord_name and chord_name in diagram_paths:
                    if not chord.get("DIAGRAM"):
                        chord["DIAGRAM"] = diagram_paths[chord_name]
                        diagrams_generated += 1

            update_song_chords(song.id, song.chords)
            songs_updated += 1

    return songs_updated, diagrams_generated
