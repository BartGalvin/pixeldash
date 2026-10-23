"""
Screen manager - handles cycling between screens
"""

import time
from math import isfinite
from typing import Optional, Sequence
from pixeldash.screen import Screen


class ScreenManager:
    """Manages multiple screens and handles cycling between them"""

    def __init__(self, screens: Sequence[Screen], interval: float = 5.0):
        """
        Initialize the screen manager

        Args:
            screens: List of Screen instances to cycle through
            interval: Time in seconds to show each screen before switching
        """
        if not screens:
            raise ValueError("Must provide at least one screen")

        self.screens = list(screens)
        self.set_interval(interval)
        self.current_index = 0
        self.last_switch = time.monotonic()

    def get_current_screen(self) -> Screen:
        """Get the currently active screen"""
        return self.screens[self.current_index]

    def next_screen(self) -> Screen:
        """Manually advance to the next screen"""
        self.current_index = (self.current_index + 1) % len(self.screens)
        self.last_switch = time.monotonic()
        return self.get_current_screen()

    def previous_screen(self) -> Screen:
        """Manually go to the previous screen"""
        self.current_index = (self.current_index - 1) % len(self.screens)
        self.last_switch = time.monotonic()
        return self.get_current_screen()

    def set_screen(self, index: int) -> Screen:
        """Jump to a specific screen by index"""
        if 0 <= index < len(self.screens):
            self.current_index = index
            self.last_switch = time.monotonic()
            return self.get_current_screen()
        raise IndexError(f"Screen index {index} out of range (0-{len(self.screens)-1})")

    def update(self) -> Optional[Screen]:
        """
        Check if it's time to switch screens and switch if needed.

        Returns:
            The new current screen if a switch occurred, None otherwise
        """
        now = time.monotonic()
        if now - self.last_switch >= self.interval:
            return self.next_screen()
        return None

    def set_interval(self, interval: float):
        """Change the time interval between screen switches"""
        if not isfinite(interval) or interval <= 0:
            raise ValueError("Screen interval must be a positive number")
        self.interval = interval
