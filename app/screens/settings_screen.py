from pathlib import Path

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput

from app.config import (
    get_storage_folder,
    load_config,
    set_storage_folder,
    get_export_folder,
    set_export_folder,
)


class SettingsScreen(Screen):
    """Screen for configuring app settings."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation="vertical", padding=20, spacing=10)
        self.add_widget(self.layout)

        title = Label(text="Settings", size_hint_y=None, height=50)
        self.layout.add_widget(title)

        storage_label = Label(
            text="Audio Files Storage Folder:", size_hint_y=None, height=40
        )
        self.layout.add_widget(storage_label)

        storage_row = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=50, spacing=10
        )
        self.layout.add_widget(storage_row)

        self.storage_path_input = TextInput(readonly=True, size_hint_x=0.7)
        storage_row.add_widget(self.storage_path_input)

        browse_btn = Button(text="Browse", size_hint_x=0.3)
        browse_btn.bind(on_press=self.on_storage_browse_pressed)
        storage_row.add_widget(browse_btn)

        export_label = Label(
            text="JJazzLab Export Folder:", size_hint_y=None, height=40
        )
        self.layout.add_widget(export_label)

        export_row = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=50, spacing=10
        )
        self.layout.add_widget(export_row)

        self.export_path_input = TextInput(readonly=True, size_hint_x=0.7)
        export_row.add_widget(self.export_path_input)

        export_browse_btn = Button(text="Browse", size_hint_x=0.3)
        export_browse_btn.bind(on_press=self.on_export_browse_pressed)
        export_row.add_widget(export_browse_btn)

        spacer = Widget(size_hint_y=1)
        self.layout.add_widget(spacer)

        back_btn = Button(text="Back to Home", size_hint_y=None, height=50)
        back_btn.bind(on_press=self.go_home)
        self.layout.add_widget(back_btn)

    def on_enter(self):
        """Called when entering this screen."""
        config = load_config()
        self.storage_path_input.text = config.get("storage_folder", "")
        self.export_path_input.text = config.get("export_folder", "")

    def on_storage_browse_pressed(self, instance):
        """Handle storage browse button press."""
        picker = FolderPicker(on_folder_selected=self.on_storage_folder_selected)
        picker.open()

    def on_storage_folder_selected(self, instance, folder_path: str):
        """Handle storage folder selection."""
        set_storage_folder(folder_path)
        self.storage_path_input.text = folder_path

    def on_export_browse_pressed(self, instance):
        """Handle export browse button press."""
        picker = FolderPicker(on_folder_selected=self.on_export_folder_selected)
        picker.open()

    def on_export_folder_selected(self, instance, folder_path: str):
        """Handle export folder selection."""
        set_export_folder(folder_path)
        self.export_path_input.text = folder_path

    def go_home(self, instance):
        """Navigate back to home screen."""
        self.manager.current = "home"


class FolderPicker(BoxLayout):
    """Widget for selecting a folder."""

    def __init__(self, on_folder_selected=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.popup = None
        self.on_folder_selected_callback = on_folder_selected

    def open(self):
        """Open the folder picker popup."""
        content = BoxLayout(orientation="vertical", padding=10, spacing=10)

        file_chooser = FileChooserIconView(path=str(Path.home()), dirselect=True)
        content.add_widget(file_chooser)

        buttons = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=50, spacing=10
        )
        select_btn = Button(text="Select")
        select_btn.bind(on_press=lambda x: self.select_folder(file_chooser.path))
        cancel_btn = Button(text="Cancel")
        cancel_btn.bind(on_press=self.dismiss)
        buttons.add_widget(select_btn)
        buttons.add_widget(cancel_btn)
        content.add_widget(buttons)

        self.popup = Popup(title="Select Folder", content=content, size_hint=(0.9, 0.9))
        self.popup.open()

    def select_folder(self, folder_path: str):
        """Select a folder and close popup."""
        self.dismiss(None)
        if self.on_folder_selected_callback:
            self.on_folder_selected_callback(self, folder_path)

    def dismiss(self, instance):
        """Close the popup."""
        if self.popup:
            self.popup.dismiss()
