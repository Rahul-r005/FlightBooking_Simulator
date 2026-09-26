from datetime import datetime

from sqlalchemy.orm import Session

from .database import BookingModel, FlightModel, NotificationModel, UserModel


def create_notification(
    db: Session,
    user: UserModel,
    message: str,
    booking: BookingModel | None = None,
) -> NotificationModel:
    notification = NotificationModel(
        user_id=user.user_id,
        booking_id=booking.booking_id if booking else None,
        message=message,
        created_at=datetime.utcnow(),
        read=False,
    )
    db.add(notification)
    return notification


def booking_cancelled_message(booking: BookingModel, flight: FlightModel) -> str:
    departure = flight.departure_time.strftime("%d %b %Y, %I:%M %p")
    return (
        f"Your SkyBook booking {booking.pnr} for {flight.source} → "
        f"{flight.destination} on {departure} has been cancelled by our team. "
        "Please contact support if you need help rebooking."
    )
