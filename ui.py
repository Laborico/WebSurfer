import tkinter
import tkinter.font
from html_parser import Text, HTMLParser

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100
FONTS = {}


class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
                self.window,
                width=WIDTH,
                height=HEIGHT
                )
        self.canvas.pack()
        self.scroll = 0
        self.window.bind('<Down>', self.scrolldown)

    def draw(self):
        self.canvas.delete('all')
        for x, y, word, f in self.display_list:
            if y > self.scroll + HEIGHT:
                continue
            if y + VSTEP < self.scroll:
                continue
            self.canvas.create_text(
                    x, y - self.scroll,
                    text=word, anchor='nw',
                    font=f
                    )

    def load(self, url):
        body = url.request()

        self.nodes = HTMLParser(body).parse()
        self.display_list = Layout(self.nodes).display_list
        self.draw()

    def scrolldown(self, e):
        self.scroll += SCROLL_STEP
        self.draw()


class Layout:
    def __init__(self, tokens):
        self.display_list = []
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = 'normal'
        self.style = 'roman'
        self.size = 12
        self.line = []

        self.recurse(tokens)

        self.flush()

    def recurse(self, tree):
        if isinstance(tree, Text):
            for word in tree.text.split():
                self.word(word)
        else:
            self.open_tag(tree.tag)
            for child in tree.children:
                self.recurse(child)
            self.close_tag(tree.tag)

    def open_tag(self, tag):
        if tag == 'i':
            self.style = 'italic'
        elif tag == 'b':
            self.weight = 'bold'
        elif tag == 'small':
            self.size -= 2
        elif tag == 'big':
            self.size += 4
        elif tag == 'br':
            self.flush()

    def close_tag(self, tag):
        if tag == 'i':
            self.style = 'roman'
        elif tag == 'b':
            self.weight = 'normal'
        elif tag == 'small':
            self.size += 2
        elif tag == 'big':
            self.size -= 4
        elif tag == 'p':
            self.flush()
            self.cursor_y += VSTEP

    def word(self, word):
        font = get_font(self.size, self.weight, self.style)
        w = font.measure(word)

        self.line.append((self.cursor_x, word, font))
        self.cursor_x += w + font.measure(' ')

        if self.cursor_x + w > WIDTH - HSTEP:
            self.flush()

    # Aligns the words on a line, handles big and small tags font size changes
    def flush(self):
        if not self.line:
            return
        metrics = [font.metrics() for x, word, font in self.line]
        max_ascent = max([metric['ascent'] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent

        for x, word, font in self.line:
            y = baseline - font.metrics('ascent')
            self.display_list.append((x, y, word, font))

        max_descent = max([metric['descent'] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent

        self.cursor_x = HSTEP
        self.line = []


# Memoazation for the win, text caching to improve text rendering speed
def get_font(size, weight, style):
    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(
                size=size,
                weight=weight,
                slant=style
                )
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)

    return FONTS[key][0]
