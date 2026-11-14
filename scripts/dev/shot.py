"""Page screenshot via headless Edge (CDP) — for checking layouts without a browser.

Usage (server must be running, e.g. `.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8011`):
    .venv\\Scripts\\python.exe scripts\\dev\\shot.py competitors 375
    .venv\\Scripts\\python.exe scripts\\dev\\shot.py analytics 1440 --clip 0-900 --js "document.querySelector('[data-tab=audience]').click()"

Args: page path (no leading slash), viewport width. Options:
    --clip Y0-Y1[,Y0-Y1]  only these vertical slices (saves image size)
    --js CODE             run before the shot (repeatable; result is printed)
    --port 8011           app port
    --out DIR             where PNGs go (default: %TEMP%/creatorly-shots)
Edge is started once (debug port 9333) and reused; stop it when done.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DEBUG_PORT = 9333


def ensure_edge() -> None:
    url = f"http://127.0.0.1:{DEBUG_PORT}/json/version"
    try:
        urllib.request.urlopen(url, timeout=1)
        return
    except OSError:
        pass
    profile = Path(tempfile.gettempdir()) / "creatorly-edge-profile"
    subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={DEBUG_PORT}", "--disable-gpu",
                      f"--user-data-dir={profile}", "about:blank"])
    for _ in range(40):
        try:
            urllib.request.urlopen(url, timeout=1)
            return
        except OSError:
            time.sleep(0.25)
    sys.exit("Edge-ը չմիացավ")


async def run(a: argparse.Namespace) -> None:
    ensure_edge()
    req = urllib.request.Request(f"http://127.0.0.1:{DEBUG_PORT}/json/new?about:blank", method="PUT")
    tab = json.load(urllib.request.urlopen(req))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    async with websockets.connect(tab["webSocketDebuggerUrl"], max_size=None) as ws:
        n = 0

        async def cmd(method: str, **params):
            nonlocal n
            n += 1
            my = n
            await ws.send(json.dumps({"id": my, "method": method, "params": params}))
            while True:
                m = json.loads(await ws.recv())
                if m.get("id") == my:
                    if "error" in m:
                        raise RuntimeError(m["error"])
                    return m.get("result", {})
                if m.get("method") == "Runtime.exceptionThrown":
                    print("JS error:", m["params"]["exceptionDetails"].get("exception", {}).get("description"))

        await cmd("Runtime.enable")
        mobile = a.width < 768
        await cmd("Emulation.setDeviceMetricsOverride", width=a.width, height=900, deviceScaleFactor=1, mobile=mobile)
        await cmd("Page.navigate", url=f"http://127.0.0.1:{a.port}/{a.page.lstrip('/')}")
        await asyncio.sleep(1.8)
        for code in a.js:
            r = await cmd("Runtime.evaluate", expression=code, awaitPromise=True, returnByValue=True)
            if "exceptionDetails" in r:
                print("step error:", r["exceptionDetails"].get("exception", {}).get("description"))
            elif r.get("result", {}).get("value") is not None:
                print("=>", r["result"]["value"])
            await asyncio.sleep(0.6)
        await cmd("Emulation.setScrollbarsHidden", hidden=True)
        h = (await cmd("Runtime.evaluate", expression="document.documentElement.scrollHeight", returnByValue=True))["result"]["value"]
        await cmd("Emulation.setDeviceMetricsOverride", width=a.width, height=min(h, 12000), deviceScaleFactor=1, mobile=mobile)
        await asyncio.sleep(0.4)
        name = f"{a.page.strip('/').replace('/', '_') or 'home'}_{a.width}"
        parts = [tuple(map(int, p.split("-"))) for p in a.clip.split(",")] if a.clip else [(0, min(h, 12000))]
        for k, (y0, y1) in enumerate(parts):
            shot = await cmd("Page.captureScreenshot", format="png",
                             clip={"x": 0, "y": y0, "width": a.width, "height": y1 - y0, "scale": 1})
            path = out / (f"{name}_{k}.png" if len(parts) > 1 else f"{name}.png")
            path.write_bytes(base64.b64decode(shot["data"]))
            print("saved", path, f"(page {a.width}x{h})")
    urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json/close/{tab['id']}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("page")
    p.add_argument("width", type=int)
    p.add_argument("--clip")
    p.add_argument("--js", action="append", default=[])
    p.add_argument("--port", type=int, default=8011)
    p.add_argument("--out", default=os.path.join(tempfile.gettempdir(), "creatorly-shots"))
    asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    main()
