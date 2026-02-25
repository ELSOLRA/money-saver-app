
import tkinter as tk

from models import DataModel
from views import MainView
from utils.config import DATA_FILE, BUDGET_CATEGORIES, CURRENCIES
from utils.helpers import set_currency_state, convert_currency, set_exchange_rates


class MainController:
    """
    Main application controller for budget tracking.
    """

    def __init__(self):
        self.root = tk.Tk()
        self.model = DataModel(DATA_FILE, BUDGET_CATEGORIES)
        self._apply_currency_state(self.model.currency)
        set_exchange_rates(self.model.exchange_rates)   # Load custom or default rates
        self.view = MainView(self.root)

        self._setup_callbacks()
        self._initialize_view()

    def _setup_callbacks(self):
        """Set up view callbacks."""
        self.view.on_add_budget = self.add_to_budget
        self.view.on_spend_budget = self.spend_from_budget
        self.view.on_clear_data = self.clear_data
        self.view.on_clear_category = self.clear_category
        self.view.on_create_category = self.create_category
        self.view.on_export_data = self.export_data
        self.view.on_delete_category = self.delete_category
        self.view.on_currency_change = self.change_currency
        self.view.on_edit_rates = self.open_rates_dialog

    def _initialize_view(self):
        """Initialize the view with existing data."""
        
        self.view.set_currency(self.model.currency)

        # Add category tabs
        for category in self.model.categories:
            transactions = self.model.get_transactions_by_category(category)
            self.view.add_category_tab(category, transactions)

        # Add the "+" tab for creating new categories
        self.view.add_new_category_tab()

        # Update summary, category balances, and foreign currency tracker
        self._update_summary()
        self._update_all_category_balances()
        self._update_foreign_currency_display()

    def _update_summary(self):
        """Update the summary display."""
        total = self.model.get_total_budget()
        added = self.model.get_total_added()
        spent = self.model.get_total_spent()
        self.view.update_summary(total, added, spent)

    def _update_all_category_balances(self):
        """Update balances for all categories."""
        for category in self.model.categories:
            balance = self.model.get_category_balance(category)
            self.view.update_category(category, balance)

    def add_to_budget(self, amount: float, category: str, input_currency: str = None):
        """Add money to a category budget, converting from input_currency if needed."""
        main_currency = self.model.currency
        if input_currency and input_currency != main_currency:
            converted = convert_currency(amount, input_currency, main_currency)
            orig_curr, orig_amt = input_currency, amount
        else:
            converted, orig_curr, orig_amt = amount, None, None

        transaction = self.model.add_transaction(
            amount=converted, action='add', category=category,
            original_currency=orig_curr, original_amount=orig_amt,
        )
        balance = self.model.get_category_balance(category)
        self.view.update_category(category, balance, transaction)
        self._update_summary()
        self._update_foreign_currency_display()

    def spend_from_budget(self, amount: float, category: str, input_currency: str = None):
        """Spend money from a category budget, converting from input_currency if needed."""
        main_currency = self.model.currency
        if input_currency and input_currency != main_currency:
            converted = convert_currency(amount, input_currency, main_currency)
            orig_curr, orig_amt = input_currency, amount
        else:
            converted, orig_curr, orig_amt = amount, None, None

        transaction = self.model.add_transaction(
            amount=converted, action='spend', category=category,
            original_currency=orig_curr, original_amount=orig_amt,
        )
        balance = self.model.get_category_balance(category)
        self.view.update_category(category, balance, transaction)
        self._update_summary()
        self._update_foreign_currency_display()

    def clear_data(self):
        """Clear all transaction data."""
        self.model.clear_all_data()

        for category in self.model.categories:
            self.view.refresh_all_transactions(category, [])
            self.view.update_category(category, 0)

        self._update_summary()
        self._update_foreign_currency_display()
        self.view.show_message("Success", "All data has been cleared.")

    def clear_category(self, category: str):
        """Clear all transactions for a specific category."""
        self.model.clear_category(category)

        self.view.refresh_all_transactions(category, [])
        self.view.update_category(category, 0)

        self._update_summary()
        self._update_foreign_currency_display()
        self.view.show_message("Success", f"{category} data has been cleared.")

    def create_category(self, category_name: str) -> bool:
        """Create a new budget category."""
        success = self.model.add_category(category_name)
        
        if success:
            # Add new tab (insert before + tab)
            self.view.add_category_tab(category_name, [], insert_before_plus=True)
            self.view.select_tab(category_name)
            self.view.show_message("Success", f"Category '{category_name}' created!")
            return True
        else:
            self.view.show_message("Error", f"Category '{category_name}' already exists.", "error")
            return False
        
    def export_data(self):
        from utils.helpers import export_to_excel
        from tkinter import filedialog
        import os

        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="budget_export.xlsx"
        )
        if path:
            export_to_excel(
                transactions=self.model.transactions,
                categories=self.model.categories,
                get_category_balance=self.model.get_category_balance,
                get_totals=None,
                output_path=path,
                main_currency=self.model.currency,
            )
            self.view.show_message("Success", f"Exported to:\n{os.path.basename(path)}")
    
    def delete_category(self, category: str):
        self.model.delete_category(category)
        self.view.remove_category_tab(category)
        self._update_summary()
        self._update_foreign_currency_display()
        self.view.show_message("Success", f"'{category}' has been deleted.")

    def _apply_currency_state(self, currency_code: str):
        """Push the currency symbol into the helpers module state."""
        cur = CURRENCIES.get(currency_code, CURRENCIES['EUR'])
        set_currency_state(cur['symbol'], cur['suffix'])

    def _update_foreign_currency_display(self):
        """Push foreign currency totals from the model into the view tracker."""
        totals = self.model.get_foreign_currency_totals()
        self.view.update_foreign_currency_display(totals)

    def change_currency(self, currency_code: str):
        """Switch main currency: convert all stored amounts and refresh the view."""
        old_code = self.model.currency
        if old_code == currency_code:
            return
        # Convert every stored amount from old currency to new currency
        self.model.convert_all_amounts(old_code, currency_code)
        self._apply_currency_state(currency_code)
        self.model.set_currency(currency_code)
        self.view.refresh_summary_currency()
        self._update_summary()
        self._update_all_category_balances()
        for category in self.model.categories:
            transactions = self.model.get_transactions_by_category(category)
            self.view.refresh_all_transactions(category, transactions)
        self._update_foreign_currency_display()

    def open_rates_dialog(self):
        """Open the exchange-rate editor dialog."""
        from utils.config import EXCHANGE_RATES as _defaults
        self.view.show_rates_dialog(
            current_rates=self.model.exchange_rates,
            default_rates=_defaults,
            on_save=self.change_exchange_rates,
        )

    def change_exchange_rates(self, rates: dict):
        """Apply new exchange rates, re-price foreign transactions, refresh view."""
        set_exchange_rates(rates)
        self.model.set_exchange_rates(rates)
        self.model.recalculate_foreign_amounts()
        self._update_summary()
        self._update_all_category_balances()
        for category in self.model.categories:
            transactions = self.model.get_transactions_by_category(category)
            self.view.refresh_all_transactions(category, transactions)
        self._update_foreign_currency_display()

    def run(self):
        """Start the application main loop."""
        self.root.mainloop()
        
        