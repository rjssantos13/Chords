import os
from typing import Dict, List, Optional

from just_playback import Playback
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.widget import Widget

from app.data.storage import Song, update_song_chords
from chords import align_chords_to_beats, extract_beats, get_audio_duration


class ChordButton(Button):
    """Button representing a single chord in the grid."""

    def __init__(
        self,
        chord_data: Dict,
        is_active: bool = False,
        remove_callback=None,
        seek_callback=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.chord_data = chord_data
        self.chord_name = chord_data.get("CHORD", "")
        self.start_time = chord_data.get("START", 0)
        self.is_removed = chord_data.get("REMOVED", False)
        self.remove_callback = remove_callback
        self.seek_callback = seek_callback
        self.text = self.chord_name
        self.size_hint_y = None
        self.height = 60
        self.font_size = "20sp"
        self.is_active = is_active

        if self.is_removed:
            self.background_color = [0.5, 0.2, 0.2, 1]
            self.opacity = 0.5
        elif is_active:
            self.background_color = [0.2, 0.6, 0.2, 1]
        else:
            self.background_color = [0.3, 0.3, 0.3, 1]

        self.bind(on_press=self.toggle_removal)

    def on_touch_down(self, touch):
        """Handle touch to detect right-click for seek."""
        if touch.button == "right" and self.collide_point(*touch.pos):
            if self.seek_callback:
                self.seek_callback(self.start_time)
            return True
        return super(ChordButton, self).on_touch_down(touch)

    def toggle_removal(self, instance):
        """Handle button press to toggle removal."""
        if self.remove_callback:
            self.remove_callback(self)


class PlayerScreen(Screen):
    """Screen for playing back song with chord visualization."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation="vertical", padding=20, spacing=10)
        self.add_widget(self.layout)

        self.song: Optional[Song] = None
        self.playback: Optional[Playback] = None
        self.update_clock: Optional[object] = None
        self.current_chord_index: int = -1
        self.chord_buttons: List[ChordButton] = []

        self.beat_mode: bool = False
        self.beat_data: List[Dict] = []
        self.beat_buttons: List[ChordButton] = []
        self.current_beat_index: int = -1
        self.last_diagram_index: int = -1

        self.title_label = Label(text="", size_hint_y=None, height=50)
        self.layout.add_widget(self.title_label)

        controls = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=50, spacing=10
        )
        self.layout.add_widget(controls)

        self.play_btn = Button(text="Play", on_press=self.on_play_pressed)
        controls.add_widget(self.play_btn)

        self.stop_btn = Button(text="Stop", on_press=self.on_stop_pressed)
        controls.add_widget(self.stop_btn)

        self.progress_container = BoxLayout(
            orientation="vertical", size_hint_y=None, height=50
        )
        self.layout.add_widget(self.progress_container)

        self.time_label = Label(text="0:00 / 0:00", size_hint_y=None, height=30)
        self.progress_container.add_widget(self.time_label)

        self.seek_slider = Slider(min=0, max=100, value=0)
        self.seek_slider.bind(on_touch_move=self.on_seek)
        self.seek_slider.bind(on_touch_up=self.on_seek_release)
        self.progress_container.add_widget(self.seek_slider)

        diagram_bar_label = Label(text="Chord Diagrams:", size_hint_y=None, height=30)
        self.layout.add_widget(diagram_bar_label)

        self.diagram_scroll = ScrollView(
            size_hint_y=None, height=150, do_scroll_x=True, do_scroll_y=False
        )
        self.diagram_grid = BoxLayout(
            orientation="horizontal", size_hint_x=None, spacing=5
        )
        self.diagram_grid.bind(minimum_width=self.diagram_grid.setter("width"))
        self.diagram_scroll.add_widget(self.diagram_grid)
        self.layout.add_widget(self.diagram_scroll)

        self.diagram_widgets = []

        chord_label = Label(text="Chord Progression:", size_hint_y=None, height=30)
        self.layout.add_widget(chord_label)

        button_row = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=40, spacing=10
        )
        self.layout.add_widget(button_row)

        self.show_removed_btn = Button(text="Show Removed")
        self.show_removed_btn.bind(on_press=self.on_toggle_removed)
        button_row.add_widget(self.show_removed_btn)
        self.show_removed = False

        self.export_btn = Button(text="Export")
        self.export_btn.bind(on_press=self.on_export_pressed)
        button_row.add_widget(self.export_btn)

        self.toggle_mode_btn = Button(text="Switch to Beat Grid")
        self.toggle_mode_btn.bind(on_press=self.on_toggle_mode_pressed)
        button_row.add_widget(self.toggle_mode_btn)

        self.grid_scroll = ScrollView(size_hint_y=1)
        self.grid_panel = GridLayout(cols=8, size_hint_y=None, spacing=5, padding=5)
        self.grid_panel.bind(minimum_height=self.grid_panel.setter("height"))
        self.grid_scroll.add_widget(self.grid_panel)
        self.layout.add_widget(self.grid_scroll)

        self.chord_grid = None
        self.beat_grid = None

        back_btn = Button(text="Back to Home", size_hint_y=None, height=50)
        back_btn.bind(on_press=self.on_back_pressed)
        self.layout.add_widget(back_btn)

    def load_song(self, song: Song):
        """Load a song for playback."""
        self.song = song
        self.title_label.text = song.name
        self.show_removed = False
        self.show_removed_btn.text = "Show Removed"
        self.beat_mode = False
        self.toggle_mode_btn.text = "Switch to Beat Grid"
        self.grid_panel.cols = 8

        if self.playback:
            self.playback.stop()

        self.playback = Playback()
        self.playback.load_file(song.file_path)

        self.seek_slider.value = 0
        self.current_chord_index = -1
        self.current_beat_index = -1
        self.last_diagram_index = -1
        self.play_btn.text = "Play"
        self.build_chord_grid()
        self.build_diagram_bar()
        self.update_time_display()

    def build_chord_grid(self):
        """Build the chord grid from song data."""
        self.grid_panel.clear_widgets()
        self.grid_panel.cols = 8
        self.chord_buttons = []
        self.beat_buttons = []

        if not self.song:
            return

        for chord_data in self.song.chords:
            if chord_data.get("REMOVED", False) and not self.show_removed:
                continue
            button = ChordButton(
                chord_data,
                remove_callback=self.on_chord_remove,
                seek_callback=self.seek_to,
            )
            self.chord_buttons.append(button)
            self.grid_panel.add_widget(button)

    def get_visible_chords(self):
        """Get list of visible (non-removed) chords."""
        if not self.song:
            return []
        return [c for c in self.song.chords if not c.get("REMOVED", False)]

    def show_version_popup(self, chord_name: str, widget):
        """Show popup to select chord version."""
        from app.data.chord_diagram import (
            generate_chord_diagram_for_version,
            get_chord_versions_count,
        )

        version_count = get_chord_versions_count(chord_name)
        if version_count <= 1:
            return

        content = BoxLayout(orientation="vertical", spacing=10, padding=10)
        content.add_widget(
            Label(text=f"Select version for {chord_name}:", size_hint_y=None, height=40)
        )

        versions_scroll = ScrollView(size_hint_y=1)
        versions_layout = BoxLayout(
            orientation="horizontal", size_hint_x=None, spacing=10
        )
        versions_layout.bind(minimum_width=versions_layout.setter("width"))

        popup = Popup(
            title=f"Select {chord_name} Version",
            content=content,
            size_hint=(0.8, 0.6),
            auto_dismiss=True,
        )

        for v in range(1, version_count + 1):
            diagram_path = generate_chord_diagram_for_version(chord_name, v)

            ver_box = BoxLayout(
                orientation="vertical", size_hint_x=None, width=120, spacing=5
            )

            if diagram_path:
                img = AsyncImage(source=diagram_path, size_hint_y=None, height=150)
            else:
                img = Label(text="No Diagram", size_hint_y=None, height=150, width=120)

            ver_box.add_widget(img)

            btn = Button(text=f"v{v}", size_hint_y=None, height=40)
            btn.bind(
                on_press=lambda instance, ver=v, p=popup: self.on_version_selected(
                    chord_name, ver, p
                )
            )
            ver_box.add_widget(btn)

            versions_layout.add_widget(ver_box)

        versions_scroll.add_widget(versions_layout)
        content.add_widget(versions_scroll)

        close_btn = Button(text="Cancel", size_hint_y=None, height=40)
        close_btn.bind(on_press=lambda x: popup.dismiss())
        content.add_widget(close_btn)

        popup.open()

    def on_version_selected(self, chord_name: str, version: int, popup=None):
        """Handle version selection for a chord."""
        from app.data.chord_diagram import generate_chord_diagram_for_version

        if popup:
            popup.dismiss()

        for chord_data in self.song.chords:
            if chord_data.get("CHORD") == chord_name:
                diagram_path = generate_chord_diagram_for_version(chord_name, version)
                if diagram_path:
                    chord_data["DIAGRAM"] = diagram_path
                    chord_data["VERSION"] = version

        update_song_chords(self.song.id, self.song.chords)
        self.build_diagram_bar()

    def build_diagram_bar(self):
        """Build the chord diagram bar."""
        self.diagram_grid.clear_widgets()
        self.diagram_widgets = []

        if not self.song:
            return

        for chord_data in self.song.chords:
            if chord_data.get("REMOVED", False) and not self.show_removed:
                continue

            diagram_path = chord_data.get("DIAGRAM")
            chord_name = chord_data.get("CHORD", "")

            # Backwards compatibility: if diagram path is missing or file doesn't exist,
            # regenerate it using the default version
            if not diagram_path or not os.path.exists(diagram_path):
                from app.data.chord_diagram import generate_chord_diagram

                diagram_path = generate_chord_diagram(chord_name)
                if diagram_path:
                    chord_data["DIAGRAM"] = diagram_path
                    # Save the updated chord data
                    update_song_chords(self.song.id, self.song.chords)

            widget = BoxLayout(
                orientation="vertical", size_hint_x=None, width=100, spacing=2
            )

            name_label = Label(
                text=chord_name, size_hint_y=None, height=25, font_size="14sp"
            )
            widget.add_widget(name_label)

            if diagram_path and os.path.exists(diagram_path):
                diagram_img = AsyncImage(source=diagram_path, size_hint_y=1)
            else:
                diagram_img = Label(text="No Diagram", size_hint_y=1, font_size="10sp")

            widget.add_widget(diagram_img)

            widget.chord_index = len(self.diagram_widgets)
            widget.chord_start = chord_data.get("START", 0)
            widget.chord_name = chord_name

            widget.bind(
                on_touch_down=lambda w, touch: (
                    self.show_version_popup(w.chord_name, w)
                    if w.collide_point(touch.x, touch.y)
                    else None
                )
            )

            self.diagram_widgets.append(widget)
            self.diagram_grid.add_widget(widget)

    def build_beat_grid(self):
        """Build the beat grid from extracted beats and aligned chords."""
        self.grid_panel.clear_widgets()
        self.grid_panel.cols = 16
        self.chord_buttons = []
        self.beat_buttons = []
        self.beat_data = []

        if not self.song:
            return

        try:
            beats = extract_beats(self.song.file_path)
            if not beats:
                print("No beats extracted, falling back to tempo-based beats")
                tempo = self.song.tempo if self.song.tempo else 120
                beat_duration = 60.0 / tempo
                beats = [
                    i * beat_duration
                    for i in range(int(self.song.duration / beat_duration) + 1)
                ]

            audio_duration = get_audio_duration(self.song.file_path)
            if audio_duration <= 0:
                audio_duration = self.song.duration

            visible_chords = self.get_visible_chords()
            self.beat_data = align_chords_to_beats(
                visible_chords, beats, audio_duration
            )

            prev_chord = None
            for beat_info in self.beat_data:
                chord_name = beat_info.get("chord", "N")
                display_text = (
                    "" if chord_name == prev_chord or chord_name == "N" else chord_name
                )
                prev_chord = chord_name

                chord_data = {
                    "CHORD": display_text,
                    "START": beat_info.get("start_time", 0),
                }
                button = ChordButton(chord_data, seek_callback=self.seek_to)
                button.beat_index = beat_info.get("beat_index", 0)
                button.full_chord = beat_info.get("chord", "N")
                self.beat_buttons.append(button)
                self.grid_panel.add_widget(button)

        except Exception as e:
            print(f"Error building beat grid: {e}")

    def on_toggle_mode_pressed(self, instance):
        """Toggle between chord mode and beat mode."""
        self.beat_mode = not self.beat_mode

        if self.beat_mode:
            self.toggle_mode_btn.text = "Switch to Chord Grid"
            self.show_removed_btn.disabled = True
            self.current_beat_index = -1
            self.last_diagram_index = -1
            self.build_beat_grid()
            Clock.schedule_once(lambda dt: self._reset_scroll_position())
        else:
            self.toggle_mode_btn.text = "Switch to Beat Grid"
            self.show_removed_btn.disabled = False
            self.current_chord_index = -1
            self.last_diagram_index = -1
            self.build_chord_grid()
            Clock.schedule_once(lambda dt: self._reset_scroll_position())

    def _reset_scroll_position(self):
        """Reset scroll positions to top/left."""
        self.grid_scroll.scroll_y = 1
        self.diagram_scroll.scroll_x = 0

    def on_toggle_removed(self, instance):
        """Toggle showing removed chords."""
        self.show_removed = not self.show_removed
        self.show_removed_btn.text = (
            "Hide Removed" if self.show_removed else "Show Removed"
        )
        self.build_chord_grid()
        self.build_diagram_bar()

    def on_chord_remove(self, button: ChordButton):
        """Handle chord removal toggle."""
        button.is_removed = not button.is_removed
        button.chord_data["REMOVED"] = button.is_removed

        if button.is_removed:
            button.background_color = [0.5, 0.2, 0.2, 1]
            button.opacity = 0.5
        else:
            button.background_color = [0.3, 0.3, 0.3, 1]
            button.opacity = 1.0

        if self.song:
            update_song_chords(self.song.id, self.song.chords)

    def on_export_pressed(self, instance):
        """Show export format selection."""
        if not self.song:
            return

        visible_chords = self.get_visible_chords()
        if not visible_chords:
            return

        from kivy.uix.popup import Popup

        content = BoxLayout(orientation="vertical", padding=20, spacing=10)
        content.add_widget(
            Label(text="Select Export Format", size_hint_y=None, height=40)
        )

        midi_btn = Button(text="MIDI (.mid)", size_hint_y=None, height=50)
        midi_btn.bind(on_press=lambda x: self.on_export_midi())
        content.add_widget(midi_btn)

        text_btn = Button(text="Text (.txt)", size_hint_y=None, height=50)
        text_btn.bind(on_press=lambda x: self.on_export_text())
        content.add_widget(text_btn)

        xml_btn = Button(text="MusicXML (.xml)", size_hint_y=None, height=50)
        xml_btn.bind(on_press=lambda x: self.on_export_musicxml())
        content.add_widget(xml_btn)

        cancel_btn = Button(text="Cancel", size_hint_y=None, height=50)
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        content.add_widget(cancel_btn)

        popup = Popup(title="Export", content=content, size_hint=(0.6, 0.6))
        popup.open()

    def on_export_midi(self):
        """Export filtered chords to MIDI format."""
        from kivy.uix.popup import Popup
        from kivy.uix.textinput import TextInput

        visible_chords = self.get_visible_chords()
        default_tempo = int(self.song.tempo) if self.song.tempo else 120
        default_filename = f"{self.song.name}.mid"

        content = BoxLayout(orientation="vertical", padding=20, spacing=10)
        content.add_widget(Label(text="MIDI Export"))

        filename_label = Label(text="Filename:", size_hint_y=None, height=30)
        content.add_widget(filename_label)

        filename_input = TextInput(
            text=default_filename, size_hint_y=None, height=40, multiline=False
        )
        content.add_widget(filename_input)

        tempo_label = Label(text="Tempo BPM (e.g., 120):", size_hint_y=None, height=30)
        content.add_widget(tempo_label)

        tempo_input = TextInput(
            text=str(default_tempo), size_hint_y=None, height=40, multiline=False
        )
        content.add_widget(tempo_input)

        buttons = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=50, spacing=10
        )
        export_btn = Button(text="Export")
        export_btn.bind(
            on_press=lambda x: self.perform_midi_export(
                visible_chords,
                tempo_input.text,
                filename_input.text,
            )
        )
        cancel_btn = Button(text="Cancel")
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        buttons.add_widget(export_btn)
        buttons.add_widget(cancel_btn)
        content.add_widget(buttons)

        popup = Popup(title="Export to MIDI", content=content, size_hint=(0.8, 0.6))
        popup.open()

    def on_export_text(self):
        """Export filtered chords to JJazzLab text format."""
        from kivy.uix.popup import Popup
        from kivy.uix.textinput import TextInput

        visible_chords = self.get_visible_chords()
        default_time_sig = (
            self.song.time_signature if self.song.time_signature else "4/4"
        )
        default_tempo = int(self.song.tempo) if self.song.tempo else 120
        default_filename = f"{self.song.name}.txt"

        content = BoxLayout(orientation="vertical", padding=20, spacing=10)
        content.add_widget(Label(text="JJazzLab Text Export"))

        filename_label = Label(text="Filename:", size_hint_y=None, height=30)
        content.add_widget(filename_label)

        filename_input = TextInput(
            text=default_filename, size_hint_y=None, height=40, multiline=False
        )
        content.add_widget(filename_input)

        time_sig_label = Label(
            text="Time Signature (e.g., 4/4):", size_hint_y=None, height=30
        )
        content.add_widget(time_sig_label)

        time_sig_input = TextInput(
            text=default_time_sig, size_hint_y=None, height=40, multiline=False
        )
        content.add_widget(time_sig_input)

        tempo_label = Label(text="Tempo BPM (e.g., 120):", size_hint_y=None, height=30)
        content.add_widget(tempo_label)

        tempo_input = TextInput(
            text=str(default_tempo), size_hint_y=None, height=40, multiline=False
        )
        content.add_widget(tempo_input)

        buttons = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=50, spacing=10
        )
        export_btn = Button(text="Export")
        export_btn.bind(
            on_press=lambda x: self.perform_text_export(
                visible_chords,
                time_sig_input.text,
                tempo_input.text,
                filename_input.text,
            )
        )
        cancel_btn = Button(text="Cancel")
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        buttons.add_widget(export_btn)
        buttons.add_widget(cancel_btn)
        content.add_widget(buttons)

        popup = Popup(title="Export to Text", content=content, size_hint=(0.8, 0.7))
        popup.open()

    def on_export_musicxml(self):
        """Export filtered chords to MusicXML format."""
        from kivy.uix.popup import Popup
        from kivy.uix.textinput import TextInput

        visible_chords = self.get_visible_chords()
        default_tempo = int(self.song.tempo) if self.song.tempo else 120
        default_filename = f"{self.song.name}.xml"

        content = BoxLayout(orientation="vertical", padding=20, spacing=10)
        content.add_widget(Label(text="MusicXML Export"))

        filename_label = Label(text="Filename:", size_hint_y=None, height=30)
        content.add_widget(filename_label)

        filename_input = TextInput(
            text=default_filename, size_hint_y=None, height=40, multiline=False
        )
        content.add_widget(filename_input)

        tempo_label = Label(text="Tempo BPM:", size_hint_y=None, height=30)
        content.add_widget(tempo_label)

        tempo_input = TextInput(
            text=str(default_tempo), size_hint_y=None, height=40, multiline=False
        )
        content.add_widget(tempo_input)

        buttons = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=50, spacing=10
        )
        export_btn = Button(text="Export")
        export_btn.bind(
            on_press=lambda x: self.perform_musicxml_export(
                visible_chords,
                tempo_input.text,
                filename_input.text,
            )
        )
        cancel_btn = Button(text="Cancel")
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        buttons.add_widget(export_btn)
        buttons.add_widget(cancel_btn)
        content.add_widget(buttons)

        popup = Popup(title="Export to MusicXML", content=content, size_hint=(0.8, 0.6))
        popup.open()

    def perform_musicxml_export(self, chords: List[Dict], tempo: str, filename: str):
        """Generate and save the MusicXML file."""
        from kivy.uix.filechooser import FileChooserListView
        from kivy.uix.popup import Popup
        from app.config import get_export_folder
        import os

        export_folder = get_export_folder()

        if not filename.endswith(".xml"):
            filename = filename + ".xml"

        content = BoxLayout(orientation="vertical", padding=10, spacing=10)

        file_chooser = FileChooserListView(path=str(export_folder), filters=["*.xml"])
        content.add_widget(file_chooser)

        buttons = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=50, spacing=10
        )
        save_btn = Button(text="Save")
        cancel_btn = Button(text="Cancel")

        def save_file(instance):
            path = file_chooser.path
            selected = file_chooser.selection
            if selected:
                full_path = (
                    selected[0]
                    if isinstance(selected, list)
                    else os.path.join(path, selected)
                )
            else:
                full_path = os.path.join(path, filename)
            if not full_path.endswith(".xml"):
                full_path += ".xml"

            try:
                xml_content = self.generate_musicxml_content(chords, tempo)
                with open(full_path, "w") as f:
                    f.write(xml_content)
                popup.dismiss()
                self.export_btn.text = "Exported!"
            except Exception as e:
                print(f"Error saving file: {e}")

        save_btn.bind(on_press=save_file)
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        buttons.add_widget(save_btn)
        buttons.add_widget(cancel_btn)
        content.add_widget(buttons)

        popup = Popup(title="Save MusicXML File", content=content, size_hint=(0.9, 0.9))
        popup.open()

    def generate_musicxml_content(self, chords: List[Dict], tempo: str) -> str:
        """Generate MusicXML format content."""
        import xml.etree.ElementTree as ET

        ns = {"": "http://www.musicxml.org/schema/MusicXML"}
        ET.register_namespace("", "http://www.musicxml.org/schema/MusicXML")

        score_partwise = ET.Element("score-partwise", version="4.0")
        identification = ET.SubElement(score_partwise, "identification")
        encoding = ET.SubElement(identification, "encoding")
        software = ET.SubElement(encoding, "software")
        software.text = "Chords App"

        part_list = ET.SubElement(score_partwise, "part-list")
        score_part = ET.SubElement(part_list, "score-part", id="P1")
        part_name = ET.SubElement(score_part, "part-name")
        part_name.text = "Chord Sheet"

        part = ET.SubElement(score_partwise, "part", id="P1")

        divisions = 480
        beats_per_measure = 4

        try:
            tempo_val = int(float(tempo)) if tempo else 120
        except (ValueError, TypeError):
            tempo_val = 120
        seconds_per_beat = 60.0 / tempo_val
        seconds_per_bar = seconds_per_beat * beats_per_measure

        measure_num = 1
        current_measure = None
        attributes_added = False
        used_offsets = set()
        max_offset = divisions * beats_per_measure

        for i, chord_data in enumerate(chords):
            chord_name = chord_data.get("CHORD", "N")
            start_time = chord_data.get("START", 0)

            if i == 0:
                start_time = 0.0

            # Calculate bar number directly from time
            bar_number = int(start_time // seconds_per_bar) + 1

            # Calculate offset within the measure (0 to max_offset)
            beat_position = (
                (start_time % seconds_per_bar) / seconds_per_bar * beats_per_measure
            )
            offset_beats = int(beat_position * divisions)

            # If offset exceeds max, move to next measure
            while offset_beats >= max_offset and bar_number < 1000:
                offset_beats -= max_offset
                bar_number += 1

            if bar_number != measure_num or current_measure is None:
                measure_num = bar_number
                current_measure = ET.SubElement(
                    part, "measure", number=str(measure_num)
                )
                used_offsets = set()

                if not attributes_added:
                    attributes = ET.SubElement(current_measure, "attributes")
                    div_elem = ET.SubElement(attributes, "divisions")
                    div_elem.text = str(divisions)
                    key = ET.SubElement(attributes, "key")
                    fifths = ET.SubElement(key, "fifths")
                    fifths.text = "0"
                    mode = ET.SubElement(key, "mode")
                    mode.text = "major"
                    time_elem = ET.SubElement(current_measure, "time")
                    beats = ET.SubElement(time_elem, "beats")
                    beats.text = "4"
                    beat_type = ET.SubElement(time_elem, "beat-type")
                    beat_type.text = "4"
                    attributes_added = True

            # Skip if this offset is already used in this measure
            if offset_beats in used_offsets:
                continue
            used_offsets.add(offset_beats)

            harmony = ET.SubElement(current_measure, "harmony")
            offset_elem = ET.SubElement(harmony, "offset")
            offset_elem.text = str(offset_beats)

            root_elem = ET.SubElement(harmony, "root")
            root_step = ET.SubElement(root_elem, "root-step")

            parsed = self._parse_chord_for_musicxml(chord_name)
            root_step.text = parsed["root"]

            if parsed.get("alter"):
                root_alter = ET.SubElement(root_elem, "root-alter")
                root_alter.text = str(parsed["alter"])

            kind_elem = ET.SubElement(harmony, "kind")
            kind_elem.text = parsed["kind"]
            kind_elem.set("text", chord_name)

            if parsed.get("bass"):
                bass_elem = ET.SubElement(harmony, "bass")
                bass_step = ET.SubElement(bass_elem, "bass-step")
                bass_step.text = parsed["bass"]
                if parsed.get("bass_alter"):
                    bass_alter = ET.SubElement(bass_elem, "bass-alter")
                    bass_alter.text = str(parsed["bass_alter"])

        ET.indent(score_partwise)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
            score_partwise, encoding="unicode"
        )

    def _parse_chord_for_musicxml(self, chord: str) -> Dict:
        """Parse chord name into MusicXML root, kind, and bass."""
        chord = chord.strip()

        root_offsets = {
            "C": ("C", 0),
            "C#": ("C", 1),
            "Db": ("D", -1),
            "D": ("D", 0),
            "D#": ("D", 1),
            "Eb": ("E", -1),
            "E": ("E", 0),
            "F": ("F", 0),
            "F#": ("F", 1),
            "Gb": ("G", -1),
            "G": ("G", 0),
            "G#": ("G", 1),
            "Ab": ("A", -1),
            "A": ("A", 0),
            "A#": ("A", 1),
            "Bb": ("B", -1),
            "B": ("B", 0),
        }

        bass = None
        bass_alter = 0
        if "/" in chord:
            parts = chord.split("/")
            chord = parts[0]
            if len(parts) > 1:
                bass_part = parts[1]
                if bass_part and bass_part[0] in "ABCDEFG":
                    bass_info = root_offsets.get(bass_part, ("C", 0))
                    bass = bass_info[0]
                    bass_alter = bass_info[1]

        root = "C"
        alter = 0
        if chord and chord[0] in "ABCDEFG":
            root_info = root_offsets.get(
                chord[:2], root_offsets.get(chord[0], ("C", 0))
            )
            root = root_info[0]
            alter = root_info[1]

        chord_type = chord[len(root) :] if len(chord) > 1 else ""

        kind_map = {
            "maj7": "major-seventh",
            "M7": "major-seventh",
            "maj": "major-seventh",
            "m7b5": "half-diminished",
            "m11": "minor-11th",
            "m9": "minor-ninth",
            "m7": "minor-seventh",
            "m6": "minor-sixth",
            "min": "minor",
            "m": "minor",
            "dim7": "diminished-seventh",
            "dim": "diminished",
            "aug": "augmented",
            "sus4": "suspended-fourth",
            "sus2": "suspended-second",
            "sus": "suspended-fourth",
            "6": "major-sixth",
            "7b5": "dominant",
            "7#5": "augmented-seventh",
            "9": "dominant-ninth",
            "11": "dominant-11th",
            "13": "dominant-13th",
            "7": "dominant",
            "": "major",
        }

        kind = "major"
        for key, value in kind_map.items():
            if chord_type == key or (key and chord_type.startswith(key)):
                kind = value
                break

        result = {"root": root, "kind": kind}
        if alter != 0:
            result["alter"] = alter
        if bass:
            result["bass"] = bass
            if bass_alter != 0:
                result["bass_alter"] = bass_alter

        return result

    def perform_midi_export(self, chords: List[Dict], tempo: str, filename: str):
        """Generate and save the MIDI file."""
        from kivy.uix.filechooser import FileChooserListView
        from kivy.uix.popup import Popup
        from app.config import get_export_folder
        import os

        export_folder = get_export_folder()

        if not filename.endswith(".mid"):
            filename = filename + ".mid"

        content = BoxLayout(orientation="vertical", padding=10, spacing=10)

        file_chooser = FileChooserListView(path=str(export_folder), filters=["*.mid"])
        content.add_widget(file_chooser)

        buttons = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=50, spacing=10
        )
        save_btn = Button(text="Save")
        cancel_btn = Button(text="Cancel")

        def save_file(instance):
            path = file_chooser.path
            selected = file_chooser.selection
            if selected:
                full_path = (
                    selected[0]
                    if isinstance(selected, list)
                    else os.path.join(path, selected)
                )
            else:
                full_path = os.path.join(path, filename)
            if not full_path.endswith(".mid"):
                full_path += ".mid"

            try:
                self.generate_midi_file(chords, tempo, full_path)
                popup.dismiss()
                self.export_btn.text = "Exported!"
            except Exception as e:
                print(f"Error saving file: {e}")

        save_btn.bind(on_press=save_file)
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        buttons.add_widget(save_btn)
        buttons.add_widget(cancel_btn)
        content.add_widget(buttons)

        popup = Popup(title="Save MIDI File", content=content, size_hint=(0.9, 0.9))
        popup.open()

    def perform_text_export(
        self, chords: List[Dict], time_sig: str, tempo: str, filename: str
    ):
        """Generate and save the JJazzLab text file."""
        from kivy.uix.filechooser import FileChooserListView
        from kivy.uix.popup import Popup
        from app.config import get_export_folder
        import os

        export_folder = get_export_folder()

        if not filename.endswith(".txt"):
            filename = filename + ".txt"

        content = BoxLayout(orientation="vertical", padding=10, spacing=10)

        file_chooser = FileChooserListView(path=str(export_folder), filters=["*.txt"])
        content.add_widget(file_chooser)

        buttons = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=50, spacing=10
        )
        save_btn = Button(text="Save")
        cancel_btn = Button(text="Cancel")

        def save_file(instance):
            path = file_chooser.path
            selected = file_chooser.selection
            if selected:
                full_path = (
                    selected[0]
                    if isinstance(selected, list)
                    else os.path.join(path, selected)
                )
            else:
                full_path = os.path.join(path, filename)
            if not full_path.endswith(".txt"):
                full_path += ".txt"

            try:
                text_content = self.generate_jjazzlab_content(chords, time_sig, tempo)
                with open(full_path, "w") as f:
                    f.write(text_content)
                popup.dismiss()
                self.export_btn.text = "Exported!"
            except Exception as e:
                print(f"Error saving file: {e}")

        save_btn.bind(on_press=save_file)
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        buttons.add_widget(save_btn)
        buttons.add_widget(cancel_btn)
        content.add_widget(buttons)

        popup = Popup(title="Save Text File", content=content, size_hint=(0.9, 0.9))
        popup.open()

    def generate_midi_file(self, chords: List[Dict], tempo: str, filepath: str):
        """Generate MIDI file with chord progression."""
        from midiutil import MIDIFile

        tempo_bpm = int(tempo) if tempo else 120

        midi = MIDIFile(1)
        midi.addTempo(0, 0, tempo_bpm)

        channel = 0
        track = 0

        seconds_per_beat = 60.0 / tempo_bpm

        for i, chord_data in enumerate(chords):
            start_time = chord_data.get("START", 0)

            if i == 0:
                start_time = 0.0

            chord_name = chord_data.get("CHORD", "N")

            duration = 4.0
            if i + 1 < len(chords):
                next_start = chords[i + 1].get("START", 0)
                duration = next_start - chord_data.get("START", 0)
                if duration <= 0:
                    duration = seconds_per_beat
                duration = min(duration, 4.0 * seconds_per_beat)
            else:
                duration = 4.0 * seconds_per_beat

            notes = self._chord_to_midi_notes(chord_name)
            for note in notes:
                midi.addNote(track, channel, note, start_time, duration, 80)

        with open(filepath, "wb") as f:
            midi.writeFile(f)

    def _chord_to_midi_notes(self, chord: str) -> List[int]:
        """Convert chord name to MIDI note numbers."""
        note_offsets = {
            "C": 0,
            "C#": 1,
            "Db": 1,
            "D": 2,
            "D#": 3,
            "Eb": 3,
            "E": 4,
            "F": 5,
            "F#": 6,
            "Gb": 6,
            "G": 7,
            "G#": 8,
            "Ab": 8,
            "A": 9,
            "A#": 10,
            "Bb": 10,
            "B": 11,
        }

        chord = chord.strip()
        root = chord[0] if chord else "C"
        modifier = ""
        if len(chord) > 1 and chord[1] in "#b":
            modifier = chord[1]
            if len(chord) > 2 and chord[2] in "#b":
                modifier += chord[2]

        root_note = note_offsets.get(root + modifier, 0)

        bass_note = root_note
        if "/" in chord:
            bass_part = chord.split("/")[1]
            if bass_part:
                bass_root = bass_part[0] if bass_part else "C"
                bass_mod = ""
                if len(bass_part) > 1 and bass_part[1] in "#b":
                    bass_mod = bass_part[1]
                bass_note = note_offsets.get(bass_root + bass_mod, root_note)

        chord_type = chord.replace(root, "").replace(modifier, "").split("/")[0]

        if "maj" in chord_type or chord_type == "" or chord_type == "6":
            intervals = [0, 4, 7]
        elif "min" in chord_type or chord_type == "m":
            intervals = [0, 3, 7]
        elif "7" in chord_type:
            if "maj7" in chord_type or "M7" in chord_type:
                intervals = [0, 4, 7, 11]
            else:
                intervals = [0, 4, 7, 10]
        elif "dim" in chord_type:
            intervals = [0, 3, 6]
        elif "aug" in chord_type or "+" in chord_type:
            intervals = [0, 4, 8]
        elif "sus" in chord_type:
            if "sus4" in chord_type:
                intervals = [0, 5, 7]
            else:
                intervals = [0, 5, 7]
        elif "9" in chord_type:
            intervals = [0, 4, 7, 10, 14]
        elif "11" in chord_type:
            intervals = [0, 4, 7, 10, 14, 17]
        else:
            intervals = [0, 4, 7]

        midi_notes = []
        for interval in intervals:
            note = 60 + root_note + interval
            midi_notes.append(note)

        if bass_note != root_note:
            midi_notes.insert(0, 48 + bass_note)

        return midi_notes

    def generate_jjazzlab_content(
        self, chords: List[Dict], time_sig: str, tempo: str
    ) -> str:
        """Generate JJazzLab TIME-BASED format content."""
        lines = []
        lines.append(f"timeSignature={time_sig}")
        lines.append(f"tempoBPM={tempo}")

        first_start = chords[0].get("START", 0) if chords else 0
        for chord_data in chords:
            start = chord_data.get("START", 0)
            if start == first_start:
                start = 0
            chord = chord_data.get("CHORD", "N")
            lines.append(f"{start}, {chord}")

        return "\n".join(lines)

    def on_play_pressed(self, instance):
        """Handle play/pause button press."""
        if not self.playback:
            return

        if self.play_btn.text == "Pause":
            self.playback.pause()
            self.play_btn.text = "Unpause"
        elif self.play_btn.text == "Unpause":
            self.playback.resume()
            self.play_btn.text = "Pause"
            self.start_update_clock()
        else:
            self.playback.play()
            self.play_btn.text = "Pause"
            self.start_update_clock()

    def on_stop_pressed(self, instance):
        """Handle stop button press."""
        if not self.playback:
            return

        self.playback.stop()
        self.playback.seek(0)
        self.seek_slider.value = 0
        self.current_chord_index = -1
        self.current_beat_index = -1
        self.last_diagram_index = -1
        self.play_btn.text = "Play"
        self.update_time_display()
        self.update_chord_highlight()
        self._reset_scroll_position()

    def on_seek(self, instance, touch):
        """Handle seek slider movement."""
        if not self.playback or not self.song:
            return

        if touch.grab_current == instance:
            position = (instance.value / 100) * self.song.duration
            self.update_time_display(position)

    def seek_to(self, position: float):
        """Seek to a specific position in the song."""
        if not self.playback or not self.song:
            return
        self.playback.seek(float(position))
        self.seek_slider.value = float((position / self.song.duration) * 100)
        self.update_time_display(float(position))
        self.update_chord_highlight()

    def on_seek_release(self, instance, touch):
        """Handle seek slider release."""
        if not self.playback or not self.song:
            return

        position = (instance.value / 100) * self.song.duration
        self.playback.seek(position)
        self.update_chord_highlight()

    def start_update_clock(self):
        """Start the clock for updating playback position."""
        if self.update_clock:
            return

        self.update_clock = Clock.schedule_interval(self.update_playback, 0.1)

    def stop_update_clock(self):
        """Stop the update clock."""
        if self.update_clock:
            self.update_clock.cancel()
            self.update_clock = None

    def update_playback(self, dt):
        """Update playback display and chord highlighting."""
        if not self.playback or not self.song:
            return

        position = self.playback.curr_pos
        duration = self.playback.duration

        if duration > 0:
            self.seek_slider.value = (position / duration) * 100

        self.update_time_display(position)

        if self.playback.playing:
            self.update_chord_highlight()
        elif position >= duration:
            self.stop_update_clock()
            self.play_btn.text = "Play"
            self._reset_scroll_position()

    def update_time_display(self, position: float = 0):
        """Update the time display."""
        if not self.song:
            return

        duration = self.song.duration
        if position == 0 and self.playback:
            position = self.playback.curr_pos

        pos_min = int(position // 60)
        pos_sec = int(position % 60)
        dur_min = int(duration // 60)
        dur_sec = int(duration % 60)

        self.time_label.text = f"{pos_min}:{pos_sec:02d} / {dur_min}:{dur_sec:02d}"

    def update_chord_highlight(self):
        """Update the highlighted chord based on current playback position."""
        if not self.playback or not self.song:
            return

        position = self.playback.curr_pos

        if self.beat_mode:
            self._update_beat_highlight(position)
        else:
            self._update_chord_grid_highlight(position)

    def _scroll_diagram_to_center(self, widget):
        """Scroll diagram to center horizontally in scroll view."""
        if not widget or not self.diagram_scroll:
            return
        scroll_width = self.diagram_scroll.width
        widget_x = widget.x
        widget_width = widget.width
        grid_width = self.diagram_grid.width

        if grid_width <= scroll_width:
            return

        center_offset = widget_x - (scroll_width / 2) + (widget_width / 2)
        scroll_x = center_offset / (grid_width - scroll_width)
        self.diagram_scroll.scroll_x = max(0, min(1, scroll_x))

    def _scroll_beat_grid(self, target_button, cols=16):
        """Scroll beat grid to keep highlighted item centered, 2 rows from bottom."""
        if not target_button or not self.grid_scroll:
            return

        scroll_height = self.grid_scroll.height
        widget_y = target_button.y
        widget_height = target_button.height
        grid_height = self.grid_panel.height

        if grid_height <= scroll_height:
            return

        # Calculate position - aim to keep widget 2 rows from bottom
        # Each row is approximately widget_height
        two_rows_offset = widget_height * 2
        target_y = widget_y - two_rows_offset

        # Convert to scroll_y (0 = bottom, 1 = top)
        scroll_range = grid_height - scroll_height
        if scroll_range <= 0:
            return

        scroll_y = 1 - (target_y / scroll_range)
        self.grid_scroll.scroll_y = max(0, min(1, scroll_y))

    def _update_chord_grid_highlight(self, position: float):
        """Update chord grid highlighting."""
        visible_chords = self.get_visible_chords()
        new_index = -1

        for i, chord_data in enumerate(visible_chords):
            start_time = chord_data.get("START", 0)
            if i + 1 < len(visible_chords):
                next_start = visible_chords[i + 1].get("START", 0)
            else:
                next_start = self.song.duration

            if start_time <= position < next_start:
                new_index = i
                break

        if new_index != self.current_chord_index:
            self.current_chord_index = new_index

            for i, button in enumerate(self.chord_buttons):
                if i == new_index:
                    button.background_color = [0.2, 0.6, 0.2, 1]
                else:
                    button.background_color = [0.3, 0.3, 0.3, 1]

            if new_index >= 0 and new_index < len(self.chord_buttons):
                target_button = self.chord_buttons[new_index]
                self.grid_scroll.scroll_to(target_button, padding=200, animate=True)

            for i, widget in enumerate(self.diagram_widgets):
                if i == new_index:
                    widget.children[0].color = [0.2, 0.8, 0.2, 1]
                else:
                    widget.children[0].color = [1, 1, 1, 1]

            if new_index >= 0 and new_index < len(self.diagram_widgets):
                target_widget = self.diagram_widgets[new_index]
                self._scroll_diagram_to_center(target_widget)

    def _update_beat_highlight(self, position: float):
        """Update beat grid highlighting."""
        if not self.beat_data:
            return

        new_index = -1

        for i, beat_info in enumerate(self.beat_data):
            start_time = beat_info.get("start_time", 0)
            if i + 1 < len(self.beat_data):
                next_start = self.beat_data[i + 1].get("start_time", 0)
            else:
                next_start = self.song.duration

            if start_time <= position < next_start:
                new_index = i
                break

        if new_index != self.current_beat_index:
            self.current_beat_index = new_index

            for i, button in enumerate(self.beat_buttons):
                if i == new_index:
                    button.background_color = [0.2, 0.6, 0.2, 1]
                else:
                    button.background_color = [0.3, 0.3, 0.3, 1]

            if new_index >= 0 and new_index < len(self.beat_buttons):
                target_button = self.beat_buttons[new_index]
                self.grid_scroll.scroll_to(target_button, padding=50, animate=True)

            current_chord_name = None
            current_chord_start = None
            if new_index >= 0 and new_index < len(self.beat_data):
                current_chord_name = self.beat_data[new_index].get("chord", "N")
                current_chord_start = self.beat_data[new_index].get("start_time", 0)

            # First, clear all diagram highlights
            for widget in self.diagram_widgets:
                widget.children[0].color = [1, 1, 1, 1]

            if current_chord_name and current_chord_name != "N":
                visible_chords = self.get_visible_chords()
                target_idx = -1
                for i, chord_data in enumerate(visible_chords):
                    if (
                        chord_data.get("CHORD") == current_chord_name
                        and abs(chord_data.get("START", 0) - current_chord_start) < 1.0
                    ):
                        target_idx = i
                        break

                if target_idx >= 0 and target_idx < len(self.diagram_widgets):
                    self.diagram_widgets[target_idx].children[0].color = [
                        0.2,
                        0.8,
                        0.2,
                        1,
                    ]
                    self.last_diagram_index = target_idx
                    self._scroll_diagram_to_center(self.diagram_widgets[target_idx])
                else:
                    # Keep last diagram highlighted
                    if self.last_diagram_index >= 0 and self.last_diagram_index < len(
                        self.diagram_widgets
                    ):
                        self.diagram_widgets[self.last_diagram_index].children[
                            0
                        ].color = [0.2, 0.8, 0.2, 1]
            else:
                for i, widget in enumerate(self.diagram_widgets):
                    if i == self.last_diagram_index:
                        widget.children[0].color = [0.2, 0.8, 0.2, 1]
                    else:
                        widget.children[0].color = [1, 1, 1, 1]

    def on_back_pressed(self, instance):
        """Handle back button press."""
        self.stop_update_clock()
        if self.playback:
            self.playback.stop()
        self.manager.current = "home"

    def on_leave(self):
        """Called when leaving this screen."""
        self.stop_update_clock()
        if self.playback:
            self.playback.stop()
