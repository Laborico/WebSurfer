from .functions2 import parse_color
from .paintcommand import PaintCommand
import skia


class DrawText(PaintCommand):
    def __init__(self, x1, y1, text, font, color):
        self.font = font
        self.text = text
        self.color = color
        super().__init__(skia.Rect.MakeLTRB(
            x1, y1, x1 + font.measureText(text),
            y1 - font.getMetrics().fAscent + font.getMetrics().fDescent))

    def execute(self, canvas):
        paint = skia.Paint(
                AntiAlias=True,
                Color=parse_color(self.color))

        baseline = self.rect.top() - self.font.getMetrics().fAscent

        canvas.drawString(self.text, float(self.rect.left()),
                          baseline, self.font, paint)
