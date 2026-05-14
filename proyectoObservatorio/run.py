from __future__ import annotations

import threading
import time
import webbrowser

import uvicorn


def open_browser(url: str, delay: float = 1.0) -> None:
    time.sleep(delay)
    webbrowser.open(url, new=2)


def main() -> None:
    url = "http://127.0.0.1:8000"
    thread = threading.Thread(target=open_browser, args=(url,), daemon=True)
    thread.start()
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
