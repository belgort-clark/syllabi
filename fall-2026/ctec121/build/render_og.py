#!/usr/bin/env python3
"""Render og.png (1200x630) from og_card_source.html.

Usage: python3 build/render_og.py "<absolute path to fall-2026/ctec121>"

Run this in a Claude session -- it needs the cloud container's chromium at
/opt/pw-browsers/chromium and the playwright python package. Regenerate
whenever og_card_source.html changes, then commit og.png alongside it.

NOTE: fonts.googleapis.com is blocked from the build environment, so the card
renders in the fallback stack, not Atkinson Hyperlegible. Self-hosting the
woff2 files and pointing og_card_source.html at them fixes this (and fixes
the two PDFs, which have the same problem).
"""
import os, sys
from struct import unpack

CHROMIUM = "/opt/pw-browsers/chromium"
W, H = 1200, 630


def main(folder):
    folder = os.path.abspath(folder)
    src = os.path.join(folder, "og_card_source.html")
    out = os.path.join(folder, "og.png")
    if not os.path.exists(src):
        sys.exit("missing " + src)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROMIUM)
        page = browser.new_page(viewport={"width": W, "height": H},
                                device_scale_factor=1)
        page.goto("file://" + src)
        page.wait_for_timeout(300)
        page.screenshot(path=out)
        browser.close()

    with open(out, "rb") as f:
        w, h = unpack(">II", f.read(24)[16:24])
    assert (w, h) == (W, H), "expected %dx%d, got %dx%d" % (W, H, w, h)
    print("PASS og.png is %dx%d (%d bytes)" % (w, h, os.path.getsize(out)))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
