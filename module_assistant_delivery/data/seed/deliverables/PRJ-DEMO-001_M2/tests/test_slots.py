from datetime import datetime

from src.slots import MAX_ORDERS_PER_SLOT, slot_is_open


def test_full_slot_is_closed():
    start = datetime(2026, 11, 3, 9, 0)
    assert not slot_is_open(start, datetime(2026, 11, 3, 6, 0), MAX_ORDERS_PER_SLOT)


def test_slot_open_with_capacity():
    start = datetime(2026, 11, 3, 9, 0)
    assert slot_is_open(start, datetime(2026, 11, 3, 6, 0), 3)
