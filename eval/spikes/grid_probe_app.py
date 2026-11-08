r"""A Qt window with one table and one list, for `grid_probe.py qt` to measure.

Kept as close as possible to what the sample app's list screen will be (#33, RS C.2): a
`QTableWidget` with three named columns and three data rows, and a `QListWidget` of Turkish
items. The table sets `SelectionBehavior = SelectRows`, because that is what makes the v0.2
`SelectRow` keyword work by selecting a row's first cell — the ADR records that the sample
app must set it, so the probe measures the configuration we are committing to, not Qt's
default.

Run it on its own to look at it by hand:

    python grid_probe_app.py
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QListWidget,
    QMainWindow,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

TITLE = "AYNA Grid Probe"
COLUMNS = ("Ad", "Soyad", "Şehir")
ROWS = (
    ("Ayşe", "Yılmaz", "Ankara"),
    ("Mehmet", "Demir", "İstanbul"),
    ("Zeynep", "Kaya", "İzmir"),
)
ITEMS = ("Ankara", "İstanbul", "İzmir", "Bursa")


class GridProbeWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(TITLE)
        self.setObjectName("GridProbeWindow")
        self.resize(520, 380)

        central = QWidget()
        central.setObjectName("central")
        layout = QVBoxLayout(central)

        self.customer_grid = QTableWidget(len(ROWS), len(COLUMNS))
        self.customer_grid.setObjectName("customerGrid")
        self.customer_grid.setHorizontalHeaderLabels(list(COLUMNS))
        # The configuration the v0.2 ADR requires of the sample app's grid: with Qt's
        # default (SelectItems) the same Select() call selects one cell, not the row.
        self.customer_grid.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        for row, values in enumerate(ROWS):
            for column, value in enumerate(values):
                self.customer_grid.setItem(row, column, QTableWidgetItem(value))
        layout.addWidget(self.customer_grid)

        self.city_list = QListWidget()
        self.city_list.setObjectName("cityList")
        self.city_list.addItems(list(ITEMS))
        layout.addWidget(self.city_list)

        self.setCentralWidget(central)


def main() -> int:
    app = QApplication(sys.argv)
    window = GridProbeWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
