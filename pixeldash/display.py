"""
Display adapter abstraction

A Display is anything that can show an image.
This lets us swap between emulator and real hardware easily.
"""

from abc import ABC, abstractmethod
from PIL import Image
from pixeldash.config import get_config


class Display(ABC):
    """Abstract display interface"""

    def __init__(self, width: int, height: int):
        """
        Args:
            width: Display width in pixels
            height: Display height in pixels
        """
        self.width = width
        self.height = height

    def _ensure_rgb(self, image: Image.Image) -> Image.Image:
        """Convert image to RGB if needed"""
        if image.mode != "RGB":
            return image.convert("RGB")
        return image

    def poll_input(self) -> list[str]:
        """Return input actions, if supported by this display."""
        return []

    @abstractmethod
    def show(self, image: Image.Image) -> None:
        """
        Display an image.

        Args:
            image: PIL Image to display (should be width x height, RGB)
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear the display (show black)"""
        pass

    @abstractmethod
    def close(self) -> None:
        """Clean up resources"""
        pass


class EmulatorDisplay(Display):
    """Display adapter using pygame emulator"""

    def __init__(self):
        """Initialize emulator display from config"""
        import pygame

        config = get_config()

        width = config.get("display.width")
        height = config.get("display.height")
        pixel_size = config.get("emulator.pixel_size")

        super().__init__(width, height)

        self.pygame = pygame
        self.pixel_size = pixel_size
        self.window_width = width * pixel_size
        self.window_height = height * pixel_size

        self.pygame.display.init()
        try:
            self.screen = pygame.display.set_mode((self.window_width, self.window_height))
            self.pygame.display.set_caption("Pixeldash")
        except pygame.error:
            self.pygame.display.quit()
            raise

    def poll_input(self) -> list[str]:
        actions = []
        for event in self.pygame.event.get():
            if event.type == self.pygame.QUIT:
                actions.append("quit")
            elif event.type == self.pygame.KEYDOWN:
                if event.key in (self.pygame.K_q, self.pygame.K_ESCAPE):
                    actions.append("quit")
                elif event.key in (self.pygame.K_RIGHT, self.pygame.K_SPACE):
                    actions.append("next")
                elif event.key == self.pygame.K_LEFT:
                    actions.append("previous")
        return actions

    def show(self, image: Image.Image) -> None:
        """Display an image in the emulator window"""
        image = self._ensure_rgb(image)

        # Scale up to window size
        scaled = image.resize(
            (self.window_width, self.window_height),
            Image.Resampling.NEAREST,  # Keep it pixelated
        )

        # Convert to pygame surface
        py_image = self.pygame.image.fromstring(scaled.tobytes(), scaled.size, "RGB")

        # Draw and update
        self.screen.blit(py_image, (0, 0))
        self.pygame.display.flip()

    def clear(self) -> None:
        """Show black screen"""
        black = Image.new("RGB", (self.width, self.height), color=(0, 0, 0))
        self.show(black)

    def close(self) -> None:
        """Close the window"""
        self.pygame.display.quit()


class MatrixDisplay(Display):
    """Display adapter for actual RGB LED matrix hardware"""

    def __init__(self):
        """Initialize matrix display from config"""
        config = get_config()
        from pixeldash.matrix_import import get_matrix_classes

        # Get dimensions
        width = config.get("display.width")
        height = config.get("display.height")
        super().__init__(width, height)

        matrix = config.get("matrix")
        if (matrix["cols"] * matrix["chain_length"], matrix["rows"] * matrix["parallel"]) != (
            width, height
        ):
            raise ValueError("display size must match matrix cols/rows and chain_length/parallel")

        RGBMatrix, RGBMatrixOptions = get_matrix_classes()
        options = RGBMatrixOptions()
        for key, value in config.get("matrix").items():
            if hasattr(options, key):
                setattr(options, key, value)

        # Create matrix
        self.matrix = RGBMatrix(options=options)

    def show(self, image: Image.Image) -> None:
        """Display image on the LED matrix"""
        image = self._ensure_rgb(image)

        # Set the image on the matrix
        self.matrix.SetImage(image)

    def clear(self) -> None:
        """Clear the matrix"""
        self.matrix.Clear()

    def close(self) -> None:
        """Clean up"""
        self.clear()
