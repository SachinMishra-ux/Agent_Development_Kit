"""Sample Order & Payment Calculation Service (Target Software for Testing)."""

from typing import List, Dict, Optional


def calculate_subtotal(items: List[Dict[str, float]]) -> float:
    """Calculates sum of item prices in a cart."""
    if not items:
        return 0.0
    return sum(item.get("price", 0.0) * item.get("quantity", 1) for item in items)


def apply_discount(subtotal: float, discount_percent: float) -> float:
    """Applies a discount percentage to subtotal.
    
    Expected constraints:
    - discount_percent must be between 0 and 100
    - subtotal cannot be negative
    
    NOTE: Intentional bug for testing agent:
    Does NOT raise ValueError when discount_percent < 0 or discount_percent > 100!
    """
    # Intentional bug: Missing boundary check:
    # if discount_percent < 0 or discount_percent > 100:
    #     raise ValueError("Discount must be between 0 and 100")
    discount_amount = subtotal * (discount_percent / 100.0)
    return round(subtotal - discount_amount, 2)


def calculate_tax(amount: float, tax_rate: float = 0.08) -> float:
    """Calculates tax based on the tax rate (default 8%)."""
    if amount < 0:
        raise ValueError("Amount cannot be negative")
    return round(amount * tax_rate, 2)


def calculate_order_total(items: List[Dict[str, float]], discount_percent: float = 0.0, tax_rate: float = 0.08) -> float:
    """Calculates final order total after discount and tax."""
    subtotal = calculate_subtotal(items)
    discounted = apply_discount(subtotal, discount_percent)
    tax = calculate_tax(discounted, tax_rate)
    return round(discounted + tax, 2)


def split_bill_among_people(total_amount: float, num_people: int) -> float:
    """Splits a total bill among friends.
    
    Intentional bug for testing:
    Does not guard against num_people <= 0 (causes ZeroDivisionError).
    """
    return round(total_amount / num_people, 2)
