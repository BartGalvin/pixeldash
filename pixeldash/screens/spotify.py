"""
Spotify screen
"""

import requests
from PIL import Image, ImageDraw
from io import BytesIO
from pixeldash.screen import Screen
from pixeldash.services.spotify_service import SpotifyService


# Layout constants
ORIGIN = (0, 0)
LEFT_MARGIN = 1
ALBUM_ART_SIZE = (16, 16)
ALBUM_ART_TEXT_SPACING = 2
TEXT_X_START = LEFT_MARGIN + ALBUM_ART_SIZE[0] + ALBUM_ART_TEXT_SPACING
ERR_LEFT_MARGIN = 2
ROW_HEIGHT = 8

# Default colors (used if no color scheme is set)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (150, 150, 150)

# Network
HTTP_TIMEOUT = 5

# Time conversion
MS_TO_SECONDS = 1000
SECONDS_TO_MINUTES = 60


class SpotifyScreen(Screen):
    """Display currently playing Spotify track"""

    def __init__(self):
        super().__init__()
        self.spotify_service = SpotifyService()

        # Set up colors from color scheme or use defaults
        if self.color_scheme:
            self.text_color = self.color_scheme.foreground
            self.artist_color = self.color_scheme.cyan  # More colorful secondary color
            self.time_color = self.color_scheme.green
            self.background_color = self.color_scheme.background
        else:
            self.text_color = WHITE
            self.artist_color = GRAY
            self.time_color = WHITE
            self.background_color = BLACK

        # Calculate vertical positions for 3 rows (track, artist, time)
        # Using ALBUM_ART_SIZE[1] as row height to match album art
        row_positions = self.get_vertical_positions(1, ALBUM_ART_SIZE[1])
        album_art_center_y = row_positions[0]

        # Position album art
        self.album_art_pos = (LEFT_MARGIN, album_art_center_y)

        # Position text rows centered vertically
        text_row_positions = self.get_vertical_positions(3, ROW_HEIGHT)
        self.track_y = text_row_positions[0]
        self.artist_y = text_row_positions[1]
        self.time_y = text_row_positions[2]

        # Album art caching
        self.current_album_art_url = None
        self.album_art_image = None

        # Scrolling text state (synchronized for both track and artist)
        self.scroll_offset = 0
        self.scroll_counter = 0
        self.scroll_direction = 1  # 1 for right, -1 for left

        self.scroll_speed = 1  # pixels per frame
        self.scroll_delay = 10  # frames to wait before scrolling

    def format_time(self, ms: int) -> str:
        """Format milliseconds to MM:SS"""
        total_seconds = ms // MS_TO_SECONDS
        minutes = total_seconds // SECONDS_TO_MINUTES
        seconds = total_seconds % SECONDS_TO_MINUTES
        return f"{minutes}:{seconds:02d}"

    def display_error(self, text_line1: str, text_line2: str) -> Image.Image:
        """Display an error message on the screen"""
        image, draw = self.create_canvas(color=self.background_color)
        error_positions = self.get_vertical_positions(2, ROW_HEIGHT)
        draw.text(
            (ERR_LEFT_MARGIN, error_positions[0]), text_line1, font=self.font, fill=self.text_color
        )
        draw.text(
            (ERR_LEFT_MARGIN, error_positions[1]), text_line2, font=self.font, fill=self.text_color
        )
        return image

    def fetch_album_art(self, url: str) -> Image.Image | None:
        """Download and cache album art from URL"""
        # Use cache if URL hasn't changed
        if url == self.current_album_art_url and self.album_art_image is not None:
            return self.album_art_image

        try:
            response = requests.get(url, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))
            img = img.resize(ALBUM_ART_SIZE, Image.Resampling.LANCZOS)
            if img.mode != "RGB":
                img = img.convert("RGB")

            self.current_album_art_url = url
            self.album_art_image = img
            return img

        except Exception as e:
            print(f"Warning: Could not fetch album art: {e}")
            return None

    def render_text_to_image(
        self, text: str, text_width: int, text_height: int, color: tuple[int, int, int]
    ) -> Image.Image:
        """Render text to a temporary image for scrolling"""
        temp_image = Image.new("RGB", (text_width, text_height), color=self.background_color)
        temp_draw = ImageDraw.Draw(temp_image)
        temp_draw.text(ORIGIN, text, font=self.font, fill=color)
        return temp_image

    def crop_scrolled_text(
        self, text_image: Image.Image, text_width: int, available_width: int
    ) -> Image.Image:
        """Crop text image to visible scrolled portion"""
        max_offset = text_width - available_width
        clamped_offset = min(self.scroll_offset, max_offset)
        crop_box = (clamped_offset, 0, clamped_offset + available_width, text_image.height)
        return text_image.crop(crop_box)

    def draw_scrolling_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        position: tuple[int, int],
        color: tuple[int, int, int],
    ) -> None:
        """Draw text that scrolls back and forth if too long to fit"""
        # Calculate text dimensions and available space
        text_width = self.get_text_width(draw, text)
        bbox = draw.textbbox(ORIGIN, text, font=self.font)
        text_height = int(bbox[3] - bbox[1])
        available_width = self.width - position[0]

        # If text fits, just draw it directly
        if text_width <= available_width:
            draw.text(position, text, font=self.font, fill=color)
        else:
            # Render text to temporary image and crop to visible portion
            text_image = self.render_text_to_image(text, text_width, text_height, color)
            visible_portion = self.crop_scrolled_text(text_image, text_width, available_width)
            draw._image.paste(visible_portion, position)

    def update_scroll_state(self, draw: ImageDraw.ImageDraw, texts: list[str]) -> None:
        """Update synchronized scroll position for multiple texts"""
        available_width = self.width - TEXT_X_START

        # Calculate max scroll needed (use the longest text)
        max_scroll = 0
        for text in texts:
            text_width = self.get_text_width(draw, text)
            text_max_scroll = max(0, text_width - available_width)
            max_scroll = max(max_scroll, text_max_scroll)

        # Only scroll if at least one text needs it
        if max_scroll > 0:
            self.scroll_counter += 1

            if self.scroll_counter > self.scroll_delay:
                self.scroll_offset += self.scroll_speed * self.scroll_direction

                # Reverse direction at boundaries
                if self.scroll_offset >= max_scroll:
                    self.scroll_offset = max_scroll
                    self.scroll_direction = -1
                    self.scroll_counter = 0  # Pause at end
                elif self.scroll_offset <= 0:
                    self.scroll_offset = 0
                    self.scroll_direction = 1
                    self.scroll_counter = 0  # Pause at start

    def render(self) -> Image.Image:
        """Render the Spotify display"""
        image, draw = self.create_canvas(color=self.background_color)

        # Get current track
        track = self.spotify_service.get_current_track()

        if track is None:
            return self.display_error("No track", "playing")

        # Get track info
        track_name = track.get("name", "Unknown")
        artist_name = track.get("artist", "Unknown")
        album_art_url = track.get("album_art_url")
        progress_ms = track.get("progress_ms", 0)
        duration_ms = track.get("duration_ms", 0)

        # Draw album art if available
        if album_art_url:
            album_art = self.fetch_album_art(album_art_url)
            if album_art:
                image.paste(album_art, self.album_art_pos)

        # Draw track name with scrolling
        self.draw_scrolling_text(draw, track_name, (TEXT_X_START, self.track_y), self.text_color)

        # Draw artist name with scrolling
        self.draw_scrolling_text(
            draw, artist_name, (TEXT_X_START, self.artist_y), self.artist_color
        )

        # Draw elapsed/total time
        time_str = f"{self.format_time(progress_ms)}/{self.format_time(duration_ms)}"
        draw.text((TEXT_X_START, self.time_y), time_str, font=self.font, fill=self.time_color)

        # Update synchronized scroll position for both texts
        self.update_scroll_state(draw, [track_name, artist_name])

        return image
