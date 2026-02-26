
import tkinter as tk

from models import DataModel
from views import MainView
from utils.config import (
    DATA_FILE, EXPENSE_DATA_FILE,
    BUDGET_CATEGORIES, EXPENSE_CATEGORIES,
    CURRENCIES, SALARY_CATEGORY,
    DISTRIBUTABLE_CATEGORY, TRANSFER_OUT_CATEGORY,
)
from utils.helpers import set_currency_state, convert_currency, set_exchange_rates, format_currency


class MainController:
    """Main application controller for budget tracking."""

    def __init__(self):
        self.root = tk.Tk()

        # ── Savings model ────────────────────────────────────────────
        self.model = DataModel(DATA_FILE, BUDGET_CATEGORIES)
        self._apply_currency_state(self.model.currency)
        set_exchange_rates(self.model.exchange_rates)

        # ── Expenses model ───────────────────────────────────────────
        self.expenses_model = DataModel(EXPENSE_DATA_FILE, EXPENSE_CATEGORIES)
        # Sync currency to savings on first run (or if files drifted)
        if self.expenses_model.currency != self.model.currency:
            self.expenses_model.convert_all_amounts(
                self.expenses_model.currency, self.model.currency
            )
            self.expenses_model.set_currency(self.model.currency)

        self.view = MainView(self.root)
        self._setup_callbacks()
        self._initialize_view()

    # ── Callback wiring ──────────────────────────────────────────────

    def _setup_callbacks(self):
        # Savings
        self.view.on_add_budget      = self.add_to_budget
        self.view.on_spend_budget    = self.spend_from_budget
        self.view.on_clear_data      = self.clear_data
        self.view.on_clear_category  = self.clear_category
        self.view.on_create_category = self.create_category
        self.view.on_export_data     = self.export_data
        self.view.on_delete_category = self.delete_category
        self.view.on_currency_change = self.change_currency
        self.view.on_edit_rates      = self.open_rates_dialog

        # Expenses
        self.view.on_add_expense             = self.add_to_expense
        self.view.on_spend_expense           = self.spend_from_expense
        self.view.on_clear_expense_data      = self.clear_expense_data
        self.view.on_clear_expense_category  = self.clear_expense_category
        self.view.on_create_expense_category = self.create_expense_category
        self.view.on_export_expense_data     = self.export_expense_data
        self.view.on_delete_expense_category = self.delete_expense_category
        self.view.on_transfer_to_savings     = self.transfer_to_savings
        self.view.on_add_direct_income       = self.add_direct_income
        self.view.on_edit_income             = self.edit_income
        self.view.on_delete_income           = self.delete_income

    def _initialize_view(self):
        self.view.set_currency(self.model.currency)

        # ── Savings tabs ─────────────────────────────────────────────
        for category in self.model.categories:
            transactions = self.model.get_transactions_by_category(category)
            self.view.add_category_tab(category, transactions)
        self.view.add_new_category_tab()
        self._update_summary()
        self._update_all_category_balances()
        self._update_foreign_currency_display()
        self._update_distributable_balance()

        # ── Expenses tabs ────────────────────────────────────────────
        for category in self.expenses_model.categories:
            transactions = self.expenses_model.get_transactions_by_category(category)
            self.view.add_expense_category_tab(category, transactions)
        self.view.add_new_expense_category_tab()
        self._update_expenses_summary()
        self._update_all_expense_category_balances()
        self._update_expenses_foreign_currency_display()
        self._update_transferred_display()
        self._update_income_list()

    # ── Savings helpers ──────────────────────────────────────────────

    def _update_summary(self):
        self.view.update_summary(
            self.model.get_total_budget(exclude_categories=[DISTRIBUTABLE_CATEGORY]),
            self.model.get_total_added(exclude_categories=[DISTRIBUTABLE_CATEGORY]),
            self.model.get_total_spent(exclude_categories=[DISTRIBUTABLE_CATEGORY]),
        )

    def _update_all_category_balances(self):
        for cat in self.model.categories:
            self.view.update_category(cat, self.model.get_category_balance(cat))

    def _update_foreign_currency_display(self):
        self.view.update_foreign_currency_display(self.model.get_foreign_currency_totals())

    # ── Savings operations ───────────────────────────────────────────

    def add_to_budget(self, amount: float, category: str, input_currency: str = None):
        main_currency = self.model.currency
        if input_currency and input_currency != main_currency:
            converted = convert_currency(amount, input_currency, main_currency)
            orig_curr, orig_amt = input_currency, amount
        else:
            converted, orig_curr, orig_amt = amount, None, None

        available = self.model.get_distributable_balance()
        if converted > available:
            if available <= 0:
                msg = (
                    f"No funds available to allocate.\n\n"
                    f"Transfer money from Expenses or add Other Income\n"
                    f"to the Savings 'Available to Allocate' bar first."
                )
            else:
                msg = (
                    f"Only {format_currency(available)} is available to allocate.\n\n"
                    f"Enter an amount up to {format_currency(available)},\n"
                    f"or add more income via Other Income / Transfer from Expenses."
                )
            self.view.show_message("Insufficient Funds", msg, "warning")
            return

        transaction = self.model.add_transaction(
            amount=converted, action='add', category=category,
            original_currency=orig_curr, original_amount=orig_amt,
        )
        self.view.update_category(category, self.model.get_category_balance(category), transaction)
        self._update_summary()
        self._update_foreign_currency_display()
        self._update_distributable_balance()

    def spend_from_budget(self, amount: float, category: str, input_currency: str = None, note: str = ''):
        main_currency = self.model.currency
        if input_currency and input_currency != main_currency:
            converted = convert_currency(amount, input_currency, main_currency)
            orig_curr, orig_amt = input_currency, amount
        else:
            converted, orig_curr, orig_amt = amount, None, None

        balance = self.model.get_category_balance(category)
        if converted > balance:
            if balance <= 0:
                msg = f"'{category}' has no savings. Add to this category first."
            else:
                msg = (
                    f"'{category}' only has {format_currency(balance)}.\n"
                    f"Enter an amount up to {format_currency(balance)}."
                )
            self.view.show_message("No Savings", msg, "warning")
            return

        transaction = self.model.add_transaction(
            amount=converted, action='spend', category=category,
            original_currency=orig_curr, original_amount=orig_amt,
            note=note if note else None,
        )
        self.view.update_category(category, self.model.get_category_balance(category), transaction)
        self._update_summary()
        self._update_foreign_currency_display()

    def clear_data(self):
        self.model.clear_all_data()
        for cat in self.model.categories:
            self.view.refresh_all_transactions(cat, [])
            self.view.update_category(cat, 0)
        self._update_summary()
        self._update_foreign_currency_display()
        self._update_distributable_balance()
        # Return transferred amounts back to expenses (remove the debit records)
        self.expenses_model.clear_category(TRANSFER_OUT_CATEGORY)
        self._update_expenses_summary()
        self._update_transferred_display()
        self.view.show_message("Success", "All savings data has been cleared.")

    def clear_category(self, category: str):
        self.model.clear_category(category)
        self.view.refresh_all_transactions(category, [])
        self.view.update_category(category, 0)
        self._update_summary()
        self._update_foreign_currency_display()
        self._update_distributable_balance()
        self.view.show_message("Success", f"{category} data has been cleared.")

    def create_category(self, category_name: str) -> bool:
        success = self.model.add_category(category_name)
        if success:
            self.view.add_category_tab(category_name, [], insert_before_plus=True)
            self.view.select_tab(category_name)
            self._update_distributable_balance()
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
            initialfile="savings_export.xlsx",
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
        self._update_distributable_balance()
        self.view.show_message("Success", f"'{category}' has been deleted.")

    # ── Expenses helpers ─────────────────────────────────────────────

    def _update_expenses_summary(self):
        self.view.update_expenses_summary(
            self.expenses_model.get_total_budget(),
            self.expenses_model.get_total_added(),
            self.expenses_model.get_total_spent(),
        )

    def _update_all_expense_category_balances(self):
        for cat in self.expenses_model.categories:
            spent = sum(
                t.amount for t in self.expenses_model.get_transactions_by_category(cat)
                if t.action == 'spend'
            )
            self.view.update_expense_category(cat, spent)

    def _update_expenses_foreign_currency_display(self):
        self.view.update_expenses_foreign_currency_display(
            self.expenses_model.get_foreign_currency_totals()
        )

    # ── Expenses operations ──────────────────────────────────────────

    def add_to_expense(self, amount: float, category: str, input_currency: str = None):
        """Add income to the expense pot (salary or other income, stored under SALARY_CATEGORY)."""
        main_currency = self.expenses_model.currency
        if input_currency and input_currency != main_currency:
            converted = convert_currency(amount, input_currency, main_currency)
            orig_curr, orig_amt = input_currency, amount
        else:
            converted, orig_curr, orig_amt = amount, None, None
        self.expenses_model.add_transaction(
            amount=converted, action='add', category=category,
            original_currency=orig_curr, original_amount=orig_amt,
        )
        # Income goes to the central pot — no category tab to update
        self._update_expenses_summary()
        self._update_expenses_foreign_currency_display()
        if category == SALARY_CATEGORY:
            self._update_income_list()

    def spend_from_expense(self, amount: float, category: str, input_currency: str = None, note: str = ''):
        main_currency = self.expenses_model.currency
        if input_currency and input_currency != main_currency:
            converted = convert_currency(amount, input_currency, main_currency)
            orig_curr, orig_amt = input_currency, amount
        else:
            converted, orig_curr, orig_amt = amount, None, None

        remaining = self.expenses_model.get_total_budget()
        if converted > remaining:
            if remaining <= 0:
                msg = "No funds remaining in Expenses. Add income first."
            else:
                msg = (
                    f"Only {format_currency(remaining)} remaining in Expenses.\n"
                    f"Enter an amount up to {format_currency(remaining)}."
                )
            self.view.show_message("No Savings", msg, "warning")
            return

        transaction = self.expenses_model.add_transaction(
            amount=converted, action='spend', category=category,
            original_currency=orig_curr, original_amount=orig_amt,
            note=note if note else None,
        )
        # Show total spent in this category (positive number)
        spent = sum(
            t.amount for t in self.expenses_model.get_transactions_by_category(category)
            if t.action == 'spend'
        )
        self.view.update_expense_category(category, spent, transaction)
        self._update_expenses_summary()
        self._update_expenses_foreign_currency_display()

    def clear_expense_data(self):
        self.expenses_model.clear_all_data()
        for cat in self.expenses_model.categories:
            self.view.refresh_expense_transactions(cat, [])
            self.view.update_expense_category(cat, 0)
        self._update_expenses_summary()
        self._update_expenses_foreign_currency_display()
        self._update_transferred_display()
        self._update_income_list()
        self.model.clear_category_tagged(DISTRIBUTABLE_CATEGORY, '__transfer__')
        self._update_distributable_balance()
        self.view.show_message("Success", "All expenses data has been cleared.")

    def clear_expense_category(self, category: str):
        self.expenses_model.clear_category(category)
        self.view.refresh_expense_transactions(category, [])
        self.view.update_expense_category(category, 0)
        self._update_expenses_summary()
        self._update_expenses_foreign_currency_display()
        self.view.show_message("Success", f"{category} expenses have been cleared.")

    def create_expense_category(self, category_name: str) -> bool:
        success = self.expenses_model.add_category(category_name)
        if success:
            self.view.add_expense_category_tab(category_name, [], insert_before_plus=True)
            self.view.select_expense_tab(category_name)
            self.view.show_message("Success", f"Expense category '{category_name}' created!")
            return True
        else:
            self.view.show_message("Error", f"Category '{category_name}' already exists.", "error")
            return False

    def export_expense_data(self):
        from utils.helpers import export_to_excel
        from tkinter import filedialog
        import os
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="expenses_export.xlsx",
        )
        if path:
            export_to_excel(
                transactions=self.expenses_model.transactions,
                categories=self.expenses_model.categories,
                get_category_balance=self.expenses_model.get_category_balance,
                get_totals=None,
                output_path=path,
                main_currency=self.expenses_model.currency,
            )
            self.view.show_message("Success", f"Exported to:\n{os.path.basename(path)}")

    def delete_expense_category(self, category: str):
        self.expenses_model.delete_category(category)
        self.view.remove_expense_category_tab(category)
        self._update_expenses_summary()
        self._update_expenses_foreign_currency_display()
        self.view.show_message("Success", f"Expense category '{category}' has been deleted.")

    # ── Transfer bridge (Expenses → Savings) ─────────────────────────

    def transfer_to_savings(self, amount: float, input_currency: str = None):
        """Move money from the Expenses pot into the Savings distributable pool."""
        main_currency = self.model.currency
        if input_currency and input_currency != main_currency:
            converted = convert_currency(amount, input_currency, main_currency)
            orig_curr, orig_amt = input_currency, amount
        else:
            converted, orig_curr, orig_amt = amount, None, None

        # Guard: don't allow transferring more than what's remaining in expenses
        remaining = self.expenses_model.get_total_budget()
        if converted > remaining:
            if remaining <= 0:
                msg = (
                    "Expenses Remaining is zero or negative.\n"
                    "Add income first before transferring to Savings."
                )
            else:
                msg = (
                    f"Only {format_currency(remaining)} remaining in Expenses.\n"
                    f"Enter an amount up to {format_currency(remaining)}."
                )
            self.view.show_message("Insufficient Funds", msg, "warning")
            return

        # Debit the expenses model (reduces Remaining)
        self.expenses_model.add_transaction(
            amount=converted, action='spend', category=TRANSFER_OUT_CATEGORY,
            original_currency=orig_curr, original_amount=orig_amt,
        )

        self.model.add_transaction(
            amount=converted, action='add', category=DISTRIBUTABLE_CATEGORY,
            original_currency=orig_curr, original_amount=orig_amt,
            note='__transfer__',
        )

        self._update_expenses_summary()
        self._update_summary()
        self._update_distributable_balance()
        self._update_transferred_display()

    def add_direct_income(self, amount: float, input_currency: str = None):
        """Add income directly into the savings distributable pool (no expenses debit)."""
        main_currency = self.model.currency
        if input_currency and input_currency != main_currency:
            converted = convert_currency(amount, input_currency, main_currency)
            orig_curr, orig_amt = input_currency, amount
        else:
            converted, orig_curr, orig_amt = amount, None, None
        self.model.add_transaction(
            amount=converted, action='add', category=DISTRIBUTABLE_CATEGORY,
            original_currency=orig_curr, original_amount=orig_amt,
        )
        self._update_summary()
        self._update_distributable_balance()

    def _update_income_list(self):
        self.view.update_income_list(
            self.expenses_model.get_transactions_by_category(SALARY_CATEGORY)
        )

    def _get_total_transferred(self) -> float:
        return sum(
            t.amount for t in self.expenses_model.transactions
            if t.category == TRANSFER_OUT_CATEGORY and t.action == 'spend'
        )

    def edit_income(self, transaction, new_amount: float, input_currency: str = None):
        main_currency = self.expenses_model.currency
        if input_currency and input_currency != main_currency:
            converted = convert_currency(new_amount, input_currency, main_currency)
            orig_curr, orig_amt = input_currency, new_amount
        else:
            converted, orig_curr, orig_amt = new_amount, None, None

        total_transferred = self._get_total_transferred()
        if total_transferred > 0 and converted < total_transferred:
            self.view.show_message(
                "Cannot Reduce Income",
                f"{format_currency(total_transferred)} has already been transferred to Savings.\n"
                f"The income amount cannot be less than {format_currency(total_transferred)}.",
                "warning",
            )
            return

        self.expenses_model.update_transaction_amount(transaction, converted, orig_amt, orig_curr)
        self._update_expenses_summary()
        self._update_expenses_foreign_currency_display()
        self._update_income_list()

    def delete_income(self, transaction):
        total_transferred = self._get_total_transferred()
        if total_transferred > 0:
            self.view.show_message(
                "Cannot Delete Income",
                f"{format_currency(total_transferred)} has already been transferred to Savings.\n"
                "You can edit the income amount, but it cannot be deleted while a transfer exists.",
                "warning",
            )
            return
        self.expenses_model.delete_transaction_by_ref(transaction)
        self._update_expenses_summary()
        self._update_expenses_foreign_currency_display()
        self._update_income_list()

    def _update_distributable_balance(self):
        self.view.update_distributable_balance(self.model.get_distributable_balance())

    def _update_transferred_display(self):
        total = sum(
            t.amount for t in self.expenses_model.transactions
            if t.category == TRANSFER_OUT_CATEGORY and t.action == 'spend'
        )
        self.view.update_transferred_display(total)

    # ── Currency / Rates (affect both models) ────────────────────────

    def _apply_currency_state(self, currency_code: str):
        cur = CURRENCIES.get(currency_code, CURRENCIES['EUR'])
        set_currency_state(cur['symbol'], cur['suffix'])

    def change_currency(self, currency_code: str):
        old_code = self.model.currency
        if old_code == currency_code:
            return

        # Convert savings amounts
        self.model.convert_all_amounts(old_code, currency_code)
        self.model.set_currency(currency_code)

        # Convert expenses amounts
        self.expenses_model.convert_all_amounts(old_code, currency_code)
        self.expenses_model.set_currency(currency_code)

        self._apply_currency_state(currency_code)

        self.view.refresh_summary_currency()
        self.view.refresh_expenses_summary_currency()

        self._update_summary()
        self._update_expenses_summary()

        self._update_all_category_balances()
        self._update_all_expense_category_balances()

        for cat in self.model.categories:
            self.view.refresh_all_transactions(cat, self.model.get_transactions_by_category(cat))
        for cat in self.expenses_model.categories:
            self.view.refresh_expense_transactions(cat, self.expenses_model.get_transactions_by_category(cat))

        self._update_foreign_currency_display()
        self._update_expenses_foreign_currency_display()
        self._update_distributable_balance()
        self._update_transferred_display()
        self._update_income_list()

    def open_rates_dialog(self):
        from utils.config import EXCHANGE_RATES as _defaults
        self.view.show_rates_dialog(
            current_rates=self.model.exchange_rates,
            default_rates=_defaults,
            on_save=self.change_exchange_rates,
        )

    def change_exchange_rates(self, rates: dict):
        set_exchange_rates(rates)

        self.model.set_exchange_rates(rates)
        self.model.recalculate_foreign_amounts()

        self.expenses_model.set_exchange_rates(rates)
        self.expenses_model.recalculate_foreign_amounts()

        self._update_summary()
        self._update_expenses_summary()

        self._update_all_category_balances()
        self._update_all_expense_category_balances()

        for cat in self.model.categories:
            self.view.refresh_all_transactions(cat, self.model.get_transactions_by_category(cat))
        for cat in self.expenses_model.categories:
            self.view.refresh_expense_transactions(cat, self.expenses_model.get_transactions_by_category(cat))

        self._update_foreign_currency_display()
        self._update_expenses_foreign_currency_display()
        self._update_distributable_balance()
        self._update_transferred_display()
        self._update_income_list()

    def run(self):
        self.root.mainloop()
