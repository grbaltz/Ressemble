from PySide6.QtWidgets import QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout
from PySide6.QtCore import Qt, Signal
from gui.widgets.no_wheel_combo import NoWheelComboBox
from src.advisors import (
    load_cached_advisors,
    load_cached_advisor_combos,
    advisor_combo_file,
    load_advisor_roles,
    ROLE_ADVISOR,
    ROLE_SERVICE,
)

# (label, which classified role is offered in that slot -- see
# load_advisor_roles() in src/advisors.py)
ADVISOR_ROLES = [
    ("Advisor 1", ROLE_ADVISOR),
    ("Advisor 2", ROLE_ADVISOR),
    ("Advisor 3", ROLE_ADVISOR),
    ("Service", ROLE_SERVICE),
]

NO_COMBO_WARNING = "This combination doesn't match an existing team page. The report will use a placeholder for it."


class TeamPicker(QWidget):
    """Who's on this report: an optional "Team page" shortcut plus one
    dropdown per role (Advisor 1/2/3, Service).

    Picking a team page just fills the role dropdowns with that team's
    names (advisors into Advisor 1/2/3, service into Service -- see
    _slot_assignment()). It then keeps showing whichever team the role
    dropdowns currently add up to: a hand-edit there reselects the
    matching team, or blanks the shortcut if none matches. Nothing here
    stops an unmatched combination -- the warning only informs.

    Four independent role slots rather than a multi-select list because
    picking a team is really "who's in each of these roles", and the combo
    file is just whichever set of names that produces (advisor_combo_file()
    dedupes and sorts before matching, so which slot a name lands in
    doesn't matter to the lookup).
    """

    changed = Signal()
    edit_roles_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        # Shown instead of the (empty) dropdowns when there's nobody to
        # offer yet -- no advisors file scanned, or nobody classified.
        self.empty_label = QLabel("")
        self.empty_label.setProperty("class", "status")
        self.empty_label.setWordWrap(True)
        outer.addWidget(self.empty_label)

        self.quick_select_label = QLabel("Team page")
        self.quick_select_label.setProperty("class", "field-label")
        self.quick_select_combo = NoWheelComboBox()
        self.quick_select_combo.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.quick_select_combo.currentIndexChanged.connect(self._on_quick_select_changed)

        self.quick_select_box = QWidget()
        quick_layout = QVBoxLayout()
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(4)
        quick_layout.addWidget(self.quick_select_label)
        quick_layout.addWidget(self.quick_select_combo)
        self.quick_select_box.setLayout(quick_layout)
        outer.addWidget(self.quick_select_box)

        self.advisor_combos = []
        self.roles_box = QWidget()
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        for index, (role_label, _) in enumerate(ADVISOR_ROLES):
            label = QLabel(role_label)
            label.setProperty("class", "field-label")

            combo = NoWheelComboBox()
            combo.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            combo.currentIndexChanged.connect(self._on_role_changed)
            self.advisor_combos.append(combo)

            cell = QVBoxLayout()
            cell.setSpacing(4)
            cell.addWidget(label)
            cell.addWidget(combo)
            grid.addLayout(cell, index // 2, index % 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        self.roles_box.setLayout(grid)
        outer.addWidget(self.roles_box)

        self.warning_label = QLabel(NO_COMBO_WARNING)
        self.warning_label.setProperty("class", "banner-text")
        self.warning_label.setWordWrap(True)
        self.warning_label.setVisible(False)
        outer.addWidget(self.warning_label)

        # Anyone left unclassified isn't offered in any dropdown, so say so
        # right here rather than failing silently.
        self.roles_notice = QLabel("")
        self.roles_notice.setWordWrap(True)
        self.edit_roles_button = QPushButton("Edit roles")
        self.edit_roles_button.setProperty("class", "link")
        self.edit_roles_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_roles_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.edit_roles_button.clicked.connect(self.edit_roles_requested)

        notice_row = QHBoxLayout()
        notice_row.setSpacing(8)
        notice_row.addWidget(self.roles_notice, 1)
        notice_row.addWidget(self.edit_roles_button, 0, Qt.AlignmentFlag.AlignTop)
        self.roles_notice_box = QFrame()
        self.roles_notice_box.setProperty("class", "banner")
        notice_row.setContentsMargins(10, 8, 10, 8)
        self.roles_notice_box.setLayout(notice_row)
        self.roles_notice_box.setVisible(False)
        outer.addWidget(self.roles_notice_box)

        self.setLayout(outer)

    # --- reading state ---

    def role_values(self):
        """One entry per dropdown, in role order -- "" for a slot left blank.
        Duplicate names across slots are kept as-is; deduplication happens
        in advisor_combo_file(), not here."""
        return [combo.currentData() or "" for combo in self.advisor_combos]

    def selected_advisors(self):
        return [name for name in self.role_values() if name]

    def has_unmatched_combination(self):
        selected = self.selected_advisors()
        return bool(selected) and advisor_combo_file(selected) is None

    # --- filling the dropdowns ---

    def refresh(self, preserve_selection=True):
        previous = self.role_values() if preserve_selection else [""] * len(self.advisor_combos)
        _, names = load_cached_advisors()
        self._populate(names, previous)

    def _populate(self, names, previous):
        # Each slot only offers people classified into its role -- anyone
        # not yet classified isn't offered anywhere.
        roles = load_advisor_roles()
        for combo, (_, slot_role), prior_value in zip(self.advisor_combos, ADVISOR_ROLES, previous):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("None", "")
            for name in names:
                if roles.get(name) == slot_role:
                    combo.addItem(name, name)

            index = combo.findData(prior_value) if prior_value else 0
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.blockSignals(False)

        # Filtered to teams that can actually be laid out in the role
        # dropdowns -- see _slot_assignment(). One with an unclassified
        # member, or more advisors/service people than there are slots for,
        # couldn't be fully applied by _on_quick_select_changed(), so it's
        # left out rather than offered and silently truncated.
        assignments = []
        for combo_names in load_cached_advisor_combos():
            slots = self._slot_assignment(combo_names, roles)
            if slots is not None:
                assignments.append((combo_names, slots))

        self.quick_select_combo.blockSignals(True)
        self.quick_select_combo.clear()
        self.quick_select_combo.addItem("Choose a team page", None)
        for combo_names, slots in assignments:
            self.quick_select_combo.addItem(", ".join(combo_names), slots)
        self.quick_select_combo.setCurrentIndex(0)
        self.quick_select_combo.blockSignals(False)
        self._sync_quick_select()

        classified = [name for name in names if name in roles]
        unclassified = [name for name in names if name not in roles]

        self.empty_label.setText("No advisors yet. Add an advisors file in the Library.")
        self.empty_label.setVisible(not names)

        self.roles_notice_box.setVisible(bool(unclassified))
        if unclassified:
            plural = "people need" if len(unclassified) != 1 else "person needs"
            self.roles_notice.setText(f"{len(unclassified)} {plural} a role before they can be picked.")
        self.quick_select_box.setVisible(bool(assignments))
        self.roles_box.setVisible(bool(classified))

        self._update_warning()

    @staticmethod
    def _slot_assignment(combo_names, roles):
        """One name (or "") per role dropdown, in ADVISOR_ROLES order, with
        each of combo_names placed into the next free slot for its role --
        or None if that can't be done."""
        slots = [""] * len(ADVISOR_ROLES)
        for name in combo_names:
            free = [
                i for i, (_, slot_role) in enumerate(ADVISOR_ROLES)
                if slot_role == roles.get(name) and not slots[i]
            ]
            if not free:
                return None
            slots[free[0]] = name
        return slots

    # --- reacting to changes ---

    def _on_quick_select_changed(self):
        slots = self.quick_select_combo.currentData()

        if slots:
            for role_combo, name in zip(self.advisor_combos, slots):
                role_combo.blockSignals(True)
                index = role_combo.findData(name) if name else 0
                role_combo.setCurrentIndex(index if index >= 0 else 0)
                role_combo.blockSignals(False)

        self._update_warning()
        self.changed.emit()

    def _on_role_changed(self):
        self._sync_quick_select()
        self._update_warning()
        self.changed.emit()

    def _sync_quick_select(self):
        """Points the Team page dropdown at the team the role dropdowns
        currently add up to -- compared as a set of names, since a
        hand-built team may sit in different slots than _slot_assignment()
        would put it -- or at the blank entry if no listed team matches."""
        selected = set(self.selected_advisors())
        index = 0
        if selected:
            for i in range(1, self.quick_select_combo.count()):
                slots = self.quick_select_combo.itemData(i)
                if {name for name in slots if name} == selected:
                    index = i
                    break

        self.quick_select_combo.blockSignals(True)
        self.quick_select_combo.setCurrentIndex(index)
        self.quick_select_combo.blockSignals(False)

    def _update_warning(self):
        self.warning_label.setVisible(self.has_unmatched_combination())
