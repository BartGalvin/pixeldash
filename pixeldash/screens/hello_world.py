"""
Hello World screen
"""

from PIL import Image
from pixeldash.screen import Screen


class HelloWorldScreen(Screen):
    """Simple screen that shows 'Hello World'"""

    def render(self) -> Image.Image:
        image, draw = self.create_canvas()
        draw.text((5, 10), "Hello World", font=self.font, fill=(255, 255, 255))
        return image
