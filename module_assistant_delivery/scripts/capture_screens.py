"""Report screenshots of the module UI, taken with headless Chrome (or Edge) over the DevTools protocol.

Needs the service running (http://127.0.0.1:8003). Asking a question calls the local model once per shot.
Usage: ..\\.venv\\Scripts\\python.exe scripts\\capture_screens.py --prefix after- [--theme dark|light] [--only assistant-answer]
"""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import websocket  # websocket-client, already in the service venv

MODULE_ROOT = Path(__file__).resolve().parents[1]
BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]
QUESTION = "The client asks for a dark mode. Is that in scope?"


class Page:
    def __init__(self, port: int) -> None:
        for _ in range(50):
            try:
                targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1))
                target = next(t for t in targets if t["type"] == "page")
                break
            except Exception:
                time.sleep(0.2)
        self.ws = websocket.create_connection(target["webSocketDebuggerUrl"], suppress_origin=True)
        self.next_id = 0

    def send(self, method: str, **params):
        self.next_id += 1
        self.ws.send(json.dumps({"id": self.next_id, "method": method, "params": params}))
        while True:
            message = json.loads(self.ws.recv())
            if message.get("id") == self.next_id:
                if "error" in message:
                    raise RuntimeError(f"{method}: {message['error']}")
                return message.get("result", {})

    def js(self, expression: str):
        result = self.send("Runtime.evaluate", expression=expression, awaitPromise=True, returnByValue=True)
        return result.get("result", {}).get("value")

    def wait(self, condition: str, timeout_s: float = 120.0) -> None:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if self.js(f"Boolean({condition})"):
                return
            time.sleep(0.3)
        raise TimeoutError(condition)

    def open(self, url: str, storage: dict[str, str]) -> None:
        self.send("Page.navigate", url=url)
        self.wait("document.readyState === 'complete'")
        self.js("localStorage.clear();" + "".join(f"localStorage.setItem({json.dumps(k)}, {json.dumps(v)});" for k, v in storage.items()))
        self.send("Page.reload", ignoreCache=True)
        time.sleep(0.5)
        self.wait("document.readyState === 'complete' && document.querySelector('select option[value=\"PRJ-DEMO-001\"]')", 30)
        time.sleep(0.8)

    def shot(self, path: Path) -> None:
        time.sleep(1.4)  # let entry transitions and the quote highlight settle
        path.write_bytes(base64.b64decode(self.send("Page.captureScreenshot", format="png")["data"]))
        print("wrote", path.relative_to(MODULE_ROOT))


def ask(page: Page, question: str) -> None:
    page.js(f"""(() => {{
        const box = document.querySelector('#ad-message');
        Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(box, {json.dumps(question)});
        box.dispatchEvent(new Event('input', {{ bubbles: true }}));
    }})()""")
    time.sleep(0.2)
    page.js("document.querySelector('.ad-composer button[type=submit]').click()")
    page.wait("document.querySelector('.ad-answer__text') && !document.body.innerText.includes('Reading the project documents')", 180)


def click_text(page: Page, selector: str, pattern: str) -> None:
    page.js(f"[...document.querySelectorAll({json.dumps(selector)})].find(e => new RegExp({json.dumps(pattern)}, 'i').test(e.textContent)).click()")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8003/assistant/")
    parser.add_argument("--out", default=str(MODULE_ROOT / "docs" / "images"))
    parser.add_argument("--prefix", default="")
    parser.add_argument("--theme", default="light", choices=["light", "dark"])
    parser.add_argument("--only", nargs="*", default=None)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    browser = next(b for b in BROWSERS if Path(b).is_file())
    profile = tempfile.mkdtemp(prefix="ad-shots-")
    port = 9333
    proc = subprocess.Popen([browser, "--headless=new", f"--remote-debugging-port={port}", "--remote-allow-origins=*",
                             f"--user-data-dir={profile}", "--window-size=1440,900", "--hide-scrollbars", "--no-first-run",
                             "--no-default-browser-check", "--force-color-profile=srgb", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        page = Page(port)
        page.send("Emulation.setDeviceMetricsOverride", width=1440, height=900, deviceScaleFactor=1, mobile=False)
        page.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": args.theme}])
        user = {"assistant.demoUser": "demo-freelancer-a"}
        client = {"assistant.demoUser": "demo-client-b"}
        want = lambda name: args.only is None or name in args.only  # noqa: E731

        if want("assistant-empty"):
            page.open(args.url, user)
            page.shot(out / f"{args.prefix}assistant-empty.png")
        if want("assistant-answer"):
            page.open(args.url, user)
            ask(page, QUESTION)
            page.shot(out / f"{args.prefix}assistant-answer.png")
        if want("assistant-thinking"):  # the thinking state, caught while the model works
            page.open(args.url, user)
            page.js(f"""(() => {{
                const box = document.querySelector('#ad-message');
                Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(box, {json.dumps("When does booking for a pickup slot close?")});
                box.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }})()""")
            time.sleep(0.2)
            page.js("document.querySelector('.ad-composer button[type=submit]').click()")
            page.wait("document.querySelector('.ad-thinking')", 10)
            time.sleep(1.2)
            path = out / f"{args.prefix}assistant-thinking.png"
            path.write_bytes(base64.b64decode(page.send("Page.captureScreenshot", format="png")["data"]))
            print("wrote", path.relative_to(MODULE_ROOT))
            page.wait("document.querySelector('.ad-answer__text') && !document.querySelector('.ad-thinking')", 180)
        if want("model-picker"):  # redesigned UI only: the model menu, open
            page.open(args.url, user)
            page.js("document.querySelector('.ad-model-btn').click()")
            page.wait("document.querySelector('.ad-model-menu')", 5)
            page.shot(out / f"{args.prefix}model-picker.png")
        if want("failure-drill"):  # redesigned UI only: base skipped, RAFT answers
            page.open(args.url, user)
            page.js("document.querySelector('.ad-model-btn').click()")
            page.wait("document.querySelector('#ad-drill')", 5)
            page.js("document.querySelector('#ad-drill').click(); document.querySelector('.ad-model-btn').click()")
            ask(page, "What is the fixed price of the project?")
            page.shot(out / f"{args.prefix}failure-drill.png")
        if want("review-report"):
            page.open(args.url, client)
            click_text(page, "[role=tab]", "review")
            page.wait("[...document.querySelectorAll('button')].some(b => /open last review/i.test(b.textContent))", 20)
            click_text(page, "button", "open last review")
            page.wait("document.querySelector('.ad-tiles')", 20)
            page.shot(out / f"{args.prefix}review-report.png")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
