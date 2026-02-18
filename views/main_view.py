
import tkinter as tk
from tkinter import ttk, messagebox
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
        self.on_add_budget: Optional[Callable[[float, str], None]] = None
        self.on_spend_budget: Optional[Callable[[float, str], None]] = None
        self.on_clear_data: Optional[Callable[[], None]] = None
        self.on_clear_category: Optional[Callable[[str], None]] = None
        self.on_create_category: Optional[Callable[[str], bool]] = None

    def _setup_window(self):
        """Configure the main window."""
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.root.configure(bg=COLORS['background'])

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

        # Title
        title_label = ttk.Label(
            header_frame,
            text="💰 Budget Saver",
            font=FONTS['title']
        )
        title_label.pack(anchor='w')

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
            on_add_click=lambda amount: self._on_add_click(amount, category_name),
            on_spend_click=lambda amount: self._on_spend_click(amount, category_name)
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
            text=f"🗑️ Clear {category_name}",
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

    def _on_add_click(self, amount: float, category: str):
        """Handle add button click."""
        if self.on_add_budget:
            self.on_add_budget(amount, category)

    def _on_spend_click(self, amount: float, category: str):
        """Handle spend button click."""
        if self.on_spend_budget:
            self.on_spend_budget(amount, category)

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

    def update_summary(self, total: float, added: float, spent: float):
        """Update the summary cards."""
        self.total_card.update_value(total)
        self.added_card.update_value(added)
        self.spent_card.update_value(spent)

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