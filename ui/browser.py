import sdl2
import skia
import math
import threading
import OpenGL.GL
from processing.task import Task
from processing.measuretime import MeasureTime
from .variables import WIDTH, HEIGHT, REFRESH_RATE_SEC, SCROLL_STEP
from .chrome import Chrome
from .tab import Tab
from .paintcommand import PaintCommand
from .functions import tree_to_list, add_parent_pointers, local_to_absolute
from .compositedlayer import CompositedLayer
from .blend import Blend
from .drawcompositedlayer import DrawCompositedLayer


class Browser:
    def __init__(self):
        self.lock = threading.Lock()

        self.active_tab_url = None
        self.active_tab_scroll = 0
        self.active_tab_height = 0
        self.active_tab_display_list = None
        self.chrome = Chrome(self)

        if sdl2.SDL_BYTEORDER == sdl2.SDL_BIG_ENDIAN:
            self.RED_MASK = 0xff000000
            self.GREEN_MASK = 0x00ff0000
            self.BLUE_MASK = 0x0000ff00
            self.ALPHA_MASK = 0x000000ff
        else:
            self.RED_MASK = 0x000000ff
            self.GREEN_MASK = 0x0000ff00
            self.BLUE_MASK = 0x00ff0000
            self.ALPHA_MASK = 0xff000000
        self.sdl_window = sdl2.SDL_CreateWindow(b'Browser',
                                                sdl2.SDL_WINDOWPOS_CENTERED,
                                                sdl2.SDL_WINDOWPOS_CENTERED,
                                                WIDTH, HEIGHT,
                                                sdl2.SDL_WINDOW_SHOWN |
                                                sdl2.SDL_WINDOW_OPENGL)

        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_MAJOR_VERSION, 3)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_MINOR_VERSION, 2)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_FORWARD_COMPATIBLE_FLAG,
                                 True)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_PROFILE_MASK,
                                 sdl2.SDL_GL_CONTEXT_PROFILE_CORE)

        self.gl_context = sdl2.SDL_GL_CreateContext(
                self.sdl_window)

        print(('OpenGL initialized: vendor={}, renderer={}').format(
            OpenGL.GL.glGetString(OpenGL.GL.GL_VENDOR),
            OpenGL.GL.glGetString(OpenGL.GL.GL_RENDERER)))

        self.skia_context = skia.GrDirectContext.MakeGL()

        self.root_surface = skia.Surface.MakeFromBackendRenderTarget(
                self.skia_context,
                skia.GrBackendRenderTarget(
                    WIDTH, HEIGHT, 0, 0,
                    skia.GrGLFramebufferInfo(
                        0, OpenGL.GL.GL_RGBA8)),
                skia.kBottomLeft_GrSurfaceOrigin,
                skia.kRGBA_8888_ColorType,
                skia.ColorSpace.MakeSRGB())
        assert self.root_surface is not None

        self.chrome_surface = skia.Surface.MakeRenderTarget(
                self.skia_context, skia.Budgeted.kNo,
                skia.ImageInfo.MakeN32Premul(
                    WIDTH, math.ceil(self.chrome.bottom)))
        assert self.chrome_surface is not None

        self.tab_surface = None

        self.tabs = []
        self.active_tab = None
        self.address_bar = ''
        self.focus = None
        self.animation_timer = None
        self.needs_raster_and_draw = False
        self.needs_animation_frame = False
        self.measure = MeasureTime()
        threading.current_thread().name = 'Browser Thread'
        self.composited_layers = []
        self.needs_composite = False
        self.needs_raster = False
        self.needs_draw = False
        self.composited_updates = {}
        self.draw_list = []
        self.dark_mode = False
        self.tab_focus = None
        self.last_tab_focus = None
        self.root_frame_focused = False

    def handle_down(self):
        self.lock.acquire(blocking=True)
        if self.root_frame_focused:
            if not self.active_tab_height:
                self.lock.release()
                return
            self.active_tab_scroll = \
                self.clamp_scroll(self.active_tab_scroll + SCROLL_STEP)
            self.set_needs_draw()
            self.needs_animation_frame = True
            self.lock.release()
            return
        task = Task(self.active_tab.scrolldown)
        self.active_tab.task_runner.schedule_task(task)
        self.needs_animation_frame = True
        self.lock.release()

    def handle_click(self, e):
        self.lock.acquire(blocking=True)
        if e.y < self.chrome.bottom:
            self.focus = None
            self.chrome.click(e.x, e.y)
            self.set_needs_raster()
        else:
            if self.focus != 'content':
                self.set_needs_raster()

            self.focus = 'content'
            self.chrome.blur()
            tab_y = e.y - self.chrome.bottom
            task = Task(self.active_tab.click, e.x, tab_y)
            self.active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def draw(self):
        canvas = self.root_surface.getCanvas()

        if self.dark_mode:
            canvas.clear(skia.ColorBLACK)
        else:
            canvas.clear(skia.ColorWHITE)

        canvas.save()
        canvas.translate(0, self.chrome.bottom - self.active_tab_scroll)
        for item in self.draw_list:
            item.execute(canvas)
        canvas.restore()

        chrome_rect = skia.Rect.MakeLTRB(
                0, 0, WIDTH, self.chrome.bottom)
        canvas.save()
        canvas.clipRect(chrome_rect)
        self.chrome_surface.draw(canvas, 0, 0)
        canvas.restore()

        self.root_surface.flushAndSubmit()
        sdl2.SDL_GL_SwapWindow(self.sdl_window)

    def new_tab(self, url):
        self.lock.acquire(blocking=True)
        self.new_tab_internal(url)
        self.lock.release()

    def new_tab_internal(self, url):
        new_tab = Tab(self, HEIGHT - self.chrome.bottom)
        self.tabs.append(new_tab)
        self.set_active_tab(new_tab)
        self.schedule_load(url)

    def set_active_tab(self, tab):
        self.active_tab = tab
        task = Task(self.active_tab.set_dark_mode, self.dark_mode)
        self.active_tab.task_runner.schedule_task(task)
        task = Task(self.active_tab.set_needs_render_all_frames)
        self.active_tab.task_runner.schedule_task(task)

        self.clear_data()
        self.needs_animation_frame = True
        self.animation_timer = None

    def handle_key(self, char):
        self.lock.acquire(blocking=True)
        if not (0x20 <= ord(char) < 0x7f):
            return

        if self.chrome.keypress(char):
            self.set_needs_raster()
        elif self.focus == 'content':
            task = Task(self.active_tab.keypress, char)
            self.active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def handle_enter(self):
        self.lock.acquire(blocking=True)
        if self.chrome.enter():
            self.set_needs_raster()
        elif self.focus == 'content':
            task = Task(self.active_tab.enter)
            self.active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def handle_quit(self):
        self.measure.finish()
        for tab in self.tabs:
            tab.task_runner.set_needs_quit()
        sdl2.SDL_GL_DeleteContext(self.gl_context)
        sdl2.SDL_DestroyWindow(self.sdl_window)

    def handle_tab(self):
        self.focus = 'content'
        self.chrome.blur()
        task = Task(self.active_tab.advance_tab)
        self.active_tab.task_runner.schedule_task(task)

    def raster_tab(self):
        for composited_layer in self.composited_layers:
            composited_layer.raster()

    def raster_chrome(self):
        if self.dark_mode:
            background_color = skia.ColorBLACK
        else:
            background_color = skia.ColorWHITE
        canvas = self.chrome_surface.getCanvas()
        canvas.clear(background_color)

        for cmd in self.chrome.paint():
            cmd.execute(canvas)

    def composite_raster_and_draw(self):
        self.lock.acquire(blocking=True)
        if not self.needs_composite and\
                len(self.composited_updates) == 0\
                and not self.needs_raster \
                and not self.needs_draw:
            self.lock.release()
            return

        self.measure.time('composite_raster_and_draw')

        if self.needs_composite:
            self.measure.time('composite')
            self.composite()
            self.measure.stop('composite')

        if self.needs_raster:
            self.measure.time('raster')
            self.raster_chrome()
            self.raster_tab()
            self.measure.stop('raster')

        if self.needs_draw:
            self.measure.time('draw')
            self.paint_draw_list()
            self.draw()
            self.measure.stop('draw')

        self.measure.stop('composite_raster_and_draw')

        self.needs_composite = False
        self.needs_raster = False
        self.needs_draw = False

        self.lock.release()

    def schedule_animation_frame(self):
        def callback():
            self.lock.acquire(blocking=True)
            scroll = self.active_tab_scroll
            self.needs_animation_frame = False
            active_tab = self.active_tab
            self.lock.release()
            task = Task(self.active_tab.run_animation_frame, scroll)
            active_tab.task_runner.schedule_task(task)

        self.lock.acquire(blocking=True)
        if self.needs_animation_frame and not self.animation_timer:
            self.animation_timer = threading.Timer(REFRESH_RATE_SEC, callback)
            self.animation_timer.start()
        self.lock.release()

    def set_needs_raster_and_draw(self):
        self.needs_raster_and_draw = True

    def set_needs_animation_frame(self, tab):
        self.lock.acquire(blocking=True)
        if tab == self.active_tab:
            self.needs_animation_frame = True
        self.lock.release()

    def schedule_load(self, url, body=None):
        self.active_tab.task_runner.clear_pending_tasks()
        task = Task(self.active_tab.load, url, body)
        self.active_tab.task_runner.schedule_task(task)

    def commit(self, tab, data):
        self.lock.acquire(blocking=True)
        if tab == self.active_tab:
            self.active_tab_url = data.url

            if data.scroll is not None:
                self.active_tab_scroll = data.scroll

            self.root_frame_focused = data.root_frame_focused
            self.active_tab_height = data.height

            if data.display_list:
                self.active_tab_display_list = data.display_list

            self.animation_timer = None
            self.composited_updates = data.composited_updates
            if self.composited_updates is None:
                self.composited_updates = {}
                self.set_needs_composite()
            else:
                self.set_needs_draw()
        self.lock.release()

    def clamp_scroll(self, scroll):
        height = self.active_tab_height
        maxscroll = height - (HEIGHT - self.chrome.bottom)
        return max(0, min(scroll, maxscroll))

    def composite(self):
        add_parent_pointers(self.active_tab_display_list)
        self.composited_layers = []
        all_commands = []
        for cmd in self.active_tab_display_list:
            all_commands = tree_to_list(cmd, all_commands)

        non_composited_commands = [cmd for cmd in all_commands
                                   if isinstance(cmd, PaintCommand) or
                                   not cmd.needs_compositing
                                   if not cmd.parent or
                                   cmd.parent.needs_compositing
                                   ]

        for cmd in non_composited_commands:
            for layer in reversed(self.composited_layers):
                if layer.can_merge(cmd):
                    layer.add(cmd)
                    break
                elif skia.Rect.Intersects(
                        layer.absoulte_bounds(),
                        local_to_absolute(cmd, cmd.rect)):
                    layer = CompositedLayer(self.skia_context, cmd)
                    self.composited_layers.append(layer)
                    break
            else:
                layer = CompositedLayer(self.skia_context, cmd)
                self.composited_layers.append(layer)

        self.active_tab_height = 0
        for layer in self.composited_layers:
            self.active_tab_height = max(self.active_tab_height,
                                         layer.absoulte_bounds().bottom())

    def paint_draw_list(self):
        new_effects = {}
        self.draw_list = []
        for composited_layer in self.composited_layers:
            current_effect = DrawCompositedLayer(composited_layer)

            if not composited_layer.display_items:
                continue

            parent = composited_layer.display_items[0].parent

            while parent:
                new_parent = self.get_latest(parent)
                if new_parent in new_effects:
                    new_effects[new_parent].children.append(current_effect)
                    break
                else:
                    current_effect = new_parent.clone(current_effect)
                    new_effects[new_parent] = current_effect
                    parent = parent.parent
            if not parent:
                self.draw_list.append(current_effect)

    def set_needs_raster(self):
        self.needs_raster = True
        self.needs_draw = True

    def set_needs_composite(self):
        self.needs_composite = True
        self.needs_raster = True
        self.needs_draw = True

    def set_needs_draw(self):
        self.needs_draw = True

    def get_latest(self, effect):
        node = effect.node
        if node not in self.composited_updates:
            return effect
        if not isinstance(effect, Blend):
            return effect
        return self.composited_updates[node]

    def clear_data(self):
        self.active_tab_scroll = 0
        self.active_tab_url = None
        self.display_list = []
        self.composited_updates = {}
        self.composited_layers = []

    def increment_zoom(self, increment):
        self.lock.acquire(blocking=True)
        task = Task(self.active_tab.zoom_by, increment)
        self.active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def reset_zoom(self):
        self.lock.acquire(blocking=True)
        task = Task(self.active_tab.reset_zoom)
        self.active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def toggle_dark_mode(self):
        self.lock.acquire(blocking=True)
        self.dark_mode = not self.dark_mode
        task = Task(self.active_tab.set_dark_mode, self.dark_mode)
        self.active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def focus_addressbar(self):
        self.lock.acquire(blocking=True)
        self.focus = None
        self.chrome.focus_addressbar()
        self.set_needs_raster()
        self.lock.release()

    def focus_content(self):
        self.lock.acquire(blocking=True)
        self.chrome.blur()
        self.focus = 'content'
        self.lock.release()

    def cycle_tabs(self):
        self.lock.acquire(blocking=True)
        active_idx = self.tabs.index(self.active_tab)
        new_active_idx = (active_idx + 1) % len(self.tabs)
        self.set_active_tab(self.tabs[new_active_idx])
        self.lock.release()

    def go_back(self):
        task = Task(self.active_tab.go_back)
        self.active_tab.task_runner.schedule_task(task)
        self.clear_data()
