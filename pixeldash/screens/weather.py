"""
Weather screen
"""

from PIL import Image, ImageDraw
from pixeldash.screen import Screen
from pixeldash.services.weather_service import WeatherService
from pixeldash.config import get_config, IMAGE_DIR


ICON_POS = (2, 8)  # Position to paste weather icon
TEMP_POS = (20, 10)  # Position to draw temperature
CITY_POS = (20, 18)  # Position to draw city name
ERR_POS_1 = (2, 12)  # Position to draw error text
ERR_POS_2 = (2, 20)  # Position to draw error text

ICON_SIZE = (16, 16)  # Size to resize weather icon to

# Default colors (used if no color scheme is set)
WHITE = (255, 255, 255)
SLATE_BLUE = (100, 100, 255)


class WeatherScreen(Screen):
    """Display current weather conditions"""

    def __init__(self):
        super().__init__()
        self.weather_service = WeatherService()

        # Set up colors from color scheme or use defaults
        if self.color_scheme:
            self.text_color = self.color_scheme.foreground
            self.city_color = self.color_scheme.blue
            self.background_color = self.color_scheme.background
        else:
            self.text_color = WHITE
            self.city_color = SLATE_BLUE
            self.background_color = (0, 0, 0)

        # Get config for display preferences
        config = get_config()
        self.units = config.get("weather.units")
        self.city = config.get("weather.city").split(",")[0]  # Just show city name
        self.icon_dir = IMAGE_DIR / "weather"

        # Scrolling text state
        self.scroll_offset = 0
        self.scroll_speed = 1  # pixels per frame
        self.scroll_delay = 30  # frames to wait before scrolling
        self.scroll_counter = 0

        # Animation state
        self.current_icon_code = None
        self.icon_gif = None
        self.current_frame = 0
        self.frame_count = 0

    def display_error(self, text_line1: str, text_line2: str) -> Image.Image:
        """Display an error message on the screen"""
        image, draw = self.create_canvas(color=self.background_color)
        draw.text(ERR_POS_1, text_line1, font=self.font, fill=self.text_color)
        draw.text(ERR_POS_2, text_line2, font=self.font, fill=self.text_color)
        return image

    def get_temperature(self) -> str | None:
        """Get the current temperature as a formatted string"""
        temp = self.weather_service.get_temperature()
        if temp is None:
            return None
        temp_rounded = round(temp)
        unit_symbol = "F" if self.units == "imperial" else "C"
        return f"{temp_rounded}°{unit_symbol}"

    def draw_icon(self, image: Image.Image, icon_code: str) -> Image.Image:
        """Draw weather icon - supports both static PNG and animated GIF"""
        # Check if icon changed (reload if needed)
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
                    self.icon_gif.seek(0)  # Reset to first frame
                except Exception as e:
                    print(f"Warning: Could not load GIF {gif_path}: {e}")
                    self.icon_gif = None
            elif png_path.exists():
                self.icon_gif = None  # Use static PNG
            else:
                print(f"Warning: No icon found for {icon_code}")
                return image

        # Draw the current frame
        try:
            if self.icon_gif:
                # Animated GIF
                self.icon_gif.seek(self.current_frame)
                frame = self.icon_gif.copy()

                # Resize
                frame = frame.resize(ICON_SIZE, Image.Resampling.LANCZOS)

                if frame.mode != "RGB":
                    frame = frame.convert("RGB")

                image.paste(frame, ICON_POS)

                # Advance to next frame
                self.current_frame = (self.current_frame + 1) % self.frame_count
            else:
                # Static PNG
                png_path = self.icon_dir / f"{icon_code}.png"
                icon = Image.open(png_path)
                icon = icon.resize(ICON_SIZE, Image.Resampling.LANCZOS)
                if icon.mode != "RGB":
                    icon = icon.convert("RGB")
                image.paste(icon, ICON_POS)

        except Exception as e:
            print(f"Warning: Could not draw icon: {e}")

        return image

    def draw_scrolling_text(
        self, draw: ImageDraw.ImageDraw, text: str, position: tuple[int, int]
    ) -> None:
        """Draw text that scrolls if too long to fit, clipped to available area"""
        # Calculate text width and available space
        bbox = draw.textbbox((0, 0), text, font=self.font)
        text_width = int(bbox[2] - bbox[0])
        text_height = int(bbox[3] - bbox[1])
        available_width = self.width - position[0]  # All space from position to right edge

        # If text fits, just draw it
        if text_width <= available_width:
            draw.text(position, text, font=self.font, fill=self.city_color)
            self.scroll_offset = 0
        else:
            # Create a temporary image for the text
            temp_image = Image.new("RGB", (text_width, text_height), color=(0, 0, 0))
            temp_draw = ImageDraw.Draw(temp_image)
            temp_draw.text((0, 0), text, font=self.font, fill=self.city_color)

            # Crop to the visible portion (with scrolling offset)
            crop_x = self.scroll_offset
            crop_box = (crop_x, 0, crop_x + available_width, text_height)
            visible_portion = temp_image.crop(crop_box)

            # Paste the visible portion at the position
            draw._image.paste(visible_portion, position)

            # Update scroll position
            self.scroll_counter += 1
            if self.scroll_counter > self.scroll_delay:
                self.scroll_offset += self.scroll_speed

                # Reset when we've scrolled through all the text
                if self.scroll_offset > text_width - available_width + 10:  # Add gap before loop
                    self.scroll_offset = 0
                    self.scroll_counter = 0

    def draw_text(
        self, image: Image.Image, draw: ImageDraw.ImageDraw, temp_str: str
    ) -> Image.Image:
        """Draw temperature and city name on the image"""
        # Draw temperature on the right side of icon
        draw.text(TEMP_POS, temp_str, font=self.font, fill=self.text_color)

        # Draw city name with scrolling if needed
        self.draw_scrolling_text(draw, self.city, CITY_POS)

        return image

    def render(self) -> Image.Image:
        """Render the weather display"""
        image, draw = self.create_canvas(color=self.background_color)

        # Get weather data
        temp_str = self.get_temperature()
        if temp_str is None:
            return self.display_error("Weather data", "not available")

        icon_code = self.weather_service.get_icon_code()
        if icon_code is None:
            return self.display_error("Weather icon", "not available")

        image = self.draw_icon(image, icon_code)
        image = self.draw_text(image, draw, temp_str)

        return image
