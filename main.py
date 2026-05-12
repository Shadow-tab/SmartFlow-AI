"""
main.py
-------
Entry point for SmartFlow AI.
Launches the Tkinter GUI window which connects to all AI modules.
Run this file to start the application:
    python3 main.py
"""

from modules.gui import launch_gui

if __name__ == "__main__":
    launch_gui()