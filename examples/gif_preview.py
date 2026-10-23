"""Preview an animated GIF in the desktop emulator."""

import argparse
from pathlib import Path
from PIL import Image

from pixeldash.screen import Screen
from pixeldash.display import EmulatorDisplay
from pixeldash.cli import run
from pixeldash.screen_manager import ScreenManager


ICON_POS = (22, 8)  # Centered position for icon
ICON_SIZE = (21, 21)  # Icon size


class GifScreen(Screen):
    """Display frames from a user-supplied GIF."""

    def __init__(self, gif_path: str):
        super().__init__()

        self.gif_path = Path(gif_path)
        self.icon_gif = None
        self.current_frame = 0
        self.frame_count = 0

        # Load the GIF
        try:
            self.icon_gif = Image.open(self.gif_path)
            # Count frames
            self.frame_count = 0
            try:
                while True:
                    self.icon_gif.seek(self.frame_count)
                    self.frame_count += 1
            except EOFError:
                pass
            self.icon_gif.seek(0)  # Reset to first frame
            print(f"Loaded GIF with {self.frame_count} frames")
        except (OSError, ValueError) as exc:
            raise ValueError(f"Could not load GIF: {self.gif_path}") from exc

    def render(self) -> Image.Image:
        # Create canvas
        image, draw = self.create_canvas()

        # Draw the current frame
        if self.icon_gif and self.frame_count > 0:
            try:
                # Seek to current frame
                self.icon_gif.seek(self.current_frame)
                frame = self.icon_gif.copy()

                # Resize
                frame = frame.resize(ICON_SIZE, Image.Resampling.LANCZOS)

                # Convert to RGB
                if frame.mode != "RGB":
                    rgb_frame = Image.new("RGB", frame.size, (0, 0, 0))
                    if frame.mode == "RGBA":
                        rgb_frame.paste(frame, mask=frame.split()[3])
                    else:
                        rgb_frame.paste(frame)
                    frame = rgb_frame

                # Paste onto canvas
                image.paste(frame, ICON_POS)

                # Advance to next frame
                self.current_frame = (self.current_frame + 1) % self.frame_count

            except Exception as e:
                print(f"Error rendering frame: {e}")

        return image


def main():
    parser = argparse.ArgumentParser(description="Preview a GIF in the desktop emulator")
    parser.add_argument("gif", type=Path, help="animation file to display")
    args = parser.parse_args()
    try:
        screen = GifScreen(str(args.gif.expanduser()))
    except ValueError as exc:
        parser.error(str(exc))
    display = EmulatorDisplay()
    try:
        run(display, ScreenManager([screen]))
    except KeyboardInterrupt:
        pass
    finally:
        display.close()


if __name__ == "__main__":
    main()
