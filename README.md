# WebSurfer
> A browser stops being a mystery when it becomes code.

WebSurfer is a simple browser built with Python, and following the blessing of [BrowserEngineering](https://browser.engineering).

### How to Use

```sh
python3 main.py http://example.org/
```

### Features
- http/1 support
- https support
- custom port support
- Basic UI with basic scrolling (only down arrow works)

#### Todo when the blessings are over:
- Update http support from 1.0 to 3.0
- Add [QUIC](https://en.wikipedia.org/wiki/QUIC) support
- Better UI (including mouse controls, resizing, scrollbars, line breaks, dynamic fonts, etc.)
- Add unicode support (emojis, right-to-left languages, etc.)
- Add malformed url case handling
- Improve text rendering
