from html_parser.parser import HTMLParser
from html_parser.element import Element
from html_parser.text import Text
from css_parser.parser import DEFAULT_STYLE_SHEET
from css_parser.functions import tree_to_list, cascade_priority, style
from css_parser.parser import CSSParser
from connection.url import URL
from js_interpreter.jscontext import JSContext
from processing.taskrunner import TaskRunner
from processing.task import Task
from processing.commitdata import CommitData
from .documentlayout import DocumentLayout
from .functions import paint_tree
from .functions2 import absolute_bounds_for_objs
from .variables import VSTEP, SCROLL_STEP
import urllib.parse
import math
import skia


class Tab:
    def __init__(self, browser, tab_height):
        self.url = None
        self.tab_height = tab_height
        self.history = []
        self.focus = None
        self.task_runner = TaskRunner(self)
        self.needs_render = False
        self.browser = browser
        self.scroll_changed_in_tab = False
        self.scroll = 0
        self.needs_raf_callbacks = False
        self.js = None
        self.loaded = False
        self.task_runner.start_thread()
        self.set_needs_style = False
        self.needs_layout = False
        self.needs_paint = False
        self.needs_style = False
        self.composited_updates = []

    def raster(self, canvas):

        for cmd in self.display_list:
            cmd.execute(canvas)

    def load(self, url, payload=None):
        self.loaded = False
        self.scroll = 0
        self.scroll_changed_in_tab = True

        self.task_runner.clear_pending_tasks()
        headers, body = url.request(self.url, payload)
        self.url = url
        self.history.append(url)

        self.allowed_origins = None
        if 'content-security-policy' in headers:
            csp = headers['content-security-policy'].split()
            if len(csp) > 0 and csp[0] == 'default-src':
                self.allowed_origins = []
                for origin in csp[1:]:
                    self.allowed_origins.append(URL(origin).origin())

        self.nodes = HTMLParser(body).parse()
        self.rules = DEFAULT_STYLE_SHEET.copy()

        if self.js:
            self.js.discarded = True

        self.js = JSContext(self)
        scripts = [node.attributes['src'] for node
                   in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == 'script'
                   and 'src' in node.attributes]

        for script in scripts:
            script_url = url.resolve(script)
            if not self.allowed_request(script_url):
                print('Blocked script', script, 'due to CSP')
                continue
            try:
                header, body = script_url.request(url)
            except Exception:
                continue
            task = Task(self.js.run, script_url, body)
            self.task_runner.schedule_task(task)

        links = [node.attributes['href']
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == 'link'
                 and node.attributes.get('rel') == 'stylesheet'
                 and 'href' in node.attributes]

        for link in links:
            style_url = url.resolve(link)
            if not self.allowed_request(style_url):
                print('Blocked stylesheet', link, 'due to CSP')
                continue
            try:
                header, body = style_url.request(url)
            except Exception:
                continue
            self.rules.extend(CSSParser(body).parse())

        self.set_needs_render()
        self.loaded = True

    def scrolldown(self):
        max_y = max(self.document.height + 2*VSTEP - self.tab_height, 0)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)

    def click(self, x, y):
        self.render()
        if self.focus:
            self.focus.is_focused = False
        self.focus = None
        y += self.scroll

        loc_rect = skia.Rect.MakeXYWH(x, y, 1, 1)

        objs = [obj for obj in tree_to_list(self.document, [])
                if absolute_bounds_for_objs(obj).intersects(loc_rect)]

        if not objs:
            return
        elt = objs[-1].node
        if elt and self.js.dispatch_event('click', elt):
            return

        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == 'a' and 'href' in elt.attributes:
                url = self.url.resolve(elt.attributes['href'])
                self.load(url)
                return
            elif elt.tag == 'input':
                elt.attributes['value'] = ''
                self.focus = elt
                elt.is_focused = True
                self.set_needs_render()
                return
            elif elt.tag == 'button':
                while elt.parent:
                    if elt.tag == 'form' and 'action' in elt.attributes:
                        return self.submit_form(elt)
                    elt = elt.parent

            elt = elt.parent

        objs = [obj for obj in tree_to_list(self.document, [])
                if absolute_bounds_for_objs(obj).intersects(loc_rect)]

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

    def render(self):
        self.browser.measure.time('render')

        if self.needs_style:
            style(self.nodes, sorted(self.rules, key=cascade_priority), self)
            self.needs_layout = True
            self.needs_style = False

        if self.needs_layout:
            self.document = DocumentLayout(self.nodes)
            self.document.layout()
            self.needs_paint = True
            self.needs_layout = False

        if self.needs_paint:
            self.display_list = []
            paint_tree(self.document, self.display_list)
            self.needs_paint = False

        clamped_scroll = self.clamp_scroll(self.scroll)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_tab = True
        self.scroll = clamped_scroll

        self.browser.measure.stop('render')

    def keypress(self, char):
        if self.focus:
            if self.js.dispatch_event('keydown', self.focus):
                return
            self.focus.attributes['value'] += char
            self.set_needs_render()

    def submit_form(self, elt):
        if self.js.dispatch_event('submit', elt):
            return
        inputs = [node for node in tree_to_list(elt, [])
                  if isinstance(node, Element)
                  and node.tag == 'input'
                  and 'name' in node.attributes]

        body = ''
        for input in inputs:
            name = input.attributes['name']
            value = input.attributes.get('value', '')
            body += '&' + name + '=' + value
        body = body[1:]

        name = urllib.parse.quote(name)
        value = urllib.parse.quote(value)

        url = self.url.resolve(elt.attributes['action'])
        self.load(url, body)

    def allowed_request(self, url):
        return self.allowed_origins is None or \
                url.origin() in self.allowed_origins

    def set_needs_render(self):
        self.needs_style = True
        self.browser.set_needs_animation_frame(self)

    def set_needs_layout(self):
        self.needs_layout = True
        self.browser.set_needs_animation_frame(self)

    def set_needs_paint(self):
        self.needs_paint = True
        self.browser.set_needs_animation_frame(self)

    def run_animation_frame(self, scroll):
        if not self.scroll_changed_in_tab:
            self.scroll = scroll

        self.browser.measure.time('script-runRAFHandlers')
        self.js.interp.evaljs('__runRAFHandlers()')
        self.browser.measure.stop('script-runRAFHandlers')

        for node in tree_to_list(self.nodes, []):
            for (property_name, animation) in node.animations.items():
                value = animation.animate()
                if value:
                    node.style[property_name] = value
                    self.composited_updates.append(node)
                    self.set_needs_paint()
                    self.set_needs_layout()

        needs_composite = self.needs_style or self.needs_layout

        self.render()

        scroll = None
        if self.scroll_changed_in_tab:
            scroll = self.scroll

        composited_updates = None

        if not needs_composite:
            composited_updates = {}
            for node in self.composited_updates:
                composited_updates[node] = node.blend_op
        self.composited_updates = []

        document_height = math.ceil(self.document.height + 2*VSTEP)

        commit_data = CommitData(
                self.url, self.scroll, document_height, self.display_list,
                composited_updates
                )
        self.display_list = None
        self.scroll_changed_in_tab = False
        self.browser.commit(self, commit_data)

    def clamp_scroll(self, scroll):
        height = math.ceil(self.document.height + 2*VSTEP)
        maxscroll = height - self.tab_height
        return max(0, min(scroll, maxscroll))
