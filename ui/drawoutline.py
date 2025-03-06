from .functions2 import parse_color
import skia


class DrawOutline:
    def __init__(self, rect, color, thickness):
        self.rect = rect
        self.color = color
        self.thickness = thickness

    def execute(self, canvas):
        paint = skia.Paint(
                Color=parse_color(self.color),
                StrokeWidth=self.thickness,
                Style=skia.Paint.kStroke_Style)

        canvas.drawRect(self.rect, paint)
