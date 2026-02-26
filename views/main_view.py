
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
    """Main application view for budget tracking."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self._setup_window()
        self._setup_styles()

        # ── Savings callbacks ────────────────────────────────────────
        self.on_add_budget:          Optional[Callable] = None
        self.on_spend_budget:        Optional[Callable] = None
        self.on_clear_data:          Optional[Callable] = None
        self.on_clear_category:      Optional[Callable] = None
        self.on_create_category:     Optional[Callable] = None
        self.on_export_data:         Optional[Callable] = None
        self.on_delete_category:     Optional[Callable] = None
        self.on_currency_change:     Optional[Callable] = None
        self.on_edit_rates:          Optional[Callable] = None

        # ── Expenses callbacks ───────────────────────────────────────
        self.on_add_expense:             Optional[Callable] = None
        self.on_spend_expense:           Optional[Callable] = None
        self.on_clear_expense_data:      Optional[Callable] = None
        self.on_clear_expense_category:  Optional[Callable] = None
        self.on_create_expense_category: Optional[Callable] = None
        self.on_export_expense_data:     Optional[Callable] = None
        self.on_delete_expense_category: Optional[Callable] = None
        self.on_transfer_to_savings:     Optional[Callable] = None
        self.on_add_direct_income:       Optional[Callable] = None
        self.on_edit_income:             Optional[Callable] = None
        self.on_delete_income:           Optional[Callable] = None

        self._create_widgets()

    # ── Window / style setup ─────────────────────────────────────────

    def _setup_window(self):
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.root.configure(bg=COLORS['background'])

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
        x = (self.root.winfo_screenwidth()  // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame',        background=COLORS['background'])
        style.configure('Card.TFrame',   background=COLORS['card_bg'])
        style.configure('TLabel',        background=COLORS['background'], foreground=COLORS['text_primary'])
        style.configure('Card.TLabel',   background=COLORS['card_bg'])
        style.configure('TNotebook',     background=COLORS['background'])
        style.configure('TNotebook.Tab', padding=[20, 10], font=FONTS['body'])
        style.configure('TButton',       font=FONTS['button'], padding=10)

    # ── Widget creation ──────────────────────────────────────────────

    def _create_widgets(self):
        main_container = ttk.Frame(self.root, padding=PADDING['large'])
        main_container.pack(fill='both', expand=True)

        self._create_top_bar(main_container)

        self.savings_frame = ttk.Frame(main_container)
        self.savings_frame.pack(fill='both', expand=True)
        self._create_savings_content(self.savings_frame)

        self.expenses_frame = ttk.Frame(main_container)
        # Not packed initially — shown only when mode == 'expenses'
        self._create_expenses_content(self.expenses_frame)

        self.active_mode = 'savings'

    # ── Top bar (mode switch + currency) ────────────────────────────

    def _create_top_bar(self, parent):
        bar = ttk.Frame(parent)
        bar.pack(fill='x', pady=(0, PADDING['medium']))

        # Mode toggle buttons (left)
        mode_frame = ttk.Frame(bar)
        mode_frame.pack(side='left')

        self._btn_savings = tk.Button(
            mode_frame, text="💰 Savings",
            font=FONTS['button'],
            bg=COLORS['text_primary'], fg='white',
            activebackground=COLORS['text_primary'], activeforeground='white',
            relief='flat', cursor='hand2', padx=12, pady=6,
            command=lambda: self.switch_mode('savings'),
        )
        self._btn_savings.pack(side='left', padx=(0, 4))

        self._btn_expenses = tk.Button(
            mode_frame, text="💸 Expenses",
            font=FONTS['button'],
            bg=COLORS['text_secondary'], fg='white',
            activebackground=COLORS['text_secondary'], activeforeground='white',
            relief='flat', cursor='hand2', padx=12, pady=6,
            command=lambda: self.switch_mode('expenses'),
        )
        self._btn_expenses.pack(side='left')

        # Currency selector (right) — shared by both modes
        currency_frame = ttk.Frame(bar)
        currency_frame.pack(side='right')

        ttk.Label(currency_frame, text="Currency:", font=FONTS['body']).pack(
            side='left', padx=(0, PADDING['small'])
        )

        self.currency_var = tk.StringVar(value='EUR')
        for code in ['EUR', 'SEK', 'USD']:
            rb = tk.Radiobutton(
                currency_frame, text=code,
                variable=self.currency_var, value=code,
                font=FONTS['button'],
                bg=COLORS['background'], activebackground=COLORS['background'],
                selectcolor=COLORS['background'],
                cursor='hand2', command=self._on_currency_change,
            )
            rb.pack(side='left', padx=PADDING['small'])

        tk.Button(
            currency_frame, text="⚙ Rates",
            font=FONTS['body'],
            bg=COLORS['text_secondary'], fg='white',
            activebackground=COLORS['text_primary'], activeforeground='white',
            relief='flat', cursor='hand2',
            command=self._on_edit_rates_click,
        ).pack(side='left', padx=(PADDING['medium'], 0))

    def switch_mode(self, mode: str):
        """Toggle between savings and expenses views."""
        self.active_mode = mode
        if mode == 'savings':
            self.expenses_frame.pack_forget()
            self.savings_frame.pack(fill='both', expand=True)
            self._btn_savings.config(bg=COLORS['text_primary'])
            self._btn_expenses.config(bg=COLORS['text_secondary'])
        else:
            self.savings_frame.pack_forget()
            self.expenses_frame.pack(fill='both', expand=True)
            self._btn_savings.config(bg=COLORS['text_secondary'])
            self._btn_expenses.config(bg=COLORS['text_primary'])

    # ── Savings content ──────────────────────────────────────────────

    def _create_savings_content(self, parent):
        # Summary cards row
        cards_frame = ttk.Frame(parent)
        cards_frame.pack(fill='x', pady=(0, PADDING['medium']))

        self.total_card = SummaryCard(cards_frame, title="Total Budget", value=0, color=COLORS['text_primary'])
        self.total_card.pack(side='left', padx=(0, PADDING['large']))

        self.added_card = SummaryCard(cards_frame, title="Total Added", value=0, color=COLORS['add'])
        self.added_card.pack(side='left', padx=PADDING['large'])

        self.spent_card = SummaryCard(cards_frame, title="Total Spent", value=0, color=COLORS['spend'])
        self.spent_card.pack(side='left', padx=PADDING['large'])

        tk.Button(
            cards_frame, text="Clear All Data",
            font=FONTS['body'], bg=COLORS['warning'], fg='white',
            relief='flat', cursor='hand2', command=self._on_clear_click,
        ).pack(side='right')

        tk.Button(
            cards_frame, text="📊 Export to Excel",
            font=FONTS['body'], bg=COLORS['add'], fg='white',
            relief='flat', cursor='hand2', command=self._on_export_click,
        ).pack(side='right', padx=(0, PADDING['small']))

        # Foreign currency row
        self.foreign_currency_frame = ttk.Frame(parent)
        self.foreign_currency_frame.pack(fill='x', pady=(0, PADDING['small']))

        # Distributable balance bar
        self._create_distributable_display(parent)

        # Notebook
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill='both', expand=True)
        self.category_tabs: Dict[str, Dict] = {}

    def _create_distributable_display(self, parent):
        """Colored banner showing how much transferred money is still free to allocate."""
        from utils.config import CURRENCIES
        bar = tk.Frame(parent, bg='#eafaf1', relief='flat', bd=0)
        bar.pack(fill='x', pady=(0, PADDING['small']), ipady=6)

        # Left: balance display
        tk.Label(
            bar, text="Available to Allocate:",
            font=FONTS['heading'], bg='#eafaf1', fg=COLORS['text_primary'],
        ).pack(side='left', padx=(PADDING['medium'], PADDING['small']))

        self._distributable_label = tk.Label(
            bar, text=format_currency(0),
            font=FONTS['heading'], bg='#eafaf1', fg=COLORS['text_secondary'],
        )
        self._distributable_label.pack(side='left')

        # Right: Other Income quick-add (adds directly to distributable pool)
        tk.Button(
            bar, text="Add →",
            font=FONTS['button'],
            bg=COLORS['add'], fg='white',
            activebackground=COLORS['add_hover'], activeforeground='white',
            relief='flat', cursor='hand2',
            command=self._on_add_direct_income_click,
        ).pack(side='right', padx=(PADDING['small'], PADDING['medium']))

        self._direct_income_currency_var = tk.StringVar(value='SEK')
        ttk.Combobox(
            bar,
            textvariable=self._direct_income_currency_var,
            values=list(CURRENCIES.keys()),
            state='readonly',
            width=5,
            font=FONTS['body'],
        ).pack(side='right', padx=PADDING['small'])

        tk.Label(
            bar, text="Currency:", font=FONTS['body'],
            bg='#eafaf1', fg=COLORS['text_secondary'],
        ).pack(side='right')

        self._direct_income_entry = tk.Entry(
            bar, width=12, font=FONTS['body'], relief='solid', bd=1,
        )
        self._direct_income_entry.pack(side='right', padx=PADDING['small'])
        self._direct_income_entry.bind('<Return>', lambda e: self._on_add_direct_income_click())

        tk.Label(
            bar, text="Other Income:",
            font=FONTS['body'], bg='#eafaf1', fg=COLORS['text_primary'],
        ).pack(side='right', padx=(PADDING['large'], PADDING['small']))

    def add_new_category_tab(self):
        """Add the '+' tab for creating new savings categories."""
        add_tab_frame = ttk.Frame(self.notebook, padding=PADDING['large'])
        self.notebook.add(add_tab_frame, text="  ➕  ")
        self._build_new_category_ui(
            add_tab_frame,
            label="Create New Budget Category",
            entry_attr='new_category_entry',
            on_create=self._on_create_category,
        )
        self.add_tab_index = self.notebook.index('end') - 1

    def add_category_tab(self, category_name: str, transactions: list, insert_before_plus: bool = False):
        """Add a new savings category tab to the notebook."""
        tab_frame = ttk.Frame(self.notebook, padding=PADDING['medium'])
        if insert_before_plus and hasattr(self, 'add_tab_index'):
            self.notebook.insert(self.add_tab_index, tab_frame, text=category_name)
            self.add_tab_index += 1
        else:
            self.notebook.add(tab_frame, text=category_name)

        left_panel = ttk.Frame(tab_frame)
        left_panel.pack(side='left', fill='y', padx=(0, PADDING['large']))

        BudgetButtonPanel(
            left_panel,
            on_add_click=lambda amt, cur: self._on_add_click(amt, category_name, cur),
            on_spend_click=lambda amt, cur, note='': self._on_spend_click(amt, category_name, cur, note),
            initial_currency=self.currency_var.get(),
            show_note=True,
        ).pack(fill='x')

        balance_frame = ttk.Frame(left_panel)
        balance_frame.pack(fill='x', pady=PADDING['large'])
        ttk.Label(balance_frame, text=f"📊 {category_name} Balance:", font=FONTS['heading']).pack(anchor='w')
        balance_label = ttk.Label(
            balance_frame, text=format_currency(0),
            font=FONTS['amount'], foreground=COLORS['text_primary']
        )
        balance_label.pack(anchor='w')

        avail_row = ttk.Frame(left_panel)
        avail_row.pack(fill='x', pady=(0, PADDING['small']))
        ttk.Label(
            avail_row, text="Available to allocate:",
            font=FONTS['body'], foreground=COLORS['text_secondary'],
        ).pack(side='left')
        available_label = ttk.Label(
            avail_row, text=format_currency(0),
            font=FONTS['body'], foreground=COLORS['text_secondary'],
        )
        available_label.pack(side='left', padx=(PADDING['small'], 0))

        tk.Button(
            left_panel, text=f"Clear {category_name}",
            font=FONTS['body'], bg=COLORS['warning'], fg='white',
            relief='flat', cursor='hand2',
            command=lambda c=category_name: self._on_clear_category_click(c),
        ).pack(fill='x', pady=PADDING['medium'])

        tk.Button(
            left_panel, text=f"Delete {category_name}",
            font=FONTS['body'], bg=COLORS['spend'], fg='white',
            relief='flat', cursor='hand2',
            command=lambda c=category_name: self._on_delete_category_click(c),
        ).pack(fill='x', pady=(0, PADDING['medium']))

        right_panel = ttk.Frame(tab_frame)
        right_panel.pack(side='right', fill='both', expand=True)
        ttk.Label(right_panel, text="Recent Transactions", font=FONTS['heading']).pack(
            anchor='w', pady=(0, PADDING['small'])
        )
        tx_list = TransactionList(right_panel)
        tx_list.pack(fill='both', expand=True)
        for t in reversed(transactions[-20:]):
            tx_list.add_item(t)

        self.category_tabs[category_name] = {
            'frame': tab_frame,
            'balance_label': balance_label,
            'available_label': available_label,
            'transaction_list': tx_list,
        }

    # ── Transfer to Savings bar ──────────────────────────────────────

    def _create_transfer_bar(self, parent):
        """Bar in the Expenses view that lets the user push money into Savings."""
        from utils.config import CURRENCIES
        bar = tk.Frame(parent, bg='#d6eaf8', relief='flat', bd=0)
        bar.pack(fill='x', pady=(0, PADDING['medium']), ipady=8)

        tk.Label(
            bar, text="↗️ Transfer to Savings:",
            font=FONTS['heading'], bg='#d6eaf8', fg=COLORS['text_primary'],
        ).pack(side='left', padx=(PADDING['medium'], PADDING['small']))

        self.transfer_entry = tk.Entry(
            bar, width=14, font=FONTS['body'], relief='solid', bd=1,
        )
        self.transfer_entry.pack(side='left', padx=PADDING['small'])
        self.transfer_entry.bind('<Return>', lambda e: self._on_transfer_click())

        tk.Label(
            bar, text="Currency:", font=FONTS['body'],
            bg='#d6eaf8', fg=COLORS['text_secondary'],
        ).pack(side='left', padx=(PADDING['medium'], PADDING['small']))

        self.transfer_currency_var = tk.StringVar(value='SEK')
        ttk.Combobox(
            bar,
            textvariable=self.transfer_currency_var,
            values=list(CURRENCIES.keys()),
            state='readonly',
            width=5,
            font=FONTS['body'],
        ).pack(side='left', padx=PADDING['small'])

        tk.Button(
            bar, text="Transfer →",
            font=FONTS['button'],
            bg='#2980b9', fg='white',
            activebackground='#1f618d', activeforeground='white',
            relief='flat', cursor='hand2',
            command=self._on_transfer_click,
        ).pack(side='left', padx=(PADDING['medium'], PADDING['small']))

        # Right side: running total of what has been transferred so far
        self._transferred_label = tk.Label(
            bar, text=format_currency(0),
            font=FONTS['heading'], bg='#d6eaf8', fg='#2980b9',
        )
        self._transferred_label.pack(side='right', padx=(0, PADDING['medium']))
        tk.Label(
            bar, text="Total sent to Savings:",
            font=FONTS['body'], bg='#d6eaf8', fg=COLORS['text_secondary'],
        ).pack(side='right')

    def _on_transfer_click(self):
        from utils.helpers import parse_amount
        amount = parse_amount(self.transfer_entry.get())
        if amount is None:
            self.show_message("Error", "Please enter a valid amount.", "error")
            return
        currency = self.transfer_currency_var.get()
        if self.on_transfer_to_savings:
            self.on_transfer_to_savings(amount, currency)
        self.transfer_entry.delete(0, tk.END)

    # ── Salary input bar ─────────────────────────────────────────────

    def _create_salary_input(self, parent):
        from utils.config import CURRENCIES
        self._edit_income_transaction = None
        bar = tk.Frame(parent, bg=COLORS['card_bg'], relief='flat', bd=0)
        bar.pack(fill='x', pady=(0, PADDING['medium']), ipady=8)

        tk.Label(
            bar, text="💰 Salary / Income:",
            font=FONTS['heading'], bg=COLORS['card_bg'],
            fg=COLORS['text_primary'],
        ).pack(side='left', padx=(PADDING['medium'], PADDING['small']))

        self.salary_entry = tk.Entry(
            bar, width=14, font=FONTS['body'],
            relief='solid', bd=1,
        )
        self.salary_entry.pack(side='left', padx=PADDING['small'])
        self.salary_entry.bind('<Return>', lambda e: self._on_salary_add())

        tk.Label(bar, text="Currency:", font=FONTS['body'],
                 bg=COLORS['card_bg'], fg=COLORS['text_secondary']).pack(
            side='left', padx=(PADDING['medium'], PADDING['small'])
        )

        self.salary_currency_var = tk.StringVar(value='SEK')
        ttk.Combobox(
            bar,
            textvariable=self.salary_currency_var,
            values=list(CURRENCIES.keys()),
            state='readonly',
            width=5,
            font=FONTS['body'],
        ).pack(side='left', padx=PADDING['small'])

        tk.Button(
            bar, text="Add Income",
            font=FONTS['button'],
            bg=COLORS['add'], fg='white',
            activebackground=COLORS['add_hover'], activeforeground='white',
            relief='flat', cursor='hand2',
            command=self._on_salary_add,
        ).pack(side='left', padx=(PADDING['medium'], PADDING['small']))

        self._income_edit_btn = tk.Button(
            bar, text="Edit",
            font=FONTS['button'],
            bg=COLORS['text_secondary'], fg='white',
            activebackground=COLORS['text_primary'], activeforeground='white',
            relief='flat', cursor='hand2',
            command=self._on_edit_income_last,
        )
        self._income_edit_btn.pack(side='left', padx=(0, PADDING['small']))

        self._income_delete_btn = tk.Button(
            bar, text="Delete",
            font=FONTS['button'],
            bg=COLORS['spend'], fg='white',
            activebackground=COLORS['spend_hover'], activeforeground='white',
            relief='flat', cursor='hand2',
            command=self._on_delete_income_last,
        )
        self._income_delete_btn.pack(side='left')

    def _on_salary_add(self):
        from utils.helpers import parse_amount
        from utils.config import SALARY_CATEGORY
        amount = parse_amount(self.salary_entry.get())
        if amount is None:
            self.show_message("Error", "Please enter a valid amount.", "error")
            return
        currency = self.salary_currency_var.get()
        if self.on_add_expense:
            self.on_add_expense(amount, SALARY_CATEGORY, currency)
        self.salary_entry.delete(0, tk.END)

    def update_income_list(self, transactions: list):
        """Track the most recent income transaction for Edit/Delete actions."""
        self._edit_income_transaction = transactions[-1] if transactions else None

    def _on_edit_income_click(self, transaction):
        """Open a modal dialog to correct an income transaction's amount."""
        from utils.config import CURRENCIES
        if transaction.original_currency and transaction.original_amount is not None:
            edit_currency = transaction.original_currency
            edit_amount   = transaction.original_amount
        else:
            edit_currency = self.currency_var.get()
            edit_amount   = transaction.amount

        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Income")
        dialog.resizable(False, False)
        dialog.grab_set()

        w, h = 340, 155
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width()  - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        dialog.geometry(f"{w}x{h}+{x}+{y}")

        frame = ttk.Frame(dialog, padding=PADDING['large'])
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text="Edit Income Amount", font=FONTS['heading']).pack(anchor='w', pady=(0, PADDING['medium']))

        input_row = ttk.Frame(frame)
        input_row.pack(fill='x', pady=PADDING['small'])
        ttk.Label(input_row, text="Amount:", font=FONTS['body']).pack(side='left')
        amount_entry = ttk.Entry(input_row, width=14, font=FONTS['body'])
        amount_entry.insert(0, str(edit_amount))
        amount_entry.pack(side='left', padx=PADDING['small'])
        amount_entry.select_range(0, tk.END)
        amount_entry.focus_set()
        currency_var = tk.StringVar(value=edit_currency)
        ttk.Combobox(
            input_row, textvariable=currency_var,
            values=list(CURRENCIES.keys()), state='readonly', width=5, font=FONTS['body'],
        ).pack(side='left', padx=PADDING['small'])

        def _save():
            from utils.helpers import parse_amount
            new_amt = parse_amount(amount_entry.get())
            if new_amt is None:
                self.show_message("Error", "Please enter a valid amount.", "error")
                return
            if self.on_edit_income:
                self.on_edit_income(transaction, new_amt, currency_var.get())
            dialog.destroy()

        amount_entry.bind('<Return>', lambda e: _save())
        btn_row = ttk.Frame(frame)
        btn_row.pack(fill='x', pady=(PADDING['medium'], 0))
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

    def _on_edit_income_last(self):
        if self._edit_income_transaction:
            self._on_edit_income_click(self._edit_income_transaction)

    def _on_delete_income_last(self):
        if self._edit_income_transaction:
            if messagebox.askyesno("Confirm Delete", "Delete the last income entry?\nThis cannot be undone."):
                if self.on_delete_income:
                    self.on_delete_income(self._edit_income_transaction)

    # ── Expenses content ─────────────────────────────────────────────

    def _create_expenses_content(self, parent):
        # Summary cards row
        cards_frame = ttk.Frame(parent)
        cards_frame.pack(fill='x', pady=(0, PADDING['medium']))

        self.exp_total_card = SummaryCard(cards_frame, title="Remaining", value=0, color=COLORS['text_primary'])
        self.exp_total_card.pack(side='left', padx=(0, PADDING['large']))

        self.exp_added_card = SummaryCard(cards_frame, title="Total Income", value=0, color=COLORS['add'])
        self.exp_added_card.pack(side='left', padx=PADDING['large'])

        self.exp_spent_card = SummaryCard(cards_frame, title="Total Spent", value=0, color=COLORS['spend'])
        self.exp_spent_card.pack(side='left', padx=PADDING['large'])

        tk.Button(
            cards_frame, text="Clear All Data",
            font=FONTS['body'], bg=COLORS['warning'], fg='white',
            relief='flat', cursor='hand2', command=self._on_clear_expense_click,
        ).pack(side='right')

        tk.Button(
            cards_frame, text="📊 Export to Excel",
            font=FONTS['body'], bg=COLORS['add'], fg='white',
            relief='flat', cursor='hand2', command=self._on_export_expense_click,
        ).pack(side='right', padx=(0, PADDING['small']))

        # Foreign currency row
        self.exp_foreign_currency_frame = ttk.Frame(parent)
        self.exp_foreign_currency_frame.pack(fill='x', pady=(0, PADDING['small']))

        # Salary / income quick-add bar with inline Edit / Delete
        self._create_salary_input(parent)

        # Transfer-to-savings bar
        self._create_transfer_bar(parent)

        # Notebook
        self.expenses_notebook = ttk.Notebook(parent)
        self.expenses_notebook.pack(fill='both', expand=True)
        self.expenses_category_tabs: Dict[str, Dict] = {}

    def add_new_expense_category_tab(self):
        """Add the '+' tab for creating new expense categories."""
        add_tab_frame = ttk.Frame(self.expenses_notebook, padding=PADDING['large'])
        self.expenses_notebook.add(add_tab_frame, text="  ➕  ")
        self._build_new_category_ui(
            add_tab_frame,
            label="Create New Expense Category",
            entry_attr='new_expense_category_entry',
            on_create=self._on_create_expense_category,
        )
        self.exp_add_tab_index = self.expenses_notebook.index('end') - 1

    def add_expense_category_tab(self, category_name: str, transactions: list, insert_before_plus: bool = False):
        """Add a new expense category tab to the expenses notebook."""
        tab_frame = ttk.Frame(self.expenses_notebook, padding=PADDING['medium'])
        if insert_before_plus and hasattr(self, 'exp_add_tab_index'):
            self.expenses_notebook.insert(self.exp_add_tab_index, tab_frame, text=category_name)
            self.exp_add_tab_index += 1
        else:
            self.expenses_notebook.add(tab_frame, text=category_name)

        left_panel = ttk.Frame(tab_frame)
        left_panel.pack(side='left', fill='y', padx=(0, PADDING['large']))

        BudgetButtonPanel(
            left_panel,
            on_add_click=None,
            on_spend_click=lambda amt, cur, note='': self._on_spend_expense_click(amt, category_name, cur, note),
            initial_currency=self.currency_var.get(),
            show_add=False,
            show_note=True,
        ).pack(fill='x')

        balance_frame = ttk.Frame(left_panel)
        balance_frame.pack(fill='x', pady=PADDING['large'])
        ttk.Label(balance_frame, text=f"💸 {category_name} Spent:", font=FONTS['heading']).pack(anchor='w')
        balance_label = ttk.Label(
            balance_frame, text=format_currency(0),
            font=FONTS['amount'], foreground=COLORS['text_primary']
        )
        balance_label.pack(anchor='w')

        tk.Button(
            left_panel, text=f"Clear {category_name}",
            font=FONTS['body'], bg=COLORS['warning'], fg='white',
            relief='flat', cursor='hand2',
            command=lambda c=category_name: self._on_clear_expense_category_click(c),
        ).pack(fill='x', pady=PADDING['medium'])

        tk.Button(
            left_panel, text=f"Delete {category_name}",
            font=FONTS['body'], bg=COLORS['spend'], fg='white',
            relief='flat', cursor='hand2',
            command=lambda c=category_name: self._on_delete_expense_category_click(c),
        ).pack(fill='x', pady=(0, PADDING['medium']))

        right_panel = ttk.Frame(tab_frame)
        right_panel.pack(side='right', fill='both', expand=True)
        ttk.Label(right_panel, text="Recent Transactions", font=FONTS['heading']).pack(
            anchor='w', pady=(0, PADDING['small'])
        )
        tx_list = TransactionList(right_panel)
        tx_list.pack(fill='both', expand=True)
        for t in reversed(transactions[-20:]):
            tx_list.add_item(t)

        self.expenses_category_tabs[category_name] = {
            'frame': tab_frame,
            'balance_label': balance_label,
            'transaction_list': tx_list,
        }

    # ── Shared helper ────────────────────────────────────────────────

    def _build_new_category_ui(self, parent, label: str, entry_attr: str, on_create):
        center_frame = ttk.Frame(parent)
        center_frame.place(relx=0.5, rely=0.4, anchor='center')

        ttk.Label(center_frame, text=label, font=FONTS['title']).pack(pady=PADDING['medium'])

        input_frame = ttk.Frame(center_frame)
        input_frame.pack(pady=PADDING['medium'])

        ttk.Label(input_frame, text="Category Name:", font=FONTS['body']).pack(
            side='left', padx=PADDING['small']
        )
        entry = ttk.Entry(input_frame, width=20, font=FONTS['body'])
        entry.pack(side='left', padx=PADDING['small'])
        entry.bind('<Return>', lambda e: on_create())
        setattr(self, entry_attr, entry)

        tk.Button(
            input_frame, text="Create",
            font=FONTS['button'], bg=COLORS['add'], fg='white',
            activebackground=COLORS['add_hover'], activeforeground='white',
            relief='flat', cursor='hand2', command=on_create,
        ).pack(side='left', padx=PADDING['small'])

    # ── Savings event handlers ───────────────────────────────────────

    def _on_add_click(self, amount: float, category: str, currency: str):
        if self.on_add_budget:
            self.on_add_budget(amount, category, currency)

    def _on_spend_click(self, amount: float, category: str, currency: str, note: str = ''):
        if self.on_spend_budget:
            self.on_spend_budget(amount, category, currency, note)

    def _on_clear_click(self):
        if messagebox.askyesno("Confirm Clear", "Clear all savings data?\nThis cannot be undone."):
            if self.on_clear_data:
                self.on_clear_data()

    def _on_clear_category_click(self, category: str):
        if messagebox.askyesno("Confirm Clear", f"Clear all {category} data?\nThis cannot be undone."):
            if self.on_clear_category:
                self.on_clear_category(category)

    def _on_delete_category_click(self, category: str):
        if messagebox.askyesno("Confirm Delete", f"Delete '{category}' and all its transactions?\nThis cannot be undone."):
            if self.on_delete_category:
                self.on_delete_category(category)

    def _on_export_click(self):
        if self.on_export_data:
            self.on_export_data()

    def _on_add_direct_income_click(self):
        from utils.helpers import parse_amount
        amount = parse_amount(self._direct_income_entry.get())
        if amount is None:
            self.show_message("Error", "Please enter a valid amount.", "error")
            return
        currency = self._direct_income_currency_var.get()
        if self.on_add_direct_income:
            self.on_add_direct_income(amount, currency)
        self._direct_income_entry.delete(0, tk.END)

    def _on_create_category(self):
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

    # ── Expenses event handlers ──────────────────────────────────────

    def _on_add_expense_click(self, amount: float, category: str, currency: str):
        if self.on_add_expense:
            self.on_add_expense(amount, category, currency)

    def _on_spend_expense_click(self, amount: float, category: str, currency: str, note: str = ''):
        if self.on_spend_expense:
            self.on_spend_expense(amount, category, currency, note)

    def _on_clear_expense_click(self):
        if messagebox.askyesno("Confirm Clear", "Clear all expenses data?\nThis cannot be undone."):
            if self.on_clear_expense_data:
                self.on_clear_expense_data()

    def _on_clear_expense_category_click(self, category: str):
        if messagebox.askyesno("Confirm Clear", f"Clear all {category} expenses?\nThis cannot be undone."):
            if self.on_clear_expense_category:
                self.on_clear_expense_category(category)

    def _on_delete_expense_category_click(self, category: str):
        if messagebox.askyesno("Confirm Delete", f"Delete expense category '{category}' and all its transactions?\nThis cannot be undone."):
            if self.on_delete_expense_category:
                self.on_delete_expense_category(category)

    def _on_export_expense_click(self):
        if self.on_export_expense_data:
            self.on_export_expense_data()

    def _on_create_expense_category(self):
        name = self.new_expense_category_entry.get().strip()
        if not name:
            self.show_message("Error", "Please enter a category name.", "error")
            return
        if name in self.expenses_category_tabs:
            self.show_message("Error", f"Category '{name}' already exists.", "error")
            return
        if self.on_create_expense_category:
            success = self.on_create_expense_category(name)
            if success:
                self.new_expense_category_entry.delete(0, tk.END)

    # ── Shared event handlers ────────────────────────────────────────

    def _on_currency_change(self):
        if self.on_currency_change:
            self.on_currency_change(self.currency_var.get())

    def _on_edit_rates_click(self):
        if self.on_edit_rates:
            self.on_edit_rates()

    # ── Savings public API ───────────────────────────────────────────

    def set_currency(self, code: str):
        self.currency_var.set(code)

    def refresh_summary_currency(self):
        self.total_card.refresh_display()
        self.added_card.refresh_display()
        self.spent_card.refresh_display()

    def update_summary(self, total: float, added: float, spent: float):
        self.total_card.update_value(total)
        self.added_card.update_value(added)
        self.spent_card.update_value(spent)

    def update_foreign_currency_display(self, totals: dict):
        from utils.helpers import format_currency_for_code
        for w in self.foreign_currency_frame.winfo_children():
            w.destroy()
        if not totals:
            return
        ttk.Label(
            self.foreign_currency_frame, text="Foreign Currency Activity:",
            font=FONTS['body'], foreground=COLORS['text_secondary'],
        ).pack(side='left', padx=(0, PADDING['medium']))
        for code, data in totals.items():
            net   = data['added'] - data['spent']
            sign  = '+' if net >= 0 else '-'
            color = COLORS['add'] if net >= 0 else COLORS['spend']
            ttk.Label(
                self.foreign_currency_frame,
                text=f"{code}: {sign}{format_currency_for_code(abs(net), code)}",
                font=FONTS['heading'], foreground=color,
            ).pack(side='left', padx=(0, PADDING['large']))

    def update_category(self, category_name: str, balance: float, transaction=None):
        if category_name not in self.category_tabs:
            return
        tab = self.category_tabs[category_name]
        tab['balance_label'].config(text=format_currency(balance))
        if transaction:
            tab['transaction_list'].add_item(transaction)

    def refresh_all_transactions(self, category_name: str, transactions: list):
        if category_name not in self.category_tabs:
            return
        tab = self.category_tabs[category_name]
        tab['transaction_list'].clear()
        for t in reversed(transactions[-20:]):
            tab['transaction_list'].add_item(t)

    def select_tab(self, category_name: str):
        if category_name in self.category_tabs:
            self.notebook.select(self.category_tabs[category_name]['frame'])

    def remove_category_tab(self, category_name: str):
        if category_name not in self.category_tabs:
            return
        self.notebook.forget(self.category_tabs[category_name]['frame'])
        del self.category_tabs[category_name]
        if hasattr(self, 'add_tab_index'):
            self.add_tab_index -= 1

    def update_distributable_balance(self, amount: float):
        """Update the 'Available to Allocate' banner and all per-tab labels."""
        if amount > 0:
            color = COLORS['add']
        elif amount < 0:
            color = COLORS['spend']
        else:
            color = COLORS['text_secondary']
        label_text = format_currency(amount)
        self._distributable_label.config(text=label_text, fg=color)
        for tab_data in self.category_tabs.values():
            if 'available_label' in tab_data:
                tab_data['available_label'].config(text=label_text, foreground=color)

    def update_transferred_display(self, amount: float):
        """Update the 'Total sent to Savings' label inside the transfer bar."""
        self._transferred_label.config(text=format_currency(amount))

    # ── Expenses public API ──────────────────────────────────────────

    def refresh_expenses_summary_currency(self):
        self.exp_total_card.refresh_display()
        self.exp_added_card.refresh_display()
        self.exp_spent_card.refresh_display()

    def update_expenses_summary(self, total: float, added: float, spent: float):
        self.exp_total_card.update_value(total)
        self.exp_added_card.update_value(added)
        self.exp_spent_card.update_value(spent)

    def update_expenses_foreign_currency_display(self, totals: dict):
        from utils.helpers import format_currency_for_code
        for w in self.exp_foreign_currency_frame.winfo_children():
            w.destroy()
        if not totals:
            return
        ttk.Label(
            self.exp_foreign_currency_frame, text="Foreign Currency Activity:",
            font=FONTS['body'], foreground=COLORS['text_secondary'],
        ).pack(side='left', padx=(0, PADDING['medium']))
        for code, data in totals.items():
            net   = data['added'] - data['spent']
            sign  = '+' if net >= 0 else '-'
            color = COLORS['add'] if net >= 0 else COLORS['spend']
            ttk.Label(
                self.exp_foreign_currency_frame,
                text=f"{code}: {sign}{format_currency_for_code(abs(net), code)}",
                font=FONTS['heading'], foreground=color,
            ).pack(side='left', padx=(0, PADDING['large']))

    def update_expense_category(self, category_name: str, balance: float, transaction=None):
        if category_name not in self.expenses_category_tabs:
            return
        tab = self.expenses_category_tabs[category_name]
        tab['balance_label'].config(text=format_currency(balance))
        if transaction:
            tab['transaction_list'].add_item(transaction)

    def refresh_expense_transactions(self, category_name: str, transactions: list):
        if category_name not in self.expenses_category_tabs:
            return
        tab = self.expenses_category_tabs[category_name]
        tab['transaction_list'].clear()
        for t in reversed(transactions[-20:]):
            tab['transaction_list'].add_item(t)

    def select_expense_tab(self, category_name: str):
        if category_name in self.expenses_category_tabs:
            self.expenses_notebook.select(self.expenses_category_tabs[category_name]['frame'])

    def remove_expense_category_tab(self, category_name: str):
        if category_name not in self.expenses_category_tabs:
            return
        self.expenses_notebook.forget(self.expenses_category_tabs[category_name]['frame'])
        del self.expenses_category_tabs[category_name]
        if hasattr(self, 'exp_add_tab_index'):
            self.exp_add_tab_index -= 1

    # ── Dialogs ──────────────────────────────────────────────────────

    def show_rates_dialog(self, current_rates: dict, default_rates: dict, on_save):
        from utils.config import CURRENCIES

        dialog = tk.Toplevel(self.root)
        dialog.title("Exchange Rates")
        dialog.resizable(False, False)
        dialog.grab_set()

        dialog.update_idletasks()
        w = 380
        h = 60 + len([c for c in default_rates if c != 'EUR']) * 50 + 70
        x = self.root.winfo_x() + (self.root.winfo_width()  - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        dialog.geometry(f"{w}x{h}+{x}+{y}")

        frame = ttk.Frame(dialog, padding=PADDING['large'])
        frame.pack(fill='both', expand=True)

        ttk.Label(frame, text="Exchange Rates  (1 EUR = X)", font=FONTS['heading']).pack(
            anchor='w', pady=(0, PADDING['medium'])
        )

        entries = {}
        for code in default_rates:
            if code == 'EUR':
                continue
            sym         = CURRENCIES[code]['symbol']
            default_val = default_rates[code]
            row = ttk.Frame(frame)
            row.pack(fill='x', pady=(0, PADDING['small']))
            ttk.Label(row, text="1 EUR =", font=FONTS['body']).pack(side='left')
            entry = ttk.Entry(row, width=10, font=FONTS['body'])
            entry.insert(0, str(current_rates.get(code, default_val)))
            entry.pack(side='left', padx=PADDING['small'])
            ttk.Label(
                row, text=f"{sym}    (default: {default_val})",
                font=FONTS['body'], foreground=COLORS['text_secondary'],
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

    def show_message(self, title: str, message: str, msg_type: str = 'info'):
        if msg_type == 'error':
            messagebox.showerror(title, message)
        elif msg_type == 'warning':
            messagebox.showwarning(title, message)
        else:
            messagebox.showinfo(title, message)
