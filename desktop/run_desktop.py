
"""TimanStat desktop application entry point.

The desktop interface uses the shared TimanStat branding configuration.
The desktop shell is intentionally lightweight and is designed to connect
to the shared analytical engine as desktop functionality is developed.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from timan_intelligence.config import (
    APP_DESCRIPTION,
    APP_NAME,
    APP_ORGANISATION,
    APP_TAGLINE,
    APP_VERSION,
)


class TimanStatDesktop(QMainWindow):
    """Main window for the TimanStat desktop application."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(f"{APP_NAME} | {APP_ORGANISATION}")
        self.setMinimumSize(900, 600)

        self._build_interface()

    def _build_interface(self) -> None:
        """Construct the desktop application's initial interface."""

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        layout.setContentsMargins(50, 40, 50, 40)
        layout.setSpacing(18)

        heading = QLabel(APP_NAME)
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading.setStyleSheet(
            """
            QLabel {
                font-size: 34px;
                font-weight: bold;
                color: #174A7E;
            }
            """
        )

        organisation = QLabel(APP_ORGANISATION)
        organisation.setAlignment(Qt.AlignmentFlag.AlignCenter)
        organisation.setStyleSheet(
            """
            QLabel {
                font-size: 17px;
                font-weight: 600;
                color: #555555;
            }
            """
        )

        tagline = QLabel(APP_TAGLINE)
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setWordWrap(True)
        tagline.setStyleSheet(
            """
            QLabel {
                font-size: 15px;
                color: #444444;
            }
            """
        )

        description = QLabel(APP_DESCRIPTION)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        description.setMaximumWidth(650)
        description.setStyleSheet(
            """
            QLabel {
                font-size: 13px;
                color: #666666;
                line-height: 1.5;
            }
            """
        )

        description_container = QVBoxLayout()
        description_container.addWidget(
            description,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )

        status = QLabel("Desktop foundation is ready for further development.")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status.setWordWrap(True)
        status.setStyleSheet(
            """
            QLabel {
                font-size: 13px;
                color: #666666;
                padding: 12px;
            }
            """
        )

        version = QLabel(f"Version {APP_VERSION}")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet(
            """
            QLabel {
                font-size: 11px;
                color: #888888;
            }
            """
        )

        close_button = QPushButton("Close Application")
        close_button.setFixedWidth(180)
        close_button.clicked.connect(self.close)
        close_button.setStyleSheet(
            """
            QPushButton {
                background-color: #174A7E;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 16px;
                font-size: 13px;
            }

            QPushButton:hover {
                background-color: #10365D;
            }
            """
        )

        layout.addStretch()
        layout.addWidget(heading)
        layout.addWidget(organisation)
        layout.addWidget(tagline)
        layout.addSpacing(15)
        layout.addLayout(description_container)
        layout.addSpacing(25)
        layout.addWidget(status)
        layout.addWidget(version)
        layout.addSpacing(15)
        layout.addWidget(
            close_button,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        layout.addStretch()

        self.setCentralWidget(central_widget)


def main() -> int:
    """Start the TimanStat desktop application."""

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORGANISATION)
    app.setApplicationVersion(APP_VERSION)

    window = TimanStatDesktop()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
