"""
This module provides functionality to load a QSS stylesheet file and handle potential
errors related to file reading or encoding issues.

Functions:
    load_stylesheet: Reads a QSS stylesheet from the file system and returns its
    content, applying fallbacks for encoding issues or missing files.
"""
import os

def load_stylesheet():
    """Loads a QSS file and returns its content."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    layout_file = os.path.join(base_dir, "layout.qss")

    try:
        with open(layout_file, 'r', encoding="utf-8-sig", newline="") as f:
            return f.read()

    except UnicodeDecodeError as e:
        print(f"Error: Could not decode stylesheet '{layout_file}' as UTF-8 ({e}).")
        print("Tip: Re-save layout.qss as UTF-8, or remove any unusual characters.")
        # Fallback: load with a Windows-friendly encoding so the app can still start
        with open(layout_file, "r", encoding="cp1252", errors="replace", newline="") as f:
            return f.read()

    except FileNotFoundError:
        print("Error: Stylesheet file {} not found.".format(layout_file))

        return ""
