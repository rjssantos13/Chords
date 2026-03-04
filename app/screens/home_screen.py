from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from app.data.storage import Song, load_songs, delete_song


class SongListItem(BoxLayout):
    """Widget for displaying a single song in the list."""

    def __init__(self, song: Song, play_callback, delete_callback, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_y = None
        self.height = 80
        self.spacing = 5
        self.padding = 10

        self.song = song
        self.play_callback = play_callback
        self.delete_callback = delete_callback

        top_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=40)
        self.add_widget(top_row)

        self.name_label = Label(
            text=song.name,
            size_hint_x=0.5,
            halign="left",
            valign="middle",
            text_size=(None, 40),
        )
        top_row.add_widget(self.name_label)

        tempo_text = f"{int(song.tempo)} BPM" if song.tempo else ""
        time_sig_text = song.time_signature if song.time_signature else ""
        info_text = f"{tempo_text} | {time_sig_text}".strip(" | ")
        info_label = Label(
            text=info_text,
            size_hint_x=0.3,
            halign="center",
            valign="middle",
            color=(0.7, 0.7, 0.7, 1),
        )
        top_row.add_widget(info_label)

        play_btn = Button(text="Play", size_hint_x=0.2)
        play_btn.bind(on_press=self.on_play_pressed)
        top_row.add_widget(play_btn)

        delete_btn = Button(text="Delete", size_hint_x=0.2)
        delete_btn.bind(on_press=self.on_delete_pressed)
        top_row.add_widget(delete_btn)

    def on_play_pressed(self, instance):
        """Handle play button press."""
        if self.play_callback:
            self.play_callback(self.song)

    def on_delete_pressed(self, instance):
        """Handle delete button press."""
        if self.delete_callback:
            self.delete_callback(self.song)


class HomeScreen(Screen):
    """Home screen displaying the list of saved songs."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation="vertical", padding=20, spacing=10)
        self.add_widget(self.layout)

        title = Label(text="Chord Progression Visualizer", size_hint_y=None, height=50)
        self.layout.add_widget(title)

        self.song_container = ScrollView(size_hint_y=1, size_hint_x=1)
        self.song_list = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=5, size_hint_x=1
        )
        self.song_list.bind(minimum_height=self.song_list.setter("height"))
        self.song_container.add_widget(self.song_list)
        self.layout.add_widget(self.song_container)

        self.empty_label = Label(
            text="No songs yet. Click 'Add Song' to get started.",
            size_hint_y=None,
            height=40,
        )
        self.layout.add_widget(self.empty_label)

        button_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=50)
        self.layout.add_widget(button_row)

        add_btn = Button(text="Add Song")
        add_btn.bind(on_press=self.on_add_song_pressed)
        button_row.add_widget(add_btn)

        settings_btn = Button(text="Settings")
        settings_btn.bind(on_press=self.on_settings_pressed)
        button_row.add_widget(settings_btn)

        chord_db_btn = Button(text="Chord DB")
        chord_db_btn.bind(on_press=self.on_chord_db_pressed)
        button_row.add_widget(chord_db_btn)

    def on_enter(self):
        """Called when entering this screen."""
        self.refresh_song_list()

    def refresh_song_list(self):
        """Refresh the song list display."""
        self.song_list.clear_widgets()
        songs = load_songs()

        if not songs:
            self.empty_label.size_hint_y = 1
            self.song_container.size_hint_y = 0
        else:
            self.empty_label.size_hint_y = 0
            self.song_container.size_hint_y = 1
            for song in songs:
                item = SongListItem(
                    song,
                    play_callback=self.play_song,
                    delete_callback=self.delete_song_item,
                )
                self.song_list.add_widget(item)

    def play_song(self, song: Song):
        """Navigate to player screen with the selected song."""
        player_screen = self.manager.get_screen("player")
        player_screen.load_song(song)
        self.manager.current = "player"

    def delete_song_item(self, song: Song):
        """Delete the selected song."""
        delete_song(song.id)
        self.refresh_song_list()

    def on_add_song_pressed(self, instance):
        """Handle add song button press."""
        self.manager.current = "add_song"

    def on_settings_pressed(self, instance):
        """Handle settings button press."""
        self.manager.current = "settings"

    def on_chord_db_pressed(self, instance):
        """Handle chord database button press."""
        self.manager.current = "chord_db_manager"
