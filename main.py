import sys
import traceback
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QWidget,
)


def main():
    print("=" * 60)
    print("FLOWPILOT STARTING")
    print("=" * 60)
    print(f"Python executable: {sys.executable}")
    print(f"Project directory: {Path.cwd()}")

    try:
        from app.ui.main_window import MainWindow

        print("MainWindow imported successfully.")

        app = QApplication(sys.argv)
        app.setApplicationName("FlowPilot")
        app.setOrganizationName("FlowPilot")

        window = MainWindow()
        window.setWindowTitle(
            "FlowPilot | Research Engineering Workbench"
        )
        window.resize(1400, 850)

        # Keep a reference to the window throughout the event loop.
        app.main_window = window

        window.show()
        window.raise_()
        window.activateWindow()

        # Confirm that Qt has processed the initial show event.
        app.processEvents()

        print(f"Window visible: {window.isVisible()}")
        print(f"Window size: {window.size().width()} x "
              f"{window.size().height()}")
        print("FlowPilot GUI started successfully.")

        return_code = app.exec()

        print(f"FlowPilot exited with code: {return_code}")
        return return_code

    except Exception:
        error = traceback.format_exc()

        print("\nFLOWPILOT STARTUP ERROR")
        print(error)

        # Attempt to show the error in a GUI dialog.
        try:
            app = QApplication.instance()

            if app is None:
                app = QApplication(sys.argv)

            QMessageBox.critical(
                None,
                "FlowPilot Startup Error",
                error,
            )
        except Exception:
            print("Could not display the error dialog.")

        return 1


if __name__ == "__main__":
    sys.exit(main())