import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
from PIL import Image

from pixeldash.display import EmulatorDisplay, MatrixDisplay
from support import ConfiguredTestCase


class EmulatorTests(ConfiguredTestCase):
    def setUp(self):
        super().setUp()
        self.display = EmulatorDisplay()
        self.addCleanup(self.display.close)
        pygame.event.clear()

    def test_rgba_image_scales_without_blurring(self):
        image = Image.new("RGBA", (64, 32), (20, 40, 60, 255))
        image.putpixel((0, 0), (255, 0, 0, 255))
        self.display.show(image)
        surface = pygame.display.get_surface()
        self.assertEqual(surface.get_size(), (640, 320))
        self.assertEqual(tuple(surface.get_at((9, 9)))[:3], (255, 0, 0))
        self.assertEqual(tuple(surface.get_at((10, 10)))[:3], (20, 40, 60))
        self.assertIsNone(pygame.mixer.get_init())

    def test_keyboard_and_close_controls(self):
        for key in (pygame.K_RIGHT, pygame.K_LEFT, pygame.K_SPACE, pygame.K_q, pygame.K_ESCAPE):
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.assertEqual(
            self.display.poll_input(), ["next", "previous", "next", "quit", "quit", "quit"]
        )


class MatrixTests(ConfiguredTestCase):
    def test_matrix_dimensions_and_frame_conversion(self):
        config = self.configure_with("display: {width: 128}\nmatrix: {chain_length: 2}\n")
        options = SimpleNamespace(**config.get("matrix"))
        matrix_class = Mock()
        with patch("pixeldash.matrix_import.get_matrix_classes", return_value=(
            matrix_class, lambda: options
        )):
            display = MatrixDisplay()
        self.assertEqual(options.cols, 64)
        self.assertEqual(options.chain_length, 2)
        display.show(Image.new("RGBA", (128, 32)))
        frame = matrix_class.return_value.SetImage.call_args.args[0]
        self.assertEqual(frame.mode, "RGB")
        display.close()
        matrix_class.return_value.Clear.assert_called_once()

    def test_bad_matrix_dimensions_fail_before_opening_hardware(self):
        self.configure_with("display: {width: 128}\n")
        with patch("pixeldash.matrix_import.get_matrix_classes") as matrix:
            with self.assertRaisesRegex(ValueError, "display size must match"):
                MatrixDisplay()
        matrix.assert_not_called()
