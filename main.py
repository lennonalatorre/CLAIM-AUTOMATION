"""
main.py — Entry point for the Claim Processor (PyQt6 version)
-------------------------------------------------------------
Launches the offline insurance claim automation GUI.
"""
from debugger import setup_debugger
setup_debugger()  # initializes logging early
import sys
from PyQt6.QtWidgets import QApplication
from gui import ClaimGUI


def main():
    """Initialize and launch the Claim Processor GUI."""
    app = QApplication(sys.argv)
    app.setApplicationName("Claim Processor")

    window = ClaimGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
