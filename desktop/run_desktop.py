
"""TimanStat desktop application shell.

The desktop interface uses the central TimanStat identity configuration.
Statistical functionality remains in the shared application package.
"""

import sys
from pathlib import Path

# Support launching from a source checkout as well as an installed package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from timan_intelligence.config import (
    APP_DESCRIPTION,
    APP_NAME,
    APP_ORGANISATION,
    APP_TAGLINE,
    APP_VERSION,
)

try:
    from PySide6.QtWidgets import (
        QApplication,
        QLabel,
        QMainWindow,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise SystemExit(
        "Desktop dependencies are missing. Install them using: "
        "pip install -r requirements-desktop.txt"
    ) from exc


def main() -> int:
    """Launch the TimanStat desktop application."""

    app = QApplication(sys.argv)

    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORGANISATION)
    app.setApplicationVersion(APP_VERSION)

    window = QMainWindow()
    window.setWindowTitle(f"{APP_NAME} | {APP_ORGANISATION}")
    window.resize(900, 600)

    central = QWidget()
    layout = QVBoxLayout(central)

    heading = QLabel(APP_NAME)
    heading.setStyleSheet(
        """
        font-size: 28px;
        font-weight: 700;
        color: #174a7e;
        """
    )

    tagline = QLabel(APP_TAGLINE)
    tagline.setStyleSheet(
        """
        font-size: 14px;
        color: #526579;
        """
    )

    description = QLabel(
        f"{APP_DESCRIPTION}\n\n"
        f"Developed by {APP_ORGANISATION}.\n"
        f"Version: {APP_VERSION}\n\n"
        "Desktop interface foundation. The complete analytical "
        "workflow is still under development."
    )
    description.setWordWrap(True)

    layout.addWidget(heading)
    layout.addWidget(tagline)
    layout.addWidget(description)

    window.setCentralWidget(central)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
