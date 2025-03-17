from html_parser.text import Text
from .variables import BLOCK_ELEMENTS, INPUT_WIDTH_PX
from .functions import paint_visual_effects, dpx, font
from .textlayout import TextLayout
from .drawrect import DrawRRect
from .linelayout import LineLayout
from .inputlayout import InputLayout
from .imagelayout import ImageLayout
from .iframelayout import IframeLayout
from .variables import IFRAME_WIDTH_PX
import skia


class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.display_list = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.layout_object = self
        self.frame = frame

    def recurse(self, node):
        if isinstance(node, Text):
            for word in node.text.split():
                self.word(node, word)
        else:
            if node.tag == 'br':
                self.new_line()
            elif node.tag == 'input' or node.tag == 'button':
                self.input(node)
            elif node.tag == 'img':
                self.image(node)
            elif node.tag == 'iframe' and 'src' in node.attributes:
                self.iframe(node)
            else:
                for child in node.children:
                    self.recurse(child)

    def word(self, node, word):
        node_font = font(node.style, self.zoom)
        w = node_font.measureText(word)
        self.add_inline_child(node, w, TextLayout, self.frame, word)

    def layout_mode(self):
        if isinstance(self.node, Text):
            return 'inline'
        elif self.node.children:
            for child in self.node.children:
                if isinstance(child, Text):
                    continue
                if child.tag in BLOCK_ELEMENTS:
                    return "block"
            return "inline"
        elif self.node.tag in ["input", "img", "iframe"]:
            return "inline"
        else:
            return "block"

    def layout(self):
        self.zoom = self.parent.zoom
        self.x = self.parent.x
        self.width = self.parent.width

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        mode = self.layout_mode()
        if mode == 'block':
            previous = None
            for child in self.node.children:
                next = BlockLayout(child, self, previous, self.frame)
                self.children.append(next)
                previous = next

        else:
            self.new_line()
            self.recurse(self.node)

        for child in self.children:
            child.layout()

        self.height = sum([child.height for child in self.children])

    def paint(self):
        cmds = []

        bgcolor = self.node.style.get('background-color', 'transparent')

        if bgcolor != 'transparent':
            radius = dpx(float(
                    self.node.style.get(
                        'border-radius', '0px')[:-2]), self.zoom)
            cmds.append(DrawRRect(
                self.self_rect(), radius, bgcolor))

        return cmds

    def new_line(self):
        self.cursor_x = self.x
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)

    def self_rect(self):
        return skia.Rect.MakeLTRB(self.x, self.y, self.x + self.width,
                                  self.y + self.height)

    def input(self, node):
        w = dpx(INPUT_WIDTH_PX, self.zoom)
        self.add_inline_child(node, w, InputLayout, self.frame)

    def should_paint(self):
        return isinstance(self.node, Text) or \
                (self.node.tag not in ["input", "button", "img", "iframe"])

    def paint_effects(self, cmds):
        cmds = paint_visual_effects(
                self.node, cmds, self.self_rect())
        return cmds

    def add_inline_child(self, node, w, child_class, frame, word=None):
        if self.cursor_x + w > self.x + self.width:
            self.new_line()

        line = self.children[-1]
        previous_word = line.children[-1] if line.children else None

        if word:
            child = child_class(node, word, line, previous_word)
        else:
            child = child_class(node, line, previous_word, frame)
        line.children.append(child)

        self.cursor_x += w + font(node.style, self.zoom).measureText(' ')

    def image(self, node):
        if 'width' in node.attributes:
            w = dpx(int(node.attributes['width']), self.zoom)
        else:
            w = dpx(node.image.width(), self.zoom)
        self.add_inline_child(node, w, ImageLayout, self.frame)

    def iframe(self, node):
        if 'width' in self.node.attributes:
            w = dpx(int(self.node.attributes['width']),
                    self.zoom)
        else:
            w = IFRAME_WIDTH_PX + dpx(2, self.zoom)
        self.add_inline_child(node, w, IframeLayout, self.frame)
