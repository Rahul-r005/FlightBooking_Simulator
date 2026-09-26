"""Compatibility entrypoint for the SkyBook FastAPI application."""

from flight_booking.api import app
from flight_booking.database import (
    AirlineModel,
    Base,
    BookingModel,
    FareHistoryModel,
    FlightModel,
    PassengerModel,
    PaymentModel,
    SessionLocal,
    engine,
)
from flight_booking.pricing import calculate_dynamic_fare, calculate_legacy_fare
from flight_booking.schemas import (
    BookingIn,
    BookingOut,
    DBBookingRequest,
    DBBookingResponse,
    DBFlightResponse,
    Flight,
    FlightOut,
)

__all__ = [
    "app",
    "Base",
    "engine",
    "SessionLocal",
    "AirlineModel",
    "FlightModel",
    "PassengerModel",
    "BookingModel",
    "PaymentModel",
    "FareHistoryModel",
    "UserModel",
    "SessionModel",
    "NotificationModel",
    "Flight",
    "FlightOut",
    "BookingIn",
    "BookingOut",
    "DBBookingRequest",
    "DBBookingResponse",
    "DBFlightResponse",
    "calculate_dynamic_fare",
    "calculate_legacy_fare",
]
