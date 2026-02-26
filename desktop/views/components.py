
import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional

from utils.config import COLORS, FONTS, PADDING, PRESET_AMOUNTS, CURRENCIES
from utils.helpers import format_currency, format_currency_for_code


class BudgetButtonPanel(ttk.Frame):
    """Panel with preset amount buttons for both Add and Spend actions."""

    def __init__(
        self,
        parent,
        on_add_click: Optional[Callable[[float, str], None]],
        on_spend_click: Callable[[float, str], None],
        initial_currency: str = 'EUR',
        show_add: bool = True,
        show_note: bool = False,
        preset_notes: Optional[List] = None,
        on_add_preset_note: Optional[Callable] = None,
        on_remove_preset_note: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.on_add_click = on_add_click
        self.on_spend_click = on_spend_click
        self._initial_currency = initial_currency
        self.show_add = show_add
        self.show_note = show_note
        self.preset_notes: list = list(preset_notes or [])
        self.on_add_preset_note = on_add_preset_note
        self.on_remove_preset_note = on_remove_preset_note
        self._note_presets_frame = None
        self.add_preset_buttons: list = []
        self.spend_preset_buttons: list = []
        self._create_widgets()

    def _create_widgets(self):
        """Create all widgets for the panel."""

        # === INPUT CURRENCY SELECTOR ===
        currency_row = ttk.Frame(self)
        currency_row.pack(fill='x', pady=(0, PADDING['small']))

        ttk.Label(currency_row, text="Input Currency:", font=FONTS['body']).pack(side='left')

        self.input_currency_var = tk.StringVar(value=self._initial_currency)
        currency_combo = ttk.Combobox(
            currency_row,
            textvariable=self.input_currency_var,
            values=list(CURRENCIES.keys()),
            state='readonly',
            width=5,
            font=FONTS['body'],
        )
        currency_combo.pack(side='left', padx=PADDING['small'])
        currency_combo.bind('<<ComboboxSelected>>', self._on_input_currency_changed)

        if self.show_add:
            # === ADD SECTION ===
            ttk.Label(
                self, text="➕ Add to Budget",
                font=FONTS['heading'], foreground=COLORS['add']
            ).pack(anchor='w', pady=(0, PADDING['small']))

            add_buttons_frame = ttk.Frame(self)
            add_buttons_frame.pack(fill='x', pady=PADDING['small'])

            for i, amount in enumerate(PRESET_AMOUNTS):
                btn = tk.Button(
                    add_buttons_frame,
                    text=format_currency_for_code(amount, self._initial_currency),
                    font=FONTS['button'],
                    bg=COLORS['add'], fg='white',
                    activebackground=COLORS['add_hover'], activeforeground='white',
                    relief='flat', cursor='hand2',
                    command=lambda a=amount: self.on_add_click(a, self.input_currency_var.get())
                )
                btn.pack(side='left', padx=(0 if i == 0 else PADDING['small'], 0), expand=True, fill='x')
                self.add_preset_buttons.append(btn)

            add_custom_frame = ttk.Frame(self)
            add_custom_frame.pack(fill='x', pady=PADDING['small'])
            ttk.Label(add_custom_frame, text="Custom:", font=FONTS['body']).pack(side='left')
            self.add_entry = ttk.Entry(add_custom_frame, width=12, font=FONTS['body'])
            self.add_entry.pack(side='left', padx=PADDING['small'])
            self.add_entry.bind('<Return>', lambda e: self._on_custom_add())
            tk.Button(
                add_custom_frame, text="Add",
                font=FONTS['button'], bg=COLORS['add'], fg='white',
                activebackground=COLORS['add_hover'], activeforeground='white',
                relief='flat', cursor='hand2', command=self._on_custom_add
            ).pack(side='left', padx=PADDING['small'])

            # Separator between add and spend sections
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
                text=format_currency_for_code(amount, self._initial_currency),
                font=FONTS['button'],
                bg=COLORS['spend'],
                fg='white',
                activebackground=COLORS['spend_hover'],
                activeforeground='white',
                relief='flat',
                cursor='hand2',
                command=lambda a=amount: self.on_spend_click(a, self.input_currency_var.get())
            )
            btn.pack(side='left', padx=(0 if i == 0 else PADDING['small'], 0), expand=True, fill='x')
            self.spend_preset_buttons.append(btn)

        # Spend custom amount
        spend_custom_frame = ttk.Frame(self)
        spend_custom_frame.pack(fill='x', pady=PADDING['small'])

        ttk.Label(spend_custom_frame, text="Custom:", font=FONTS['body']).pack(side='left')

        self.spend_entry = ttk.Entry(spend_custom_frame, width=12, font=FONTS['body'])
        self.spend_entry.pack(side='left', padx=PADDING['small'])
        self.spend_entry.bind('<Return>', lambda e: self._on_custom_spend())

        if self.show_note:
            ttk.Label(spend_custom_frame, text="Note:", font=FONTS['body']).pack(side='left', padx=(PADDING['small'], 0))
            self.spend_note_entry = ttk.Combobox(spend_custom_frame, width=18, font=FONTS['body'])
            self.spend_note_entry['values'] = self.preset_notes
            self.spend_note_entry.pack(side='left', padx=PADDING['small'])
            self.spend_note_entry.bind('<Return>', lambda e: self._on_custom_spend())
            self.spend_note_entry.bind('<KeyRelease>', self._on_note_key_release)
            self.spend_note_entry.bind('<Button-3>', self._on_note_combobox_right_click)

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

    def _on_input_currency_changed(self, *args):
        """Update preset button labels when the input currency selector changes."""
        currency = self.input_currency_var.get()
        for btn, amount in zip(self.add_preset_buttons, PRESET_AMOUNTS):
            btn.config(text=format_currency_for_code(amount, currency))
        for btn, amount in zip(self.spend_preset_buttons, PRESET_AMOUNTS):
            btn.config(text=format_currency_for_code(amount, currency))

    def _on_custom_add(self):
        """Handle custom add amount."""
        from utils.helpers import parse_amount
        amount = parse_amount(self.add_entry.get())
        if amount is not None:
            self.on_add_click(amount, self.input_currency_var.get())
            self.add_entry.delete(0, tk.END)

    def _on_custom_spend(self):
        """Handle custom spend amount."""
        from utils.helpers import parse_amount
        amount = parse_amount(self.spend_entry.get())
        if amount is not None:
            note = ''
            if self.show_note:
                note = self.spend_note_entry.get().strip()
                self.spend_note_entry.set('')
                if note and note not in self.preset_notes and self.on_add_preset_note:
                    self.on_add_preset_note(note)
            self.on_spend_click(amount, self.input_currency_var.get(), note)
            self.spend_entry.delete(0, tk.END)

    # ── Note preset management ───────────────────────────────────────

    def _rebuild_note_presets(self):
        pass

    def _fill_note(self, note: str):
        """Fill the note entry with the clicked preset text."""
        if hasattr(self, 'spend_note_entry'):
            self.spend_note_entry.set(note)

    def _on_note_combobox_right_click(self, event):
        """Show context menu listing all presets with remove options."""
        if not self.preset_notes or not self.on_remove_preset_note:
            return
        menu = tk.Menu(self, tearoff=0)
        for note in self.preset_notes:
            menu.add_command(
                label=f'Remove "{note}"',
                command=lambda n=note: self.on_remove_preset_note(n),
            )
        menu.tk_popup(event.x_root, event.y_root)

    def update_preset_notes(self, notes: List):
        """Update the preset notes list and rebuild the buttons."""
        self.preset_notes = list(notes)
        self._rebuild_note_presets()
        if hasattr(self, 'spend_note_entry'):
            self.spend_note_entry['values'] = self.preset_notes

    def _on_note_key_release(self, event):
        """Filter combobox dropdown as the user types."""
        if event.keysym in ('Return', 'Escape', 'Tab'):
            return
        typed = self.spend_note_entry.get().strip().lower()
        filtered = [n for n in self.preset_notes if typed in n.lower()] if typed else list(self.preset_notes)
        self.spend_note_entry['values'] = filtered


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

    def refresh_display(self):
        """Re-render the value label using the current currency symbol."""
        self.value_label.config(text=format_currency(self._value))


class TransactionList(ttk.Frame):
    """Scrollable list of transactions."""

    def __init__(self, parent, on_edit=None, on_delete=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_edit = on_edit
        self.on_delete = on_delete
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

        color = COLORS['add'] if transaction.action == 'add' else COLORS['spend']
        sign = '+' if transaction.action == 'add' else '-'

        # Show original currency + converted amount when input currency differed
        has_foreign = (
            getattr(transaction, 'original_currency', None) is not None
            and getattr(transaction, 'original_amount', None) is not None
        )
        if has_foreign:
            orig_str = format_currency_for_code(transaction.original_amount, transaction.original_currency)
            main_str = format_currency(transaction.amount)
            amount_text = f"{sign}{orig_str} ({main_str})"
        else:
            amount_text = f"{sign}{format_currency(transaction.amount)}"

        amount_label = ttk.Label(
            item_frame,
            text=amount_text,
            font=FONTS['body'],
            foreground=color
        )
        amount_label.pack(side='left')

        # Note (if present)
        note = getattr(transaction, 'note', None)
        if note:
            ttk.Label(
                item_frame,
                text=f"— {note}",
                font=FONTS['body'],
                foreground=COLORS['text_secondary'],
            ).pack(side='left', padx=(PADDING['small'], 0))

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

        if self.on_edit or self.on_delete:
            for widget in item_frame.winfo_children():
                widget.bind('<Button-3>', lambda e, t=transaction: self._show_context_menu(e, t))
            item_frame.bind('<Button-3>', lambda e, t=transaction: self._show_context_menu(e, t))

    def _show_context_menu(self, event, transaction):
        menu = tk.Menu(self, tearoff=0)
        if self.on_edit:
            menu.add_command(label='Edit', command=lambda: self.on_edit(transaction))
        if self.on_delete:
            menu.add_command(label='Delete', command=lambda: self.on_delete(transaction))
        menu.tk_popup(event.x_root, event.y_root)