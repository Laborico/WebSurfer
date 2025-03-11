from .functions2 import parse_color
from .paintcommand import PaintCommand
import skia


class DrawOutline(PaintCommand):
    def __init__(self, rect, color, thickness):
        super().__init__(rect)
        self.color = color
        self.thickness = thickness

    def execute(self, canvas):
        paint = skia.Paint(
                Color=parse_color(self.color),
                StrokeWidth=self.thickness,
                Style=skia.Paint.kStroke_Style)

        canvas.drawRect(self.rect, paint)
