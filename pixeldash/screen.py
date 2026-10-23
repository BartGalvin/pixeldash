"""
Screen abstraction

A Screen is anything that can generate an image to display.
"""

from abc import ABC, abstractmethod
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Union

from pixeldash.config import get_config
from pixeldash.color_scheme import get_color_scheme, ColorScheme
from pixeldash.font_manager import FontManager


class Screen(ABC):
    """Base class for all screens"""

    def __init__(self):
        """Initialize screen with values from config"""
        config = get_config()

        # Get display size from config
        self.width: int = config.get("display.width")
        self.height: int = config.get("display.height")

        # Initialize font manager and set default font
        self.font_manager = FontManager()
        self.load_font()

        # Load color scheme if specified
        self.color_scheme: Optional[ColorScheme] = None
        try:
            scheme_name = config.get("color_scheme")
            if scheme_name:
                self.color_scheme = get_color_scheme(scheme_name)
        except KeyError:
            # color_scheme is optional, so it's fine if it doesn't exist
            pass
        except Exception as e:
            print(f"Warning: Could not load color scheme: {e}")

    def load_font(
        self, path: Optional[str] = None, size: Optional[int] = None
    ) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
        """Load a font using the font manager (with caching)"""
        self.font = self.font_manager.load_font(path, size)
        return self.font

    def create_canvas(self, color=(0, 0, 0)) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        """
        Create a blank image and drawing context.

        Args:
            color: RGB tuple for background color (default: black)

        Returns:
            Tuple of (image, draw) ready to use
        """
        image = Image.new("RGB", (self.width, self.height), color=color)
        draw = ImageDraw.Draw(image)
        return image, draw

    def get_centered_position(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: Optional[Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]] = None,
    ) -> tuple[int, int]:
        """
        Calculate position to center text on the display.

        Args:
            draw: ImageDraw object (needed for textbbox)
            text: The text to measure
            font: Font to use (defaults to self.font)

        Returns:
            (x, y) position tuple for centered text
        """
        if font is None:
            font = self.font

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = int((self.width - text_width) // 2) - bbox[0]
        y = int((self.height - text_height) // 2) - bbox[1]

        return (x, y)

    def get_vertical_positions(self, num_rows: int, row_height: int = 8) -> list[int]:
        """
        Calculate Y positions to vertically center N rows of text.

        Args:
            num_rows: Number of rows to position
            row_height: Height of each row in pixels (default: 8)

        Returns:
            List of Y positions for each row
        """
        total_height = num_rows * row_height
        start_y = (self.height - total_height) // 2
        return [start_y + i * row_height for i in range(num_rows)]

    def get_text_width(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: Optional[Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]] = None,
    ) -> int:
        """
        Calculate the width of text in pixels.

        Args:
            draw: ImageDraw object (needed for textbbox)
            text: The text to measure
            font: Font to use (defaults to self.font)

        Returns:
            Width in pixels
        """
        if font is None:
            font = self.font

        bbox = draw.textbbox((0, 0), text, font=font)
        return int(bbox[2] - bbox[0])

    def get_centered_x(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: Optional[Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]] = None,
    ) -> int:
        """
        Calculate X position to horizontally center text.

        Args:
            draw: ImageDraw object (needed for textbbox)
            text: The text to measure
            font: Font to use (defaults to self.font)

        Returns:
            X position for centered text
        """
        font = font or self.font
        bbox = draw.textbbox((0, 0), text, font=font)
        return (self.width - (bbox[2] - bbox[0])) // 2 - bbox[0]

    def draw_centered_rows(
        self,
        draw: ImageDraw.ImageDraw,
        rows: list[
            tuple[
                str,
                tuple[int, int, int],
                Optional[Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]],
                int,
            ]
        ],
    ) -> None:
        """
        Draw multiple rows of text, each centered horizontally and vertically as a group.

        Args:
            draw: ImageDraw object
            rows: List of (text, color, font, row_height) tuples
                  font can be None to use default
        """
        # Calculate total height and vertical positions
        row_heights = [row[3] for row in rows]
        total_height = sum(row_heights)
        start_y = (self.height - total_height) // 2

        y_positions = []
        current_y = start_y
        for height in row_heights:
            y_positions.append(current_y)
            current_y += height

        # Draw each row
        for (text, color, font, row_height), y_pos in zip(rows, y_positions):
            if font is None:
                font = self.font
            x = self.get_centered_x(draw, text, font)
            bbox = draw.textbbox((0, 0), text, font=font)
            y = y_pos + (row_height - (bbox[3] - bbox[1])) // 2 - bbox[1]
            draw.text((x, y), text, font=font, fill=color)

    @abstractmethod
    def render(self) -> Image.Image:
        """
        Generate the current frame.

        Returns:
            PIL Image of size (width, height) in RGB mode
        """
        pass

    def update(self, dt: float) -> None:
        """Called every frame to update state"""
        pass

    def on_input(self, event: str) -> bool:
        """Handle input event. Returns True if handled."""
        return False
