"""
Checks that the desktop frontend works offline and stays free of emoji.
The app runs with no network, so every asset must be bundled and referenced locally.
"""

import os
import re
import unittest

FRONTEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
TEXT_EXTENSIONS = (".html", ".css", ".js", ".svg")

# XML namespace identifiers are names, not requests; localhost is the app's own engine.
ALLOWED_URL = re.compile(r"https?://(localhost|127\.0\.0\.1|www\.w3\.org/)")
ANY_URL = re.compile(r"https?://[^\s\"'`)<>]+")
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍]")


def frontend_text_files():
    for folder, _, files in os.walk(FRONTEND):
        for name in files:
            if name.endswith(TEXT_EXTENSIONS):
                path = os.path.join(folder, name)
                with open(path, encoding="utf-8") as f:
                    yield os.path.relpath(path, FRONTEND), f.read()


class TestFrontendOffline(unittest.TestCase):

    def test_no_remote_urls(self):
        remote = [
            f"{name}: {url}"
            for name, text in frontend_text_files()
            for url in ANY_URL.findall(text)
            if not ALLOWED_URL.match(url)
        ]
        self.assertEqual(remote, [], "Frontend files must not load anything from the network")

    def test_css_assets_exist(self):
        missing = []
        for name, text in frontend_text_files():
            if not name.endswith(".css"):
                continue
            for ref in re.findall(r"url\(\"?([^\")]+)\"?\)", text):
                path = os.path.normpath(os.path.join(FRONTEND, os.path.dirname(name), ref))
                if not os.path.exists(path):
                    missing.append(f"{name}: {ref}")
        self.assertEqual(missing, [])

    def test_icons_exist_in_sprite(self):
        with open(os.path.join(FRONTEND, "icons", "icons.svg"), encoding="utf-8") as f:
            sprite_ids = set(re.findall(r'<symbol id="([^"]+)"', f.read()))
        used = set()
        for name, text in frontend_text_files():
            if name.endswith(".js"):
                # The first quoted name in each icon(...) call, including both arms of a ternary.
                for args in re.findall(r"\bicon\(([^()]*)\)", text):
                    used.update(re.findall(r"'([a-z0-9-]+)'", args.split(",")[0]))
                used.update(re.findall(r"\bicon: '([a-z0-9-]+)'", text))
        self.assertTrue(used, "No icon references found")
        self.assertEqual(sorted(used - sprite_ids), [])


class TestFrontendNoEmoji(unittest.TestCase):

    def test_no_emoji(self):
        found = [
            f"{name}: {match!r}"
            for name, text in frontend_text_files()
            for match in EMOJI.findall(text)
        ]
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
