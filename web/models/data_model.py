import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

import streamlit as st
from supabase import create_client, Client

from utils.config import DEFAULT_CURRENCY, EXCHANGE_RATES as _DEFAULT_RATES


def _get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


@dataclass
class Transaction:
    """Represents a single budget transaction."""
    amount: float
    action: str          # 'add' or 'spend'
    category: str
    timestamp: str
    note: Optional[str] = None
    original_currency: Optional[str] = None
    original_amount: Optional[float] = None
    id: Optional[str] = None   # Supabase row UUID

    def to_dict(self) -> dict:
        return {
            'amount': self.amount,
            'action': self.action,
            'category': self.category,
            'timestamp': self.timestamp,
            'note': self.note,
            'original_currency': self.original_currency,
            'original_amount': self.original_amount,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Transaction':
        return cls(
            amount=data['amount'],
            action=data['action'],
            category=data['category'],
            timestamp=data['timestamp'],
            note=data.get('note'),
            original_currency=data.get('original_currency'),
            original_amount=data.get('original_amount'),
            id=data.get('id'),
        )


class DataModel:
    """Manages all budget data — backed by Supabase."""

    def __init__(self, data_file: str = 'savings_data.json', categories: List[str] = None, user_id: str = ''):
        self.model_type = 'expenses' if 'expense' in str(data_file).lower() else 'savings'
        self.data_file = data_file
        self.user_id = user_id

        self.transactions: List[Transaction] = []
        self.categories: List[str] = list(categories or [])
        self.currency: str = DEFAULT_CURRENCY
        self.exchange_rates: dict = dict(_DEFAULT_RATES)
        self.preset_notes: Dict[str, List[str]] = {}

        self._sb = _get_supabase()
        self._load_data()

    # ── Internal helpers ──────────────────────────────────────────────

    def _load_data(self) -> None:
        """Load settings and transactions from Supabase."""
        # Settings row
        res = (
            self._sb.table('settings')
            .select('*')
            .eq('user_id', self.user_id)
            .eq('model_type', self.model_type)
            .execute()
        )
        if res.data:
            row = res.data[0]
            self.currency       = row.get('currency') or DEFAULT_CURRENCY
            self.exchange_rates = row.get('exchange_rates') or dict(_DEFAULT_RATES)
            self.preset_notes   = row.get('preset_notes') or {}
            for cat in (row.get('categories') or []):
                if cat not in self.categories:
                    self.categories.append(cat)

        # Transactions
        res = (
            self._sb.table('transactions')
            .select('*')
            .eq('user_id', self.user_id)
            .eq('model_type', self.model_type)
            .order('timestamp')
            .execute()
        )
        self.transactions = [Transaction.from_dict(r) for r in res.data]

    def _save_settings(self) -> None:
        """Persist settings (currency, categories, exchange rates, preset notes)."""
        self._sb.table('settings').upsert({
            'user_id':        self.user_id,
            'model_type':     self.model_type,
            'currency':       self.currency,
            'exchange_rates': self.exchange_rates,
            'categories':     self.categories,
            'preset_notes':   self.preset_notes,
        }).execute()

    def save_data(self) -> None:
        """Save settings. (Transactions are written individually on each operation.)"""
        self._save_settings()

    # ── Transactions ──────────────────────────────────────────────────

    def add_transaction(
        self,
        amount: float,
        action: str,
        category: str,
        note: Optional[str] = None,
        original_currency: Optional[str] = None,
        original_amount: Optional[float] = None,
    ) -> 'Transaction':
        row = {
            'user_id':           self.user_id,
            'model_type':        self.model_type,
            'amount':            amount,
            'action':            action,
            'category':          category,
            'timestamp':         datetime.now().isoformat(),
            'note':              note,
            'original_currency': original_currency,
            'original_amount':   original_amount,
        }
        res = self._sb.table('transactions').insert(row).execute()
        t = Transaction.from_dict(res.data[0])
        self.transactions.append(t)
        return t

    def delete_transaction_by_ref(self, transaction: 'Transaction') -> bool:
        if transaction.id:
            self._sb.table('transactions').delete().eq('id', transaction.id).execute()
        try:
            self.transactions.remove(transaction)
            return True
        except ValueError:
            return False

    def update_transaction_amount(
        self,
        transaction: 'Transaction',
        new_amount: float,
        new_original_amount: Optional[float] = None,
        new_original_currency: Optional[str] = None,
        note: Optional[str] = None,
    ) -> None:
        transaction.amount            = new_amount
        transaction.original_amount   = new_original_amount
        transaction.original_currency = new_original_currency
        if note is not None:
            transaction.note = note or None

        if transaction.id:
            self._sb.table('transactions').update({
                'amount':            new_amount,
                'original_amount':   new_original_amount,
                'original_currency': new_original_currency,
                'note':              transaction.note,
            }).eq('id', transaction.id).execute()

    def clear_all_data(self) -> None:
        (
            self._sb.table('transactions').delete()
            .eq('user_id', self.user_id)
            .eq('model_type', self.model_type)
            .execute()
        )
        self.transactions = []

    def clear_category(self, category: str) -> None:
        (
            self._sb.table('transactions').delete()
            .eq('user_id', self.user_id)
            .eq('model_type', self.model_type)
            .eq('category', category)
            .execute()
        )
        self.transactions = [t for t in self.transactions if t.category != category]

    def clear_category_tagged(self, category: str, tag: str) -> None:
        (
            self._sb.table('transactions').delete()
            .eq('user_id', self.user_id)
            .eq('model_type', self.model_type)
            .eq('category', category)
            .eq('note', tag)
            .execute()
        )
        self.transactions = [
            t for t in self.transactions
            if not (t.category == category and t.note == tag)
        ]

    def convert_all_amounts(self, from_code: str, to_code: str) -> None:
        from utils.helpers import convert_currency
        for t in self.transactions:
            new_amt  = convert_currency(t.amount, from_code, to_code)
            t.amount = new_amt
            if t.id:
                self._sb.table('transactions').update({'amount': new_amt}).eq('id', t.id).execute()

    def recalculate_foreign_amounts(self) -> None:
        from utils.helpers import convert_currency
        for t in self.transactions:
            if t.original_currency and t.original_amount is not None:
                new_amt  = convert_currency(t.original_amount, t.original_currency, self.currency)
                t.amount = new_amt
                if t.id:
                    self._sb.table('transactions').update({'amount': new_amt}).eq('id', t.id).execute()

    # ── Categories & presets ─────────────────────────────────────────

    def add_category(self, category_name: str) -> bool:
        if category_name in self.categories:
            return False
        self.categories.append(category_name)
        self._save_settings()
        return True

    def delete_category(self, category: str) -> None:
        (
            self._sb.table('transactions').delete()
            .eq('model_type', self.model_type)
            .eq('category', category)
            .execute()
        )
        self.transactions = [t for t in self.transactions if t.category != category]
        if category in self.categories:
            self.categories.remove(category)
        self.preset_notes.pop(category, None)
        self._save_settings()

    def get_preset_notes(self, category: str) -> List[str]:
        return list(self.preset_notes.get(category, []))

    def add_preset_note(self, category: str, note: str) -> bool:
        notes = self.preset_notes.setdefault(category, [])
        if note in notes:
            return False
        notes.append(note)
        self._save_settings()
        return True

    def remove_preset_note(self, category: str, note: str) -> bool:
        notes = self.preset_notes.get(category, [])
        if note in notes:
            notes.remove(note)
            self._save_settings()
            return True
        return False

    # ── Currency / rates ─────────────────────────────────────────────

    def set_currency(self, currency_code: str) -> None:
        self.currency = currency_code
        self._save_settings()

    def set_exchange_rates(self, rates: dict) -> None:
        self.exchange_rates = dict(rates)
        self._save_settings()

    # ── Read-only computed helpers ────────────────────────────────────

    def get_category_balance(self, category: str) -> float:
        total = 0
        for t in self.transactions:
            if t.category == category:
                total += t.amount if t.action == 'add' else -t.amount
        return total

    def get_total_budget(self, exclude_categories=None) -> float:
        total = 0
        for t in self.transactions:
            if exclude_categories and t.category in exclude_categories:
                continue
            total += t.amount if t.action == 'add' else -t.amount
        return total

    def get_total_added(self, exclude_categories=None) -> float:
        return sum(
            t.amount for t in self.transactions
            if t.action == 'add'
            and (not exclude_categories or t.category not in exclude_categories)
        )

    def get_total_spent(self, exclude_categories=None) -> float:
        return sum(
            t.amount for t in self.transactions
            if t.action == 'spend'
            and (not exclude_categories or t.category not in exclude_categories)
        )

    def get_transactions_by_category(self, category: str) -> List[Transaction]:
        return [t for t in self.transactions if t.category == category]

    def get_foreign_currency_totals(self) -> Dict[str, Dict[str, float]]:
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

    def get_distributable_balance(self) -> float:
        from utils.config import DISTRIBUTABLE_CATEGORY
        transferred = sum(
            t.amount for t in self.transactions
            if t.category == DISTRIBUTABLE_CATEGORY and t.action == 'add'
        )
        returned = sum(
            t.amount for t in self.transactions
            if t.category == DISTRIBUTABLE_CATEGORY and t.action == 'spend'
        )
        allocated = sum(
            t.amount for t in self.transactions
            if t.category != DISTRIBUTABLE_CATEGORY and t.action == 'add'
        )
        return transferred - returned - allocated

    # ── Legacy helpers ────────────────────────────────────────────────

    def add_to_budget(self, amount, category, original_currency=None, original_amount=None):
        return self.add_transaction(amount, 'add', category,
                                    original_currency=original_currency,
                                    original_amount=original_amount)

    def spend_from_budget(self, amount, category, original_currency=None, original_amount=None):
        return self.add_transaction(amount, 'spend', category,
                                    original_currency=original_currency,
                                    original_amount=original_amount)