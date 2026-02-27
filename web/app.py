import sys
import os
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from models.data_model import DataModel
from utils.config import (
    DATA_FILE, EXPENSE_DATA_FILE,
    BUDGET_CATEGORIES, EXPENSE_CATEGORIES,
    CURRENCIES, DISTRIBUTABLE_CATEGORY,
    SALARY_CATEGORY, TRANSFER_OUT_CATEGORY,
    PRESET_AMOUNTS,
)
from utils.helpers import (
    convert_currency, format_currency, format_currency_for_code,
    set_currency_state, set_exchange_rates,
    export_to_excel,
)

# ── Page config ───────────────────────────────────────────────────
st.set_page_config(page_title="Budget Saver", page_icon="💰", layout="wide")

# ── Load models once, shared across reruns ────────────────────────
@st.cache_resource
def load_models():
    model     = DataModel(DATA_FILE,         list(BUDGET_CATEGORIES))
    exp_model = DataModel(EXPENSE_DATA_FILE, list(EXPENSE_CATEGORIES))
    return model, exp_model

model, exp_model = load_models()

# Sync currency helpers with whatever is stored in the model
set_currency_state(
    CURRENCIES[model.currency]['symbol'],
    CURRENCIES[model.currency]['suffix'],
)
set_exchange_rates(model.exchange_rates)


# ── Global computed values (used across both tabs) ────────────────
def _get_net_transferred():
    sent = sum(
        t.amount for t in model.transactions
        if t.category == DISTRIBUTABLE_CATEGORY
        and t.action == 'add'
        and t.note == '__transfer__'
    )
    returned = sum(
        t.amount for t in model.transactions
        if t.category == DISTRIBUTABLE_CATEGORY
        and t.action == 'spend'
        and t.note == '__transfer_back__'
    )
    return sent - returned


# ── Sidebar: settings ─────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Settings")

    selected_currency = st.selectbox(
        "Main Currency",
        list(CURRENCIES.keys()),
        index=list(CURRENCIES.keys()).index(model.currency),
    )
    if selected_currency != model.currency:
        old = model.currency
        model.convert_all_amounts(old, selected_currency)
        model.set_currency(selected_currency)
        exp_model.convert_all_amounts(old, selected_currency)
        exp_model.set_currency(selected_currency)
        set_currency_state(
            CURRENCIES[selected_currency]['symbol'],
            CURRENCIES[selected_currency]['suffix'],
        )
        st.rerun()

    st.divider()

    with st.expander("📈 Exchange Rates"):
        st.caption("Rates relative to EUR (1 EUR = X units)")
        new_rates = {}
        for code in CURRENCIES:
            cur_rate = model.exchange_rates.get(code, 1.0)
            new_rates[code] = st.number_input(
                f"1 EUR = ? {code}",
                value=float(cur_rate),
                min_value=0.0001,
                step=0.01,
                format="%.4f",
                key=f"rate_{code}",
            )
        if st.button("💾 Save Rates", key="btn_save_rates"):
            model.set_exchange_rates(new_rates)
            exp_model.set_exchange_rates(new_rates)
            set_exchange_rates(new_rates)
            model.recalculate_foreign_amounts()
            exp_model.recalculate_foreign_amounts()
            st.success("Exchange rates saved")
            st.rerun()

    st.divider()
    st.caption("Budget Saver — Web version")


# ── Helper: Excel export download button ─────────────────────────
def _export_button(m, label, filename):
    if not m.transactions:
        st.button(label, disabled=True, key=f"dl_disabled_{filename}")
        return
    tmp = tempfile.mktemp(suffix=".xlsx")
    try:
        export_to_excel(
            m.transactions, m.categories,
            m.get_category_balance, None,
            tmp, m.currency,
        )
        with open(tmp, "rb") as f:
            data = f.read()
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    st.download_button(
        label=label,
        data=data,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"dl_{filename}",
    )


# ── Helper: preset amount quick-buttons ──────────────────────────
def _preset_buttons(amt_key):
    cols = st.columns(len(PRESET_AMOUNTS))
    for i, amt in enumerate(PRESET_AMOUNTS):
        if cols[i].button(format_currency(amt), key=f"preset_{amt_key}_{amt}"):
            st.session_state[amt_key] = float(amt)
            st.rerun()


# ── Helper: note input — dropdown of saved presets + custom entry ─
_NEW_NOTE = "✏️ Type new note..."

def _note_input(model_ref, category, prefix):
    """Selectbox showing saved presets; last option opens a text field.

    Uses a version counter so that after a spend the widget key changes,
    guaranteeing a fresh widget with no previous value.
    """
    ver_key   = f"note_ver_{prefix}_{category}"
    reset_key = f"reset_note_{prefix}_{category}"

    if st.session_state.pop(reset_key, False):
        # Bump the version → completely new widget key → defaults to first option
        st.session_state[ver_key] = st.session_state.get(ver_key, 0) + 1

    ver      = st.session_state.get(ver_key, 0)
    sel_key  = f"nsel_{prefix}_{category}_{ver}"
    cust_key = f"ncustom_{prefix}_{category}_{ver}"

    presets = model_ref.get_preset_notes(category)
    options = [""] + presets + [_NEW_NOTE]

    sel = st.selectbox(
        "Note",
        options,
        key=sel_key,
        format_func=lambda x: "(no note)" if x == "" else x,
    )

    if sel == _NEW_NOTE:
        note = st.text_input(
            "Note", placeholder="Type note…",
            key=cust_key,
            label_visibility="collapsed",
        )
    else:
        note = "" if sel == "" else sel

    # Remove-preset management (shown only when presets exist)
    if presets:
        with st.expander("🗑️ Remove saved notes"):
            for p in list(presets):
                pc1, pc2 = st.columns([5, 1])
                pc1.text(p)
                if pc2.button("✖", key=f"rm_{prefix}_{category}_{p}"):
                    model_ref.remove_preset_note(category, p)
                    st.rerun()

    return note


# ── Helper: transaction table with inline edit / delete ──────────
def _tx_table(transactions, model_ref, category, prefix, limit=100):
    items = list(reversed(transactions[-limit:]))
    if not items:
        st.caption("No transactions yet.")
        return

    # Header stays outside the scroll box
    hdr = st.columns([2, 1, 3, 4, 1, 1])
    for col, lbl in zip(hdr, ["Date", "Type", "Amount", "Note", "", ""]):
        col.caption(lbl)

    # ~5 rows visible; scroll to see the rest
    with st.container(height=255, border=False):
      for t in items:
        dt  = datetime.fromisoformat(t.timestamp)
        uid = f"{prefix}_{t.timestamp.replace(':', '_').replace('.', '_')}"

        row = st.columns([2, 1, 3, 4, 1, 1])
        row[0].text(dt.strftime("%m/%d %H:%M"))
        row[1].text("+" if t.action == "add" else "−")

        amt_str = format_currency(t.amount)
        if t.original_currency and t.original_amount is not None:
            amt_str += f" ({format_currency_for_code(t.original_amount, t.original_currency)})"
        row[2].text(amt_str)
        row[3].text(t.note or "")

        edit_clicked = row[4].button("✏️", key=f"edit_{uid}")
        del_clicked  = row[5].button("🗑️", key=f"del_{uid}")

        if del_clicked:
            model_ref.delete_transaction_by_ref(t)
            st.rerun()

        if edit_clicked:
            st.session_state[f"editing_{uid}"] = not st.session_state.get(
                f"editing_{uid}", False
            )

        if st.session_state.get(f"editing_{uid}"):
            with st.container(border=True):
                ec1, ec2, ec3, ec4, ec5 = st.columns([3, 2, 3, 1, 1])
                new_amt  = ec1.number_input(
                    "New amount", value=float(t.amount),
                    min_value=0.01, step=0.01, key=f"eamt_{uid}",
                )
                new_cur  = ec2.selectbox(
                    "Currency", list(CURRENCIES.keys()),
                    index=list(CURRENCIES.keys()).index(model_ref.currency),
                    key=f"ecur_{uid}",
                )
                new_note = ec3.text_input("Note", value=t.note or "", key=f"enote_{uid}")
                if ec4.button("✔", key=f"esave_{uid}"):
                    converted = convert_currency(new_amt, new_cur, model_ref.currency)
                    orig_c = new_cur if new_cur != model_ref.currency else None
                    orig_a = new_amt if new_cur != model_ref.currency else None
                    model_ref.update_transaction_amount(t, converted, orig_a, orig_c, note=new_note)
                    st.session_state.pop(f"editing_{uid}", None)
                    st.rerun()
                if ec5.button("✖", key=f"ecancel_{uid}"):
                    st.session_state.pop(f"editing_{uid}", None)
                    st.rerun()


# ════════════════════════════════════════════════════════════════════
# MAIN TABS
# ════════════════════════════════════════════════════════════════════
savings_tab, expenses_tab = st.tabs(["💰 Savings", "💸 Expenses"])


# ════════════════════════════════════════════════════════════════════
# SAVINGS TAB
# ════════════════════════════════════════════════════════════════════
with savings_tab:

    # ── Top bar: available balance + return + export ─────────────
    distributable   = model.get_distributable_balance()
    net_transferred = _get_net_transferred()

    cb1, cb2, cb3 = st.columns([3, 2, 1])
    with cb1:
        st.metric("Available to Allocate", format_currency(distributable))
    with cb2:
        if net_transferred > 0:
            with st.expander("↩ Return to Expenses"):
                rc1, rc2, rc3 = st.columns([3, 2, 1])
                ret_amt = rc1.number_input("Amount", min_value=0.01, step=100.0, key="ret_amt")
                ret_cur = rc2.selectbox("Currency", list(CURRENCIES.keys()), index=list(CURRENCIES.keys()).index(model.currency), key="ret_cur")
                if rc3.button("Return →", key="btn_ret"):
                    converted      = convert_currency(ret_amt, ret_cur, model.currency)
                    max_returnable = min(distributable, net_transferred)
                    actual         = min(converted, max_returnable)
                    orig_curr      = ret_cur if ret_cur != model.currency else None
                    orig_amt       = ret_amt if ret_cur != model.currency else None
                    model.add_transaction(
                        amount=actual, action='spend', category=DISTRIBUTABLE_CATEGORY,
                        original_currency=orig_curr, original_amount=orig_amt,
                        note='__transfer_back__',
                    )
                    exp_model.add_transaction(
                        amount=actual, action='add', category=TRANSFER_OUT_CATEGORY,
                        original_currency=orig_curr, original_amount=orig_amt,
                        note='__transfer_back__',
                    )
                    msg = f"Returned {format_currency(actual)} to Expenses"
                    if actual < converted:
                        msg += (
                            f" (reduced to {format_currency(actual)}"
                            " — only this much was originally transferred)"
                        )
                    st.success(msg)
                    st.rerun()
    with cb3:
        _export_button(model, "📥 Export to Excel", "savings_export.xlsx")

    # ── Other Income ──────────────────────────────────────────────
    with st.expander("➕ Add Other Income"):
        c1, c2, c3 = st.columns([3, 2, 1])
        inc_amt = c1.number_input("Amount", min_value=0.01, step=100.0, key="inc_amt")
        inc_cur = c2.selectbox("Currency", list(CURRENCIES.keys()), index=list(CURRENCIES.keys()).index(model.currency), key="inc_cur")
        if c3.button("Add", key="btn_inc"):
            converted = convert_currency(inc_amt, inc_cur, model.currency)
            orig_curr = inc_cur if inc_cur != model.currency else None
            orig_amt  = inc_amt if inc_cur != model.currency else None
            model.add_transaction(
                amount=converted, action='add',
                category=DISTRIBUTABLE_CATEGORY,
                original_currency=orig_curr, original_amount=orig_amt,
            )
            st.success(f"Added {format_currency(converted)} to Available")
            st.rerun()

        # Direct-income history with delete
        direct_txs = [
            t for t in model.transactions
            if t.category == DISTRIBUTABLE_CATEGORY
            and t.action == 'add'
            and t.note != '__transfer__'
        ]
        if direct_txs:
            st.caption("Other income history:")
            for t in reversed(direct_txs[-8:]):
                dt  = datetime.fromisoformat(t.timestamp)
                uid = f"oinc_{t.timestamp.replace(':', '_').replace('.', '_')}"
                dc1, dc2, dc3 = st.columns([3, 4, 1])
                dc1.text(dt.strftime("%m/%d %H:%M"))
                s = format_currency(t.amount)
                if t.original_currency and t.original_amount is not None:
                    s += f" ({format_currency_for_code(t.original_amount, t.original_currency)})"
                dc2.text(s)
                if dc3.button("🗑️", key=f"del_{uid}"):
                    model.delete_transaction_by_ref(t)
                    st.rerun()

    # ── Create new savings category ───────────────────────────────
    with st.expander("➕ New Category"):
        new_cat_name = st.text_input("Category name", key="new_cat_savings")
        if st.button("Create", key="btn_new_cat_savings"):
            name = new_cat_name.strip()
            if not name:
                st.error("Please enter a category name.")
            elif model.add_category(name):
                st.success(f"Category '{name}' created.")
                st.rerun()
            else:
                st.warning(f"'{name}' already exists.")

    # ── Clear All Savings Data ────────────────────────────────────
    with st.expander("🗑️ Clear All Savings Data"):
        st.warning("This will permanently delete ALL savings transactions.")
        if st.checkbox("Yes, I want to clear all savings data", key="confirm_clear_all_savings"):
            if st.button("🗑️ Clear All", key="btn_clear_all_savings", type="primary"):
                model.clear_all_data()
                st.rerun()

    st.divider()

    # ── Per-category sections ─────────────────────────────────────
    for category in model.categories:
        balance      = model.get_category_balance(category)
        transactions = model.get_transactions_by_category(category)

        with st.expander(f"📊 {category}   —   {format_currency(balance)}"):
            left, right = st.columns(2)

            # ── ADD ──────────────────────────────────────────────
            with left:
                st.subheader("Add to Budget")
                add_amt_key = f"add_amt_{category}"
                add_cur_key = f"add_cur_{category}"
                _preset_buttons(add_amt_key)
                add_amt = st.number_input(
                    "Amount", min_value=0.01, step=100.0, key=add_amt_key,
                )
                add_cur = st.selectbox(
                    "Currency", list(CURRENCIES.keys()),
                    index=list(CURRENCIES.keys()).index(model.currency),
                    key=add_cur_key,
                )
                if st.button("Add", key=f"btn_add_{category}"):
                    converted = convert_currency(add_amt, add_cur, model.currency)
                    available = model.get_distributable_balance()
                    if converted > available:
                        st.error(f"Only {format_currency(available)} available to allocate.")
                    else:
                        orig_curr = add_cur if add_cur != model.currency else None
                        orig_amt  = add_amt if add_cur != model.currency else None
                        model.add_transaction(
                            amount=converted, action='add', category=category,
                            original_currency=orig_curr, original_amount=orig_amt,
                        )
                        st.success(f"Added {format_currency(converted)} to {category}")
                        st.rerun()

            # ── SPEND ─────────────────────────────────────────────
            with right:
                st.subheader("Spend from Budget")
                spd_amt_key = f"spd_amt_{category}"
                spd_cur_key = f"spd_cur_{category}"
                _preset_buttons(spd_amt_key)
                spd_amt  = st.number_input(
                    "Amount", min_value=0.01, step=100.0, key=spd_amt_key,
                )
                spd_cur  = st.selectbox(
                    "Currency", list(CURRENCIES.keys()),
                    index=list(CURRENCIES.keys()).index(model.currency),
                    key=spd_cur_key,
                )
                spd_note = _note_input(model, category, "sav")
                if st.button("Spend", key=f"btn_spd_{category}"):
                    converted = convert_currency(spd_amt, spd_cur, model.currency)
                    if converted > balance:
                        st.error(f"Only {format_currency(balance)} in {category}.")
                    else:
                        orig_curr = spd_cur if spd_cur != model.currency else None
                        orig_amt  = spd_amt if spd_cur != model.currency else None
                        model.add_transaction(
                            amount=converted, action='spend', category=category,
                            note=spd_note or None,
                            original_currency=orig_curr, original_amount=orig_amt,
                        )
                        # Auto-save new notes as presets
                        if spd_note and spd_note.strip():
                            model.add_preset_note(category, spd_note.strip())
                        # Flag note input to reset on next render
                        st.session_state[f"reset_note_sav_{category}"] = True
                        st.success(f"Spent {format_currency(converted)} from {category}")
                        st.rerun()

            # ── TRANSACTIONS ─────────────────────────────────────
            st.subheader("Recent Transactions")
            _tx_table(transactions, model, category, f"sav_{category}")

            st.divider()

            # Clear category (keep category, wipe transactions)
            if st.checkbox(
                f"Clear all transactions in '{category}'",
                key=f"confirm_clear_{category}",
            ):
                if st.button(
                    f"🗑️ Clear {category} transactions",
                    key=f"btn_clear_{category}",
                ):
                    model.clear_category(category)
                    st.rerun()

            # Delete category entirely
            if st.checkbox(
                f"I want to delete '{category}' and all its data",
                key=f"confirm_del_savings_{category}",
            ):
                if st.button(
                    f"🗑️ Delete {category}",
                    key=f"btn_del_savings_{category}",
                    type="primary",
                ):
                    model.delete_category(category)
                    st.rerun()


# ════════════════════════════════════════════════════════════════════
# EXPENSES TAB
# ════════════════════════════════════════════════════════════════════
with expenses_tab:

    # ── Summary metrics ───────────────────────────────────────────
    remaining = exp_model.get_total_budget()
    income    = exp_model.get_total_added(exclude_categories=[TRANSFER_OUT_CATEGORY])
    spent     = exp_model.get_total_spent(exclude_categories=[TRANSFER_OUT_CATEGORY])

    net_transferred = _get_net_transferred()

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Remaining",             format_currency(remaining))
    mc2.metric("Total Income",          format_currency(income))
    mc3.metric("Total Spent",           format_currency(spent))
    mc4.metric("Sent to Savings (net)", format_currency(net_transferred))

    exp_export_col = st.columns([4, 1])[1]
    with exp_export_col:
        _export_button(exp_model, "📥 Export to Excel", "expenses_export.xlsx")

    st.divider()

    # ── Add salary / income ───────────────────────────────────────
    with st.expander("💰 Add Salary / Income"):
        c1, c2, c3 = st.columns([3, 2, 1])
        sal_amt = c1.number_input("Amount", min_value=0.01, step=100.0, key="sal_amt")
        sal_cur = c2.selectbox("Currency", list(CURRENCIES.keys()), index=list(CURRENCIES.keys()).index(exp_model.currency), key="sal_cur")
        if c3.button("Add", key="btn_sal"):
            converted = convert_currency(sal_amt, sal_cur, exp_model.currency)
            orig_curr = sal_cur if sal_cur != exp_model.currency else None
            orig_amt  = sal_amt if sal_cur != exp_model.currency else None
            exp_model.add_transaction(
                amount=converted, action='add', category=SALARY_CATEGORY,
                original_currency=orig_curr, original_amount=orig_amt,
            )
            st.success(f"Added {format_currency(converted)} income")
            st.rerun()

        # Salary history with delete
        salary_txs = [t for t in exp_model.transactions if t.category == SALARY_CATEGORY]
        if salary_txs:
            st.caption("Income history:")
            for t in reversed(salary_txs[-8:]):
                dt  = datetime.fromisoformat(t.timestamp)
                uid = f"sal_{t.timestamp.replace(':', '_').replace('.', '_')}"
                sc1, sc2, sc3 = st.columns([3, 4, 1])
                sc1.text(dt.strftime("%m/%d %H:%M"))
                s = format_currency(t.amount)
                if t.original_currency and t.original_amount is not None:
                    s += f" ({format_currency_for_code(t.original_amount, t.original_currency)})"
                sc2.text(s)
                if sc3.button("🗑️", key=f"del_{uid}"):
                    exp_model.delete_transaction_by_ref(t)
                    st.rerun()

    # ── Transfer to savings ───────────────────────────────────────
    with st.expander("↗️ Transfer to Savings"):
        c1, c2, c3 = st.columns([3, 2, 1])
        tr_amt = c1.number_input("Amount", min_value=0.01, step=100.0, key="tr_amt")
        tr_cur = c2.selectbox("Currency", list(CURRENCIES.keys()), index=list(CURRENCIES.keys()).index(exp_model.currency), key="tr_cur")
        if c3.button("Transfer →", key="btn_tr"):
            converted = convert_currency(tr_amt, tr_cur, exp_model.currency)
            if converted > remaining:
                st.error(f"Only {format_currency(remaining)} remaining in Expenses.")
            else:
                orig_curr = tr_cur if tr_cur != exp_model.currency else None
                orig_amt  = tr_amt if tr_cur != exp_model.currency else None
                exp_model.add_transaction(
                    amount=converted, action='spend', category=TRANSFER_OUT_CATEGORY,
                    original_currency=orig_curr, original_amount=orig_amt,
                )
                model.add_transaction(
                    amount=converted, action='add', category=DISTRIBUTABLE_CATEGORY,
                    original_currency=orig_curr, original_amount=orig_amt,
                    note='__transfer__',
                )
                st.success(f"Transferred {format_currency(converted)} to Savings")
                st.rerun()

    # ── Create new expense category ───────────────────────────────
    with st.expander("➕ New Category"):
        new_exp_cat = st.text_input("Category name", key="new_cat_expenses")
        if st.button("Create", key="btn_new_cat_expenses"):
            name = new_exp_cat.strip()
            if not name:
                st.error("Please enter a category name.")
            elif exp_model.add_category(name):
                st.success(f"Category '{name}' created.")
                st.rerun()
            else:
                st.warning(f"'{name}' already exists.")

    # ── Clear All Expense Data ────────────────────────────────────
    with st.expander("🗑️ Clear All Expense Data"):
        st.warning("This will permanently delete ALL expense transactions.")
        if st.checkbox("Yes, I want to clear all expense data", key="confirm_clear_all_expenses"):
            if st.button("🗑️ Clear All", key="btn_clear_all_expenses", type="primary"):
                exp_model.clear_all_data()
                # Also remove linked transfer records from the savings model
                model.clear_category_tagged(DISTRIBUTABLE_CATEGORY, '__transfer__')
                model.clear_category_tagged(DISTRIBUTABLE_CATEGORY, '__transfer_back__')
                st.rerun()

    st.divider()

    # ── Expense categories ────────────────────────────────────────
    for category in exp_model.categories:
        cat_spent    = sum(
            t.amount for t in exp_model.get_transactions_by_category(category)
            if t.action == 'spend'
        )
        transactions = exp_model.get_transactions_by_category(category)

        with st.expander(f"💸 {category}   —   spent {format_currency(cat_spent)}"):
            exp_amt_key = f"exp_amt_{category}"
            exp_cur_key = f"exp_cur_{category}"

            _preset_buttons(exp_amt_key)

            c1, c2 = st.columns([3, 2])
            exp_amt = c1.number_input(
                "Amount", min_value=0.01, step=100.0, key=exp_amt_key,
            )
            exp_cur = c2.selectbox(
                "Currency", list(CURRENCIES.keys()),
                index=list(CURRENCIES.keys()).index(exp_model.currency),
                key=exp_cur_key,
            )
            exp_note = _note_input(exp_model, category, "exp")

            if st.button("Spend", key=f"btn_exp_{category}"):
                converted = convert_currency(exp_amt, exp_cur, exp_model.currency)
                pot       = exp_model.get_total_budget()
                if converted > pot:
                    st.error(f"Only {format_currency(pot)} remaining in Expenses.")
                else:
                    orig_curr = exp_cur if exp_cur != exp_model.currency else None
                    orig_amt  = exp_amt if exp_cur != exp_model.currency else None
                    exp_model.add_transaction(
                        amount=converted, action='spend', category=category,
                        note=exp_note or None,
                        original_currency=orig_curr, original_amount=orig_amt,
                    )
                    # Auto-save new notes as presets
                    if exp_note and exp_note.strip():
                        exp_model.add_preset_note(category, exp_note.strip())
                    # Flag note input to reset on next render
                    st.session_state[f"reset_note_exp_{category}"] = True
                    st.success(f"Recorded {format_currency(converted)} for {category}")
                    st.rerun()

            st.subheader("Recent Transactions")
            _tx_table(transactions, exp_model, category, f"exp_{category}")

            st.divider()

            # Clear category (keep category, wipe transactions)
            if st.checkbox(
                f"Clear all transactions in '{category}'",
                key=f"confirm_eclear_{category}",
            ):
                if st.button(
                    f"🗑️ Clear {category} transactions",
                    key=f"btn_eclear_{category}",
                ):
                    exp_model.clear_category(category)
                    st.rerun()

            # Delete category entirely
            if st.checkbox(
                f"I want to delete '{category}' and all its data",
                key=f"confirm_del_expenses_{category}",
            ):
                if st.button(
                    f"🗑️ Delete {category}",
                    key=f"btn_del_expenses_{category}",
                    type="primary",
                ):
                    exp_model.delete_category(category)
                    st.rerun()
