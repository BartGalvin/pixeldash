from unittest import TestCase
from unittest.mock import patch

from pixeldash.screen_manager import ScreenManager


class ScreenManagerTests(TestCase):
    def test_automatic_switch_uses_elapsed_time(self):
        with patch("pixeldash.screen_manager.time.monotonic", return_value=100) as clock:
            manager = ScreenManager(["clock", "hello"], interval=5)
            clock.return_value = 104.9
            self.assertIsNone(manager.update())
            clock.return_value = 105
            self.assertEqual(manager.update(), "hello")
            self.assertEqual(manager.current_index, 1)
            self.assertIsNone(manager.update())

    def test_manual_switch_wraps_and_restarts_timer(self):
        with patch("pixeldash.screen_manager.time.monotonic", return_value=100) as clock:
            manager = ScreenManager(["clock", "hello"], interval=5)
            self.assertEqual(manager.previous_screen(), "hello")
            clock.return_value = 104
            self.assertEqual(manager.next_screen(), "clock")
            clock.return_value = 106
            self.assertIsNone(manager.update())
            clock.return_value = 109
            self.assertEqual(manager.update(), "hello")

    def test_invalid_interval_or_empty_screens_are_rejected(self):
        with self.assertRaises(ValueError):
            ScreenManager([])
        for interval in (0, -1, float("nan"), float("inf")):
            with self.subTest(interval=interval), self.assertRaises(ValueError):
                ScreenManager(["clock"], interval)

    def test_screen_selection_bounds(self):
        manager = ScreenManager(["clock", "hello"])
        self.assertEqual(manager.set_screen(1), "hello")
        for index in (-1, 2):
            with self.subTest(index=index), self.assertRaises(IndexError):
                manager.set_screen(index)
