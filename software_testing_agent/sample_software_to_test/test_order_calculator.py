"""Test suite for order_calculator.py (Executed by Software Testing Agent)."""

import pytest
from software_testing_agent.sample_software_to_test.order_calculator import (
    calculate_subtotal,
    apply_discount,
    calculate_tax,
    calculate_order_total,
    split_bill_among_people,
)


def test_calculate_subtotal_happy_path():
    items = [
        {"price": 10.0, "quantity": 2},
        {"price": 5.0, "quantity": 1},
    ]
    assert calculate_subtotal(items) == 25.0


def test_calculate_subtotal_empty():
    assert calculate_subtotal([]) == 0.0


def test_calculate_tax_normal():
    assert calculate_tax(100.0, 0.10) == 10.0


def test_calculate_tax_negative_raises_error():
    with pytest.raises(ValueError):
        calculate_tax(-50.0)


def test_apply_discount_invalid_percent_raises():
    """This test expects ValueError when discount is > 100 or < 0.
    In the buggy order_calculator.py, this will FAIL, demonstrating
    the Software Testing Agent's failure detection and root-cause analysis!
    """
    with pytest.raises(ValueError, match="Discount must be between 0 and 100"):
        apply_discount(100.0, 150.0)
