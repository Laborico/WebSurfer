import tkinter
import tkinter.font
from url import URL
from html_parser import Text, HTMLParser, Element
from css_parser import DEFAULT_STYLE_SHEET, CSSParser
from css_parser import cascade_priority, style, tree_to_list

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100
FONTS = {}
BLOCK_ELEMENTS = [
        'html', 'body', 'article', 'section', 'nav', 'aside', 'h1', 'h2',
        'h3', 'h4', 'h5', 'h6', 'hgroup', 'header', 'footer', 'address',
        'p', 'hr', 'pre', 'blockquote', 'ol', 'ul', 'menu', 'li', 'dl',
        'dt', 'dd', 'figure', 'figcaption', 'main', 'div', 'table', 'form',
        'fieldset', 'legend', 'details', 'summary'
        ]


class Tab:
    def __init__(self, tab_height):
        self.url = None
        self.tab_height = tab_height
        self.history = []

    def draw(self, canvas, offset):

        for cmd in self.display_list:
            if cmd.rect.top > self.scroll + self.tab_height:
                continue
            if cmd.rect.bottom < self.scroll:
                continue
            cmd.execute(self.scroll - offset, canvas)

    def load(self, url):
        self.history.append(url)
        self.url = url
        body = url.request()
        self.scroll = 0

        self.nodes = HTMLParser(body).parse()
        rules = DEFAULT_STYLE_SHEET.copy()
        links = [node.attributes['href']
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == 'link'
                 and node.attributes.get('rel') == 'stylesheet'
                 and 'href' in node.attributes]
        for link in links:
            style_url = url.resolve(link)
            try:
                body = style_url.request()
            except Exception:
                continue
            rules.extend(CSSParser(body).parse())
        style(self.nodes, sorted(rules, key=cascade_priority))

        self.display_list = []
        self.document = DocumentLayout(self.nodes)
        self.document.layout()

        paint_tree(self.document, self.display_list)

    def scrolldown(self):
        max_y = max(self.document.height + 2*VSTEP - self.tab_height, 0)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)

    def click(self, x, y):
        y += self.scroll

        objs = [obj for obj in tree_to_list(self.document, [])
                if obj.x <= x < obj.x + obj.width
                and obj.y <= y < obj.y + obj.height]

        if not objs:
            return
        elt = objs[-1].node
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == 'a' and 'href' in elt.attributes:
                url = self.url.resolve(elt.attributes['href'])
                return self.load(url)

            elt = elt.parent

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)


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

    # Aligns the words on a line, handles big and small tags font size changes
    def flush(self):
        if not self.line:
            return
        metrics = [font.metrics() for x, word, font, color in self.line]
        max_ascent = max([metric['ascent'] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent

        for rel_x, word, font, color in self.line:
            x = self.x + rel_x
            y = self.y + baseline - font.metrics('ascent')
            self.display_list.append((x, y, word, font, color))

        max_descent = max([metric['descent'] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent

        self.cursor_x = 0
        self.line = []

    def layout_intermediate(self):
        previous = None
        for child in self.node.children:
            next = BlockLayout(child, self, previous)
            self.children.append(next)
            previous = next

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


class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.previous = None
        self.children = []

    def layout(self):
        child = BlockLayout(self.node, self, None)
        self.children.append(child)

        self.width = WIDTH - 2*HSTEP
        self.x = HSTEP
        self.y = VSTEP
        child.layout()
        self.height = child.height

    def paint(self):
        return []


class DrawText:
    def __init__(self, x1, y1, text, font, color):
        self.rect = Rect(x1, y1, x1 + font.measure(text),
                         y1 + font.metrics('linespace'))
        self.text = text
        self.font = font
        self.color = color

    def execute(self, scroll, canvas):
        canvas.create_text(
                self.rect.left, self.rect.top - scroll,
                text=self.text,
                font=self.font,
                anchor='nw',
                fill=self.color
                )


class DrawRect:
    def __init__(self, rect, color):
        self.rect = rect
        self.color = color

    def execute(self, scroll, canvas):
        canvas.create_rectangle(
                self.rect.left, self.rect.top - scroll,
                self.rect.right, self.rect.bottom - scroll,
                width=0,
                fill=self.color
                )


class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None

    def layout(self):
        self.width = self.parent.width
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        for word in self.children:
            word.layout()

        if not self.children:
            self.height = 0

        max_ascent = max([word.font.metrics('ascent')
                          for word in self.children])

        baseline = self.y + 1.25 * max_ascent

        for word in self.children:
            word.y = baseline - word.font.metrics('ascent')

        max_descent = max([word.font.metrics('descent')
                           for word in self.children])

        self.height = 1.25 * (max_ascent + max_descent)

    def paint(self):
        return []


class TextLayout:
    def __init__(self, node, word, parent, previous):
        self.node = node
        self.word = word
        self.children = []
        self.parent = parent
        self.previous = previous

    def layout(self):
        weight = self.node.style['font-weight']
        style = self.node.style['font-style']

        if style == 'normal':
            style = 'roman'

        size = int(float(self.node.style['font-size'][:-2]) * .75)
        self.font = get_font(size, weight, style)

        self.width = self.font.measure(self.word)

        if self.previous:
            space = self.previous.font.measure(' ')
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = self.font.metrics('linespace')

    def paint(self):
        color = self.node.style['color']
        return [DrawText(self.x, self.y, self.word, self.font, color)]


class Browser:
    def __init__(self):
        self.tabs = []
        self.active_tab = None
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
                self.window,
                width=WIDTH,
                height=HEIGHT,
                bg='white'
                )
        self.canvas.pack()
        self.scroll = 0
        self.window.bind('<Down>', self.handle_down)
        self.window.bind('<Button-1>', self.handle_click)
        self.window.bind('<Key>', self.handle_key)
        self.window.bind('<Return>', self.handle_enter)
        self.chrome = Chrome(self)

    def handle_down(self, e):
        self.active_tab.scrolldown()
        self.draw()

    def handle_click(self, e):
        if e.y < self.chrome.bottom:
            self.chrome.click(e.x, e.y)
        else:
            tab_y = e.y - self.chrome.bottom
            self.active_tab.click(e.x, tab_y)
        self.draw()

    def draw(self):
        self.canvas.delete('all')
        self.active_tab.draw(self.canvas, self.chrome.bottom)

        for cmd in self.chrome.paint():
            cmd.execute(0, self.canvas)

    def new_tab(self, url):
        new_tab = Tab(HEIGHT - self.chrome.bottom)
        new_tab.load(url)
        self.active_tab = new_tab
        self.tabs.append(new_tab)
        self.draw()

    def handle_key(self, e):
        if len(e.char) == 0:
            return
        if not (0x20 <= ord(e.char) < 0x7f):
            return
        self.chrome.keypress(e.char)
        self.draw()

    def handle_enter(self, e):
        self.chrome.enter()
        self.draw()


class Chrome:
    def __init__(self, browser):
        self.browser = browser
        self.font = get_font(20, 'normal', 'roman')
        self.font_height = self.font.metrics('linespace')

        self.padding = 5
        self.tabbar_top = 0
        self.tabbar_bottom = self.font_height + 2*self.padding

        plus_width = self.font.measure('+') + 2*self.padding
        self.newtab_rect = Rect(
                self.padding, self.padding,
                self.padding + plus_width,
                self.padding + self.font_height
                )

        self.urlbar_top = self.tabbar_bottom
        self.urlbar_bottom = self.urlbar_top + \
            self.font_height + 2*self.padding

        self.bottom = self.urlbar_bottom

        back_width = self.font.measure('<') + 2*self.padding
        self.back_rect = Rect(
                self.padding,
                self.urlbar_top + self.padding,
                self.padding + back_width,
                self.urlbar_bottom - self.padding)

        self.address_rect = Rect(
                self.back_rect.top + self.padding,
                self.urlbar_top + self.padding,
                WIDTH - self.padding,
                self.urlbar_bottom - self.padding)

        self.focus = None
        self.address_bar = ''

    def tab_rect(self, i):
        tabs_start = self.newtab_rect.right + self.padding
        tab_width = self.font.measure('Tab X') + 2*self.padding
        return Rect(
                tabs_start + tab_width * i, self.tabbar_top,
                tabs_start + tab_width * (i + 1), self.tabbar_bottom)

    def paint(self):
        cmds = []

        cmds.append(DrawRect(
            Rect(0, 0, WIDTH, self.bottom),
            'white'))
        cmds.append(DrawLine(
            0, self.bottom, WIDTH,
            self.bottom, 'black', 1))

        cmds.append(DrawOutline(self.newtab_rect, 'black', 1))
        cmds.append(DrawText(
            self.newtab_rect.left + self.padding,
            self.newtab_rect.top,
            '+', self.font, 'black'))

        for i, tab in enumerate(self.browser.tabs):
            bounds = self.tab_rect(i)
            cmds.append(DrawLine(
                bounds.left, 0, bounds.left, bounds.bottom,
                'black', 1))
            cmds.append(DrawLine(
                bounds.right, 0, bounds.right, bounds.bottom,
                'black', 1))
            cmds.append(DrawText(
                bounds.left + self.padding, bounds.top + self.padding,
                'Tab {}'.format(i), self.font, 'black'))

            if tab == self.browser.active_tab:
                cmds.append(DrawLine(
                    0, bounds.bottom, bounds.left, bounds.bottom,
                    'black', 1))
                cmds.append(DrawLine(
                    bounds.right, bounds.bottom, WIDTH, bounds.bottom,
                    'black', 1))

        cmds.append(DrawOutline(self.back_rect, 'black', 1))
        cmds.append(DrawText(
            self.back_rect.left + self.padding,
            self.back_rect.top,
            '<', self.font, 'black'))

        cmds.append(DrawOutline(self.address_rect, 'black', 1))

        if self.focus == 'address bar':
            cmds.append(DrawText(
                self.address_rect.left + self.padding,
                self.address_rect.top,
                self.address_bar, self.font, 'black'))

            w = self.font.measure(self.address_bar)

            cmds.append(DrawLine(
                self.address_rect.left + self.padding + w,
                self.address_rect.top,
                self.address_rect.left + self.padding + w,
                self.address_rect.bottom,
                'red', 1))
        else:
            url = str(self.browser.active_tab.url)
            cmds.append(DrawText(
                self.address_rect.left + self.padding,
                self.address_rect.top,
                url, self.font, 'black'))

        return cmds

    def click(self, x, y):
        self.focus = None
        if self.newtab_rect.contains_point(x, y):
            self.browser.new_tab(URL('https://www.wikipedia.org'))
        elif self.back_rect.contains_point(x, y):
            self.browser.active_tab.go_back()
        elif self.address_rect.contains_point(x, y):
            self.focus = 'address bar'
            self.address_bar = ''
        else:
            for i, tab in enumerate(self.browser.tabs):
                if self.tab_rect(i).contains_point(x, y):
                    self.browser.active_tab = tab
                    break

    def keypress(self, char):
        if self.focus == 'address bar':
            self.address_bar += char

    def enter(self):
        if self.focus == 'address bar':
            self.browser.active_tab.load(URL(self.address_bar))
            self.focus = None


class Rect:
    def __init__(self, left, top, right, bottom):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    def contains_point(self, x, y):
        return x >= self.left and x < self.right \
                and y >= self.top and y < self.bottom


class DrawOutline:
    def __init__(self, rect, color, thickness):
        self.rect = rect
        self.color = color
        self.thickness = thickness

    def execute(self, scroll, canvas):
        canvas.create_rectangle(
                self.rect.left, self.rect.top - scroll,
                self.rect.right, self.rect.bottom - scroll,
                width=self.thickness,
                outline=self.color)


class DrawLine:
    def __init__(self, x1, y1, x2, y2, color, thickness):
        self.rect = Rect(x1, y1, x2, y2)
        self.color = color
        self.thickness = thickness

    def execute(self, scroll, canvas):
        canvas.create_line(
                self.rect.left, self.rect.top - scroll,
                self.rect.right, self.rect.bottom - scroll,
                fill=self.color, width=self.thickness)


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


def paint_tree(layout_object, display_list):
    display_list.extend(layout_object.paint())

    for child in layout_object.children:
        paint_tree(child, display_list)
