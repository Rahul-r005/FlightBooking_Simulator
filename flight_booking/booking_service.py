from fastapi import HTTPException
from sqlalchemy.orm import Session

from .database import BookingModel, FlightModel, UserModel
from .notifications import booking_cancelled_message, create_notification


def cancel_booking(
    db: Session,
    booking: BookingModel,
    notify_user: bool = True,
) -> bool:
    if booking.status == "Cancelled":
        raise HTTPException(status_code=400, detail="Already cancelled")

    flight = (
        db.query(FlightModel)
        .filter(FlightModel.flight_id == booking.flight_id)
        .with_for_update()
        .first()
    )
    if not flight:
        raise HTTPException(status_code=500, detail="Associated flight not found")

    flight.available_seats = min(flight.total_seats, flight.available_seats + 1)
    booking.status = "Cancelled"
    booking.seat_number = None

    notification_created = False
    if notify_user and booking.user_id:
        user = db.get(UserModel, booking.user_id)
        if user:
            create_notification(
                db,
                user,
                booking_cancelled_message(booking, flight),
                booking,
            )
            notification_created = True

    return notification_created
