from datetime import datetime, timezone
import random
import string

from .database import FlightModel
from .schemas import Flight


def calculate_legacy_fare(flight: Flight) -> float:
    remaining_ratio = flight.available_seats / max(flight.total_seats, 1)
    hours_to_departure = max(
        (flight.departure_time - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds() / 3600,
        0,
    )

    demand_factor = 1 + (flight.demand / 100)
    seat_factor = 1.5 if remaining_ratio < 0.3 else 1.0
    time_factor = 1.3 if hours_to_departure < 12 else 1.0
    tier_factor = {"economy": 0.9, "standard": 1.0, "premium": 1.2}.get(
        flight.pricing_tier, 1.0
    )

    return round(
        flight.base_fare * demand_factor * seat_factor * time_factor * tier_factor,
        2,
    )


def calculate_dynamic_fare(flight: FlightModel) -> float:
    base_fare = float(flight.base_fare or 3000.0)
    demand = float(flight.simulated_demand or 50.0)
    demand_factor = 0.8 + (demand / 100.0) * 0.8

    remaining_percent = (flight.available_seats / max(flight.total_seats, 1)) * 100
    if remaining_percent <= 10:
        seat_factor = 2.0
    elif remaining_percent <= 30:
        seat_factor = 1.4
    elif remaining_percent <= 60:
        seat_factor = 1.0
    else:
        seat_factor = 0.9

    hours_to_departure = max(
        (flight.departure_time - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds() / 3600.0,
        0.0,
    )
    if hours_to_departure <= 6:
        time_factor = 1.5
    elif hours_to_departure <= 24:
        time_factor = 1.2
    elif hours_to_departure <= 72:
        time_factor = 1.0
    else:
        time_factor = 0.85

    tier_factor = {"standard": 1.0, "economy": 0.95, "premium": 1.35}.get(
        (flight.pricing_tier or "standard").lower(),
        1.0,
    )
    return round(base_fare * demand_factor * seat_factor * time_factor * tier_factor, 2)


def generate_pnr(length: int = 6) -> str:
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
    timestamp = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%m%d%H%M%S")
    return f"{code}{timestamp}"
