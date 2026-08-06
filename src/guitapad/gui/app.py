"""PySide6 application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from guitapad.gui.main_window import MainWindow
from guitapad.gui.theme import APP_STYLESHEET
from guitapad.runtime import GuitaPadRuntime


def main() -> int:
    app = QApplication(sys.argv)

    app.setApplicationName("GuitaPaD")
    app.setOrganizationName("GuitaPaD")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)

    runtime = GuitaPadRuntime(
        initial_master_gain=0.60,
    )

    window = MainWindow(runtime)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
