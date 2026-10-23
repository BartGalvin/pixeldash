from contextlib import redirect_stderr
from io import StringIO
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from pixeldash.cli import main
from pixeldash.display import EmulatorDisplay
from support import ConfiguredTestCase

ROOT = Path(__file__).resolve().parents[1]


class CliTests(ConfiguredTestCase):
    def test_real_emulator_renders_switches_and_closes(self):
        frames = []
        show = EmulatorDisplay.show

        def capture(display, image):
            show(display, image)
            frames.append(image.copy())
            event = (
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
                if len(frames) == 1 else pygame.event.Event(pygame.QUIT)
            )
            pygame.event.post(event)

        with patch.object(EmulatorDisplay, "show", capture):
            self.assertEqual(main([]), 0)
        self.assertEqual(len(frames), 2)
        self.assertEqual(frames[0].size, (64, 32))
        self.assertNotEqual(frames[0].tobytes(), frames[1].tobytes())
        self.assertFalse(pygame.display.get_init())

    def test_render_error_closes_the_window(self):
        error = StringIO()
        with patch.object(EmulatorDisplay, "show", side_effect=ValueError("Bad frame")):
            with redirect_stderr(error), self.assertRaises(SystemExit) as result:
                main(["--screens", "clock"])
        self.assertEqual(result.exception.code, 2)
        self.assertIn("Bad frame", error.getvalue())
        self.assertFalse(pygame.display.get_init())

    def test_missing_file_and_invalid_interval_have_clear_errors(self):
        for args in (["--config", "missing.yaml"], ["--interval", "-1"]):
            with self.subTest(args=args), redirect_stderr(StringIO()), self.assertRaises(
                SystemExit
            ) as result:
                main(args)
            self.assertEqual(result.exception.code, 2)
            self.assertFalse(pygame.display.get_init())

    def test_offline_screens_import_without_service_or_hardware_dependencies(self):
        code = '''
import importlib.abc
import sys
class BlockServices(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"requests", "spotipy", "dotenv", "rgbmatrix", "RGBMatrixEmulator"}:
            raise ModuleNotFoundError("Blocked optional module", name=fullname)
sys.meta_path.insert(0, BlockServices())
from pixeldash.screens import ClockScreen, HelloWorldScreen
for screen in (ClockScreen(), HelloWorldScreen()):
    assert screen.render().size == (64, 32)
from pixeldash.cli import main
try:
    main(["--screens", "weather"])
except SystemExit as result:
    assert result.code == 2
else:
    raise AssertionError("Missing service dependency should fail")
'''
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=self.directory,
            env={**os.environ, "PYTHONPATH": str(ROOT)}, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(".[services]", result.stderr)
