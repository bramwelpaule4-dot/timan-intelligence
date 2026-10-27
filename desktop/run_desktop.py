"""Minimal optional desktop shell; analytical functions remain in the shared package."""

import sys

try:
    from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget
except ImportError as exc:
    raise SystemExit(
        "Desktop dependencies are missing. Install them with: "
        "pip install -r requirements-desktop.txt"
    ) from exc


def main() -> int:
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("Timan Intelligence")
    window.resize(900, 600)

    central = QWidget()
    layout = QVBoxLayout(central)
    heading = QLabel("Timan Intelligence")
    heading.setStyleSheet("font-size: 24px; font-weight: 600;")
    description = QLabel(
        "Desktop interface foundation\n\n"
        "The shared analytical package is being established. "
        "This shell does not yet provide the full analytical workflow."
    )
    description.setWordWrap(True)
    layout.addWidget(heading)
    layout.addWidget(description)
    window.setCentralWidget(central)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
