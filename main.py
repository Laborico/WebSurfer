import sys
import tkinter
from ui.browser import Browser
from connection.url import URL

if __name__ == '__main__':
    Browser().new_tab(URL(sys.argv[1]))
    tkinter.mainloop()
