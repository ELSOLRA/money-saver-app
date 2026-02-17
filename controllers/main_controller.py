
import tkinter as tk

from models import DataModel
from views import MainView
from utils.config import DATA_FILE, BUDGET_CATEGORIES


class MainController:
    """
    Main application controller for budget tracking.
    """

    def __init__(self):
        self.root = tk.Tk()
        self.model = DataModel(DATA_FILE, BUDGET_CATEGORIES)
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

    def _initialize_view(self):
        """Initialize the view with existing data."""
        # Add category tabs
        for category in self.model.categories:
            transactions = self.model.get_transactions_by_category(category)
            self.view.add_category_tab(category, transactions)

        # Add the "+" tab for creating new categories
        self.view.add_new_category_tab()

        # Update summary and category balances
        self._update_summary()
        self._update_all_category_balances()

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

    def add_to_budget(self, amount: float, category: str):
        """Add money to a category budget."""
        transaction = self.model.add_to_budget(amount, category)
        
        # Update view
        balance = self.model.get_category_balance(category)
        self.view.update_category(category, balance, transaction)
        self._update_summary()

    def spend_from_budget(self, amount: float, category: str):
        """Spend money from a category budget."""
        transaction = self.model.spend_from_budget(amount, category)
        
        # Update view
        balance = self.model.get_category_balance(category)
        self.view.update_category(category, balance, transaction)
        self._update_summary()

    def clear_data(self):
        """Clear all transaction data."""
        self.model.clear_all_data()
        
        # Refresh all category tabs
        for category in self.model.categories:
            self.view.refresh_all_transactions(category, [])
            self.view.update_category(category, 0)
        
        self._update_summary()
        self.view.show_message("Success", "All data has been cleared.")

    def clear_category(self, category: str):
        """Clear all transactions for a specific category."""
        self.model.clear_category(category)
        
        # Refresh only this category
        self.view.refresh_all_transactions(category, [])
        self.view.update_category(category, 0)
        
        self._update_summary()
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

    def run(self):
        """Start the application main loop."""
        self.root.mainloop()