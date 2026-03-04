from kivy.app import App
from kivy.config import Config
from kivy.uix.screenmanager import ScreenManager, Screen

from app.screens.home_screen import HomeScreen
from app.screens.add_song_screen import AddSongScreen
from app.screens.settings_screen import SettingsScreen
from app.screens.player_screen import PlayerScreen
from app.screens.chord_db_screen import ChordDBManagerScreen


class ChordsApp(App):
    """Main application class for Chord Progression Visualizer."""

    def build(self):
        """Build the application."""
        Config.set("graphics", "width", 600)
        Config.set("graphics", "height", 800)
        Config.set("graphics", "minimum_width", 600)
        Config.set("graphics", "minimum_height", 600)

        sm = ScreenManager()
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(AddSongScreen(name="add_song"))
        sm.add_widget(SettingsScreen(name="settings"))
        sm.add_widget(PlayerScreen(name="player"))
        sm.add_widget(ChordDBManagerScreen(name="chord_db_manager"))
        return sm


if __name__ == "__main__":
    ChordsApp().run()
