
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Callable, Dict, Optional

from utils.config import (
    WINDOW_TITLE, WINDOW_SIZE, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    COLORS, FONTS, PADDING
)
from utils.helpers import format_currency
from .components import BudgetButtonPanel, SummaryCard, TransactionList


class MainView:
    """
    Main application view for budget tracking.
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self._setup_window()
        self._setup_styles()
        self._create_widgets()
        
        # Callbacks to be set by controller
        self.on_add_budget: Optional[Callable[[float, str, str], None]] = None  
        self.on_spend_budget: Optional[Callable[[float, str, str], None]] = None 
        self.on_clear_data: Optional[Callable[[], None]] = None
        self.on_clear_category: Optional[Callable[[str], None]] = None
        self.on_create_category: Optional[Callable[[str], bool]] = None
        self.on_currency_change: Optional[Callable[[str], None]] = None
        self.on_edit_rates: Optional[Callable[[], None]] = None

    def _setup_window(self):
        """Configure the main window."""
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.root.configure(bg=COLORS['background'])

        # Set window icon (dev: project root, packaged: PyInstaller extraction dir)
        if getattr(sys, 'frozen', False):
            base = Path(sys._MEIPASS)
        else:
            base = Path(__file__).parent.parent
        icon_path = base / 'assets' / 'budget.ico'
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass
        
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _setup_styles(self):
        """Configure ttk styles."""
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('TFrame', background=COLORS['background'])
        style.configure('Card.TFrame', background=COLORS['card_bg'])
        style.configure('TLabel', background=COLORS['background'], foreground=COLORS['text_primary'])
        style.configure('Card.TLabel', background=COLORS['card_bg'])
        style.configure('TNotebook', background=COLORS['background'])
        style.configure('TNotebook.Tab', padding=[20, 10], font=FONTS['body'])
        style.configure('TButton', font=FONTS['button'], padding=10)

    def _create_widgets(self):
        """Create all main widgets."""
        main_container = ttk.Frame(self.root, padding=PADDING['large'])
        main_container.pack(fill='both', expand=True)

        self._create_header(main_container)
        self._create_notebook(main_container)

    def _create_header(self, parent):
        """Create the header section with summary cards."""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill='x', pady=(0, PADDING['large']))

        # Title row: title on left, currency selector on right
        title_row = ttk.Frame(header_frame)
        title_row.pack(fill='x')

        title_label = ttk.Label(
            title_row,
            text="💰 Budget Saver",
            font=FONTS['title']
        )
        title_label.pack(side='left')

        # Currency radio buttons
        currency_frame = ttk.Frame(title_row)
        currency_frame.pack(side='right')

        ttk.Label(
            currency_frame,
            text="Currency:",
            font=FONTS['body']
        ).pack(side='left', padx=(0, PADDING['small']))

        self.currency_var = tk.StringVar(value='EUR')
        for code in ['EUR', 'SEK', 'USD']:
            rb = tk.Radiobutton(
                currency_frame,
                text=code,
                variable=self.currency_var,
                value=code,
                font=FONTS['button'],
                bg=COLORS['background'],
                activebackground=COLORS['background'],
                selectcolor=COLORS['background'],
                cursor='hand2',
                command=self._on_currency_change
            )
            rb.pack(side='left', padx=PADDING['small'])

        rates_btn = tk.Button(
            currency_frame,
            text="⚙ Rates",
            font=FONTS['body'],
            bg=COLORS['text_secondary'],
            fg='white',
            activebackground=COLORS['text_primary'],
            activeforeground='white',
            relief='flat',
            cursor='hand2',
            command=self._on_edit_rates_click,
        )
        rates_btn.pack(side='left', padx=(PADDING['medium'], 0))

        # Summary cards
        cards_frame = ttk.Frame(header_frame)
        cards_frame.pack(fill='x', pady=PADDING['medium'])

        # Total Budget card
        self.total_card = SummaryCard(
            cards_frame,
            title="Total Budget",
            value=0,
            color=COLORS['text_primary']
        )
        self.total_card.pack(side='left', padx=(0, PADDING['large']))

        # Total Added card
        self.added_card = SummaryCard(
            cards_frame,
            title="Total Added",
            value=0,
            color=COLORS['add']
        )
        self.added_card.pack(side='left', padx=PADDING['large'])

        # Total Spent card
        self.spent_card = SummaryCard(
            cards_frame,
            title="Total Spent",
            value=0,
            color=COLORS['spend']
        )
        self.spent_card.pack(side='left', padx=PADDING['large'])

        # Foreign currency tracker row (shown when foreign-currency transactions exist)
        self.foreign_currency_frame = ttk.Frame(header_frame)
        self.foreign_currency_frame.pack(fill='x', pady=(0, PADDING['small']))

        # Clear button
        clear_btn = tk.Button(
            cards_frame,
            text="Clear All Data",
            font=FONTS['body'],
            bg=COLORS['warning'],
            fg='white',
            relief='flat',
            cursor='hand2',
            command=self._on_clear_click
        )
        clear_btn.pack(side='right')
        
        export_btn = tk.Button(
            cards_frame,
            text="📊 Export to Excel",
            font=FONTS['body'],
            bg=COLORS['add'],
            fg='white',
            relief='flat',
            cursor='hand2',
            command=self._on_export_click
        )
        export_btn.pack(side='right', padx=(0, PADDING['small']))

    def _create_notebook(self, parent):
        """Create the tabbed notebook for categories."""
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill='both', expand=True)

        self.category_tabs: Dict[str, Dict] = {}
        
    def add_new_category_tab(self):
        """Add the '+' tab for creating new categories."""
        add_tab_frame = ttk.Frame(self.notebook, padding=PADDING['large'])
        self.notebook.add(add_tab_frame, text="  ➕  ")
        
        # Center content
        center_frame = ttk.Frame(add_tab_frame)
        center_frame.place(relx=0.5, rely=0.4, anchor='center')
        
        ttk.Label(
            center_frame,
            text="Create New Budget Category",
            font=FONTS['title']
        ).pack(pady=PADDING['medium'])
        
        # Input frame
        input_frame = ttk.Frame(center_frame)
        input_frame.pack(pady=PADDING['medium'])
        
        ttk.Label(
            input_frame,
            text="Category Name:",
            font=FONTS['body']
        ).pack(side='left', padx=PADDING['small'])
        
        self.new_category_entry = ttk.Entry(input_frame, width=20, font=FONTS['body'])
        self.new_category_entry.pack(side='left', padx=PADDING['small'])
        self.new_category_entry.bind('<Return>', lambda e: self._on_create_category())
        
        create_btn = tk.Button(
            input_frame,
            text="Create",
            font=FONTS['button'],
            bg=COLORS['add'],
            fg='white',
            activebackground=COLORS['add_hover'],
            activeforeground='white',
            relief='flat',
            cursor='hand2',
            command=self._on_create_category
        )
        create_btn.pack(side='left', padx=PADDING['small'])
        
        # Store reference to the + tab index
        self.add_tab_index = self.notebook.index('end') - 1

    def _on_create_category(self):
        """Handle create category button click."""
        name = self.new_category_entry.get().strip()
        
        if not name:
            self.show_message("Error", "Please enter a category name.", "error")
            return
            
        if name in self.category_tabs:
            self.show_message("Error", f"Category '{name}' already exists.", "error")
            return
        
        if self.on_create_category:
            success = self.on_create_category(name)
            if success:
                self.new_category_entry.delete(0, tk.END)

    def add_category_tab(self, category_name: str, transactions: list, insert_before_plus: bool = False):
        """Add a new category tab to the notebook."""
        tab_frame = ttk.Frame(self.notebook, padding=PADDING['medium'])
        
        # Insert before the + tab if it exists and requested
        if insert_before_plus and hasattr(self, 'add_tab_index'):
            self.notebook.insert(self.add_tab_index, tab_frame, text=category_name)
            self.add_tab_index += 1  # Update + tab position
        else:
            self.notebook.add(tab_frame, text=category_name)

        # Left panel - buttons
        left_panel = ttk.Frame(tab_frame)
        left_panel.pack(side='left', fill='y', padx=(0, PADDING['large']))

        # Budget buttons (Add + Spend)
        button_panel = BudgetButtonPanel(
            left_panel,
            on_add_click=lambda amount, currency: self._on_add_click(amount, category_name, currency),
            on_spend_click=lambda amount, currency: self._on_spend_click(amount, category_name, currency),
            initial_currency=self.currency_var.get(),
        )
        button_panel.pack(fill='x')

        # Category balance
        balance_frame = ttk.Frame(left_panel)
        balance_frame.pack(fill='x', pady=PADDING['large'])
        
        ttk.Label(
            balance_frame,
            text=f"📊 {category_name} Balance:",
            font=FONTS['heading']
        ).pack(anchor='w')
        
        balance_label = ttk.Label(
            balance_frame,
            text=format_currency(0),
            font=FONTS['amount'],
            foreground=COLORS['text_primary']
        )
        balance_label.pack(anchor='w')

        # Clear category button
        clear_cat_btn = tk.Button(
            left_panel,
            text=f"Clear {category_name}",
            font=FONTS['body'],
            bg=COLORS['warning'],
            fg='white',
            relief='flat',
            cursor='hand2',
            command=lambda c=category_name: self._on_clear_category_click(c)
        )
        clear_cat_btn.pack(fill='x', pady=PADDING['medium'])
        
        delete_cat_btn = tk.Button(
            left_panel,
            text=f"Delete {category_name}",
            font=FONTS['body'],
            bg=COLORS['spend'],
            fg='white',
            relief='flat',
            cursor='hand2',
            command=lambda c=category_name: self._on_delete_category_click(c)
        )
        delete_cat_btn.pack(fill='x', pady=(0, PADDING['medium']))

        # Right panel - transaction list
        right_panel = ttk.Frame(tab_frame)
        right_panel.pack(side='right', fill='both', expand=True)

        ttk.Label(
            right_panel,
            text="Recent Transactions",
            font=FONTS['heading']
        ).pack(anchor='w', pady=(0, PADDING['small']))

        transaction_list = TransactionList(right_panel)
        transaction_list.pack(fill='both', expand=True)

        # Add existing transactions
        for t in reversed(transactions[-20:]):
            transaction_list.add_item(t)

        # Store references
        self.category_tabs[category_name] = {
            'frame': tab_frame,
            'balance_label': balance_label,
            'transaction_list': transaction_list
        }

    def _on_add_click(self, amount: float, category: str, currency: str):
        """Handle add button click."""
        if self.on_add_budget:
            self.on_add_budget(amount, category, currency)

    def _on_spend_click(self, amount: float, category: str, currency: str):
        """Handle spend button click."""
        if self.on_spend_budget:
            self.on_spend_budget(amount, category, currency)

    def _on_clear_click(self):
        """Handle clear all data button click."""
        if messagebox.askyesno(
            "Confirm Clear",
            "Are you sure you want to clear all data?\nThis cannot be undone."
        ):
            if self.on_clear_data:
                self.on_clear_data()

    def _on_clear_category_click(self, category: str):
        """Handle clear category button click."""
        if messagebox.askyesno(
            "Confirm Clear",
            f"Are you sure you want to clear all {category} data?\nThis cannot be undone."
        ):
            if self.on_clear_category:
                self.on_clear_category(category)
                
    def _on_delete_category_click(self, category: str):
        if messagebox.askyesno(
            "Confirm Delete",
            f"Delete '{category}' and all its transactions?\nThis cannot be undone."
        ):
            if self.on_delete_category:
                self.on_delete_category(category)
                
    def _on_export_click(self):
        if self.on_export_data:
            self.on_export_data()

    def _on_currency_change(self):
        """Handle currency radio button change."""
        if self.on_currency_change:
            self.on_currency_change(self.currency_var.get())

    def _on_edit_rates_click(self):
        """Handle Rates button click."""
        if self.on_edit_rates:
            self.on_edit_rates()

    def show_rates_dialog(self, current_rates: dict, default_rates: dict, on_save):
        """Modal dialog for editing exchange rates."""
        from utils.config import CURRENCIES

        dialog = tk.Toplevel(self.root)
        dialog.title("Exchange Rates")
        dialog.resizable(False, False)
        dialog.grab_set()

        dialog.update_idletasks()
        w, h = 380, 60 + len([c for c in default_rates if c != 'EUR']) * 50 + 70
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        dialog.geometry(f"{w}x{h}+{x}+{y}")

        frame = ttk.Frame(dialog, padding=PADDING['large'])
        frame.pack(fill='both', expand=True)

        ttk.Label(
            frame, text="Exchange Rates  (1 EUR = X)",
            font=FONTS['heading'],
        ).pack(anchor='w', pady=(0, PADDING['medium']))

        entries = {}
        for code in default_rates:
            if code == 'EUR':
                continue
            sym = CURRENCIES[code]['symbol']
            default_val = default_rates[code]
            row = ttk.Frame(frame)
            row.pack(fill='x', pady=(0, PADDING['small']))
            ttk.Label(row, text="1 EUR =", font=FONTS['body']).pack(side='left')
            entry = ttk.Entry(row, width=10, font=FONTS['body'])
            entry.insert(0, str(current_rates.get(code, default_val)))
            entry.pack(side='left', padx=PADDING['small'])
            ttk.Label(
                row,
                text=f"{sym}    (default: {default_val})",
                font=FONTS['body'],
                foreground=COLORS['text_secondary'],
            ).pack(side='left')
            entries[code] = entry

        def _save():
            new_rates = {'EUR': 1.0}
            for code, entry in entries.items():
                try:
                    rate = float(entry.get().strip().replace(',', '.'))
                    if rate <= 0:
                        raise ValueError
                    new_rates[code] = rate
                except ValueError:
                    self.show_message("Error", f"Invalid rate for {code}. Enter a positive number.", "error")
                    return
            on_save(new_rates)
            dialog.destroy()

        def _reset():
            for code, entry in entries.items():
                entry.delete(0, tk.END)
                entry.insert(0, str(default_rates[code]))

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill='x', pady=(PADDING['medium'], 0))

        tk.Button(
            btn_row, text="Reset to Default", font=FONTS['body'],
            bg=COLORS['warning'], fg='white', relief='flat', cursor='hand2',
            command=_reset,
        ).pack(side='left')
        tk.Button(
            btn_row, text="Cancel", font=FONTS['body'],
            bg=COLORS['text_secondary'], fg='white', relief='flat', cursor='hand2',
            command=dialog.destroy,
        ).pack(side='right', padx=(PADDING['small'], 0))
        tk.Button(
            btn_row, text="Save", font=FONTS['button'],
            bg=COLORS['add'], fg='white', relief='flat', cursor='hand2',
            command=_save,
        ).pack(side='right')

    def set_currency(self, code: str):
        """Set the active currency radio button without triggering the callback."""
        self.currency_var.set(code)

    def refresh_summary_currency(self):
        """Re-render summary cards with the current currency symbol."""
        self.total_card.refresh_display()
        self.added_card.refresh_display()
        self.spent_card.refresh_display()

    def update_summary(self, total: float, added: float, spent: float):
        """Update the summary cards."""
        self.total_card.update_value(total)
        self.added_card.update_value(added)
        self.spent_card.update_value(spent)

    def update_foreign_currency_display(self, totals: dict):
        """Rebuild the foreign currency tracker row below the summary cards."""
        from utils.helpers import format_currency_for_code
        for widget in self.foreign_currency_frame.winfo_children():
            widget.destroy()

        if not totals:
            return

        ttk.Label(
            self.foreign_currency_frame,
            text="Foreign Currency Activity:",
            font=FONTS['body'],
            foreground=COLORS['text_secondary'],
        ).pack(side='left', padx=(0, PADDING['medium']))

        for code, data in totals.items():
            net = data['added'] - data['spent']
            net_str = format_currency_for_code(abs(net), code)
            sign = '+' if net >= 0 else '-'
            color = COLORS['add'] if net >= 0 else COLORS['spend']
            ttk.Label(
                self.foreign_currency_frame,
                text=f"{code}: {sign}{net_str}",
                font=FONTS['heading'],
                foreground=color,
            ).pack(side='left', padx=(0, PADDING['large']))

    def update_category(self, category_name: str, balance: float, transaction=None):
        """Update a category tab with new data."""
        if category_name not in self.category_tabs:
            return

        tab_data = self.category_tabs[category_name]
        tab_data['balance_label'].config(text=format_currency(balance))

        if transaction:
            tab_data['transaction_list'].add_item(transaction)

    def refresh_all_transactions(self, category_name: str, transactions: list):
        """Refresh all transactions for a category."""
        if category_name not in self.category_tabs:
            return

        tab_data = self.category_tabs[category_name]
        tab_data['transaction_list'].clear()
        
        for t in reversed(transactions[-20:]):
            tab_data['transaction_list'].add_item(t)

    def show_message(self, title: str, message: str, msg_type: str = 'info'):
        """Show a message dialog."""
        if msg_type == 'error':
            messagebox.showerror(title, message)
        elif msg_type == 'warning':
            messagebox.showwarning(title, message)
        else:
            messagebox.showinfo(title, message)

    def select_tab(self, category_name: str):
        """Select a specific category tab."""
        if category_name in self.category_tabs:
            tab_frame = self.category_tabs[category_name]['frame']
            self.notebook.select(tab_frame)
            
    def remove_category_tab(self, category_name: str):
        """Remove a category tab from the notebook."""
        if category_name not in self.category_tabs:
            return
        tab_frame = self.category_tabs[category_name]['frame']
        self.notebook.forget(tab_frame)
        del self.category_tabs[category_name]
        # Fix + tab index after removal
        if hasattr(self, 'add_tab_index'):
            self.add_tab_index -= 1