import sdl2
import skia
import math
import threading
from processing.task import Task
from processing.measuretime import MeasureTime
from .variables import WIDTH, HEIGHT, REFRESH_RATE_SEC, SCROLL_STEP
from .chrome import Chrome
from .tab import Tab


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
                                                sdl2.SDL_WINDOW_SHOWN)
        self.root_surface = skia.Surface.MakeRaster(
                skia.ImageInfo.Make(
                    WIDTH, HEIGHT,
                    ct=skia.kRGBA_8888_ColorType,
                    at=skia.kUnpremul_AlphaType))

        self.chrome_surface = skia.Surface(
                WIDTH, math.ceil(self.chrome.bottom))
        self.tab_surface = None

        self.tabs = []
        self.active_tab = None
        self.focus = None
        self.animation_timer = None
        self.needs_raster_and_draw = False
        self.needs_animation_frame = False
        self.measure = MeasureTime()
        threading.current_thread().name = 'Browser Thread'

    def handle_down(self):
        self.lock.acquire(blocking=True)
        if not self.active_tab_height:
            self.lock.release()
            return
        self.active_tab_scroll = self.clamp_scroll(
                self.active_tab_scroll + SCROLL_STEP)
        self.set_needs_raster_and_draw()
        self.needs_animation_frame = True
        self.lock.release()

    def handle_click(self, e):
        self.lock.acquire(blocking=True)
        if e.y < self.chrome.bottom:
            self.focus = None
            self.chrome.click(e.x, e.y)
            self.set_needs_raster_and_draw()
        else:
            if self.focus != 'content':
                self.focus = 'content'
                self.chrome.focus = None
                self.set_needs_raster_and_draw()

            self.chrome.blur()
            tab_y = e.y - self.chrome.bottom
            task = Task(self.active_tab.click, e.x, tab_y)
            self.active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def draw(self):
        canvas = self.root_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)

        tab_rect = skia.Rect.MakeLTRB(
                0, self.chrome.bottom, WIDTH, HEIGHT)
        tab_offset = self.chrome.bottom - self.active_tab.scroll
        canvas.save()
        canvas.clipRect(tab_rect)
        canvas.translate(0, tab_offset)
        self.tab_surface.draw(canvas, 0, 0)
        canvas.restore()

        chrome_rect = skia.Rect.MakeLTRB(
                0, 0, WIDTH, self.chrome.bottom)
        canvas.save()
        canvas.clipRect(chrome_rect)
        self.chrome_surface.draw(canvas, 0, 0)
        canvas.restore()

        skia_image = self.root_surface.makeImageSnapshot()
        skia_bytes = skia_image.tobytes()

        depth = 32  # Bits per pixel
        pitch = 4 * WIDTH
        sdl_surface = sdl2.SDL_CreateRGBSurfaceFrom(
                skia_bytes, WIDTH, HEIGHT, depth, pitch,
                self.RED_MASK, self.GREEN_MASK,
                self.BLUE_MASK, self.ALPHA_MASK)

        rect = sdl2.SDL_Rect(0, 0, WIDTH, HEIGHT)
        window_surface = sdl2.SDL_GetWindowSurface(self.sdl_window)
        sdl2.SDL_BlitSurface(sdl_surface, rect, window_surface, rect)
        sdl2.SDL_UpdateWindowSurface(self.sdl_window)

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
        self.active_tab_scroll = 0
        self.active_tab_url = None
        self.needs_animation_frame = True
        self.animation_timer = None

    def handle_key(self, char):
        self.lock.acquire(blocking=True)
        if not (0x20 <= ord(char) < 0x7f):
            return

        if self.chrome.keypress(char):
            self.set_needs_raster_and_draw()
        elif self.focus == 'content':
            task = Task(self.active_tab.keypress, char)
            self.active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def handle_enter(self):
        self.lock.acquire(blocking=True)
        if self.chrome.enter():
            self.set_needs_raster_and_draw()
        self.lock.release()

    def handle_quit(self):
        self.measure.finish()
        for tab in self.tabs:
            tab.task_runner.set_needs_quit()
        sdl2.SDL_DestroyWindow(self.sdl_window)

    def raster_tab(self):
        if self.active_tab_height is None:
            return

        if not self.tab_surface or \
                self.active_tab_height != self.tab_surface.height():
            self.tab_surface = skia.Surface(WIDTH, self.active_tab_height)

        canvas = self.tab_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        for cmd in self.active_tab_display_list:
            cmd.execute(canvas)

    def raster_chrome(self):
        canvas = self.chrome_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)

        for cmd in self.chrome.paint():
            cmd.execute(canvas)

    def raster_and_draw(self):
        self.lock.acquire(blocking=True)
        if not self.needs_raster_and_draw:
            self.lock.release()
            return
        self.measure.time('raster and draw')
        self.raster_chrome()
        self.raster_tab()
        self.draw()
        self.needs_raster_and_draw = False
        self.measure.stop('raster and draw')
        self.lock.release()

    def schedule_animatoin_frame(self):
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

            self.active_tab_height = data.height
            if data.display_list:
                self.active_tab_display_list = data.display_list
            self.animation_timer = None

            self.set_needs_raster_and_draw()
        self.lock.release()

    def clamp_scroll(self, scroll):
        height = self.active_tab_height
        maxscroll = height - (HEIGHT - self.chrome.bottom)
        return max(0, min(scroll, maxscroll))
