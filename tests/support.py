import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from pixeldash.config import configure


class ConfiguredTestCase(TestCase):
    """Keep tests away from the checkout's settings and credentials."""

    def setUp(self):
        config_patch = patch("pixeldash.config._config", None)
        config_patch.start()
        self.addCleanup(config_patch.stop)
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        original = Path.cwd()
        self.addCleanup(os.chdir, original)
        self.directory = Path(temporary.name)
        os.chdir(self.directory)
        credentials = patch.dict(os.environ, {
            "OPENWEATHER_API_KEY": "",
            "SPOTIFY_CLIENT_ID": "",
            "SPOTIFY_CLIENT_SECRET": "",
        })
        credentials.start()
        self.addCleanup(credentials.stop)
        configure()

    def configure_with(self, text):
        path = self.directory / "settings.yaml"
        path.write_text(text)
        return configure(path)
