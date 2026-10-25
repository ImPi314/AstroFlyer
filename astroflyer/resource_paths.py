"""
Resolves bundled read-only files and the per-user writable folder, in development and in the
PyInstaller onedir build (where files live under sys._MEIPASS, i.e. <install dir>/_internal).
"""

import os
import sys

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))


def bundle_root() -> str:
    """Folder that holds the astroflyer package files (frontend/, resources/, cpp_engine/ ...)."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidate = os.path.join(meipass, "astroflyer")
        return candidate if os.path.isdir(candidate) else meipass
    return _PACKAGE_DIR


def resource_path(*parts: str) -> str:
    """Path to a bundled, read-only file, e.g. resource_path("resources", "manifest.json")."""
    return os.path.join(bundle_root(), *parts)


def user_data_dir(*parts: str) -> str:
    """Per-user writable folder for exports, logs and imported data updates. Created on first use."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = os.path.join(base, "AstroFlyer", *parts)
    os.makedirs(path, exist_ok=True)
    return path
