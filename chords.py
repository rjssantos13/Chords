from typing import Dict, List, Optional, Tuple, Union

import librosa
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
