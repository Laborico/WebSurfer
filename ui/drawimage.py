import skia
from .paintcommand import PaintCommand
from .functions import parse_image_rendering


class DrawImage(PaintCommand):
    def __init__(self, image, rect, quality):
        super().__init__(rect)
        self.image = image
        self.quality = parse_image_rendering(quality)

    def execute(self, canvas):
        paint = skia.Paint(FilterQuality=self.quality)
        canvas.drawImageRect(self.image, self.rect, paint)
