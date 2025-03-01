from html_parser.text import Text
from html_parser.element import Element
from .variables import VSTEP, BLOCK_ELEMENTS
from .functions import get_font
from .textlayout import TextLayout
from .drawrect import DrawRect
from .linelayout import LineLayout
from .rectangle import Rect


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

    def recurse(self, node):
        if isinstance(node, Text):
            for word in node.text.split():
                self.word(node, word)
        else:
            if node.tag == 'br':
                self.new_line()
            for child in node.children:
                self.recurse(child)

    def word(self, node, word):
        weight = node.style['font-weight']
        style = node.style['font-style']
        if style == 'normal':
            style = 'roman'
        size = int(float(node.style['font-size'][:-2]) * .75)

        font = get_font(size, weight, style)
        w = font.measure(word)

        if self.cursor_x + w > self.width:
            self.new_line()

        line = self.children[-1]
        previous_word = line.children[-1] if line.children else None
        text = TextLayout(node, word, line, previous_word)
        line.children.append(text)
        self.cursor_x += w + font.measure(' ')

    def layout_mode(self):
        if isinstance(self.node, Text):
            return 'inline'
        elif any([isinstance(child, Element) and child.tag in
                  BLOCK_ELEMENTS for child in self.node.children]):
            return 'block'
        elif self.node.children:
            return 'inline'
        else:
            return 'block'

    def layout(self):
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
            rect = DrawRect(self.self_rect(), bgcolor)
            cmds.append(rect)

        return cmds

    def new_line(self):
        self.cursor_x = 0
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)

    def self_rect(self):
        return Rect(self.x, self.y, self.x + self.width,
                    self.y + self.height)
