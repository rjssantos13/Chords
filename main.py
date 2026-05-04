from kivy.config import Config

Config.set("postproc", "show_touch", False)
Config.set("input", "mouse", "mouse,disable_multitouch")

import os

os.environ["KIVY_NO_CONSOLELOG"] = "1"

from app.main import ChordsApp

if __name__ == "__main__":
    ChordsApp().run()
