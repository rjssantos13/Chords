import os
import tempfile
import threading
from pathlib import Path
from typing import Dict, List, Optional

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from app.config import get_storage_folder, ensure_storage_exists
from app.data.downloader import download_youtube_audio, search_youtube
from app.data.storage import Song, save_song
from chords import get_chord_dict, get_tempo_and_time_signature
from app.data.chord_diagram import generate_all_chord_diagrams
from app.data.chord_defaults import get_default_version


class YouTubeSearchResult(BoxLayout):
    """Widget for displaying a YouTube search result."""

    def __init__(self, result: Dict, select_callback, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = 160
        self.padding = 10
        self.spacing = 10

        self.result = result
        self.select_callback = select_callback

        thumbnails = result.get("thumbnails", [])
        thumbnail_url = thumbnails[0] if thumbnails else ""

        self.thumbnail = AsyncImage(
            source=thumbnail_url,
            size_hint_x=None,
            size_hint_y=None,
            width=160,
            height=160,
            allow_stretch=True,
            keep_ratio=False,
        )
        self.add_widget(self.thumbnail)

        info_layout = GridLayout(
            cols=1,
            size_hint_x=1,
            padding=(5, 10),
            row_force_default=True,
            row_default_height=40,
        )
        info_layout.bind(minimum_height=info_layout.setter("height"))
        self.add_widget(info_layout)

        title_label = Label(
            text=result.get("title", "Unknown"),
            size_hint_y=None,
            size_hint_x=None,
            width=280,
            halign="center",
            valign="top",
            text_size=(280, 40),
        )
        info_layout.add_widget(title_label)

        channel_label = Label(
            text=result.get("channel", "Unknown"),
            size_hint_y=None,
            size_hint_x=None,
            width=280,
            height=30,
            halign="center",
            valign="middle",
            text_size=(280, 30),
            color=(0.7, 0.7, 0.7, 1),
        )
        info_layout.add_widget(channel_label)

        duration_label = Label(
            text=result.get("duration", "N/A"),
            size_hint_y=None,
            size_hint_x=None,
            width=280,
            height=30,
            halign="center",
            valign="middle",
            text_size=(280, 30),
            color=(0.7, 0.7, 0.7, 1),
        )
        info_layout.add_widget(duration_label)

        select_btn = Button(text="Select", size_hint_x=0.2, size_hint_y=None, height=50)
        select_btn.bind(on_press=self.on_select_pressed)
        self.add_widget(select_btn)

    def on_select_pressed(self, instance):
        """Handle select button press."""
        if self.select_callback:
            self.select_callback(self.result)


class AddSongScreen(Screen):
    """Screen for adding a new song from local file or YouTube."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation="vertical", padding=20, spacing=10)
        self.add_widget(self.layout)

        title = Label(text="Add Song", size_hint_y=None, height=50)
        self.layout.add_widget(title)

        self.tabs = BoxLayout(orientation="horizontal", size_hint_y=None, height=50)
        self.layout.add_widget(self.tabs)

        self.local_btn = Button(text="Local File", on_press=self.show_local_tab)
        self.tabs.add_widget(self.local_btn)

        self.youtube_btn = Button(text="YouTube", on_press=self.show_youtube_tab)
        self.tabs.add_widget(self.youtube_btn)

        self.content_container = BoxLayout()
        self.layout.add_widget(self.content_container)

        self.local_container = None
        self.youtube_container = None
        self.current_container = None

        back_btn = Button(text="Back to Home", size_hint_y=None, height=50)
        back_btn.bind(on_press=self.go_home)
        self.layout.add_widget(back_btn)

    def on_enter(self):
        """Called when entering this screen."""
        self.show_local_tab(None)

    def show_local_tab(self, instance):
        """Show the local file tab."""
        self.clear_content_container()

        self.local_container = BoxLayout(orientation="vertical", spacing=10)

        header = Label(
            text="Select an audio file or zip from your computer",
            size_hint_y=None,
            height=40,
        )
        self.local_container.add_widget(header)

        self.file_chooser = FileChooserListView(
            path=str(Path.home() / "Music"),
            filters=[
                lambda folder, filename: filename.endswith(
                    (".mp3", ".wav", ".flac", ".zip")
                )
            ],
        )
        self.local_container.add_widget(self.file_chooser)

        btn_row = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=50, spacing=10
        )
        self.local_container.add_widget(btn_row)

        select_btn = Button(text="Extract Chords")
        select_btn.bind(on_press=self.on_local_file_selected)
        btn_row.add_widget(select_btn)

        self.content_container.add_widget(self.local_container)
        self.current_container = self.local_container

    def show_youtube_tab(self, instance):
        """Show the YouTube tab."""
        self.clear_content_container()

        self.youtube_container = BoxLayout(orientation="vertical", spacing=10)

        header = Label(text="Search for a song on YouTube", size_hint_y=None, height=40)
        self.youtube_container.add_widget(header)

        search_row = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=50, spacing=10
        )
        self.youtube_container.add_widget(search_row)

        self.search_input = TextInput(
            hint_text="Enter song name...",
            size_hint_x=0.7,
            multiline=False,
            write_tab=False,
        )
        self.search_input.bind(on_text_validate=self.on_search_pressed)
        search_row.add_widget(self.search_input)

        search_btn = Button(text="Search", size_hint_x=0.3)
        search_btn.bind(on_press=self.on_search_pressed)
        search_row.add_widget(search_btn)

        self.search_results_container = ScrollView()
        self.search_results_list = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=5
        )
        self.search_results_list.bind(
            minimum_height=self.search_results_list.setter("height")
        )
        self.search_results_container.add_widget(self.search_results_list)
        self.youtube_container.add_widget(self.search_results_container)

        self.download_status = Label(text="", size_hint_y=None, height=40)
        self.youtube_container.add_widget(self.download_status)

        self.content_container.add_widget(self.youtube_container)
        self.current_container = self.youtube_container

    def clear_content_container(self):
        """Clear the content container."""
        if self.current_container:
            self.content_container.remove_widget(self.current_container)
        self.current_container = None

    def on_local_file_selected(self, instance):
        """Handle local file selection and chord extraction."""
        selection = self.file_chooser.selection
        if not selection:
            return

        file_path = selection[0]
        if not os.path.exists(file_path):
            return

        if file_path.endswith(".zip"):
            temp_dir = Path(tempfile.mkdtemp())
            try:
                import zipfile

                with zipfile.ZipFile(file_path, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)
                for mp3_file in temp_dir.rglob("*.mp3"):
                    file_path = str(mp3_file)
                    break
                else:
                    for audio_file in temp_dir.rglob("*.wav"):
                        file_path = str(audio_file)
                        break
                    else:
                        for audio_file in temp_dir.rglob("*.flac"):
                            file_path = str(audio_file)
                            break
            except Exception as e:
                print(f"Error extracting zip: {e}")
                return

        name_input = SongNameDialog(file_path, on_save=self.process_local_file)
        name_input.open()

    def process_local_file(self, instance, name: str, file_path: str):
        """Process the local file and extract chords."""
        try:
            chords = get_chord_dict(file_path)

            unique_chord_names = list(
                set(c["CHORD"] for c in chords if c.get("CHORD") and c["CHORD"] != "N")
            )
            diagram_paths = generate_all_chord_diagrams(unique_chord_names)

            for chord in chords:
                chord_name = chord.get("CHORD")
                if chord_name and chord_name in diagram_paths:
                    chord["DIAGRAM"] = diagram_paths[chord_name]
                    # Store the version used (default version)
                    version = get_default_version(chord_name)
                    chord["VERSION"] = version

            storage_folder = ensure_storage_exists()
            file_name = os.path.basename(file_path)
            dest_path = storage_folder / file_name
            import shutil

            shutil.copy(file_path, dest_path)

            duration = 0.0
            if chords:
                duration = max(c["START"] for c in chords)

            audio_info = get_tempo_and_time_signature(str(dest_path))

            song = Song(
                name=name,
                source="local",
                file_path=str(dest_path),
                chords=chords,
                duration=duration,
                tempo=audio_info.get("tempo"),
                time_signature=audio_info.get("time_signature"),
            )
            save_song(song)
            self.go_home(None)
        except Exception as e:
            print(f"Error processing file: {e}")

    def on_search_pressed(self, instance):
        """Handle YouTube search."""
        query = self.search_input.text.strip()
        if not query:
            return

        self.download_status.text = "Searching..."

        thread = threading.Thread(target=self.perform_youtube_search, args=(query,))
        thread.start()

    def perform_youtube_search(self, query: str):
        """Perform YouTube search in background thread."""
        try:
            results = search_youtube(query)
            Clock.schedule_once(lambda dt: self.display_search_results(results))
        except Exception as e:
            error_msg = str(e)
            Clock.schedule_once(
                lambda dt, msg=error_msg: setattr(
                    self.download_status, "text", f"Error: {msg}"
                )
            )

    def display_search_results(self, results: List[Dict]):
        """Display YouTube search results."""
        self.search_results_list.clear_widgets()
        self.download_status.text = f"Found {len(results)} results"

        for result in results:
            item = YouTubeSearchResult(result, select_callback=self.on_youtube_selected)
            self.search_results_list.add_widget(item)

    def on_youtube_selected(self, result: Dict):
        """Handle YouTube video selection."""
        url_suffix = result.get("url_suffix", "")
        url = f"https://www.youtube.com{url_suffix}"
        title = result.get("title", "Unknown")

        def handle_save(inst, name):
            self.download_youtube(url, name)

        name_input = YouTubeNameDialog(title, on_save=handle_save)
        name_input.open()

    def download_youtube(self, url: str, name: str):
        """Download YouTube audio and extract chords."""
        self.download_status.text = "Downloading..."

        thread = threading.Thread(target=self.perform_download, args=(url, name))
        thread.start()

    def perform_download(self, url: str, name: str):
        """Perform YouTube download in background thread."""
        try:
            storage_folder = ensure_storage_exists()
            file_path = download_youtube_audio(url, storage_folder)

            if not file_path:
                Clock.schedule_once(
                    lambda dt: setattr(self.download_status, "text", "Download failed")
                )
                return

            Clock.schedule_once(
                lambda dt: setattr(self.download_status, "text", "Extracting chords...")
            )

            chords = get_chord_dict(file_path)

            unique_chord_names = list(
                set(c["CHORD"] for c in chords if c.get("CHORD") and c["CHORD"] != "N")
            )
            diagram_paths = generate_all_chord_diagrams(unique_chord_names)

            for chord in chords:
                chord_name = chord.get("CHORD")
                if chord_name and chord_name in diagram_paths:
                    chord["DIAGRAM"] = diagram_paths[chord_name]
                    # Store the version used (default version)
                    version = get_default_version(chord_name)
                    chord["VERSION"] = version

            duration = 0.0
            if chords:
                duration = max(c["START"] for c in chords)

            audio_info = get_tempo_and_time_signature(file_path)

            song = Song(
                name=name,
                source="youtube",
                file_path=file_path,
                youtube_url=url,
                chords=chords,
                duration=duration,
                tempo=audio_info.get("tempo"),
                time_signature=audio_info.get("time_signature"),
            )
            save_song(song)

            Clock.schedule_once(
                lambda dt: setattr(self.download_status, "text", "Done!")
            )
            Clock.schedule_once(lambda dt: self.go_home(None))

        except Exception as e:
            Clock.schedule_once(
                lambda dt: setattr(self.download_status, "text", f"Error: {e}")
            )

    def go_home(self, instance):
        """Navigate back to home screen."""
        self.manager.current = "home"


class SongNameDialog(BoxLayout):
    """Dialog for entering song name."""

    def __init__(self, file_path: str, on_save=None, **kwargs):
        super().__init__(**kwargs)
        self.file_path = file_path
        self.popup = None
        self.on_save_callback = on_save

    def open(self):
        """Open the dialog."""
        from kivy.uix.popup import Popup

        content = BoxLayout(orientation="vertical", padding=20, spacing=10)
        content.add_widget(Label(text="Enter a name for this song:"))

        name_input = TextInput(
            text=os.path.splitext(os.path.basename(self.file_path))[0],
            size_hint_y=None,
            height=30,
            font_size="16sp",
        )
        content.add_widget(name_input)

        buttons = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=50, spacing=10
        )
        save_btn = Button(text="Save")
        save_btn.bind(on_press=lambda x: self.save(name_input.text))
        cancel_btn = Button(text="Cancel")
        cancel_btn.bind(on_press=self.dismiss)
        buttons.add_widget(save_btn)
        buttons.add_widget(cancel_btn)
        content.add_widget(buttons)

        self.popup = Popup(title="Song Name", content=content, size_hint=(0.8, 0.4))
        self.popup.open()

    def save(self, name: str):
        """Save the song name and close dialog."""
        if name.strip():
            self.dismiss(None)
            if self.on_save_callback:
                self.on_save_callback(self, name.strip(), self.file_path)

    def dismiss(self, instance):
        """Close the popup."""
        if self.popup:
            self.popup.dismiss()


class YouTubeNameDialog(BoxLayout):
    """Dialog for entering YouTube video name."""

    def __init__(self, default_title: str, on_save=None, **kwargs):
        super().__init__(**kwargs)
        self.default_title = default_title
        self.popup = None
        self.on_save_callback = on_save

    def open(self):
        """Open the dialog."""
        from kivy.uix.popup import Popup

        content = BoxLayout(orientation="vertical", padding=20, spacing=10)
        content.add_widget(Label(text="Enter a name for this song:"))

        name_input = TextInput(
            text=self.default_title,
            size_hint_y=None,
            height=30,
            font_size="16sp",
        )
        content.add_widget(name_input)

        buttons = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=50, spacing=10
        )
        save_btn = Button(text="Download")
        save_btn.bind(on_press=lambda x: self.save(name_input.text))
        cancel_btn = Button(text="Cancel")
        cancel_btn.bind(on_press=self.dismiss)
        buttons.add_widget(save_btn)
        buttons.add_widget(cancel_btn)
        content.add_widget(buttons)

        self.popup = Popup(title="Song Name", content=content, size_hint=(0.8, 0.4))
        self.popup.open()

    def save(self, name: str):
        """Save the song name and close dialog."""
        if name.strip():
            self.dismiss(None)
            if self.on_save_callback:
                self.on_save_callback(self, name.strip())

    def dismiss(self, instance):
        """Close the popup."""
        if self.popup:
            self.popup.dismiss()
