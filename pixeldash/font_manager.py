from PIL import ImageFont
from typing import Optional, Union
from pixeldash.config import get_config


class FontManager:
    """Manages font loading with caching by (path, size)"""

    def __init__(self):
        """Initialize font manager with values from config"""
        config = get_config()
        self.default_path: Optional[str] = config.get("font.path")
        self.default_size: int = config.get("font.size")

        # Cache for loaded fonts keyed by (path, size)
        self._cache: dict[
            tuple[Optional[str], int], Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]
        ] = {}

    def load_font(
        self, path: Optional[str] = None, size: Optional[int] = None
    ) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
        """
        Load a font at the specified path and size (with caching).

        Args:
            path: Font file path, or None to use default from config
            size: Font size, or None to use default from config

        Returns:
            Loaded font or default PIL font
        """
        path = path or self.default_path
        size = size or self.default_size

        cache_key = (path, size)

        # Return cached font if available
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Load new font
        font = None
        if path:
            try:
                font = ImageFont.truetype(path, size)
            except Exception as e:
                print(f"Warning: Could not load font {path} at size {size}: {e}")

        if font is None:
            font = ImageFont.load_default()

        # Cache and return
        self._cache[cache_key] = font
        return font

    def get_font(
        self, path: Optional[str] = None, size: Optional[int] = None
    ) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
        """Get a font at the specified path and size (alias for load_font)"""
        return self.load_font(path, size)
