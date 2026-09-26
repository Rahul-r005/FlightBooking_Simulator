from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .auth import require_admin
from .booking_service import cancel_booking
from .database import BookingModel, FlightModel, PassengerModel, UserModel, SessionLocal
from .notifications import booking_cancelled_message, create_notification
from .schemas import (
    AdminAccountResponse,
    AdminAccountStatusUpdate,
    AdminBookingCancellationResponse,
    AdminBookingResponse,
    AdminBookingUpdate,
    UserResponse,
)

router = APIRouter(prefix="/admin", tags=["administration"])


def _account_response(db: Session, user: UserModel) -> AdminAccountResponse:
    booking_count = db.query(BookingModel).filter(BookingModel.user_id == user.user_id).count()
    return AdminAccountResponse(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        suspended=user.suspended,
        booking_count=booking_count,
    )


def _booking_response(booking: BookingModel) -> AdminBookingResponse:
    passenger = booking.passenger
    flight = booking.flight
    return AdminBookingResponse(
        booking_id=booking.booking_id,
        pnr=booking.pnr,
        flight_id=booking.flight_id,
        passenger_id=booking.passenger_id,
        user_id=booking.user_id,
        seat_number=booking.seat_number,
        price_per_seat=float(booking.price_per_seat or 0),
        total_price=float(booking.total_price or 0),
        status=booking.status,
        booking_date=booking.booking_date,
        passenger_name=passenger.full_name if passenger else "",
        passenger_email=passenger.email if passenger else None,
        flight_number=flight.flight_number if flight else "",
        source=flight.source if flight else "",
        destination=flight.destination if flight else "",
        departure_time=flight.departure_time if flight else booking.booking_date,
    )


@router.get("/accounts", response_model=list[AdminAccountResponse])
def list_accounts(
    q: str | None = Query(None),
    admin: UserModel = Depends(require_admin),
):
    db = SessionLocal()
    try:
        query = db.query(UserModel)
        if q:
            term = f"%{q.strip().lower()}%"
            query = query.filter(
                or_(
                    func.lower(UserModel.email).like(term),
                    func.lower(UserModel.full_name).like(term),
                )
            )
        return [
            _account_response(db, user)
            for user in query.order_by(UserModel.created_at.desc()).all()
        ]
    finally:
        db.close()


@router.get("/accounts/{user_id}", response_model=AdminAccountResponse)
def account_detail(user_id: int, admin: UserModel = Depends(require_admin)):
    db = SessionLocal()
    try:
        user = db.get(UserModel, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Account not found.")
        return _account_response(db, user)
    finally:
        db.close()


@router.get("/accounts/{user_id}/bookings", response_model=list[AdminBookingResponse])
def account_bookings(user_id: int, admin: UserModel = Depends(require_admin)):
    db = SessionLocal()
    try:
        if not db.get(UserModel, user_id):
            raise HTTPException(status_code=404, detail="Account not found.")
        bookings = (
            db.query(BookingModel)
            .filter(BookingModel.user_id == user_id)
            .order_by(BookingModel.booking_date.desc())
            .all()
        )
        return [_booking_response(booking) for booking in bookings]
    finally:
        db.close()


@router.patch("/accounts/{user_id}/status", response_model=UserResponse)
def update_account_status(
    user_id: int,
    request: AdminAccountStatusUpdate,
    admin: UserModel = Depends(require_admin),
):
    if user_id == admin.user_id and request.suspended:
        raise HTTPException(status_code=400, detail="You cannot suspend your own administrator account.")

    db = SessionLocal()
    try:
        user = db.get(UserModel, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Account not found.")
        user.suspended = request.suspended
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


@router.get("/bookings", response_model=list[AdminBookingResponse])
def list_bookings(
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
    date: str | None = Query(None),
    admin: UserModel = Depends(require_admin),
):
    db = SessionLocal()
    try:
        query = db.query(BookingModel).join(FlightModel)
        now = datetime.utcnow()
        normalized = (status_filter or "").lower()
        if normalized == "cancelled":
            query = query.filter(BookingModel.status == "Cancelled")
        elif normalized == "upcoming":
            query = query.filter(
                BookingModel.status == "Confirmed",
                FlightModel.departure_time >= now,
            )
        elif normalized == "past":
            query = query.filter(
                FlightModel.departure_time < now,
                BookingModel.status != "Cancelled",
            )

        if search:
            term = f"%{search.strip().lower()}%"
            query = query.join(
                PassengerModel,
                BookingModel.passenger_id == PassengerModel.passenger_id,
            ).filter(
                or_(
                    func.lower(BookingModel.pnr).like(term),
                    func.lower(PassengerModel.full_name).like(term),
                    func.lower(PassengerModel.email).like(term),
                )
            )

        if date:
            try:
                target = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format (YYYY-MM-DD).",
                ) from exc
            query = query.filter(func.date(FlightModel.departure_time) == target)

        bookings = query.order_by(BookingModel.booking_date.desc()).limit(500).all()
        return [_booking_response(booking) for booking in bookings]
    finally:
        db.close()


@router.patch("/bookings/{pnr}", response_model=AdminBookingResponse)
def update_booking(
    pnr: str,
    request: AdminBookingUpdate,
    admin: UserModel = Depends(require_admin),
):
    db = SessionLocal()
    try:
        booking = db.query(BookingModel).filter(BookingModel.pnr == pnr).first()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found.")
        if request.seat_number is not None:
            seat = request.seat_number.strip().upper()
            if not seat:
                raise HTTPException(status_code=400, detail="Seat number cannot be empty.")
            booking.seat_number = seat
        if request.status is not None:
            if request.status not in {"Confirmed", "Cancelled"}:
                raise HTTPException(status_code=400, detail="Status must be Confirmed or Cancelled.")
            booking.status = request.status
        db.commit()
        db.refresh(booking)
        return _booking_response(booking)
    finally:
        db.close()


@router.post("/bookings/{pnr}/cancel", response_model=AdminBookingCancellationResponse)
def cancel_booking_as_admin(
    pnr: str,
    admin: UserModel = Depends(require_admin),
):
    db = SessionLocal()
    try:
        booking = (
            db.query(BookingModel)
            .filter(BookingModel.pnr == pnr)
            .with_for_update()
            .first()
        )
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found.")

        notification_created = cancel_booking(db, booking, notify_user=True)
        db.commit()
        return AdminBookingCancellationResponse(
            message="Booking cancelled and the customer has been notified.",
            pnr=pnr,
            notification_created=notification_created,
        )
    finally:
        db.close()
