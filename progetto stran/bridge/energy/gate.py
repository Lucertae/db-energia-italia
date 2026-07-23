"""Gate timing for PWR-01 v2 — signal snapshot at D-1 ~10:30 UTC."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def gate_hour_key(
    delivery_hour_key: str,
    *,
    gate_hour_utc: int = 10,
    gate_minute_utc: int = 30,
) -> str:
    """Map delivery hour YYYY-MM-DDTHH to OM/published snapshot bucket at gate (D-1).

    Hourly caches use UTC hour buckets; 10:30 maps to the 10:00–11:00 bucket.
    """
    try:
        delivery = datetime.strptime(delivery_hour_key[:13], "%Y-%m-%dT%H").replace(tzinfo=timezone.utc)
    except ValueError:
        return delivery_hour_key[:13]
    gate_day = (delivery - timedelta(days=1)).date()
    if gate_minute_utc >= 30:
        gate_h = gate_hour_utc
    else:
        gate_h = max(0, gate_hour_utc - 1) if gate_hour_utc > 0 else 23
    gate = datetime(gate_day.year, gate_day.month, gate_day.day, gate_h, 0, tzinfo=timezone.utc)
    return gate.strftime("%Y-%m-%dT%H")


def delivery_hours_in_range(
    start_hk: str,
    end_hk: str,
) -> list[str]:
    """Inclusive list of delivery hour keys between two YYYY-MM-DDTHH keys."""
    start = datetime.strptime(start_hk[:13], "%Y-%m-%dT%H").replace(tzinfo=timezone.utc)
    end = datetime.strptime(end_hk[:13], "%Y-%m-%dT%H").replace(tzinfo=timezone.utc)
    out: list[str] = []
    cur = start
    while cur <= end:
        out.append(cur.strftime("%Y-%m-%dT%H"))
        cur += timedelta(hours=1)
    return out
