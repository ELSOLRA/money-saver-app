
import json
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from utils.config import DEFAULT_CURRENCY, EXCHANGE_RATES as _DEFAULT_RATES


@dataclass
class Transaction:
    """Represents a single budget transaction."""
    amount: float
    action: str  # 'add' or 'spend'
    category: str
    timestamp: str
    note: Optional[str] = None
    original_currency: Optional[str] = None   
    original_amount: Optional[float] = None   #

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
        self.currency: str = DEFAULT_CURRENCY
        self.exchange_rates: dict = dict(_DEFAULT_RATES)
        self.preset_notes: Dict[str, List[str]] = {}
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
                self.currency = data.get('currency', DEFAULT_CURRENCY)
                self.exchange_rates = data.get('exchange_rates', dict(_DEFAULT_RATES))
                self.preset_notes = data.get('preset_notes', {})
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading data: {e}. Starting with empty data.")
                self.transactions = []

    def save_data(self) -> None:
        """Save all data to JSON file encoded as Base64."""
        data = {
            'transactions': [t.to_dict() for t in self.transactions],
            'categories': self.categories,
            'currency': self.currency,
            'exchange_rates': self.exchange_rates,
            'preset_notes': self.preset_notes,
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
        note: Optional[str] = None,
        original_currency: Optional[str] = None,
        original_amount: Optional[float] = None,
    ) -> Transaction:
        """Add a new transaction and save to file."""
        transaction = Transaction(
            amount=amount,
            action=action,
            category=category,
            timestamp=datetime.now().isoformat(),
            note=note,
            original_currency=original_currency,
            original_amount=original_amount,
        )
        self.transactions.append(transaction)
        self.save_data()
        return transaction

    def add_to_budget(self, amount: float, category: str,
                      original_currency: Optional[str] = None,
                      original_amount: Optional[float] = None) -> Transaction:
        """Add money to a category budget."""
        return self.add_transaction(amount, 'add', category,
                                    original_currency=original_currency,
                                    original_amount=original_amount)

    def spend_from_budget(self, amount: float, category: str,
                          original_currency: Optional[str] = None,
                          original_amount: Optional[float] = None) -> Transaction:
        """Spend money from a category budget."""
        return self.add_transaction(amount, 'spend', category,
                                    original_currency=original_currency,
                                    original_amount=original_amount)

    def get_category_balance(self, category: str) -> float:
        """Get current balance for a specific category."""
        total = 0
        for t in self.transactions:
            if t.category == category:
                if t.action == 'add':
                    total += t.amount
                else:  
                    total -= t.amount
        return total

    def get_total_budget(self, exclude_categories=None) -> float:
        """Get total budget across all categories."""
        total = 0
        for t in self.transactions:
            if exclude_categories and t.category in exclude_categories:
                continue
            if t.action == 'add':
                total += t.amount
            else:
                total -= t.amount
        return total

    def get_total_added(self, exclude_categories=None) -> float:
        """Get total money added across all categories."""
        return sum(
            t.amount for t in self.transactions
            if t.action == 'add'
            and (not exclude_categories or t.category not in exclude_categories)
        )

    def get_total_spent(self, exclude_categories=None) -> float:
        """Get total money spent across all categories."""
        return sum(
            t.amount for t in self.transactions
            if t.action == 'spend'
            and (not exclude_categories or t.category not in exclude_categories)
        )

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
        self.preset_notes.pop(category, None)
        self.save_data()

    def get_preset_notes(self, category: str) -> List[str]:
        """Return the list of preset note strings for a category."""
        return list(self.preset_notes.get(category, []))

    def add_preset_note(self, category: str, note: str) -> bool:
        """Add a preset note to a category. Returns False if already exists."""
        notes = self.preset_notes.setdefault(category, [])
        if note in notes:
            return False
        notes.append(note)
        self.save_data()
        return True

    def remove_preset_note(self, category: str, note: str) -> bool:
        """Remove a preset note from a category. Returns False if not found."""
        notes = self.preset_notes.get(category, [])
        if note in notes:
            notes.remove(note)
            self.save_data()
            return True
        return False

    def get_foreign_currency_totals(self) -> Dict[str, Dict[str, float]]:
        """Get added/spent totals for each non-main currency used as input."""
        totals: Dict[str, Dict[str, float]] = {}
        for t in self.transactions:
            if t.original_currency and t.original_amount is not None:
                curr = t.original_currency
                if curr not in totals:
                    totals[curr] = {'added': 0.0, 'spent': 0.0}
                if t.action == 'add':
                    totals[curr]['added'] += t.original_amount
                else:
                    totals[curr]['spent'] += t.original_amount
        return totals

    def convert_all_amounts(self, from_code: str, to_code: str) -> None:
        """Re-convert every stored amount when the main currency changes."""
        from utils.helpers import convert_currency
        for t in self.transactions:
            t.amount = convert_currency(t.amount, from_code, to_code)
        self.save_data()

    def recalculate_foreign_amounts(self) -> None:
        """Recompute main-currency amounts for foreign-input transactions using active rates."""
        from utils.helpers import convert_currency
        for t in self.transactions:
            if t.original_currency and t.original_amount is not None:
                t.amount = convert_currency(t.original_amount, t.original_currency, self.currency)
        self.save_data()

    def set_exchange_rates(self, rates: dict) -> None:
        """Persist custom exchange rates."""
        self.exchange_rates = dict(rates)
        self.save_data()

    def set_currency(self, currency_code: str) -> None:
        """Set the active currency and persist it."""
        self.currency = currency_code
        self.save_data()

    def delete_transaction_by_ref(self, transaction: 'Transaction') -> bool:
        """Delete a specific transaction by object reference. Returns True if found."""
        try:
            self.transactions.remove(transaction)
            self.save_data()
            return True
        except ValueError:
            return False

    def clear_category_tagged(self, category: str, tag: str) -> None:
        """Remove only transactions in category whose note matches tag."""
        self.transactions = [
            t for t in self.transactions
            if not (t.category == category and t.note == tag)
        ]
        self.save_data()

    def update_transaction_amount(
        self,
        transaction: 'Transaction',
        new_amount: float,
        new_original_amount: Optional[float] = None,
        new_original_currency: Optional[str] = None,
    ) -> None:
        """Update the amount fields of an existing transaction in-place."""
        transaction.amount = new_amount
        transaction.original_amount = new_original_amount
        transaction.original_currency = new_original_currency
        self.save_data()

    def get_distributable_balance(self) -> float:
        """
        Money received via transfers from expenses minus money already
        allocated to actual savings categories.
        distributable = sum(DISTRIBUTABLE_CATEGORY adds) - sum(all other adds)
        """
        from utils.config import DISTRIBUTABLE_CATEGORY
        transferred = sum(
            t.amount for t in self.transactions
            if t.category == DISTRIBUTABLE_CATEGORY and t.action == 'add'
        )
        allocated = sum(
            t.amount for t in self.transactions
            if t.category != DISTRIBUTABLE_CATEGORY and t.action == 'add'
        )
        return transferred - allocated