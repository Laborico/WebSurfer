from html_parser.element import Element
from css_parser.functions import tree_to_list
from js_interpreter.jscontext import JSContext
from processing.taskrunner import TaskRunner
from processing.commitdata import CommitData
from .paint_tree import paint_tree
from .variables import VSTEP, SCROLL_STEP, WIDTH
from .frame import Frame
import urllib.parse
import math


class Tab:
    def __init__(self, browser, tab_height):
        self.url = ''
        self.tab_height = tab_height
        self.history = []
        self.focus = None
        self.focused_frame = None
        self.needs_raf_callbacks = False
        self.needs_paint = False
        self.root_frame = None
        self.dark_mode = browser.dark_mode

        self.loaded = False

        self.browser = browser
        self.task_runner = TaskRunner(self)

        self.task_runner.start_thread()

        self.composited_updates = []
        self.zoom = 1.0
        self.scroll = 0

        self.window_id_to_frame = {}
        self.origin_to_js = {}

    def raster(self, canvas):

        for cmd in self.display_list:
            cmd.execute(canvas)

    def load(self, url, payload=None):
        self.loaded = False
        self.history.append(url)
        self.task_runner.clear_pending_tasks()
        self.root_frame = Frame(self, None, None)
        self.root_frame.load(url, payload)
        self.root_frame.frame_width = WIDTH
        self.root_frame.frame_height = self.tab_height
        self.loaded = True

    def scrolldown(self):
        frame = self.focused_frame or self.root_frame
        frame.scrolldown()
        self.set_needs_paint()

    def click(self, x, y):
        self.render()
        self.root_frame.click(x, y)

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

    def render(self):
        self.browser.measure.time('render')

        for id, frame in self.window_id_to_frame.items():
            if frame.loaded:
                frame.render()

        if self.needs_paint:
            self.display_list = []
            paint_tree(self.root_frame.document, self.display_list)
            self.needs_paint = False

        self.browser.measure.stop('render')

    def keypress(self, char):
        frame = self.focused_frame
        if not frame:
            frame = self.root_frame
        frame.keypress(char)

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
        if not self.root_frame.scroll_changed_in_frame:
            self.root_frame.scroll = scroll

        needs_composite = False
        for (window_id, frame) in self.window_id_to_frame.items():
            if not frame.loaded:
                continue

            self.browser.measure.time('script-runRAFHandlers')
            frame.js.dispatch_RAF(frame.window_id)
            self.browser.measure.stop('script-runRAFHandlers')

            for node in tree_to_list(frame.nodes, []):
                for (property_name, animation) in node.animations.items():
                    value = animation.animate()
                    if value:
                        node.style[property_name] = value
                        self.composited_updates.append(node)
                        self.set_needs_paint()
            if frame.needs_style or frame.needs_layout:
                needs_composite = True

        self.render()

        if self.focus and self.focused_frame.needs_focus_scroll:
            self.focused_frame.scroll_to(self.focus)
            self.focused_frame.needs_focus_scroll = False

        for (window_id, frame) in self.window_id_to_frame.items():
            if frame == self.root_frame:
                continue
            if frame.scroll_changed_in_frame:
                needs_composite = True
                frame.scroll_changed_in_frame = False

        scroll = None
        if self.root_frame.scroll_changed_in_frame:
            scroll = self.root_frame.scroll

        composited_updates = None
        if not needs_composite:
            composited_updates = {}
            for node in self.composited_updates:
                composited_updates[node] = node.blend_op
        self.composited_updates = []

        root_frame_focused = not self.focused_frame or \
            self.focused_frame == self.root_frame

        commit_data = CommitData(
            self.root_frame.url, scroll,
            root_frame_focused,
            math.ceil(self.root_frame.document.height),
            self.display_list, composited_updates,
            self.focus
        )
        self.display_list = None
        self.root_frame.scroll_changed_in_frame = False

        self.browser.commit(self, commit_data)

    def clamp_scroll(self, scroll):
        height = math.ceil(self.document.height + 2*VSTEP)
        maxscroll = height - self.tab_height
        return max(0, min(scroll, maxscroll))

    def zoom_by(self, increment):
        if increment > 0:
            self.zoom *= 1.1
            self.scroll *= 1.1
        else:
            self.zoom *= 1/1.1
            self.scroll *= 1/1.1
        self.scroll_changed_in_tab = True
        self.set_needs_render_all_frames()

    def reset_zoom(self):
        self.scroll_changed_in_tab = True
        self.scroll /= self.zoom
        self.zoom = 1
        self.set_needs_render_all_frames()

    def set_dark_mode(self, val):
        self.dark_mode = val
        self.set_needs_render_all_frames()

    def advance_tab(self):
        frame = self.focused_frame or self.root_frame
        frame.advance_tab()

    def enter(self):
        if self.focus:
            frame = self.focused_frame or self.root_frame
            frame.activate_element(self.focus)

    def activate_element(self, elt):
        if elt.tag == 'input':
            elt.attributes['value'] = ''
            self.set_needs_render()
        elif elt.tag == 'a' and 'href' in elt.attributes:
            url = self.url.resolve(elt.attributes['href'])
            self.load(url)
        elif elt.tag == 'button':
            while elt:
                if elt.tag == 'form' and 'action' in elt.attributes:
                    self.submit_form(elt)
                    return
                elt = elt.parent

    def focus_element(self, node):
        if node and node != self.focus:
            self.needs_focus_scroll = True

        if self.focus:
            self.focus.is_focused = False
        self.focus = node

        if node:
            node.is_focused = True
        self.set_needs_render()

    def scroll_to(self, elt):
        assert not (self.needs_style or self.needs_layout)
        objs = [obj for obj in tree_to_list(self.document, [])
                if obj.node == self.focus
                ]
        if not objs:
            return
        obj = objs[0]

        if self.scroll < obj.y < self.scroll + self.tab_height:
            return

        document_height = math.ceil(self.document.height + 2*VSTEP)
        new_scroll = obj.y - SCROLL_STEP
        self.scroll = self.clamp_scroll(new_scroll)
        self.scroll_changed_in_tab = True

    def get_js(self, url):
        origin = url.origin()
        if origin not in self.origin_to_js:
            self.origin_to_js[origin] = JSContext(self, origin)
        return self.origin_to_js[origin]

    def set_needs_render_all_frames(self):
        for id, frame in self.window_id_to_frame.items():
            frame.set_needs_render()

    def post_message(self, message, target_window_id):
        frame = self.window_id_to_frame[target_window_id]
        frame.js.dispatch_post_message(
            message, target_window_id)
