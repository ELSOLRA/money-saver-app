from typing import Optional


def format_currency(amount: float, currency_symbol: str = '$') -> str:
    """Format a number as currency string."""
    return f"{currency_symbol}{amount:,.2f}"


def parse_amount(value: str) -> Optional[float]:
    """
    Parse a string value to float amount.
    Returns None if parsing fails.
    """
    try:
        # Remove common currency symbols and whitespace
        cleaned = value.strip().replace('$', '').replace(',', '').replace(' ', '')
        if not cleaned:
            return None
        amount = float(cleaned)
        return amount if amount > 0 else None
    except ValueError:
        return None


def truncate_text(text: str, max_length: int = 30) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + '...'