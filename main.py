import sys

from PyQt6.QtWidgets import QApplication

from imgtools.gui import ImageFactory


def main() -> None:
    """Entry‑point for ImageFactory GUI application."""
    app = QApplication(sys.argv)
    window = ImageFactory()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
