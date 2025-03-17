from .embedlayout import EmbedLayout
from .drawimage import DrawImage
from .functions import dpx, linespace
import skia


class ImageLayout(EmbedLayout):
    def __init__(self, node, parent, previous, frame):
        super().__init__(node, parent, previous, frame)

    def layout(self):
        super().layout()

        width_attr = self.node.attributes.get('width')
        height_attr = self.node.attributes.get('height')
        image_width = self.node.image.width()
        image_height = self.node.image.height()

        aspect_ratio = image_width / image_height

        if width_attr and height_attr:
            self.width = dpx(int(width_attr), self.zoom)
            self.img_height = dpx(int(height_attr), self.zoom)
        elif width_attr:
            self.width = dpx(int(width_attr), self.zoom)
            self.img_height = self.width / aspect_ratio
        elif height_attr:
            self.img_height = dpx(int(height_attr), self.zoom)
            self.width = self.img_height * aspect_ratio
        else:
            self.width = dpx(image_width, self.zoom)
            self.img_height = dpx(image_height, self.zoom)

        self.height = max(self.img_height, linespace(self.font))

        self.ascent = -self.height
        self.descent = 0

    def paint(self):
        cmds = []
        rect = skia.Rect.MakeLTRB(
            self.x, self.y + self.height - self.img_height,
            self.x + self.width, self.y + self.height)

        quality = self.node.style.get('image-rendering', 'auto')
        cmds.append(DrawImage(self.node.image, rect, quality))

        return cmds

    def paint_effects(self, cmds):
        return cmds
