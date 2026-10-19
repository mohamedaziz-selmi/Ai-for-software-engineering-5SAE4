"""Pickup slot booking rules (synthetic demo deliverable, corrected version v2)."""

from datetime import datetime, timedelta

SLOT_MINUTES = 15
MAX_ORDERS_PER_SLOT = 20  # NN-1: at most 20 orders per 15-minute slot
BOOKING_CLOSES_BEFORE = timedelta(hours=2)  # NN-1: booking closes 2 hours before the slot starts


def slot_is_open(slot_start: datetime, now: datetime, orders_in_slot: int) -> bool:
    """A slot can be chosen while it has capacity and booking has not closed."""
    if orders_in_slot >= MAX_ORDERS_PER_SLOT:
        return False
    return now <= slot_start - BOOKING_CLOSES_BEFORE


def slots_for_day(day: datetime, opening_hour: int = 7, closing_hour: int = 19) -> list[datetime]:
    start = day.replace(hour=opening_hour, minute=0, second=0, microsecond=0)
    count = (closing_hour - opening_hour) * 60 // SLOT_MINUTES
    return [start + timedelta(minutes=SLOT_MINUTES * i) for i in range(count)]
