import json
import os
from pathlib import Path
from typing import Dict, Optional


APP_NAME = "chords_app"
DEFAULT_STORAGE_FOLDER = "downloads"


def get_app_dir() -> Path:
    """Get the application data directory."""
    home = Path.home()
    app_dir = home / f".{APP_NAME}"
    if not app_dir.exists():
        app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_config_path() -> Path:
    """Get the path to the config file."""
    return get_app_dir() / "config.json"


def get_songs_path() -> Path:
    """Get the path to the songs database."""
    return get_app_dir() / "songs.json"


def get_downloads_dir() -> Path:
    """Get the default downloads directory."""
    return get_app_dir() / DEFAULT_STORAGE_FOLDER


def load_config() -> Dict:
    """Load configuration from file."""
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)
    return get_default_config()


def get_default_config() -> Dict:
    """Get default configuration."""
    return {
        "storage_folder": str(get_downloads_dir()),
        "export_folder": str(get_downloads_dir()),
    }


def save_config(config: Dict) -> None:
    """Save configuration to file."""
    config_path = get_config_path()
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def get_storage_folder() -> Path:
    """Get the user's configured storage folder."""
    config = load_config()
    storage_path = Path(config.get("storage_folder", str(get_downloads_dir())))
    if not storage_path.exists():
        storage_path.mkdir(parents=True, exist_ok=True)
    return storage_path


def set_storage_folder(folder_path: str) -> None:
    """Set the storage folder in config."""
    config = load_config()
    config["storage_folder"] = folder_path
    save_config(config)


def get_export_folder() -> Path:
    """Get the user's configured export folder for JJazzLab files."""
    config = load_config()
    export_path = Path(config.get("export_folder", str(get_downloads_dir())))
    if not export_path.exists():
        export_path.mkdir(parents=True, exist_ok=True)
    return export_path


def set_export_folder(folder_path: str) -> None:
    """Set the export folder in config."""
    config = load_config()
    config["export_folder"] = folder_path
    save_config(config)


def ensure_storage_exists() -> Path:
    """Ensure the storage folder exists."""
    storage = get_storage_folder()
    if not storage.exists():
        storage.mkdir(parents=True, exist_ok=True)
    return storage
