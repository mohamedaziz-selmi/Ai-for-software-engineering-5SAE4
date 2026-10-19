"""Report screenshots of the module's Swagger page (/api/ai/docs), each a real request sent from Swagger's "Try it out".

Needs the service on :8003. The chat shot calls the local model once; its conversation is deleted afterwards. The review
shot reads a stored review (no model call). Usage:
  .venv\\Scripts\\python.exe scripts\\capture_swagger.py [--only overview chat upload-refused access-denied review]
"""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path

from capture_screens import BROWSERS, MODULE_ROOT, Page

DB = MODULE_ROOT / "storage" / "assistant.sqlite3"
OP = "operations-default-{}"
SET_VALUE = """const setValue = (el, v) => {
    const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
};"""


class Swagger:
    def __init__(self, page: Page, url: str, width: int) -> None:
        self.page, self.url, self.width = page, url, width

    def load(self) -> None:
        self.page.send("Emulation.setDeviceMetricsOverride", width=self.width, height=900, deviceScaleFactor=2, mobile=False)
        self.page.send("Page.navigate", url=self.url)
        self.page.wait("document.querySelectorAll('.opblock').length > 20", 60)
        time.sleep(0.5)

    def open(self, op_id: str) -> str:
        op = OP.format(op_id)
        self.page.js(f"document.getElementById('{op}').querySelector('.opblock-summary-control').click()")
        self.page.wait(f"document.getElementById('{op}').querySelector('.try-out__btn')", 15)
        self.page.js(f"document.getElementById('{op}').querySelector('.try-out__btn').click()")
        self.page.wait(f"document.getElementById('{op}').querySelector('.execute')", 15)
        return op

    def fill(self, op: str, selector: str, value: str) -> None:
        self.page.js(f"(() => {{ {SET_VALUE} setValue(document.getElementById('{op}').querySelector({json.dumps(selector)}), {json.dumps(value)}); }})()")

    def attach(self, op: str, path: Path) -> None:
        handle = self.page.send("Runtime.evaluate", expression=f"document.getElementById('{op}').querySelector('input[type=file]')")
        self.page.send("DOM.setFileInputFiles", files=[str(path)], objectId=handle["result"]["objectId"])

    def execute(self, op: str, timeout_s: float = 240) -> dict:
        time.sleep(1.0)  # Swagger's parameter inputs are debounced (350 ms)
        self.page.js(f"document.getElementById('{op}').querySelector('.execute').click()")
        self.page.wait(f"document.getElementById('{op}').querySelector('.live-responses-table tbody .response-col_status')", timeout_s)
        time.sleep(0.6)
        status = self.page.js(f"document.getElementById('{op}').querySelector('.live-responses-table tbody .response-col_status').textContent.trim()")
        body = self.page.js(f"document.getElementById('{op}').querySelector('.live-responses-table .highlight-code pre').textContent")
        return {"status": status, "body": json.loads(body)}

    def scroll_body(self, op: str, key: str, max_height: int) -> None:
        """Show the response box at a fixed height, scrolled so that the given JSON key is its first line."""
        self.page.js(f"""(() => {{
            const pre = document.getElementById('{op}').querySelector('.live-responses-table .highlight-code pre');
            pre.style.maxHeight = '{max_height}px'; pre.style.overflowY = 'auto';
            const line = pre.textContent.split('\\n').findIndex(l => l.trimStart().startsWith({json.dumps('"' + key + '"')}));
            pre.scrollTop = Math.max(0, line) * (pre.scrollHeight / pre.textContent.split('\\n').length) - 4;
        }})()""")

    def shot(self, path: Path, top_selector: str, bottom_selector: str, op: str | None = None) -> None:
        root = f"document.getElementById('{op}')" if op else "document"
        height = self.page.js("Math.ceil(document.documentElement.scrollHeight)")
        self.page.send("Emulation.setDeviceMetricsOverride", width=self.width, height=height, deviceScaleFactor=2, mobile=False)
        time.sleep(0.6)
        box = self.page.js(f"""(() => {{
            const top = {root}.querySelector({json.dumps(top_selector)}) || {root};
            const bottoms = [...{root}.querySelectorAll({json.dumps(bottom_selector)})];
            const t = top.getBoundingClientRect(), b = bottoms[bottoms.length - 1].getBoundingClientRect();
            const frame = document.querySelector('.swagger-ui .wrapper').getBoundingClientRect();
            return JSON.stringify({{x: frame.left, y: t.top - 10, width: frame.width, height: b.bottom - t.top + 22}});
        }})()""")
        clip = {**json.loads(box), "scale": 1}
        data = self.page.send("Page.captureScreenshot", format="png", clip=clip)["data"]
        path.write_bytes(base64.b64decode(data))
        print("wrote", path.relative_to(MODULE_ROOT), f"({clip['width']:.0f}x{clip['height']:.0f} css px)")


def latest_review_id() -> str:
    conn = sqlite3.connect(DB)
    row = conn.execute("SELECT id FROM reviews WHERE status = 'done' ORDER BY started_at DESC LIMIT 1").fetchone()
    return row[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8003/api/ai/docs")
    parser.add_argument("--out", default=str(MODULE_ROOT / "docs" / "images"))
    parser.add_argument("--review-id", default=None)
    parser.add_argument("--only", nargs="*", default=None)
    args = parser.parse_args()
    out = Path(args.out)
    want = lambda name: args.only is None or name in args.only  # noqa: E731
    browser = next(b for b in BROWSERS if Path(b).is_file())
    profile = tempfile.mkdtemp(prefix="ad-swagger-")
    proc = subprocess.Popen([browser, "--headless=new", "--remote-debugging-port=9337", "--remote-allow-origins=*", f"--user-data-dir={profile}",
                             "--window-size=1200,900", "--hide-scrollbars", "--no-first-run", "--no-default-browser-check",
                             "--force-color-profile=srgb", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    created: list[str] = []
    try:
        page = Page(9337)
        page.send("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "light"}])
        if want("overview"):  # every operation, collapsed
            s = Swagger(page, args.url, 1200)
            s.load()
            s.shot(out / "swagger-overview.png", ".information-container", ".opblock-tag-section")
        s = Swagger(page, args.url, 1000)
        if want("chat"):  # a question with a verified citation
            s.load()
            op = s.open("chat_api_ai_chat_post")
            s.fill(op, "tr[data-param-name='x-demo-user'] input", "demo-freelancer-a")
            s.fill(op, "textarea.body-param__text", json.dumps(
                {"project_id": "PRJ-DEMO-001", "message": "How many orders can a shop accept per pickup slot?", "model": "base"}, indent=2))
            page.js(f"Object.assign(document.getElementById('{op}').querySelector('textarea.body-param__text').style, {{height: '112px', minHeight: '0'}})")
            result = s.execute(op)
            if "conversation_id" in result["body"]:
                created.append(result["body"]["conversation_id"])
            assert result["status"].startswith("200"), result
            print("chat:", result["status"], result["body"]["status"], result["body"]["answer"])
            s.scroll_body(op, "status", 500)
            s.shot(out / "swagger-chat.png", ".opblock-summary", ".live-responses-table .highlight-code", op)
        if want("upload-refused"):  # a CSV is refused with a readable reason
            s.load()
            op = s.open("upload_document_api_ai_documents_post")
            s.fill(op, "tr[data-param-name='x-demo-user'] input", "demo-freelancer-a")
            s.fill(op, "input[placeholder='project_id']", "PRJ-DEMO-001")
            s.attach(op, MODULE_ROOT / "demo" / "rejected" / "documents" / "PRJ-DEMO-001_budget.csv")
            result = s.execute(op)
            print("upload:", result["status"], result["body"])
            assert result["status"].startswith("415"), result
            s.scroll_body(op, "detail", 230)  # the reason first; the list of allowed types continues below
            s.shot(out / "swagger-upload-refused.png", ".opblock-summary", ".live-responses-table .highlight-code", op)
        if want("access-denied"):  # a user outside the project
            s.load()
            op = s.open("list_documents_api_ai_documents_get")
            s.fill(op, "tr[data-param-name='x-demo-user'] input", "demo-freelancer-c")
            s.fill(op, "tr[data-param-name='project_id'] input", "PRJ-DEMO-001")
            result = s.execute(op)
            print("access:", result["status"], result["body"])
            assert result["status"].startswith("403"), result
            s.shot(out / "swagger-access-denied.png", ".opblock-summary", ".live-responses-table .highlight-code", op)
        if want("review"):  # a stored delivery review, read by the client
            review_id = args.review_id or latest_review_id()
            s.load()
            op = s.open("get_review_api_ai_reviews__review_id__get")
            s.fill(op, "tr[data-param-name='x-demo-user'] input", "demo-client-b")
            s.fill(op, "tr[data-param-name='review_id'] input", review_id)
            result = s.execute(op)
            assert result["status"].startswith("200"), result
            print("review:", result["status"], result["body"]["summary"])
            s.scroll_body(op, "summary", 500)
            s.shot(out / "swagger-review.png", ".opblock-summary", ".live-responses-table .highlight-code", op)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)
        if created:  # the chat shot's conversation is test data
            conn = sqlite3.connect(DB)
            conn.execute("PRAGMA foreign_keys = ON")
            with conn:
                conn.executemany("DELETE FROM conversations WHERE id = ?", [(c,) for c in created])
            print("removed test conversations:", created)


if __name__ == "__main__":
    main()
