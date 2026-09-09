"""Money and billing boundary-condition tests."""

from decimal import Decimal

import pytest

from app.utils.money import format_money, prorate_money, round_money, split_money


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("10.004", Decimal("10.00")),
        ("10.005", Decimal("10.01")),
        ("-10.005", Decimal("-10.01")),
    ],
)
def test_round_money_uses_half_up_for_fractional_cents(value: str, expected: Decimal) -> None:
    assert round_money(value) == expected


def test_prorate_money_rounds_fractional_cent_after_decimal_arithmetic() -> None:
    # 10.00 * 1 / 6 = 1.666..., which must become 1.67 rather than 1.66.
    assert prorate_money(Decimal("10.00"), 1, 6) == Decimal("1.67")


def test_split_money_preserves_rounded_total_and_distributes_remainder() -> None:
    result = split_money(Decimal("10.00"), 3)

    assert result == [Decimal("3.34"), Decimal("3.33"), Decimal("3.33")]
    assert sum(result, Decimal("0")) == Decimal("10.00")


def test_split_money_handles_negative_remainder() -> None:
    result = split_money(Decimal("-10.01"), 3)

    assert result == [Decimal("-3.33"), Decimal("-3.34"), Decimal("-3.34")]
    assert sum(result, Decimal("0")) == Decimal("-10.01")


def test_format_money_is_deterministic_and_cent_precise() -> None:
    assert format_money("1234.565") == "$1,234.57"
    assert format_money(Decimal("-12"), currency="€") == "-€12.00"


def test_money_helpers_reject_float_inputs() -> None:
    with pytest.raises(TypeError):
        round_money(10.005)  # type: ignore[arg-type]
