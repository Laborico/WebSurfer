from html_parser.text import Text
from html_parser.element import Element
from .variables import BLOCK_ELEMENTS, INPUT_WIDTH_PX
from .functions import get_font, paint_visual_effects, dpx
from .textlayout import TextLayout
from .drawrect import DrawRRect
from .linelayout import LineLayout
from .inputlayout import InputLayout
import skia


class BlockLayout:
    def __init__(self, node, parent, previous):
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

    def recurse(self, node):
        if isinstance(node, Text):
            for word in node.text.split():
                self.word(node, word)
        else:
            if node.tag == 'br':
                self.new_line()
            elif node.tag == 'input' or node.tag == 'button':
                self.input(node)
            else:
                for child in node.children:
                    self.recurse(child)

    def word(self, node, word):
        weight = node.style['font-weight']
        style = node.style['font-style']
        px_size = float(node.style['font-size'][:-2])
        size = dpx(px_size * 0.75, self.zoom)

        font = get_font(size, weight, size)
        w = font.measureText(word)

        if self.cursor_x + w > self.width:
            self.new_line()

        line = self.children[-1]
        previous_word = line.children[-1] if line.children else None
        text = TextLayout(node, word, line, previous_word)
        line.children.append(text)
        self.cursor_x += w + font.measureText(' ')

    def layout_mode(self):
        if isinstance(self.node, Text):
            return 'inline'
        elif any([isinstance(child, Element) and child.tag in
                  BLOCK_ELEMENTS for child in self.node.children]):
            return 'block'
        elif self.node.children or self.node.tag == 'input':
            return 'inline'
        else:
            return 'block'

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
                next = BlockLayout(child, self, previous)
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
        self.cursor_x = 0
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)

    def self_rect(self):
        return skia.Rect.MakeLTRB(self.x, self.y, self.x + self.width,
                                  self.y + self.height)

    def input(self, node):
        w = dpx(INPUT_WIDTH_PX, self.zoom)
        if self.cursor_x + w > self.width:
            self.new_line()

        line = self.children[-1]
        previous_word = line.children[-1] if line.children else None
        input = InputLayout(node, line, previous_word)
        line.children.append(input)

        weight = node.style['font-weight']
        style = node.style['font-style']

        px_size = float(node.style['font-size'][:-2])
        size = dpx(px_size * 0.75, self.zoom)
        font = get_font(size, weight, size)

        self.cursor_x += w + font.measureText(' ')

    def should_paint(self):
        return isinstance(self.node, Text) or \
                (self.node.tag != 'input' and self.node.tag != 'button')

    def paint_effects(self, cmds):
        cmds = paint_visual_effects(
                self.node, cmds, self.self_rect())
        return cmds
