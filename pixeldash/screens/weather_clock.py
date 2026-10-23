"""
Combined Weather + Clock screen
"""

from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from pixeldash.screen import Screen
from pixeldash.services.weather_service import WeatherService
from pixeldash.config import get_config, IMAGE_DIR


TIME_FORMAT = "%H:%M"
DATE_FORMAT = "%a %b %d"  # e.g., "Mon Jan 15"
TIME_FONT_SIZE = 10
DATE_FONT_SIZE = 5
TEMP_FONT_SIZE = 5
ICON_SIZE = (8, 8)


class WeatherClockScreen(Screen):
    """Display current time, date, and weather in a compact layout"""

    def __init__(self):
        super().__init__()
        self.weather_service = WeatherService()

        # Get config
        config = get_config()
        self.units = config.get("weather.units")
        self.icon_dir = IMAGE_DIR / "weather"

        # Load fonts - different sizes for different elements
        self.time_font = self.font_manager.load_font(size=TIME_FONT_SIZE)
        self.date_font = self.font_manager.load_font(size=DATE_FONT_SIZE)
        self.temp_font = self.font_manager.load_font(size=TEMP_FONT_SIZE)

        # Set up colors from color scheme or use defaults
        if self.color_scheme:
            self.time_color = self.color_scheme.cyan
            self.date_color = self.color_scheme.foreground
            self.temp_color = self.color_scheme.yellow
            self.background_color = self.color_scheme.background
        else:
            self.time_color = (0, 255, 255)  # cyan
            self.date_color = (255, 255, 255)  # white
            self.temp_color = (255, 255, 0)  # yellow
            self.background_color = (0, 0, 0)  # black

        # Icon state for animated GIFs
        self.current_icon_code = None
        self.icon_gif = None
        self.current_frame = 0
        self.frame_count = 0

    def get_temperature(self) -> str | None:
        """Get the current temperature as a formatted string"""
        temp = self.weather_service.get_temperature()
        if temp is None:
            return None
        temp_rounded = round(temp)
        unit_symbol = "F" if self.units == "imperial" else "C"
        return f"{temp_rounded}°{unit_symbol}"

    def load_weather_icon(self, icon_code: str) -> Image.Image | None:
        """Load weather icon (animated GIF or static PNG)"""
        # Check if icon changed
        if icon_code != self.current_icon_code:
            self.current_icon_code = icon_code
            self.current_frame = 0

            # Try GIF first, then fall back to PNG
            gif_path = self.icon_dir / f"{icon_code}.gif"
            png_path = self.icon_dir / f"{icon_code}.png"

            if gif_path.exists():
                try:
                    self.icon_gif = Image.open(gif_path)
                    # Count frames
                    self.frame_count = 0
                    try:
                        while True:
                            self.icon_gif.seek(self.frame_count)
                            self.frame_count += 1
                    except EOFError:
                        pass
                    self.icon_gif.seek(0)
                except Exception as e:
                    print(f"Warning: Could not load GIF {gif_path}: {e}")
                    self.icon_gif = None
            elif png_path.exists():
                self.icon_gif = None
            else:
                print(f"Warning: No icon found for {icon_code}")
                return None

        # Get current frame
        try:
            if self.icon_gif:
                # Animated GIF
                self.icon_gif.seek(self.current_frame)
                frame = self.icon_gif.copy()
                frame = frame.resize(ICON_SIZE, Image.Resampling.LANCZOS)
                if frame.mode != "RGB":
                    frame = frame.convert("RGB")
                self.current_frame = (self.current_frame + 1) % self.frame_count
                return frame
            else:
                # Static PNG
                png_path = self.icon_dir / f"{icon_code}.png"
                icon = Image.open(png_path)
                icon = icon.resize(ICON_SIZE, Image.Resampling.LANCZOS)
                if icon.mode != "RGB":
                    icon = icon.convert("RGB")
                return icon
        except Exception as e:
            print(f"Warning: Could not load icon: {e}")
            return None

    def render(self) -> Image.Image:
        """Render the combined weather + clock display"""
        image, draw = self.create_canvas(color=self.background_color)

        # Get current time
        now = datetime.now()
        time_str = now.strftime(TIME_FORMAT)
        date_str = now.strftime(DATE_FORMAT)

        # Get weather data
        temp_str = self.get_temperature()
        icon_code = self.weather_service.get_icon_code()

        # Calculate vertical spacing for 3 rows (time, date, weather)
        time_height = TIME_FONT_SIZE + 2
        date_height = DATE_FONT_SIZE + 2
        weather_height = max(ICON_SIZE[1], TEMP_FONT_SIZE + 2)

        total_height = time_height + date_height + weather_height
        start_y = (self.height - total_height) // 2

        # Row Y positions
        time_y = start_y
        date_y = start_y + time_height
        weather_y = start_y + time_height + date_height

        # Draw time (centered)
        time_x = self.get_centered_x(draw, time_str, self.time_font)
        draw.text((time_x, time_y), time_str, font=self.time_font, fill=self.time_color)

        # Draw date (centered)
        date_x = self.get_centered_x(draw, date_str, self.date_font)
        draw.text((date_x, date_y), date_str, font=self.date_font, fill=self.date_color)

        # Draw weather icon + temp (centered as a unit)
        if temp_str and icon_code:
            # Calculate combined width of icon + temp
            temp_bbox = draw.textbbox((0, 0), temp_str, font=self.temp_font)
            temp_width = temp_bbox[2] - temp_bbox[0]
            temp_height = temp_bbox[3] - temp_bbox[1]
            combined_width = ICON_SIZE[0] + 2 + temp_width  # 2px spacing

            # Center the combined unit
            combined_x = (self.width - combined_width) // 2

            # Vertically center icon and text within the weather row
            icon_y = weather_y + (weather_height - ICON_SIZE[1]) // 2
            temp_y = weather_y + (weather_height - temp_height) // 2 + 1  # Nudge down 1px

            # Draw icon
            icon = self.load_weather_icon(icon_code)
            if icon:
                image.paste(icon, (combined_x, icon_y))

            # Draw temp next to icon
            temp_x = combined_x + ICON_SIZE[0] + 2
            draw.text((temp_x, temp_y), temp_str, font=self.temp_font, fill=self.temp_color)
        elif temp_str:
            # Just temp, no icon
            temp_x = self.get_centered_x(draw, temp_str, self.temp_font)
            draw.text((temp_x, weather_y), temp_str, font=self.temp_font, fill=self.temp_color)

        return image
