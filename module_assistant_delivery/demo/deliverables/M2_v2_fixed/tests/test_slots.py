from datetime import datetime

from src.slots import MAX_ORDERS_PER_SLOT, slot_is_open


def test_capacity_is_20():
    assert MAX_ORDERS_PER_SLOT == 20


def test_full_slot_is_closed():
    start = datetime(2026, 11, 3, 9, 0)
    assert not slot_is_open(start, datetime(2026, 11, 3, 6, 0), 20)


def test_slot_open_with_capacity():
    start = datetime(2026, 11, 3, 9, 0)
    assert slot_is_open(start, datetime(2026, 11, 3, 6, 0), 19)


def test_booking_closes_two_hours_before():
    start = datetime(2026, 11, 3, 9, 0)
    assert slot_is_open(start, datetime(2026, 11, 3, 7, 0), 0)
    assert not slot_is_open(start, datetime(2026, 11, 3, 7, 1), 0)
