from datetime import datetime
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .auth import require_admin
from .booking_service import cancel_booking
from .pricing import generate_pnr
from .database import (
    AdminTimelineModel,
    AirlineModel,
    BookingModel,
    FlightModel,
    PassengerModel,
    PaymentModel,
    NotificationModel,
    UserModel,
    SessionLocal,
    SessionModel,
)

from .notifications import booking_cancelled_message, create_notification
from .schemas import (
    AdminAccountResponse,
    AdminAccountStatusUpdate,
    AdminBookingCancellationResponse,
    AdminBookingCreate,
    AdminBookingResponse,
    AdminBookingUpdate,
    AdminFlightResponse,
    AdminFlightUpdate,
    AdminTimelineResponse,
    AdminRoleUpdate,
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
        notifications_enabled=user.notifications_enabled,
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


@router.delete("/accounts/{user_id}")
def delete_account(user_id: int, admin: UserModel = Depends(require_admin)):
    """Permanently delete a customer/admin account and its owned booking data."""
    if user_id == admin.user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own administrator account.")

    db = SessionLocal()
    try:
        user = db.get(UserModel, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Account not found.")

        bookings = db.query(BookingModel).filter(BookingModel.user_id == user_id).all()
        booking_ids = [booking.booking_id for booking in bookings]
        passenger_ids = {
            booking.passenger_id
            for booking in bookings
            if booking.passenger_id is not None
        }

        # Return seats for active bookings. Cancelled bookings have already
        # returned their seats when cancellation was performed.
        for booking in bookings:
            if booking.status != "Cancelled":
                flight = db.get(FlightModel, booking.flight_id)
                if flight:
                    flight.available_seats = min(
                        flight.total_seats,
                        flight.available_seats + 1,
                    )

        if booking_ids:
            db.query(PaymentModel).filter(
                PaymentModel.booking_id.in_(booking_ids)
            ).delete(synchronize_session=False)
            db.query(NotificationModel).filter(
                NotificationModel.booking_id.in_(booking_ids)
            ).delete(synchronize_session=False)
            db.query(AdminTimelineModel).filter(
                AdminTimelineModel.booking_id.in_(booking_ids)
            ).delete(synchronize_session=False)
            db.query(BookingModel).filter(
                BookingModel.booking_id.in_(booking_ids)
            ).delete(synchronize_session=False)

        # Remove sessions so the deleted account cannot continue using an
        # existing login token.
        db.query(SessionModel).filter(
            SessionModel.user_id == user_id
        ).delete(synchronize_session=False)

        # Keep audit history created by this administrator, but detach it
        # from the deleted user account.
        db.query(AdminTimelineModel).filter(
            AdminTimelineModel.admin_user_id == user_id
        ).update(
            {AdminTimelineModel.admin_user_id: None},
            synchronize_session=False,
        )

        db.delete(user)
        db.flush()

        # Passenger records are owned by booking records. Delete only those
        # no longer referenced by any remaining booking.
        for passenger_id in passenger_ids:
            still_used = db.query(BookingModel.booking_id).filter(
                BookingModel.passenger_id == passenger_id
            ).first()
            if not still_used:
                db.query(PassengerModel).filter(
                    PassengerModel.passenger_id == passenger_id
                ).delete(synchronize_session=False)

        db.commit()
        return {
            "message": "Account and its booking details were permanently deleted.",
            "deleted_bookings": len(booking_ids),
        }
    except Exception:
        db.rollback()
        raise
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


@router.patch("/accounts/{user_id}/role", response_model=AdminAccountResponse)
def update_account_role(
    user_id: int,
    request: AdminRoleUpdate,
    admin: UserModel = Depends(require_admin),
):
    db = SessionLocal()
    try:
        user = db.get(UserModel, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Account not found.")
        if user.user_id == admin.user_id and request.role != "admin":
            raise HTTPException(status_code=400, detail="You cannot remove your own administrator role.")
        if user.role == request.role:
            return _account_response(db, user)
        user.role = request.role
        db.commit()
        db.refresh(user)
        return _account_response(db, user)
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



@router.delete("/bookings/cancelled")
def clear_cancelled_bookings(admin: UserModel = Depends(require_admin)):
    """
    Permanently remove all cancelled booking records and their related details.
    Cancellation already returns each seat to inventory, so no seat counts are
    changed during this cleanup operation.
    """
    db = SessionLocal()
    try:
        cancelled = db.query(BookingModel).filter(BookingModel.status == "Cancelled").all()
        if not cancelled:
            return {"message": "No cancelled bookings found.", "deleted_count": 0}

        booking_ids = [booking.booking_id for booking in cancelled]
        passenger_ids = {
            booking.passenger_id
            for booking in cancelled
            if booking.passenger_id is not None
        }

        db.query(PaymentModel).filter(
            PaymentModel.booking_id.in_(booking_ids)
        ).delete(synchronize_session=False)
        db.query(NotificationModel).filter(
            NotificationModel.booking_id.in_(booking_ids)
        ).delete(synchronize_session=False)
        db.query(AdminTimelineModel).filter(
            AdminTimelineModel.booking_id.in_(booking_ids)
        ).delete(synchronize_session=False)
        db.query(BookingModel).filter(
            BookingModel.booking_id.in_(booking_ids)
        ).delete(synchronize_session=False)

        # Passenger rows are booking details too. Remove only passengers that
        # are no longer referenced by any remaining booking.
        for passenger_id in passenger_ids:
            still_used = db.query(BookingModel.booking_id).filter(
                BookingModel.passenger_id == passenger_id
            ).first()
            if not still_used:
                db.query(PassengerModel).filter(
                    PassengerModel.passenger_id == passenger_id
                ).delete(synchronize_session=False)

        db.commit()
        return {
            "message": "Cancelled booking details were permanently removed.",
            "deleted_count": len(booking_ids),
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.get("/flights", response_model=list[AdminFlightResponse])
def admin_flights(admin: UserModel = Depends(require_admin)):
    db = SessionLocal()
    try:
        flights = db.query(FlightModel).order_by(FlightModel.departure_time.asc()).all()
        return [
            AdminFlightResponse(
                flight_id=f.flight_id,
                airline=f.airline.airline_name if f.airline else "Unknown",
                flight_number=f.flight_number,
                source=f.source,
                destination=f.destination,
                departure_time=f.departure_time,
                arrival_time=f.arrival_time,
                total_seats=f.total_seats,
                available_seats=f.available_seats,
                active_bookings=sum(1 for b in f.bookings if b.status != "Cancelled"),
            )
            for f in flights
        ]
    finally:
        db.close()


@router.patch("/flights/{flight_id}", response_model=AdminFlightResponse)
def update_flight(
    flight_id: int,
    request: AdminFlightUpdate,
    admin: UserModel = Depends(require_admin),
):
    db = SessionLocal()
    try:
        flight = db.get(FlightModel, flight_id)
        if not flight:
            raise HTTPException(status_code=404, detail="Flight not found.")
        if request.departure_time is not None:
            flight.departure_time = request.departure_time
        if request.arrival_time is not None:
            flight.arrival_time = request.arrival_time
        if flight.arrival_time <= flight.departure_time:
            raise HTTPException(status_code=400, detail="Arrival time must be after departure time.")
        if request.total_seats is not None:
            active = db.query(BookingModel).filter(
                BookingModel.flight_id == flight_id,
                BookingModel.status != "Cancelled",
            ).count()
            if request.total_seats < active:
                raise HTTPException(status_code=400, detail=f"Total seats cannot be below {active} active bookings.")
            occupied = flight.total_seats - flight.available_seats
            if request.total_seats < occupied:
                raise HTTPException(status_code=400, detail=f"Total seats cannot be below {occupied} occupied seats.")
            flight.available_seats += request.total_seats - flight.total_seats
            flight.total_seats = request.total_seats
        db.commit()
        db.refresh(flight)
        return AdminFlightResponse(
            flight_id=flight.flight_id,
            airline=flight.airline.airline_name if flight.airline else "Unknown",
            flight_number=flight.flight_number,
            source=flight.source,
            destination=flight.destination,
            departure_time=flight.departure_time,
            arrival_time=flight.arrival_time,
            total_seats=flight.total_seats,
            available_seats=flight.available_seats,
            active_bookings=db.query(BookingModel).filter(
                BookingModel.flight_id == flight_id,
                BookingModel.status != "Cancelled",
            ).count(),
        )
    finally:
        db.close()


@router.delete("/flights/{flight_id}")
def delete_flight(flight_id: int, admin: UserModel = Depends(require_admin)):
    db = SessionLocal()
    try:
        flight = db.get(FlightModel, flight_id)
        if not flight:
            raise HTTPException(status_code=404, detail="Flight not found.")
        active = db.query(BookingModel).filter(
            BookingModel.flight_id == flight_id,
            BookingModel.status != "Cancelled",
        ).count()
        if active:
            raise HTTPException(status_code=409, detail="Cannot delete a flight with active bookings. Move or cancel those bookings first.")
        booking_ids = [b.booking_id for b in db.query(BookingModel.booking_id).filter(BookingModel.flight_id == flight_id).all()]
        if booking_ids:
            db.query(PaymentModel).filter(PaymentModel.booking_id.in_(booking_ids)).delete(synchronize_session=False)
            db.query(NotificationModel).filter(NotificationModel.booking_id.in_(booking_ids)).delete(synchronize_session=False)
            db.query(AdminTimelineModel).filter(AdminTimelineModel.booking_id.in_(booking_ids)).update({AdminTimelineModel.booking_id: None}, synchronize_session=False)
            db.query(BookingModel).filter(BookingModel.flight_id == flight_id).delete(synchronize_session=False)
        db.delete(flight)
        db.commit()
        return {"message": "Flight deleted."}
    finally:
        db.close()


@router.post("/bookings", response_model=AdminBookingResponse, status_code=201)
def create_admin_booking(
    request: AdminBookingCreate,
    admin: UserModel = Depends(require_admin),
):
    db = SessionLocal()
    try:
        flight = db.query(FlightModel).filter(FlightModel.flight_id == request.flight_id).with_for_update().first()
        if not flight:
            raise HTTPException(status_code=404, detail="Flight not found.")
        if flight.available_seats <= 0:
            raise HTTPException(status_code=400, detail="No seats available.")
        seat = request.seat_number.strip().upper()
        if not re.fullmatch(r"[0-9]+[A-E]", seat):
            raise HTTPException(status_code=400, detail="Seat number must look like 12A.")
        row = int(seat[:-1])
        if row < 1 or row > (flight.total_seats + 4) // 5:
            raise HTTPException(status_code=400, detail="Seat is outside this flight's seat map.")
        if db.query(BookingModel).filter(
            BookingModel.flight_id == flight.flight_id,
            BookingModel.seat_number == seat,
            BookingModel.status != "Cancelled",
        ).first():
            raise HTTPException(status_code=409, detail="Seat is already booked.")

        user = None
        if request.user_id is not None:
            user = db.get(UserModel, request.user_id)
            if not user:
                raise HTTPException(status_code=404, detail="Customer account not found.")
        elif request.user_email:
            user = db.query(UserModel).filter(func.lower(UserModel.email) == request.user_email.lower()).first()
            if not user:
                raise HTTPException(status_code=404, detail="Customer account not found.")

        passenger = PassengerModel(
            full_name=request.passenger_name,
            email=str(request.passenger_email) if request.passenger_email else (user.email if user else None),
            phone=request.passenger_phone,
        )
        db.add(passenger)
        db.flush()

        price = float(flight.base_fare or 0)
        booking = BookingModel(
            flight_id=flight.flight_id,
            passenger_id=passenger.passenger_id,
            user_id=user.user_id if user else None,
            seat_number=seat,
            status="Confirmed",
            pnr=generate_pnr(),
            price_per_seat=price,
            total_price=price,
        )
        db.add(booking)
        flight.available_seats -= 1
        db.flush()
        db.add(PaymentModel(booking_id=booking.booking_id, amount=price, payment_status="Success", payment_method="Admin"))
        db.add(AdminTimelineModel(
            booking_id=booking.booking_id,
            pnr=booking.pnr,
            action="created",
            details=f"Booking created by administrator; seat {seat}.",
            admin_user_id=admin.user_id,
        ))
        db.commit()
        db.refresh(booking)
        return _booking_response(booking)
    finally:
        db.close()


@router.get("/bookings/{pnr}/timeline", response_model=list[AdminTimelineResponse])
def booking_timeline(pnr: str, admin: UserModel = Depends(require_admin)):
    db = SessionLocal()
    try:
        return db.query(AdminTimelineModel).filter(
            AdminTimelineModel.pnr == pnr
        ).order_by(AdminTimelineModel.created_at.asc()).all()
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
        changes = []

        if request.seat_number is not None:
            if booking.status == "Cancelled":
                raise HTTPException(status_code=400, detail="Cancelled bookings cannot be assigned a seat.")
            seat = request.seat_number.strip().upper()
            if not re.fullmatch(r"[0-9]+[A-E]", seat):
                raise HTTPException(status_code=400, detail="Seat number must look like 12A.")
            flight = db.get(FlightModel, booking.flight_id)
            row_number = int(seat[:-1])
            max_row = (flight.total_seats + 4) // 5
            if row_number < 1 or row_number > max_row:
                raise HTTPException(status_code=400, detail="Seat number is outside this flight's seat map.")
            conflict = db.query(BookingModel).filter(
                BookingModel.flight_id == booking.flight_id,
                BookingModel.seat_number == seat,
                BookingModel.status != "Cancelled",
                BookingModel.booking_id != booking.booking_id,
            ).first()
            if conflict:
                raise HTTPException(status_code=409, detail="Seat is already booked.")
            if booking.seat_number != seat:
                changes.append(f"Seat changed from {booking.seat_number or 'unassigned'} to {seat}.")
                booking.seat_number = seat

        if request.passenger_name is not None:
            name = request.passenger_name.strip()
            if len(name) < 2:
                raise HTTPException(status_code=400, detail="Passenger name is too short.")
            booking.passenger.full_name = name
            changes.append("Passenger name updated.")
        if request.passenger_email is not None:
            booking.passenger.email = str(request.passenger_email) if request.passenger_email else None
            changes.append("Passenger email updated.")
        if request.total_price is not None:
            if request.total_price < 0:
                raise HTTPException(status_code=400, detail="Price cannot be negative.")
            booking.total_price = request.total_price
            changes.append("Booking price updated.")

        if changes:
            db.add(AdminTimelineModel(
                booking_id=booking.booking_id, pnr=booking.pnr, action="updated",
                details=" ".join(changes), admin_user_id=admin.user_id,
            ))
        db.commit()
        db.refresh(booking)
        return _booking_response(booking)
    finally:
        db.close()


@router.delete("/bookings/{pnr}")
def delete_booking(pnr: str, admin: UserModel = Depends(require_admin)):
    db = SessionLocal()
    try:
        booking = db.query(BookingModel).filter(BookingModel.pnr == pnr).first()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found.")
        if booking.status != "Cancelled":
            flight = db.get(FlightModel, booking.flight_id)
            if flight:
                flight.available_seats = min(flight.total_seats, flight.available_seats + 1)
        db.query(PaymentModel).filter(PaymentModel.booking_id == booking.booking_id).delete(synchronize_session=False)
        db.query(NotificationModel).filter(NotificationModel.booking_id == booking.booking_id).delete(synchronize_session=False)
        db.query(AdminTimelineModel).filter(AdminTimelineModel.booking_id == booking.booking_id).update(
            {AdminTimelineModel.booking_id: None}, synchronize_session=False
        )
        db.delete(booking)
        db.commit()
        return {"message": "Booking deleted and the seat was returned to inventory."}
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
        db.add(AdminTimelineModel(booking_id=booking.booking_id, pnr=booking.pnr, action="cancelled", details="Booking cancelled by administrator; seat returned to inventory.", admin_user_id=admin.user_id))
        db.commit()
        return AdminBookingCancellationResponse(
            message="Booking cancelled and the customer has been notified.",
            pnr=pnr,
            notification_created=notification_created,
        )
    finally:
        db.close()
