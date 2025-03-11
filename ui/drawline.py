from .functions2 import parse_color
from .paintcommand import PaintCommand
import skia


class DrawLine(PaintCommand):
    def __init__(self, x1, y1, x2, y2, color, thickness):
        super().__init__(skia.Rect.MakeLTRB(x1, y1, x2, y2))
        self.color = color
        self.thickness = thickness

    def execute(self, canvas):
        path = skia.Path().moveTo(
                self.rect.left(), self.rect.top()) \
                        .lineTo(self.rect.right(),
                                self.rect.bottom())

        paint = skia.Paint(
                Color=parse_color(self.color),
                StrokeWidth=self.thickness,
                Style=skia.Paint.kStroke_Style)

        canvas.drawPath(path, paint)
