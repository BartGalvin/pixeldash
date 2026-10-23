from datetime import datetime
from unittest.mock import patch

from PIL import ImageChops

from pixeldash.screens import ClockScreen, HelloWorldScreen
from support import ConfiguredTestCase


class ScreenTests(ConfiguredTestCase):
    def test_both_clock_formats_render_inside_the_display(self):
        frames = []
        for format_24h in ("true", "false"):
            self.configure_with(f"clock: {{format_24h: {format_24h}}}")
            with patch("pixeldash.screens.clock.datetime") as clock:
                clock.now.return_value = datetime(2026, 10, 23, 16, 8)
                screen = ClockScreen()
                frame = screen.render()
            background, _ = screen.create_canvas(screen.background_color)
            bounds = ImageChops.difference(frame, background).getbbox()
            self.assertIsNotNone(bounds)
            self.assertGreater(bounds[0], 0)
            self.assertLess(bounds[2], 64)
            self.assertGreater(bounds[1], 0)
            self.assertLess(bounds[3], 32)
            frames.append(frame.tobytes())
        self.assertNotEqual(frames[0], frames[1])

    def test_screen_and_emulator_dimensions_share_configuration(self):
        self.configure_with("display: {width: 128, height: 64}")
        for screen in (ClockScreen(), HelloWorldScreen()):
            self.assertEqual(screen.render().size, (128, 64))
            self.assertEqual(screen.render().mode, "RGB")
