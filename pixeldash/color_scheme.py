"""
Color scheme loader - supports iTerm2/Gogh JSON color schemes
"""

import json
from pathlib import Path
from typing import Dict, List

# Type alias for RGB color
RGB = tuple[int, int, int]


# Package directory for finding color schemes
from pixeldash.config import COLOR_SCHEMES_DIR


def hex_to_rgb(hex_color: str) -> RGB:
    """
    Convert hex color to RGB tuple.

    Args:
        hex_color: Hex string like '#RRGGBB' or 'RRGGBB'

    Returns:
        RGB tuple (r, g, b)
    """
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (r, g, b)


class ColorScheme:
    """A color scheme loaded from iTerm2/Gogh JSON format"""

    def __init__(self, data: dict):
        self.name = data.get("name", "Unnamed")
        self.comment = data.get("comment", "")

        # Convert all hex colors to RGB
        self.background = hex_to_rgb(data.get("background-color", "#000000"))
        self.foreground = hex_to_rgb(data.get("foreground-color", "#FFFFFF"))
        self.cursor = hex_to_rgb(data.get("cursor-color", "#FFFFFF"))
        self.bold = hex_to_rgb(data.get("bold-color", "#FFFFFF"))
        self.highlight_bg = hex_to_rgb(data.get("highlight-background-color", "#333333"))
        self.highlight_fg = hex_to_rgb(data.get("highlight-foreground-color", "#FFFFFF"))

        # Palette (16 colors for ANSI compatibility)
        palette_data = data.get("palette", [])
        self.palette: List[RGB] = [hex_to_rgb(color) for color in palette_data]

        # Convenience: named palette colors
        if len(self.palette) >= 16:
            self.black = self.palette[0]
            self.red = self.palette[1]
            self.green = self.palette[2]
            self.yellow = self.palette[3]
            self.blue = self.palette[4]
            self.magenta = self.palette[5]
            self.cyan = self.palette[6]
            self.white = self.palette[7]
            self.bright_black = self.palette[8]
            self.bright_red = self.palette[9]
            self.bright_green = self.palette[10]
            self.bright_yellow = self.palette[11]
            self.bright_blue = self.palette[12]
            self.bright_magenta = self.palette[13]
            self.bright_cyan = self.palette[14]
            self.bright_white = self.palette[15]

    @classmethod
    def from_file(cls, path: Path) -> "ColorScheme":
        """Load a color scheme from a JSON file"""
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return cls(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in color scheme file {path}: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load color scheme from {path}: {e}")

    @classmethod
    def from_name(cls, name: str) -> "ColorScheme":
        """
        Load a built-in color scheme by name (case-insensitive).

        Args:
            name: Scheme name (e.g., "Kanagawa", "Dracula")

        Returns:
            ColorScheme instance
        """
        if not COLOR_SCHEMES_DIR.exists():
            raise FileNotFoundError(
                f"Color schemes directory not found at {COLOR_SCHEMES_DIR}"
            )

        # Build case-insensitive map of available schemes
        available_schemes = {f.stem.lower(): f for f in COLOR_SCHEMES_DIR.glob("*.json")}

        scheme_path = available_schemes.get(name.lower())
        if not scheme_path:
            raise FileNotFoundError(
                f"Color scheme '{name}' not found at {COLOR_SCHEMES_DIR}. "
                f"Available schemes: {', '.join(sorted(available_schemes.keys()))}. "
                f"Download more from https://github.com/mbadolato/iTerm2-Color-Schemes"
            )

        return cls.from_file(scheme_path)

    def get_color(self, index: int) -> RGB:
        """Get a palette color by index (0-15)"""
        if 0 <= index < len(self.palette):
            return self.palette[index]
        return (255, 255, 255)  # Default to white


# Cache loaded schemes
_schemes_cache: Dict[str, ColorScheme] = {}


def get_color_scheme(name: str) -> ColorScheme:
    """
    Get a color scheme, with caching.

    Args:
        name: Scheme name (e.g., "Kanagawa", "Dracula")

    Returns:
        ColorScheme instance
    """
    if name not in _schemes_cache:
        _schemes_cache[name] = ColorScheme.from_name(name)
    return _schemes_cache[name]


def list_available_schemes() -> List[str]:
    """List all available color scheme names"""
    if not COLOR_SCHEMES_DIR.exists():
        return []

    return [f.stem for f in COLOR_SCHEMES_DIR.glob("*.json")]
