from PySide6.QtWidgets import QListWidget, QStyle, QStyleOptionViewItem
from PySide6.QtCore import Qt, QEvent


class CheckableListWidget(QListWidget):
    """A QListWidget whose checkable items toggle on a click anywhere in
    the row, not just the checkbox glyph itself.

    Qt's default item delegate only toggles a checkable item's state when
    a click lands exactly on the small checkbox indicator -- clicking the
    rest of the row does nothing. Clicks that land on the indicator are
    left alone (the built-in toggle already handles those correctly);
    only clicks elsewhere on the row are toggled here manually, since
    toggling both would turn an actual checkbox click into a no-op
    (toggled once by Qt, then back again by us).
    """

    def _checkbox_rect(self, index):
        option = QStyleOptionViewItem()
        self.initViewItemOption(option)
        option.rect = self.visualRect(index)
        option.features |= QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator
        return self.style().subElementRect(QStyle.SubElement.SE_ItemViewItemCheckIndicator, option, self)

    def viewportEvent(self, event):
        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            index = self.indexAt(pos)
            if index.isValid() and not self._checkbox_rect(index).contains(pos):
                item = self.itemFromIndex(index)
                if (item.flags() & Qt.ItemFlag.ItemIsUserCheckable) and (item.flags() & Qt.ItemFlag.ItemIsEnabled):
                    item.setCheckState(
                        Qt.CheckState.Unchecked
                        if item.checkState() == Qt.CheckState.Checked
                        else Qt.CheckState.Checked
                    )
        return super().viewportEvent(event)
