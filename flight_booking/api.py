import io
import os
import random
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

from .admin import router as admin_router
from .auth import get_current_user, router as auth_router
from .booking_service import cancel_booking
from .database import (
    BookingModel,
    FareHistoryModel,
    FlightModel,
    PassengerModel,
    PaymentModel,
    NotificationModel,
    SessionLocal,
    UserModel,
    initialize_database,
)
from .notifications import create_notification
from .pricing import calculate_dynamic_fare, calculate_legacy_fare, generate_pnr
from .schemas import (
    BookingIn,
    BookingOut,
    DBBookingRequest,
    DBBookingResponse,
    DBFlightResponse,
    Flight,
    FlightOut,
    NotificationResponse,
)
from .simulator import FlightAvailabilitySimulator


legacy_now = datetime.now(timezone.utc).replace(tzinfo=None)
legacy_flights: List[Flight] = [
    Flight(
        flight_id=1,
        airline="IndiGo",
        flight_number="6E203",
        source="Delhi",
        destination="Mumbai",
        departure_time=legacy_now + timedelta(hours=6),
        arrival_time=legacy_now + timedelta(hours=8),
        total_seats=180,
        available_seats=150,
        base_fare=4000.0,
        pricing_tier="standard",
        demand=60,
    ),
    Flight(
        flight_id=2,
        airline="Air India",
        flight_number="AI440",
        source="Delhi",
        destination="Chennai",
        departure_time=legacy_now + timedelta(hours=12),
        arrival_time=legacy_now + timedelta(hours=15),
        total_seats=220,
        available_seats=200,
        base_fare=4500.0,
        pricing_tier="economy",
        demand=30,
    ),
    Flight(
        flight_id=3,
        airline="SpiceJet",
        flight_number="SJ789",
        source="Bangalore",
        destination="Kolkata",
        departure_time=legacy_now + timedelta(hours=18),
        arrival_time=legacy_now + timedelta(hours=21),
        total_seats=150,
        available_seats=100,
        base_fare=3800.0,
        pricing_tier="premium",
        demand=80,
    ),
]
legacy_bookings: List[BookingOut] = []
legacy_booking_counter = 1


def _allowed_origins() -> list[str]:
    configured = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://localhost:5500,"
        "http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1:5500",
    )
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    simulator = FlightAvailabilitySimulator()
    simulator.start()
    try:
        yield
    finally:
        simulator.stop()


app = FastAPI(
    title="Flight Booking Simulator with Dynamic Pricing",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(admin_router)


@app.middleware("http")
async def themed_html_404(request: Request, call_next):
    response = await call_next(request)
    if response.status_code == 404 and "text/html" in request.headers.get("accept", ""):
        return FileResponse("frontend/404.html", status_code=404)
    return response


@app.get("/")
def home():
    return FileResponse("frontend/index.html")


@app.get("/login")
def login_page():
    return FileResponse("frontend/login.html")


@app.get("/register")
def register_page():
    return FileResponse("frontend/register.html")


@app.get("/settings")
def settings_page(user: UserModel = Depends(get_current_user)):
    return FileResponse("frontend/settings.html")


@app.get("/admin")
def admin_page(user: UserModel = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    return FileResponse("frontend/admin.html")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "server_time": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
    }


@app.get("/legacy/flights", response_model=List[FlightOut])
def get_legacy_flights(
    sort_by: Optional[str] = Query(None),
    order: str = Query("asc"),
):
    result = [_legacy_flight_response(flight) for flight in legacy_flights]
    return _sort_legacy_flights(result, sort_by, order)


@app.get("/legacy/flights/search", response_model=List[FlightOut])
def search_legacy_flights(
    origin: str,
    destination: str,
    date: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    order: str = Query("asc"),
):
    results = []
    for flight in legacy_flights:
        if flight.source.lower() != origin.lower() or flight.destination.lower() != destination.lower():
            continue
        if date:
            try:
                search_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid date format (YYYY-MM-DD)") from exc
            if flight.departure_time.date() != search_date:
                continue
        results.append(_legacy_flight_response(flight))

    if not results:
        raise HTTPException(status_code=404, detail="No flights found for given search")
    return _sort_legacy_flights(results, sort_by, order)


@app.post("/legacy/book", response_model=BookingOut)
def create_legacy_booking(
    data: BookingIn,
    user: UserModel = Depends(get_current_user),
):
    global legacy_booking_counter

    for flight in legacy_flights:
        if flight.flight_id != data.flight_id:
            continue
        if data.seats <= 0:
            raise HTTPException(status_code=400, detail="Seats must be greater than zero")
        if flight.available_seats < data.seats:
            raise HTTPException(status_code=400, detail="Not enough available seats.")

        price = calculate_legacy_fare(flight)
        booking = BookingOut(
            booking_id=legacy_booking_counter,
            flight_id=flight.flight_id,
            passenger_name=data.passenger_name,
            seats=data.seats,
            price_per_seat=price,
            total_price=round(price * data.seats, 2),
            status="CONFIRMED",
        )
        flight.available_seats -= data.seats
        legacy_bookings.append(booking)
        legacy_booking_counter += 1
        return booking

    raise HTTPException(status_code=404, detail="Flight not found.")


@app.get("/external/airline/{airline_name}/schedules")
def get_airline_schedule(airline_name: str):
    schedules = [
        {
            "flight_number": flight.flight_number,
            "source": flight.source,
            "destination": flight.destination,
            "departure_time": flight.departure_time,
            "arrival_time": flight.arrival_time,
            "available_seats": flight.available_seats,
        }
        for flight in legacy_flights
        if flight.airline.lower() == airline_name.lower()
    ]
    return {
        "airline": airline_name,
        "schedules": schedules,
        "source": "mock-external-provider",
    }


@app.get("/simulate")
def simulate_legacy_demand():
    for flight in legacy_flights:
        flight.demand = max(0, min(100, flight.demand + random.randint(-10, 10)))
    return {
        "message": "Simulator demand updated",
        "flights": [flight.model_dump() for flight in legacy_flights],
    }


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _legacy_flight_response(flight: Flight) -> FlightOut:
    return FlightOut(
        flight_id=flight.flight_id,
        airline=flight.airline,
        flight_number=flight.flight_number,
        source=flight.source,
        destination=flight.destination,
        departure_time=flight.departure_time,
        arrival_time=flight.arrival_time,
        total_seats=flight.total_seats,
        available_seats=flight.available_seats,
        duration_minutes=_duration_minutes(flight.departure_time, flight.arrival_time),
        dynamic_price=calculate_legacy_fare(flight),
        pricing_tier=flight.pricing_tier,
    )


def _sort_legacy_flights(
    flights: list[FlightOut],
    sort_by: Optional[str],
    order: str,
) -> list[FlightOut]:
    if not sort_by:
        return flights
    if sort_by not in {"price", "duration"}:
        raise HTTPException(status_code=400, detail="sort_by must be price or duration")

    key = (
        (lambda flight: flight.dynamic_price)
        if sort_by == "price"
        else (lambda flight: flight.duration_minutes)
    )
    flights.sort(key=key, reverse=order.lower() == "desc")
    return flights


def _duration_minutes(departure_time: datetime, arrival_time: datetime) -> int:
    return int((arrival_time - departure_time).total_seconds() / 60)


def _flight_response(flight: FlightModel) -> DBFlightResponse:
    return DBFlightResponse(
        flight_id=flight.flight_id,
        airline=flight.airline.airline_name if flight.airline else "Unknown",
        flight_number=flight.flight_number,
        source=flight.source,
        destination=flight.destination,
        departure_time=flight.departure_time,
        arrival_time=flight.arrival_time,
        total_seats=flight.total_seats,
        available_seats=flight.available_seats,
        duration_minutes=_duration_minutes(flight.departure_time, flight.arrival_time),
        dynamic_price=calculate_dynamic_fare(flight),
        base_fare=float(flight.base_fare or 0),
        pricing_tier=flight.pricing_tier or "standard",
        demand=int(flight.simulated_demand or 0),
    )


def _booking_response(booking: BookingModel) -> DBBookingResponse:
    return DBBookingResponse(
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
    )


def _booking_belongs_to_user(booking: BookingModel, user: UserModel) -> bool:
    return booking.user_id == user.user_id or user.role == "admin"


@app.get("/db/flights", response_model=List[DBFlightResponse])
def db_get_flights(
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    date: Optional[str] = None,
    sort_by: Optional[str] = None,
    order: str = "asc",
    db: Session = Depends(get_db),
):
    query = db.query(FlightModel)

    if origin:
        query = query.filter(FlightModel.source.ilike(origin.strip()))
    if destination:
        query = query.filter(FlightModel.destination.ilike(destination.strip()))
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid date format (YYYY-MM-DD)") from exc
        query = query.filter(func.date(FlightModel.departure_time) == target_date)

    flights = [_flight_response(flight) for flight in query.all()]

    if sort_by not in (None, "price", "duration"):
        raise HTTPException(status_code=400, detail="sort_by must be price or duration")
    if sort_by == "price":
        flights.sort(key=lambda flight: flight.dynamic_price, reverse=order.lower() == "desc")
    elif sort_by == "duration":
        flights.sort(key=lambda flight: flight.duration_minutes, reverse=order.lower() == "desc")
    return flights


@app.get("/db/flights/{flight_id}", response_model=DBFlightResponse)
def db_get_flight(flight_id: int, db: Session = Depends(get_db)):
    flight = db.query(FlightModel).filter(FlightModel.flight_id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return _flight_response(flight)


@app.get("/flights", response_model=List[DBFlightResponse])
def flights_alias(
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    date: Optional[str] = None,
    sort_by: Optional[str] = None,
    order: str = "asc",
    db: Session = Depends(get_db),
):
    return db_get_flights(origin, destination, date, sort_by, order, db)


@app.get("/flights/search", response_model=List[DBFlightResponse])
def flights_search_alias(
    origin: str,
    destination: str,
    date: Optional[str] = None,
    sort_by: Optional[str] = None,
    order: str = "asc",
    db: Session = Depends(get_db),
):
    results = db_get_flights(origin, destination, date, sort_by, order, db)
    if not results:
        raise HTTPException(status_code=404, detail="No flights found for given search")
    return results


def _validate_seat(flight: FlightModel, requested_seat: Optional[str]) -> str:
    seat_number = (requested_seat or "").strip().upper()
    if not seat_number:
        raise HTTPException(status_code=400, detail="Seat number is required")
    if len(seat_number) < 2 or not seat_number[:-1].isdigit() or not seat_number[-1].isalpha():
        raise HTTPException(status_code=400, detail="Seat number must look like 12A")

    row_number = int(seat_number[:-1])
    seat_letter = seat_number[-1]
    max_row = (flight.total_seats + 4) // 5
    if row_number < 1 or row_number > max_row or seat_letter not in "ABCDE":
        raise HTTPException(status_code=400, detail="Invalid seat number for this flight")
    return seat_number


def _seat_is_booked(db: Session, flight_id: int, seat_number: str) -> bool:
    return (
        db.query(BookingModel)
        .filter(
            BookingModel.flight_id == flight_id,
            BookingModel.seat_number == seat_number,
            BookingModel.status != "Cancelled",
        )
        .first()
        is not None
    )


def _find_or_create_passenger(db: Session, request: DBBookingRequest) -> PassengerModel:
    if request.passenger_email:
        passenger = (
            db.query(PassengerModel)
            .filter(func.lower(PassengerModel.email) == request.passenger_email.lower())
            .first()
        )
        if passenger:
            return passenger

    passenger = PassengerModel(
        full_name=request.passenger_name,
        email=request.passenger_email,
        phone=request.passenger_phone,
    )
    db.add(passenger)
    db.flush()
    return passenger


@app.post("/db/booking", response_model=DBBookingResponse, status_code=status.HTTP_201_CREATED)
def db_create_booking(
    request: DBBookingRequest,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    try:
        with db.begin():
            flight = (
                db.query(FlightModel)
                .with_for_update()
                .filter(FlightModel.flight_id == request.flight_id)
                .first()
            )
            if not flight:
                raise HTTPException(status_code=404, detail="Flight not found")
            if flight.available_seats <= 0:
                raise HTTPException(status_code=400, detail="No seats available")

            seat_number = _validate_seat(flight, request.seat_number)
            if _seat_is_booked(db, flight.flight_id, seat_number):
                raise HTTPException(status_code=409, detail="Seat is already booked")

            flight.available_seats -= 1
            db.flush()

            passenger = _find_or_create_passenger(db, request)
            price_per_seat = calculate_dynamic_fare(flight)
            payment_success = (
                bool(request.force_payment_success)
                if request.force_payment_success is not None
                else random.choice([True] * 8 + [False] * 2)
            )
            if not payment_success:
                raise HTTPException(status_code=402, detail="Payment failed (simulated)")

            booking = BookingModel(
                flight_id=flight.flight_id,
                passenger_id=passenger.passenger_id,
                user_id=user.user_id,
                seat_number=seat_number,
                status="Confirmed",
                pnr=generate_pnr(),
                price_per_seat=price_per_seat,
                total_price=price_per_seat,
            )
            db.add(booking)
            db.flush()
            db.add(
                PaymentModel(
                    booking_id=booking.booking_id,
                    amount=price_per_seat,
                    payment_status="Success",
                    payment_method="Simulated",
                )
            )
            db.add(FareHistoryModel(flight_id=flight.flight_id, price=price_per_seat))
            db.flush()
            return _booking_response(booking)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Booking failed.") from exc


@app.post("/receipt/pdf")
def receipt_pdf(
    data: dict,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pnr = data.get("pnr")
    if not pnr:
        raise HTTPException(status_code=400, detail="PNR is required")
    booking = db.query(BookingModel).filter(BookingModel.pnr == pnr).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if not _booking_belongs_to_user(booking, user):
        raise HTTPException(status_code=403, detail="You do not have access to this booking.")

    try:
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="Receipt service is unavailable.") from exc

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.setTitle("SkyBook Flight Booking Receipt")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(60, 780, "SkyBook Flight Booking")
    pdf.setFont("Helvetica", 11)

    details = {
        "PNR": booking.pnr,
        "Flight": booking.flight_id,
        "Seat": booking.seat_number or "—",
        "Status": booking.status,
        "Total": f"₹{float(booking.total_price or 0):,.2f}",
    }
    y_position = 740
    for key, value in details.items():
        pdf.drawString(60, y_position, f"{key}: {value}")
        y_position -= 22

    pdf.save()
    buffer.seek(0)
    return Response(
        content=buffer.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=booking_receipt.pdf"},
    )


@app.post("/db/bookings/{pnr}/pay", response_model=DBBookingResponse)
def db_pay_booking(
    pnr: str,
    force_success: Optional[bool] = None,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    booking = db.query(BookingModel).filter(BookingModel.pnr == pnr).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if not _booking_belongs_to_user(booking, user):
        raise HTTPException(status_code=403, detail="You do not have access to this booking.")
    if booking.status == "Confirmed":
        return _booking_response(booking)

    payment_success = random.choice([True, False]) if force_success is None else bool(force_success)
    booking.status = "Confirmed" if payment_success else "PAYMENT_FAILED"
    db.commit()
    return _booking_response(booking)


@app.delete("/db/booking/{pnr}")
def db_cancel_booking(
    pnr: str,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    try:
        with db.begin():
            booking = (
                db.query(BookingModel)
                .with_for_update()
                .filter(BookingModel.pnr == pnr)
                .first()
            )
            if not booking:
                raise HTTPException(status_code=404, detail="Booking not found")
            if not _booking_belongs_to_user(booking, user):
                raise HTTPException(status_code=403, detail="You do not have access to this booking.")
            notification_created = cancel_booking(db, booking, notify_user=False)
        return {
            "message": "Booking cancelled.",
            "pnr": pnr,
            "notification_created": notification_created,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Cancellation failed.") from exc


@app.get("/db/booking/{pnr}", response_model=DBBookingResponse)
def db_get_booking(
    pnr: str,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    booking = db.query(BookingModel).filter(BookingModel.pnr == pnr).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if not _booking_belongs_to_user(booking, user):
        raise HTTPException(status_code=403, detail="You do not have access to this booking.")
    return _booking_response(booking)


@app.get("/db/bookings", response_model=List[DBBookingResponse])
def db_list_bookings(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    bookings = (
        db.query(BookingModel)
        .filter(BookingModel.user_id == user.user_id)
        .order_by(BookingModel.booking_date.desc())
        .limit(limit)
        .all()
    )
    return [_booking_response(booking) for booking in bookings]


@app.get("/notifications", response_model=List[NotificationResponse])
def list_notifications(
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    return (
        db.query(NotificationModel)
        .filter(NotificationModel.user_id == user.user_id)
        .order_by(NotificationModel.created_at.desc())
        .limit(50)
        .all()
    )


@app.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    notification = (
        db.query(NotificationModel)
        .filter(
            NotificationModel.notification_id == notification_id,
            NotificationModel.user_id == user.user_id,
        )
        .first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.read = True
    db.commit()
    return {"message": "Notification marked as read."}


@app.get("/db/dynamic_price/{flight_id}")
def db_dynamic_price(flight_id: int, db: Session = Depends(get_db)):
    flight = db.query(FlightModel).filter(FlightModel.flight_id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    price = calculate_dynamic_fare(flight)
    db.add(FareHistoryModel(flight_id=flight.flight_id, price=price))
    db.commit()
    return {
        "flight_id": flight.flight_id,
        "flight_number": flight.flight_number,
        "origin": flight.source,
        "destination": flight.destination,
        "departure_time": flight.departure_time,
        "arrival_time": flight.arrival_time,
        "dynamic_price": price,
        "base_fare": float(flight.base_fare),
        "available_seats": flight.available_seats,
        "total_seats": flight.total_seats,
    }


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
