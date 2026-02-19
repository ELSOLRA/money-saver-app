
import json
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class Transaction:
    """Represents a single budget transaction."""
    amount: float
    action: str  # 'add' or 'spend'
    category: str
    timestamp: str
    note: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Transaction':
        return cls(**data)


class DataModel:
    """
    Manages all budget data operations.
    """

    def __init__(self, data_file: str = 'savings_data.json', categories: List[str] = None):
        self.data_file = Path(data_file)
        self.transactions: List[Transaction] = []
        self.categories = categories or []
        self._load_data()

    def _load_data(self) -> None:
        """Load data from Base64-encoded JSON file if it exists."""
        if self.data_file.exists():
            try:
                raw = self.data_file.read_bytes()
                try:
                    decoded = base64.b64decode(raw)
                    json_str = decoded.decode('utf-8')
                except Exception:
                    # Fallback: file is still plain JSON 
                    json_str = raw.decode('utf-8')
                data = json.loads(json_str)
                self.transactions = [
                    Transaction.from_dict(t) for t in data.get('transactions', [])
                ]
                # Load saved categories and merge with defaults
                saved_categories = data.get('categories', [])
                for cat in saved_categories:
                    if cat not in self.categories:
                        self.categories.append(cat)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading data: {e}. Starting with empty data.")
                self.transactions = []

    def save_data(self) -> None:
        """Save all data to JSON file encoded as Base64."""
        data = {
            'transactions': [t.to_dict() for t in self.transactions],
            'categories': self.categories,
            'last_updated': datetime.now().isoformat()
        }
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        encoded = base64.b64encode(json_str.encode('utf-8'))
        self.data_file.write_bytes(encoded)

    def add_transaction(
        self,
        amount: float,
        action: str,
        category: str,
        note: Optional[str] = None
    ) -> Transaction:
        """Add a new transaction and save to file."""
        transaction = Transaction(
            amount=amount,
            action=action,
            category=category,
            timestamp=datetime.now().isoformat(),
            note=note
        )
        self.transactions.append(transaction)
        self.save_data()
        return transaction

    def add_to_budget(self, amount: float, category: str) -> Transaction:
        """Add money to a category budget."""
        return self.add_transaction(amount, 'add', category)

    def spend_from_budget(self, amount: float, category: str) -> Transaction:
        """Spend money from a category budget."""
        return self.add_transaction(amount, 'spend', category)

    def get_category_balance(self, category: str) -> float:
        """Get current balance for a specific category."""
        total = 0
        for t in self.transactions:
            if t.category == category:
                if t.action == 'add':
                    total += t.amount
                else:  # spend
                    total -= t.amount
        return total

    def get_total_budget(self) -> float:
        """Get total budget across all categories."""
        total = 0
        for t in self.transactions:
            if t.action == 'add':
                total += t.amount
            else:  # spend
                total -= t.amount
        return total

    def get_total_added(self) -> float:
        """Get total money added across all categories."""
        return sum(t.amount for t in self.transactions if t.action == 'add')

    def get_total_spent(self) -> float:
        """Get total money spent across all categories."""
        return sum(t.amount for t in self.transactions if t.action == 'spend')

    def get_transactions_by_category(self, category: str) -> List[Transaction]:
        """Get all transactions for a specific category."""
        return [t for t in self.transactions if t.category == category]

    def clear_all_data(self) -> None:
        """Clear all transactions."""
        self.transactions = []
        self.save_data()

    def clear_category(self, category: str) -> None:
        """Clear all transactions for a specific category."""
        self.transactions = [t for t in self.transactions if t.category != category]
        self.save_data()

    def add_category(self, category_name: str) -> bool:
        """Add a new category. Returns True if successful."""
        if category_name in self.categories:
            return False
        self.categories.append(category_name)
        self.save_data()
        return True
    
    def delete_category(self, category: str) -> None:
        """Delete a category and all its transactions."""
        self.transactions = [t for t in self.transactions if t.category != category]
        if category in self.categories:
            self.categories.remove(category)
        self.save_data()