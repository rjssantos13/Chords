from typing import Dict, List, Optional, Tuple, Union

import librosa
import numpy as np
from chord_extractor.extractors import Chordino


def extract_chords(song_file: str) -> List[Tuple[str, float]]:
    """Extract chord progression from an audio file.

    Args:
        song_file: Path to the audio file (MP3, WAV, etc.)

    Returns:
        List of tuples (chord, start_time)

    Raises:
        FileNotFoundError: If the audio file doesn't exist
    """
    print("Extracting chord progression...")

    chordino = Chordino(roll_on=1)
    song_chords = chordino.extract(song_file)

    print("Chord progression extraction complete")

    return song_chords


def get_tempo_and_time_signature(song_file: str) -> Dict:
    """Extract tempo and time signature from an audio file using librosa.

    Args:
        song_file: Path to the audio file

    Returns:
        Dictionary with 'tempo' (BPM) and 'time_signature'
    """
    try:
        y, sr = librosa.load(song_file, sr=None)

        try:
            tempo_result = librosa.beat.tempo(y=y, sr=sr)
            if isinstance(tempo_result, (list, tuple)):
                tempo = tempo_result[0]
            else:
                tempo = tempo_result

        except Exception:
            tempo = 120.0

        try:
            time_sig = librosa.beat.estimate_signature(y=y, sr=sr)
            time_signature = f"{time_sig[0]}/{time_sig[1]}"
        except Exception:
            time_signature = "4/4"

        return {
            "tempo": round(float(tempo), 1),
            "time_signature": time_signature,
        }
    except Exception as e:
        print(f"Error extracting tempo/time signature: {e}")
        return {
            "tempo": 120.0,
            "time_signature": "4/4",
        }


def extract_beats(song_file: str) -> List[float]:
    """Extract beat positions from an audio file using librosa.

    Args:
        song_file: Path to the audio file

    Returns:
        List of beat positions in seconds
    """
    try:
        y, sr = librosa.load(song_file, sr=None)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)

        beat_times = librosa.frames_to_time(beat_frames, sr=sr)

        return sorted(beat_times.tolist())
    except Exception as e:
        print(f"Error extracting beats: {e}")
        return []


def get_audio_duration(song_file: str) -> float:
    """Get the duration of an audio file.

    Args:
        song_file: Path to the audio file

    Returns:
        Duration in seconds
    """
    try:
        y, sr = librosa.load(song_file, sr=None)
        return float(librosa.get_duration(y=y, sr=sr))
    except Exception as e:
        print(f"Error getting audio duration: {e}")
        return 0.0


def align_chords_to_beats(
    chords: List[Dict], beats: List[float], audio_duration: float
) -> List[Dict]:
    """Align chords to beat positions and fill gaps.

    Args:
        chords: List of chord dictionaries with 'CHORD' and 'START'
        beats: List of beat positions in seconds
        audio_duration: Total duration of the audio in seconds

    Returns:
        List of chord dictionaries aligned to beats, one per beat
    """
    if not beats or not chords:
        return []

    beat_intervals = []
    for i in range(len(beats) - 1):
        beat_intervals.append((beats[i], beats[i + 1]))
    if beats:
        beat_intervals.append((beats[-1], audio_duration))

    avg_beat_length = np.mean(np.diff(beats)) if len(beats) > 1 else 0.5
    if avg_beat_length <= 0:
        avg_beat_length = 0.5

    first_beat = beats[0]

    # Calculate pre-beats from 0 to first detected beat
    if first_beat > 0:
        num_pre_beats = int(first_beat / avg_beat_length) + 1
    else:
        num_pre_beats = 0

    num_end_beats = (
        int((audio_duration - beats[-1]) / avg_beat_length)
        if beats[-1] < audio_duration
        else 0
    )

    aligned_beats = []

    chord_map = {}
    for chord_data in chords:
        chord_start = chord_data.get("START", 0)
        chord_name = chord_data.get("CHORD", "N")
        chord_map[chord_start] = chord_name

    sorted_chord_starts = sorted(chord_map.keys())

    # Handle pre-beats (before first detected beat)
    for i in range(num_pre_beats):
        pre_beat_time = i * avg_beat_length
        if pre_beat_time >= first_beat:
            break
        # Assign chord based on midpoint of pre-beat
        beat_midpoint = pre_beat_time + avg_beat_length / 2
        assigned_chord = "N"
        for chord_start in sorted_chord_starts:
            if chord_start <= beat_midpoint:
                assigned_chord = chord_map[chord_start]
            else:
                break
        aligned_beats.append(
            {
                "beat_index": len(aligned_beats),
                "start_time": round(pre_beat_time, 3),
                "chord": assigned_chord,
                "source_beat": None,
            }
        )

    for i, (beat_start, beat_end) in enumerate(beat_intervals):
        beat_midpoint = (beat_start + beat_end) / 2

        assigned_chord = "N"
        for chord_start in sorted_chord_starts:
            if chord_start <= beat_midpoint:
                assigned_chord = chord_map[chord_start]
            else:
                break

        aligned_beats.append(
            {
                "beat_index": len(aligned_beats),
                "start_time": round(beat_start, 3),
                "chord": assigned_chord,
                "source_beat": i,
            }
        )

    if num_end_beats > 0:
        last_beat_time = beats[-1] if beats else audio_duration
        last_chord = aligned_beats[-1]["chord"] if aligned_beats else "N"
        for i in range(num_end_beats):
            end_beat_time = last_beat_time + (i + 1) * avg_beat_length
            if end_beat_time < audio_duration:
                aligned_beats.append(
                    {
                        "beat_index": len(aligned_beats),
                        "start_time": round(end_beat_time, 3),
                        "chord": last_chord,
                        "source_beat": None,
                    }
                )

    return aligned_beats


def get_chord_dict(
    song_file: str, include_no_chord: bool = False
) -> List[Dict[str, Union[str, float]]]:
    """Extract chords and return as a list of dictionaries.

    Args:
        song_file: Path to the audio file
        include_no_chord: If False, exclude 'N' (no chord) entries

    Returns:
        List of dictionaries with keys 'CHORD' and 'START'
    """
    chords = extract_chords(song_file)

    if include_no_chord:
        return [{"CHORD": chord, "START": round(start, 2)} for chord, start in chords]

    return [
        {"CHORD": chord, "START": round(start, 2)}
        for chord, start in chords
        if chord != "N"
    ]


def main() -> None:
    audio_file = "/home/ron/Music/Audio/Danny Daniel - Que Yo Te Quiero.mp3"

    chord_dict = get_chord_dict(audio_file)
    print(chord_dict)

    audio_info = get_tempo_and_time_signature(audio_file)
    print(audio_info)


if __name__ == "__main__":
    main()
