from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Flight(BaseModel):
    flight_id: int
    airline: str
    flight_number: str
    source: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    total_seats: int
    available_seats: int
    base_fare: float
    pricing_tier: str
    demand: int


class FlightOut(BaseModel):
    flight_id: int
    airline: str
    flight_number: str
    source: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    total_seats: int
    available_seats: int
    duration_minutes: int
    dynamic_price: float
    pricing_tier: str


class BookingIn(BaseModel):
    flight_id: int
    passenger_name: str
    seats: int


class BookingOut(BaseModel):
    booking_id: int
    flight_id: int
    passenger_name: str
    seats: int
    price_per_seat: float
    total_price: float
    status: str


class DBBookingRequest(BaseModel):
    flight_id: int
    passenger_name: str = Field(..., min_length=2)
    passenger_email: Optional[EmailStr] = None
    passenger_phone: Optional[str] = None
    seat_number: Optional[str] = None
    force_payment_success: Optional[bool] = None


class DBFlightResponse(BaseModel):
    flight_id: int
    airline: str
    flight_number: str
    source: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    total_seats: int
    available_seats: int
    duration_minutes: int
    dynamic_price: float
    base_fare: float
    pricing_tier: str
    demand: int


class DBBookingResponse(BaseModel):
    booking_id: int
    pnr: str
    flight_id: int
    passenger_id: int
    seat_number: Optional[str]
    price_per_seat: float
    total_price: float
    status: str
    booking_date: datetime

    model_config = ConfigDict(from_attributes=True)
