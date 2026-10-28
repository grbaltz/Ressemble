from PySide6.QtCore import Qt, QByteArray
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QLabel
from src.paths import BUNDLE_ROOT

ICON_DIR = BUNDLE_ROOT / "gui" / "assets" / "icons"

# Rendered at 2x and tagged with a device pixel ratio so they stay crisp on
# high-DPI screens without querying the screen for its actual ratio.
_SCALE = 2

_pixmap_cache = {}


def pixmap(name, color, size=18):
    """The named stroke icon drawn in `color`, or an empty pixmap if the
    file's missing -- a lost icon should never take the screen down with it."""
    key = (name, color, size)
    cached = _pixmap_cache.get(key)
    if cached is not None:
        return cached

    result = QPixmap()
    try:
        svg = (ICON_DIR / f"{name}.svg").read_text(encoding="utf-8")
    except OSError:
        _pixmap_cache[key] = result
        return result

    renderer = QSvgRenderer(QByteArray(svg.replace("currentColor", color).encode("utf-8")))
    result = QPixmap(size * _SCALE, size * _SCALE)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    renderer.render(painter)
    painter.end()
    result.setDevicePixelRatio(_SCALE)

    _pixmap_cache[key] = result
    return result


def icon(name, color, size=18):
    return QIcon(pixmap(name, color, size))


def icon_label(name, color, size=18):
    """A fixed-size QLabel showing the icon; swap it later with set_icon()."""
    label = QLabel()
    label.setFixedSize(size, size)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setPixmap(pixmap(name, color, size))
    return label


def set_icon(label, name, color):
    label.setPixmap(pixmap(name, color, label.width()))
