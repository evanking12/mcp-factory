"""
Contoso Customer Service — Python Module
Handles customer lookups, order management, and support ticket operations.
"""

from typing import Optional


def echo_sentinel(sentinel: str) -> str:
    """Echo a deterministic sentinel for MCP E2E validation."""
    return sentinel


def get_customer(customer_id: str) -> dict:
    """Retrieve a customer record by their unique identifier.

    Args:
        customer_id: The unique customer ID (e.g. 'CUST-1234').

    Returns:
        Dict with keys: id, name, email, phone, tier, loyalty_points.
    """
    pass


def create_order(customer_id: str, items: list, shipping_address: str, coupon_code: Optional[str] = None) -> str:
    """Place a new order for a customer.

    Args:
        customer_id: Customer placing the order.
        items: List of dicts with product_sku and quantity.
        shipping_address: Delivery address string.
        coupon_code: Optional promotional coupon.

    Returns:
        New order ID string (e.g. 'ORD-987654').
    """
    pass


def submit_support_ticket(customer_id: str, subject: str, body: str, priority: str = "normal") -> int:
    """Open a new customer support ticket.

    Args:
        customer_id: Affected customer.
        subject: Brief description of the issue.
        body: Full issue description.
        priority: One of 'low', 'normal', 'high', 'urgent'.

    Returns:
        Integer ticket ID.
    """
    pass


def get_order_status(order_id: str) -> str:
    """Get the current fulfilment status of an order.

    Returns one of: pending, processing, shipped, delivered, cancelled.
    """
    pass


def refund_order(order_id: str, reason: str, partial_amount: Optional[float] = None) -> bool:
    """Initiate a refund for a completed or shipped order.

    Args:
        order_id: The order to refund.
        reason: Short reason description for the audit log.
        partial_amount: If omitted, a full refund is issued.

    Returns:
        True if the refund was accepted by the payment gateway.
    """
    pass


def update_customer_email(customer_id: str, new_email: str) -> bool:
    """Update the primary email address on a customer account."""
    pass


def get_loyalty_balance(customer_id: str) -> int:
    """Return the current loyalty point balance for a customer."""
    pass


def redeem_loyalty_points(customer_id: str, points: int, reward_id: str) -> bool:
    """Redeem loyalty points for a given reward catalogue item."""
    pass
