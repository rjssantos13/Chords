import os
from typing import Dict, List, Optional

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from app.data import chord_defaults
from app.data.chord_diagram import (
    generate_chord_diagram_for_version,
    get_chord_versions_count,
)
from app.data.storage import update_songs_for_chord


class ChordDBManagerScreen(Screen):
    """Screen for managing chord database defaults."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "chord_db_manager"
        self.select_buttons = []  # Track select buttons for color updates

        self.layout = BoxLayout(orientation="vertical", padding=20, spacing=10)
        self.add_widget(self.layout)

        title = Label(text="Chord Database Manager", size_hint_y=None, height=50)
        self.layout.add_widget(title)

        search_layout = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=40, spacing=10
        )
        self.layout.add_widget(search_layout)

        search_layout.add_widget(Label(text="Search:", size_hint_x=None, width=60))
        self.search_input = TextInput(
            hint_text="Enter chord name (e.g., C, Cmaj7, Am)",
            multiline=False,
            size_hint_y=1,
            write_tab=False,
            input_type="text",
            unfocus_on_touch=False,
        )
        self.search_input.bind(on_text_validate=self.on_search_pressed)
        search_layout.add_widget(self.search_input)

        self.search_btn = Button(text="Search", size_hint_x=None, width=80)
        self.search_btn.bind(on_press=self.on_search_pressed)
        search_layout.add_widget(self.search_btn)

        clear_btn = Button(text="Clear", size_hint_x=None, width=80)
        clear_btn.bind(on_press=self.on_clear_pressed)
        search_layout.add_widget(clear_btn)

        main_content = BoxLayout(orientation="horizontal", spacing=10, size_hint_y=1)

        left_panel = BoxLayout(orientation="vertical", size_hint_x=0.4, spacing=5)
        left_panel.add_widget(Label(text="Chords", size_hint_y=None, height=30))

        self.chord_list_scroll = ScrollView(
            size_hint_y=1,
            do_scroll_x=False,
        )
        self.chord_list_box = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=2
        )
        self.chord_list_box.bind(minimum_height=self.chord_list_box.setter("height"))
        self.chord_list_scroll.add_widget(self.chord_list_box)
        left_panel.add_widget(self.chord_list_scroll)
        main_content.add_widget(left_panel)

        right_panel = BoxLayout(orientation="vertical", size_hint_x=0.6, spacing=5)
        right_panel.add_widget(Label(text="Versions", size_hint_y=None, height=30))

        self.version_list_scroll = ScrollView(size_hint_y=0.7)
        self.version_list_box = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=5
        )
        self.version_list_box.bind(
            minimum_height=self.version_list_box.setter("height")
        )
        self.version_list_scroll.add_widget(self.version_list_box)
        right_panel.add_widget(self.version_list_scroll)

        self.selected_chord_label = Label(
            text="Select a chord", size_hint_y=None, height=30
        )
        right_panel.add_widget(self.selected_chord_label)

        self.set_default_btn = Button(
            text="Set Default", size_hint_y=None, height=50, disabled=True
        )
        self.set_default_btn.bind(on_press=self.on_set_default_pressed)
        right_panel.add_widget(self.set_default_btn)

        main_content.add_widget(right_panel)
        self.layout.add_widget(main_content)

        bottom_layout = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=50, spacing=10
        )
        self.layout.add_widget(bottom_layout)

        back_btn = Button(text="Back to Home", size_hint_x=0.5)
        back_btn.bind(on_press=self.on_back_pressed)
        bottom_layout.add_widget(back_btn)

        refresh_btn = Button(text="Refresh", size_hint_x=0.5)
        refresh_btn.bind(on_press=self.on_refresh_pressed)
        bottom_layout.add_widget(refresh_btn)

        self.all_chords: List[str] = []
        self.filtered_chords: List[str] = []
        self.selected_chord: Optional[str] = None
        self.selected_version: Optional[int] = None

    def on_pre_enter(self):
        """Called before entering the screen."""
        self.load_chord_list()

    def load_chord_list(self):
        """Load the list of all available chords."""
        self.all_chords = chord_defaults.get_all_available_chords()
        self.apply_filter()

    def apply_filter(self, search_text: str = ""):
        """Apply search filter to chord list."""
        if not search_text:
            self.filtered_chords = self.all_chords[:]
        else:
            search_lower = search_text.lower()
            self.filtered_chords = [
                c for c in self.all_chords if search_lower in c.lower()
            ]

        self.build_chord_list()

    def on_search_pressed(self, instance=None):
        """Handle search button press."""
        search_text = self.search_input.text.strip()
        self.apply_filter(search_text)

    def on_clear_pressed(self, instance):
        """Handle clear button press."""
        self.search_input.text = ""
        self.apply_filter("")

    def build_chord_list(self):
        """Build the chord list in the left panel."""
        self.chord_list_box.clear_widgets()

        defaults = chord_defaults.load_defaults()

        for chord_name in self.filtered_chords:
            default_version = defaults.get(chord_name, 1)
            version_count = get_chord_versions_count(chord_name)

            item_box = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=150,
                spacing=10,
                padding=5,
            )

            name_label = Label(
                text=chord_name,
                size_hint_x=0.4,
                halign="left",
                valign="middle",
                text_size=(None, 150),
            )
            item_box.add_widget(name_label)

            diagram_path = generate_chord_diagram_for_version(
                chord_name, default_version
            )
            if diagram_path and os.path.exists(diagram_path):
                img = AsyncImage(
                    source=diagram_path,
                    size_hint_x=0.6,
                    width=150,
                    allow_stretch=True,
                    keep_ratio=True,
                )
            else:
                img = Label(text="No Diagram", size_hint_x=0.6, width=150)
            item_box.add_widget(img)

            item_box.bind(
                on_touch_down=lambda box, touch, cn=chord_name: (
                    self.on_chord_selected(cn)
                    if box.collide_point(touch.x, touch.y)
                    else None
                )
            )

            self.chord_list_box.add_widget(item_box)

    def on_chord_selected(self, chord_name: str):
        """Handle chord selection."""
        self.selected_chord = chord_name
        self.selected_version = None
        self.selected_chord_label.text = f"Selected: {chord_name}"
        self.set_default_btn.disabled = True
        self.build_version_list()

    def build_version_list(self):
        """Build the version list in the right panel."""
        self.version_list_box.clear_widgets()
        self.select_buttons = []

        if not self.selected_chord:
            return

        versions = chord_defaults.get_chord_versions(self.selected_chord)
        default_version = chord_defaults.get_default_version(self.selected_chord)

        for v in versions:
            version = v["version"]
            frets = v.get("frets", [])
            base_fret = v.get("baseFret", 1)

            diagram_path = generate_chord_diagram_for_version(
                self.selected_chord, version
            )

            version_box = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=150,
                spacing=10,
                padding=5,
            )

            is_default = version == default_version

            if diagram_path and os.path.exists(diagram_path):
                img = AsyncImage(
                    source=diagram_path, width=150, allow_stretch=True, keep_ratio=True
                )
            else:
                img = Label(text="No Diagram", width=150)

            version_box.add_widget(img)

            info_box = BoxLayout(orientation="vertical", size_hint_x=0.5, spacing=5)

            version_label = Label(
                text=f"Version {version}" + (" (Default)" if is_default else ""),
                size_hint_y=None,
                height=30,
            )
            info_box.add_widget(version_label)

            frets_label = Label(
                text=f"Frets: {', '.join(str(f) for f in frets)}",
                size_hint_y=None,
                height=25,
            )
            info_box.add_widget(frets_label)

            base_fret_label = Label(
                text=f"Base Fret: {base_fret}",
                size_hint_y=None,
                height=25,
            )
            info_box.add_widget(base_fret_label)

            select_btn = Button(
                text="Select",
                size_hint_y=None,
                height=30,
            )
            select_btn.version = version  # Store version on button for reference
            self.select_buttons.append(select_btn)
            select_btn.bind(
                on_press=lambda instance, v=version, btn=select_btn: (
                    self.on_version_selected(v, btn)
                )
            )
            info_box.add_widget(select_btn)

            version_box.add_widget(info_box)

            self.version_list_box.add_widget(version_box)

    def on_version_selected(self, version: int, selected_btn=None):
        """Handle version selection."""
        self.selected_version = version
        self.set_default_btn.disabled = False
        self.set_default_btn.text = f"Set Default (v{version})"

        # Reset all buttons to default color
        for btn in self.select_buttons:
            btn.background_color = [0.3, 0.3, 0.3, 1]

        # Set selected button to green
        if selected_btn:
            selected_btn.background_color = [0.2, 0.7, 0.2, 1]

    def on_set_default_pressed(self, instance):
        """Handle set default button press."""
        if not self.selected_chord or not self.selected_version:
            return

        chord_defaults.set_default_version(self.selected_chord, self.selected_version)

        songs_updated = update_songs_for_chord(
            self.selected_chord, self.selected_version
        )

        self.build_version_list()
        self.build_chord_list()

    def on_back_pressed(self, instance):
        """Handle back button press."""
        self.manager.current = "home"

    def on_refresh_pressed(self, instance):
        """Handle refresh button press."""
        self.load_chord_list()
        if self.selected_chord:
            self.build_version_list()
