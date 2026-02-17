
import sys
import os
from pathlib import Path


def get_data_directory() -> Path:
    """
    Get the proper directory for storing data files.
    Works for both development and packaged (.exe) versions.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled .exe - use exe's directory
        app_dir = Path(sys.executable).parent
    else:
        # Running as script - use script's directory
        app_dir = Path(__file__).parent.parent
    
    # Create data folder if it doesn't exist
    data_dir = app_dir / 'data'
    data_dir.mkdir(exist_ok=True)
    
    return data_dir


# Window settings
WINDOW_TITLE = "Budget Saver"
WINDOW_SIZE = "800x600"
WINDOW_MIN_WIDTH = 700
WINDOW_MIN_HEIGHT = 500

# Predefined amount buttons
PRESET_AMOUNTS = [1000, 2000, 3000, 5000]

# Budget categories (single list now)
BUDGET_CATEGORIES = ['Transport', 'Travel', 'Entertainment', 'Investment', 'Savings', 'Others']

# Colors
COLORS = {
    'add': '#2ecc71',              # Green - for adding
    'add_hover': '#27ae60',
    'spend': '#e74c3c',            # Red - for spending
    'spend_hover': '#c0392b',
    'background': '#f5f6fa',
    'card_bg': '#ffffff',
    'text_primary': '#2c3e50',
    'text_secondary': '#7f8c8d',
    'border': '#dcdde1',
    'success': '#2ecc71',
    'warning': '#f39c12',
}

# Fonts
FONTS = {
    'title': ('Segoe UI', 16, 'bold'),
    'heading': ('Segoe UI', 12, 'bold'),
    'body': ('Segoe UI', 10),
    'button': ('Segoe UI', 10, 'bold'),
    'amount': ('Segoe UI', 24, 'bold'),
}

# Padding
PADDING = {
    'small': 5,
    'medium': 10,
    'large': 20,
}

# Data file - stored in data folder
DATA_DIR = get_data_directory()
DATA_FILE = str(DATA_DIR / 'savings_data.json')