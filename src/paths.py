"""
Central path resolution for both dev-mode (running from a source checkout)
and a frozen PyInstaller build.

Two roots, kept separate on purpose:
  - BUNDLE_ROOT: read-only assets shipped with the app (fonts). In a frozen
    onefile build this is PyInstaller's extraction dir (sys._MEIPASS); in a
    onedir/.app build it's the folder next to the executable; in dev it's
    the repo root.
  - DATA_ROOT: writable, per-user state (scan cache, imported sources,
    exported reports). A frozen app's install location is often read-only
    (Program Files, a mounted .app) and, for a onefile build, is deleted
    after every run -- so this can never be the same as BUNDLE_ROOT. It
    lives under the OS's normal per-user data directory. In dev mode it
    stays next to the source, matching this project's pre-packaging layout.
"""
import os
import sys
from pathlib import Path

IS_FROZEN = bool(getattr(sys, "frozen", False))


def _bundle_root():
    if IS_FROZEN:
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


def _data_root():
    if not IS_FROZEN:
        # Matches this project's pre-packaging layout exactly (src/pages.json,
        # src/import/, src/export/), so dev-mode behavior is unchanged.
        return Path(__file__).resolve().parent.parent / "src"

    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    return base / "Ressemble"


BUNDLE_ROOT = _bundle_root()
DATA_ROOT = _data_root()

FONTS_DIR = BUNDLE_ROOT / "src" / "fonts"

PAGES_CONFIG_PATH = DATA_ROOT / "pages.json"
TEMPLATE_CONFIG_PATH = DATA_ROOT / "template.json"
BASE_DATA_PATH = DATA_ROOT / "import" / "split_pages"
ADVISORS_PATH = DATA_ROOT / "import" / "advisors"
TEAR_SHEETS_PATH = DATA_ROOT / "import" / "tear_sheets"
EXPORT_PATH = DATA_ROOT / "export"


def ensure_data_dirs():
    """Creates the writable data tree and seeds empty config files on
    first run. Safe to call every startup -- everything here is a no-op
    once it exists."""
    for directory in (DATA_ROOT, BASE_DATA_PATH, ADVISORS_PATH, TEAR_SHEETS_PATH, EXPORT_PATH):
        directory.mkdir(parents=True, exist_ok=True)

    for config_path in (PAGES_CONFIG_PATH, TEMPLATE_CONFIG_PATH):
        if not config_path.exists():
            config_path.write_text("{}")
