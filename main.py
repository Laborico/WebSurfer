import sys
import sdl2
from ui.functions import mainloop
from ui.browser import Browser
from connection.url import URL

if __name__ == '__main__':
    sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS)
    browser = Browser()
    browser.new_tab(URL(sys.argv[1]))
    browser.draw()
    mainloop(browser)
