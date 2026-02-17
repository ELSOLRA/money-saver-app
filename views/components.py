
import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional

from utils.config import COLORS, FONTS, PADDING, PRESET_AMOUNTS
from utils.helpers import format_currency


class BudgetButtonPanel(ttk.Frame):
    """Panel with preset amount buttons for both Add and Spend actions."""

    def __init__(
        self,
        parent,
        on_add_click: Callable[[float], None],
        on_spend_click: Callable[[float], None],
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.on_add_click = on_add_click
        self.on_spend_click = on_spend_click
        self._create_widgets()

    def _create_widgets(self):
        """Create all widgets for the panel."""
        
        # === ADD SECTION ===
        add_label = ttk.Label(
            self,
            text="➕ Add to Budget",
            font=FONTS['heading'],
            foreground=COLORS['add']
        )
        add_label.pack(anchor='w', pady=(0, PADDING['small']))

        # Add preset buttons
        add_buttons_frame = ttk.Frame(self)
        add_buttons_frame.pack(fill='x', pady=PADDING['small'])

        for i, amount in enumerate(PRESET_AMOUNTS):
            btn = tk.Button(
                add_buttons_frame,
                text=format_currency(amount),
                font=FONTS['button'],
                bg=COLORS['add'],
                fg='white',
                activebackground=COLORS['add_hover'],
                activeforeground='white',
                relief='flat',
                cursor='hand2',
                command=lambda a=amount: self.on_add_click(a)
            )
            btn.pack(side='left', padx=(0 if i == 0 else PADDING['small'], 0), expand=True, fill='x')

        # Add custom amount
        add_custom_frame = ttk.Frame(self)
        add_custom_frame.pack(fill='x', pady=PADDING['small'])

        ttk.Label(add_custom_frame, text="Custom:", font=FONTS['body']).pack(side='left')
        
        self.add_entry = ttk.Entry(add_custom_frame, width=12, font=FONTS['body'])
        self.add_entry.pack(side='left', padx=PADDING['small'])
        self.add_entry.bind('<Return>', lambda e: self._on_custom_add())

        add_btn = tk.Button(
            add_custom_frame,
            text="Add",
            font=FONTS['button'],
            bg=COLORS['add'],
            fg='white',
            activebackground=COLORS['add_hover'],
            activeforeground='white',
            relief='flat',
            cursor='hand2',
            command=self._on_custom_add
        )
        add_btn.pack(side='left', padx=PADDING['small'])

        # Separator
        ttk.Separator(self, orient='horizontal').pack(fill='x', pady=PADDING['medium'])

        # === SPEND SECTION ===
        spend_label = ttk.Label(
            self,
            text="➖ Spend from Budget",
            font=FONTS['heading'],
            foreground=COLORS['spend']
        )
        spend_label.pack(anchor='w', pady=(0, PADDING['small']))

        # Spend preset buttons
        spend_buttons_frame = ttk.Frame(self)
        spend_buttons_frame.pack(fill='x', pady=PADDING['small'])

        for i, amount in enumerate(PRESET_AMOUNTS):
            btn = tk.Button(
                spend_buttons_frame,
                text=format_currency(amount),
                font=FONTS['button'],
                bg=COLORS['spend'],
                fg='white',
                activebackground=COLORS['spend_hover'],
                activeforeground='white',
                relief='flat',
                cursor='hand2',
                command=lambda a=amount: self.on_spend_click(a)
            )
            btn.pack(side='left', padx=(0 if i == 0 else PADDING['small'], 0), expand=True, fill='x')

        # Spend custom amount
        spend_custom_frame = ttk.Frame(self)
        spend_custom_frame.pack(fill='x', pady=PADDING['small'])

        ttk.Label(spend_custom_frame, text="Custom:", font=FONTS['body']).pack(side='left')
        
        self.spend_entry = ttk.Entry(spend_custom_frame, width=12, font=FONTS['body'])
        self.spend_entry.pack(side='left', padx=PADDING['small'])
        self.spend_entry.bind('<Return>', lambda e: self._on_custom_spend())

        spend_btn = tk.Button(
            spend_custom_frame,
            text="Spend",
            font=FONTS['button'],
            bg=COLORS['spend'],
            fg='white',
            activebackground=COLORS['spend_hover'],
            activeforeground='white',
            relief='flat',
            cursor='hand2',
            command=self._on_custom_spend
        )
        spend_btn.pack(side='left', padx=PADDING['small'])

    def _on_custom_add(self):
        """Handle custom add amount."""
        from utils.helpers import parse_amount
        amount = parse_amount(self.add_entry.get())
        if amount is not None:
            self.on_add_click(amount)
            self.add_entry.delete(0, tk.END)

    def _on_custom_spend(self):
        """Handle custom spend amount."""
        from utils.helpers import parse_amount
        amount = parse_amount(self.spend_entry.get())
        if amount is not None:
            self.on_spend_click(amount)
            self.spend_entry.delete(0, tk.END)


class SummaryCard(ttk.Frame):
    """Card displaying a summary value with label."""

    def __init__(
        self,
        parent,
        title: str,
        value: float,
        color: str = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.title = title
        self.color = color or COLORS['text_primary']
        self._value = value
        self._create_widgets()

    def _create_widgets(self):
        """Create card widgets."""
        ttk.Label(
            self,
            text=self.title,
            font=FONTS['body'],
            foreground=COLORS['text_secondary']
        ).pack(anchor='center')

        self.value_label = ttk.Label(
            self,
            text=format_currency(self._value),
            font=FONTS['amount'],
            foreground=self.color
        )
        self.value_label.pack(anchor='center')

    def update_value(self, new_value: float):
        """Update the displayed value."""
        self._value = new_value
        self.value_label.config(text=format_currency(new_value))


class TransactionList(ttk.Frame):
    """Scrollable list of transactions."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._create_widgets()

    def _create_widgets(self):
        """Create the transaction list widgets."""
        self.canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            '<Configure>',
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)

    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

    def clear(self):
        """Clear all items from the list."""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

    def add_item(self, transaction):
        """Add a transaction item to the list."""
        item_frame = ttk.Frame(self.scrollable_frame)
        item_frame.pack(fill='x', pady=2)

        # Amount with color based on action
        color = COLORS['add'] if transaction.action == 'add' else COLORS['spend']
        sign = '+' if transaction.action == 'add' else '-'
        
        amount_label = ttk.Label(
            item_frame,
            text=f"{sign}{format_currency(transaction.amount)}",
            font=FONTS['body'],
            foreground=color
        )
        amount_label.pack(side='left')

        # Timestamp
        from datetime import datetime
        dt = datetime.fromisoformat(transaction.timestamp)
        time_str = dt.strftime('%m/%d %H:%M')
        
        time_label = ttk.Label(
            item_frame,
            text=time_str,
            font=FONTS['body'],
            foreground=COLORS['text_secondary']
        )
        time_label.pack(side='right')