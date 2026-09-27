"""Decimal-safe helpers for currency calculations.

Money enters and leaves the application as decimal values.  These helpers keep
all arithmetic in :class:`~decimal.Decimal`, round with the conventional
half-up rule, and make allocation sums deterministic at cent precision.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
type MoneyValue = Decimal | int | str


def _decimal(value: MoneyValue, *, name: str) -> Decimal:
    """Convert a supported money input without allowing binary floats."""
    if isinstance(value, bool | float):
        raise TypeError(f"{name} must be a Decimal, integer, or decimal string")
    try:
        converted = Decimal(value)
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise TypeError(f"{name} must be a Decimal, integer, or decimal string") from exc
    if not converted.is_finite():
        raise ValueError(f"{name} must be finite")
    return converted


def round_money(amount: MoneyValue) -> Decimal:
    """Round ``amount`` to cents using ``ROUND_HALF_UP``."""
    return _decimal(amount, name="amount").quantize(CENT, rounding=ROUND_HALF_UP)


def prorate_money(amount: MoneyValue, numerator: MoneyValue, denominator: MoneyValue) -> Decimal:
    """Return a cent-rounded fraction of ``amount``.

    ``numerator`` is the consumed portion (for example, occupied days) and
    ``denominator`` is the full period.  The denominator must be positive and
    the numerator cannot be negative.
    """
    total = _decimal(amount, name="amount")
    part = _decimal(numerator, name="numerator")
    whole = _decimal(denominator, name="denominator")
    if part < 0:
        raise ValueError("numerator must be non-negative")
    if whole <= 0:
        raise ValueError("denominator must be positive")
    return (total * part / whole).quantize(CENT, rounding=ROUND_HALF_UP)


def split_money(amount: MoneyValue, parts: int) -> list[Decimal]:
    """Split ``amount`` into ``parts`` cent-precise values whose sum is exact.

    Any leftover cents are assigned one at a time from left to right.  This is
    deterministic and works for negative amounts as well as positive amounts.
    """
    if isinstance(parts, bool) or not isinstance(parts, int) or parts <= 0:
        raise ValueError("parts must be a positive integer")

    total = round_money(amount)
    cents = int(total * 100)
    base, remainder = divmod(cents, parts)
    return [Decimal(base + (1 if index < remainder else 0)) / 100 for index in range(parts)]


def format_money(
    amount: MoneyValue,
    currency: str = "$",
    *,
    currency_symbol: str | None = None,
) -> str:
    """Format a value as a two-decimal amount with thousands separators."""
    symbol = currency if currency_symbol is None else currency_symbol
    rounded = round_money(amount)
    sign = "-" if rounded < 0 else ""
    return f"{sign}{symbol}{abs(rounded):,.2f}"


# Descriptive aliases for callers that use domain-specific terminology.
quantize_money = round_money
prorate = prorate_money
split_amount = split_money
format_currency = format_money


__all__ = [
    "CENT",
    "MoneyValue",
    "format_currency",
    "format_money",
    "prorate",
    "prorate_money",
    "quantize_money",
    "round_money",
    "split_amount",
    "split_money",
]
