"""Order placement (synthetic demo deliverable, corrected version v2)."""

from .mailer import send_email
from .slots import slot_is_open


def place_order(db, customer, cart, shop_id, slot_start, now):
    orders_in_slot = db.count("orders", {"shop_id": shop_id, "slot_start": slot_start})
    if not slot_is_open(slot_start, now, orders_in_slot):
        raise ValueError("This pickup slot is full or closed.")
    order_id = db.insert("orders", {"customer_id": customer.id, "shop_id": shop_id, "slot_start": slot_start, "items": cart})
    # REQ-004: confirmation email with order number, shop and slot, sent synchronously right after insert.
    send_email(customer.email, f"Order {order_id} confirmed",
               f"Order {order_id}: pickup at shop {shop_id}, slot {slot_start:%Y-%m-%d %H:%M}.")
    return order_id


def cancel_order(db, order, now):
    """REQ-006: cancellation is allowed up to 3 hours before the pickup slot."""
    if (order.slot_start - now).total_seconds() < 3 * 3600:
        raise ValueError("Orders can be cancelled up to 3 hours before pickup.")
    db.update("orders", order.id, {"status": "cancelled"})
