import sys
import tkinter
from ui import Browser
from url import URL


if __name__ == '__main__':
    Browser().new_tab(URL(sys.argv[1]))
    tkinter.mainloop()
