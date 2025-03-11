import skia
from .drawoutline import DrawOutline
from .variables import SHOW_COMPOSITED_LAYER_BORDERS
from .functions import local_to_absolute, absolute_to_local


class CompositedLayer:
    def __init__(self, skia_context, display_item):
        self.skia_context = skia_context
        self.surface = None
        self.display_items = [display_item]
        self.parent = display_item.parent

    def composited_bounds(self):
        rect = skia.Rect.MakeEmpty()
        for item in self.display_items:
            rect.join(absolute_to_local(
                item, local_to_absolute(item, item.rect)))
            rect.outset(1, 1)
            return rect

        rect.outset(1, 1)
        return rect

    def raster(self):
        bounds = self.composited_bounds()
        if bounds.isEmpty():
            return
        irect = bounds.roundOut()

        if not self.surface:
            self.surface = skia.Surface.MakeRenderTarget(
                    self.skia_context, skia.Budgeted.kNo,
                    skia.ImageInfo.MakeN32Premul(
                        irect.width(), irect.height()))
            if not self.surface:
                self.surface = skia.Surface(irect.width(), irect.height())
            assert self.surface

        canvas = self.surface.getCanvas()
        canvas.clear(skia.ColorTRANSPARENT)
        canvas.save()
        canvas.translate(-bounds.left(), -bounds.top())

        for item in self.display_items:
            item.execute(canvas)
        canvas.restore()

        if SHOW_COMPOSITED_LAYER_BORDERS:
            border_rect = skia.Rect.MakeXYWH(1, 1, irect.width() - 2,
                                             irect.height() - 2)
            DrawOutline(border_rect, 'red', 1).execute(canvas)

    def add(self, display_item):
        assert self.can_merge(display_item)
        self.display_items.append(display_item)

    def can_merge(self, display_item):
        return display_item.parent == self.display_items[0].parent

    def absoulte_bounds(self):
        rect = skia.Rect.MakeEmpty()
        for item in self.display_items:
            rect.join(local_to_absolute(item, item.rect))
        return rect
