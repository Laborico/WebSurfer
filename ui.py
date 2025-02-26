import tkinter
import tkinter.font
from html_parser import Text, Tag

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

        text = lex(body)
        self.display_list = Layout(text).display_list
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

        for tok in tokens:
            self.token(tok)

        self.flush()

    # Basic tokenizer for html tags
    def token(self, tok):
        if isinstance(tok, Text):
            for word in tok.text.split():
                self.word(word)

        elif tok.tag == 'i':
            self.style = 'italic'
        elif tok.tag == '/i':
            self.style = 'roman'
        elif tok.tag == 'b':
            self.weight = 'bold'
        elif tok.tag == '/b':
            self.weight = 'normal'
        elif tok.tag == 'small':
            self.size -= 2
        elif tok.tag == '/small':
            self.size += 2
        elif tok.tag == 'big':
            self.size += 4
        elif tok.tag == '/big':
            self.size -= 4
        elif tok.tag == 'br':
            self.flush()
        elif tok.tag == '/p':
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


# Basic HTML lex table, just searches for text and tags, without a tree, for now
def lex(body):
    out = []
    buffer = ''
    in_tag = False

    for c in body:
        if c == '<':
            in_tag = True
            if buffer:
                out.append(Text(buffer))
            buffer = ''
        elif c == '>':
            in_tag = False
            out.append(Tag(buffer))
            buffer = ''
        else:
            buffer += c

    if not in_tag and buffer:
        out.append(Text(buffer))

    return out


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
