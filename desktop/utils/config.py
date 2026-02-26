
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
        # Running as script - repo root (one level above desktop/)
        app_dir = Path(__file__).parent.parent.parent
    
    # Create data folder if it doesn't exist
    data_dir = app_dir / 'data'
    data_dir.mkdir(exist_ok=True)
    
    return data_dir


# Window settings
WINDOW_TITLE = "Budget Saver"
WINDOW_SIZE = "1100x788"
WINDOW_MIN_WIDTH = 900
WINDOW_MIN_HEIGHT = 630

# Predefined amount buttons
PRESET_AMOUNTS = [1000, 2000, 3000, 5000]

# Supported currencies
CURRENCIES = {
    'EUR': {'symbol': '€', 'suffix': False},
    'SEK': {'symbol': 'kr', 'suffix': True},
    'USD': {'symbol': '$', 'suffix': False},
}
DEFAULT_CURRENCY = 'EUR'

# Exchange rates relative to EUR (1 EUR = X units of that currency)
EXCHANGE_RATES = {
    'EUR': 1.0,
    'SEK': 11.5,
    'USD': 1.08,
}

# Budget categories (single list now)
BUDGET_CATEGORIES = ['Transport', 'Travel', 'Entertainment', 'Investment', 'Savings', 'Others']

# Expense categories (separate tracker)
EXPENSE_CATEGORIES = ['Loans','Housing', 'Transport', 'Healthcare', 'Shopping', 'Entertainment','Others']

# Internal category used for salary / income entries (never shown as a tab)
SALARY_CATEGORY = '__salary__'

# Internal categories for the expenses → savings transfer bridge#
DISTRIBUTABLE_CATEGORY = '__distributable__'   
TRANSFER_OUT_CATEGORY  = '__transfer_out__'   

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

# Data files - stored in data folder
DATA_DIR = get_data_directory()
DATA_FILE = str(DATA_DIR / 'savings_data.json')
EXPENSE_DATA_FILE = str(DATA_DIR / 'expenses_data.json')