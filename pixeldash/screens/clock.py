"""
Clock screen
"""

from datetime import datetime
from PIL import Image
from pixeldash.screen import Screen
from pixeldash.config import get_config

TIME_FORMAT = "%H:%M"
DATE_FORMAT = "%a %b %d"  # e.g., "Mon Jan 15"
TIME_ROW_HEIGHT = 12
DATE_ROW_HEIGHT = 8


class ClockScreen(Screen):
    """Screen that shows current time and optionally date"""

    def __init__(self):
        super().__init__()
        self.date_format = DATE_FORMAT

        config = get_config()
        format_24h = config.get("clock.format_24h")
        self.time_format = TIME_FORMAT if format_24h else "%I:%M %p"
        # Leave room for AM/PM on a 64-pixel panel.
        time_size = 10 if format_24h else 8
        self.time_font = self.font_manager.load_font(size=time_size)
        self.date_font = self.font_manager.load_font(size=5)
        self.font = self.time_font
        try:
            self.show_date = config.get("clock.show_date")
        except KeyError:
            self.show_date = False  # Default to time only

        # Set up colors from color scheme or use defaults
        if self.color_scheme:
            self.time_color = self.color_scheme.cyan
            self.date_color = self.color_scheme.foreground
            self.background_color = self.color_scheme.background
        else:
            self.time_color = (0, 255, 255)  # cyan
            self.date_color = (255, 255, 255)  # white
            self.background_color = (0, 0, 0)  # black

    def render(self) -> Image.Image:
        image, draw = self.create_canvas(color=self.background_color)

        now = datetime.now()
        time_str = now.strftime(self.time_format)

        if self.show_date:
            date_str = now.strftime(self.date_format)
            # Draw time and date as centered rows with different fonts and heights
            self.draw_centered_rows(
                draw,
                [
                    (time_str, self.time_color, self.time_font, TIME_ROW_HEIGHT),
                    (date_str, self.date_color, self.date_font, DATE_ROW_HEIGHT),
                ],
            )
        else:
            # Just time, centered both horizontally and vertically
            position = self.get_centered_position(draw, time_str)
            draw.text(position, time_str, font=self.font, fill=self.time_color)

        return image
