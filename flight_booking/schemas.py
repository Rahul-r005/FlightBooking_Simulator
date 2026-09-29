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
    cabin_class: str = Field(default="Economy", pattern="^(?i:economy|premium)$")
    passenger_name: str = Field(..., min_length=2)
    passenger_email: Optional[EmailStr] = None
    passenger_phone: Optional[str] = None
    seat_number: Optional[str] = None
    force_payment_success: Optional[bool] = None


class SeatMapResponse(BaseModel):
    flight_id: int
    total_seats: int
    premium_start_row: int
    booked_seats: list[str]


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
    user_id: Optional[int]
    seat_number: Optional[str]
    cabin_class: str
    price_per_seat: float
    total_price: float
    status: str
    booking_date: datetime

    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class ProfileUpdateRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class PreferencesUpdateRequest(BaseModel):
    notifications_enabled: bool


class UserResponse(BaseModel):
    user_id: int
    email: EmailStr
    full_name: str
    role: str
    suspended: bool
    notifications_enabled: bool

    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(BaseModel):
    notification_id: int
    message: str
    booking_id: Optional[int]
    created_at: datetime
    read: bool

    model_config = ConfigDict(from_attributes=True)


class AdminAccountResponse(UserResponse):
    booking_count: int


class AdminAccountStatusUpdate(BaseModel):
    suspended: bool


class AdminBookingResponse(DBBookingResponse):
    passenger_name: str
    passenger_email: Optional[EmailStr]
    flight_number: str
    source: str
    destination: str
    departure_time: datetime


class AdminBookingCancellationResponse(BaseModel):
    message: str
    pnr: str
    notification_created: bool


class AdminBookingCreate(BaseModel):
    flight_id: int
    cabin_class: str = Field(default="Economy", pattern="^(?i:economy|premium)$")
    passenger_name: str = Field(..., min_length=2, max_length=100)
    passenger_email: Optional[EmailStr] = None
    passenger_phone: Optional[str] = None
    user_id: Optional[int] = None
    user_email: Optional[EmailStr] = None
    seat_number: str = Field(..., min_length=2, max_length=5)


class AdminBookingUpdate(BaseModel):
    seat_number: Optional[str] = None
    passenger_name: Optional[str] = None
    passenger_email: Optional[EmailStr] = None
    total_price: Optional[float] = None


class AdminFlightUpdate(BaseModel):
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    total_seats: Optional[int] = Field(None, ge=1, le=1000)


class AdminFlightResponse(BaseModel):
    flight_id: int
    airline: str
    flight_number: str
    source: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    total_seats: int
    available_seats: int
    active_bookings: int


class AdminTimelineResponse(BaseModel):
    timeline_id: int
    booking_id: Optional[int]
    pnr: str
    action: str
    details: str
    created_at: datetime
    admin_user_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class AdminRoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(user|admin)$")
