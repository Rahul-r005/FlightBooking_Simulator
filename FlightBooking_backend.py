
from fastapi import FastAPI, HTTPException, Query, Depends, status
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime, timedelta
import random
import threading
import os
import string

# SQLAlchemy imports
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, DECIMAL, ForeignKey, func
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session

# ----------------------------
# Basic FastAPI app
# ----------------------------
app = FastAPI(title="Flight Booking Simulator with Dynamic Pricing")

# ----------------------------
# --- Original in-memory models & endpoints (kept) ---
# ----------------------------
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

flights: List[Flight] = [
    Flight(
        flight_id=1,
        airline="IndiGo",
        flight_number="6E203",
        source="Delhi",
        destination="Mumbai",
        departure_time=datetime.utcnow() + timedelta(hours=6),
        arrival_time=datetime.utcnow() + timedelta(hours=8),
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
        departure_time=datetime.utcnow() + timedelta(hours=12),
        arrival_time=datetime.utcnow() + timedelta(hours=15),
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
        departure_time=datetime.utcnow() + timedelta(hours=18),
        arrival_time=datetime.utcnow() + timedelta(hours=21),
        total_seats=150,
        available_seats=100,
        base_fare=3800.0,
        pricing_tier="premium",
        demand=80,
    ),
]

bookings: List[BookingOut] = []
booking_counter = 1

def dynamic_pricing(f: Flight) -> float:
    base = f.base_fare
    remaining_pct = f.available_seats / f.total_seats
    hours_to_departure = max((f.departure_time - datetime.utcnow()).total_seconds() / 3600, 0)

    demand_factor = 1 + (f.demand / 100)
    seat_factor = 1.5 if remaining_pct < 0.3 else 1.0
    time_factor = 1.3 if hours_to_departure < 12 else 1.0
    tier_factor = {"economy": 0.9, "standard": 1.0, "premium": 1.2}.get(f.pricing_tier, 1.0)

    price = base * demand_factor * seat_factor * time_factor * tier_factor
    return round(price, 2)

@app.get("/")
def home():
    return {"message": "Welcome to Flight Booking System"}

@app.get("/flights", response_model=List[FlightOut])
def get_all_flights(sort_by: Optional[str] = Query(None), order: Optional[str] = Query("asc")):
    result = []
    for f in flights:
        duration = int((f.arrival_time - f.departure_time).total_seconds() / 60)
        result.append(
            FlightOut(
                flight_id=f.flight_id,
                airline=f.airline,
                flight_number=f.flight_number,
                source=f.source,
                destination=f.destination,
                departure_time=f.departure_time,
                arrival_time=f.arrival_time,
                total_seats=f.total_seats,
                available_seats=f.available_seats,
                duration_minutes=duration,
                dynamic_price=dynamic_pricing(f),
                pricing_tier=f.pricing_tier,
            )
        )
    if sort_by:
        reverse = (order == "desc")
        key_func = lambda x: x.dynamic_price if sort_by == "price" else x.duration_minutes
        result.sort(key=key_func, reverse=reverse)
    return result

@app.get("/flights/search", response_model=List[FlightOut])
def search_flights(
    origin: str, destination: str, date: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None), order: Optional[str] = Query("asc")
):
    results = []
    for f in flights:
        if f.source.lower() == origin.lower() and f.destination.lower() == destination.lower():
            if date:
                try:
                    search_date = datetime.strptime(date, "%Y-%m-%d").date()
                    if f.departure_time.date() != search_date:
                        continue
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid date format (YYYY-MM-DD)")
            duration = int((f.arrival_time - f.departure_time).total_seconds() / 60)
            results.append(
                FlightOut(
                    flight_id=f.flight_id,
                    airline=f.airline,
                    flight_number=f.flight_number,
                    source=f.source,
                    destination=f.destination,
                    departure_time=f.departure_time,
                    arrival_time=f.arrival_time,
                    total_seats=f.total_seats,
                    available_seats=f.available_seats,
                    duration_minutes=duration,
                    dynamic_price=dynamic_pricing(f),
                    pricing_tier=f.pricing_tier,
                )
            )
    if not results:
        raise HTTPException(status_code=404, detail="No flights found for given search")
    if sort_by:
        reverse = (order == "desc")
        key_func = lambda x: x.dynamic_price if sort_by == "price" else x.duration_minutes
        results.sort(key=key_func, reverse=reverse)
    return results

@app.post("/book", response_model=BookingOut)
def create_booking(data: BookingIn):
    global booking_counter
    for f in flights:
        if f.flight_id == data.flight_id:
            if f.available_seats < data.seats:
                raise HTTPException(status_code=400, detail="Not enough available seats.")
            price = dynamic_pricing(f)
            total = round(price * data.seats, 2)
            f.available_seats -= data.seats

            booking = BookingOut(
                booking_id=booking_counter,
                flight_id=f.flight_id,
                passenger_name=data.passenger_name,
                seats=data.seats,
                price_per_seat=price,
                total_price=total,
                status="CONFIRMED",
            )
            bookings.append(booking)
            booking_counter += 1
            return booking
    raise HTTPException(status_code=404, detail="Flight not found.")

@app.get("/external/airline/{airline_name}/schedules")
def get_airline_schedule(airline_name: str):
    result = []
    for f in flights:
        if f.airline.lower() == airline_name.lower():
            result.append({
                "flight_number": f.flight_number,
                "source": f.source,
                "destination": f.destination,
                "departure_time": f.departure_time,
                "arrival_time": f.arrival_time,
                "available_seats": f.available_seats,
            })
    return {"airline": airline_name, "schedules": result, "source": "mock-external-provider"}

@app.get("/health")
def health():
    return {"status": "ok", "server_time": datetime.utcnow().isoformat()}

@app.get("/simulate")
def simulate_demand():
    for f in flights:
        change = random.randint(-10, 10)
        f.demand = max(0, min(100, f.demand + change))
    return {"message": "Simulator demand updated", "flights": [f.dict() for f in flights]}

# ----------------------------
# --- DB-backed booking workflow additions ---
# ----------------------------

DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", 3107)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "flight_booking") 

DATABASE_URL = f"mysql+pymysql://root:3107@localhost:3306/flight_booking"

# SQLAlchemy setup
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

# Models mirroring FlightBookingDB.sql
class AirlineModel(Base):
    __tablename__ = "Airlines"
    airline_id = Column(Integer, primary_key=True, autoincrement=True)
    airline_name = Column(String(100), nullable=False)
    contact_number = Column(String(15))
    email = Column(String(50))

class FlightModel(Base):
    __tablename__ = "Flights"
    flight_id = Column(Integer, primary_key=True, autoincrement=True)
    airline_id = Column(Integer, ForeignKey("Airlines.airline_id"))
    flight_number = Column(String(10), unique=True, nullable=False)
    source = Column(String(50))
    destination = Column(String(50))
    departure_time = Column(DateTime)
    arrival_time = Column(DateTime)
    total_seats = Column(Integer)
    available_seats = Column(Integer)
    base_fare = Column(DECIMAL(10,2), default=3000.00)
    pricing_tier = Column(String(20), default="standard")
    simulated_demand = Column(Integer, default=50)
    airline = relationship("AirlineModel")

class PassengerModel(Base):
    __tablename__ = "Passengers"
    passenger_id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(100))
    gender = Column(String(1))
    age = Column(Integer)
    email = Column(String(50))
    phone = Column(String(15))

class BookingModel(Base):
    __tablename__ = "Bookings"
    booking_id = Column(Integer, primary_key=True, autoincrement=True)
    flight_id = Column(Integer, ForeignKey("Flights.flight_id"))
    passenger_id = Column(Integer, ForeignKey("Passengers.passenger_id"))
    booking_date = Column(DateTime, server_default=func.now())
    seat_number = Column(String(5))
    status = Column(String(20), default="Confirmed")
    pnr = Column(String(20), unique=True, nullable=True)
    price_per_seat = Column(DECIMAL(10,2), nullable=True)
    total_price = Column(DECIMAL(12,2), nullable=True)

class FareHistoryModel(Base):
    __tablename__ = "FareHistory"
    id = Column(Integer, primary_key=True, autoincrement=True)
    flight_id = Column(Integer)
    recorded_at = Column(DateTime, server_default=func.now())
    price = Column(DECIMAL(10,2))

# Create tables if missing (development convenience)
Base.metadata.create_all(bind=engine)

# Pydantic schemas for DB endpoints
class DBBookingRequest(BaseModel):
    flight_id: int
    passenger_name: str = Field(..., min_length=2)
    passenger_email: Optional[EmailStr] = None
    passenger_phone: Optional[str] = None
    seat_number: Optional[str] = None
    force_payment_success: Optional[bool] = None

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

    class Config:
        orm_mode = True

# DB dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Utilities
def generate_pnr(n=6):
    part = "".join(random.choices(string.ascii_uppercase + string.digits, k=n))
    ts = datetime.utcnow().strftime("%m%d%H%M%S")
    return f"{part}{ts}"

def dynamic_pricing_from_flight(flight: FlightModel) -> float:
    base = float(flight.base_fare or 3000.0)
    demand = float(flight.simulated_demand or 50.0)
    demand_factor = 0.8 + (demand / 100.0) * 0.8

    remaining_pct = (flight.available_seats / max(flight.total_seats, 1)) * 100
    if remaining_pct <= 10:
        seat_factor = 2.0
    elif remaining_pct <= 30:
        seat_factor = 1.4
    elif remaining_pct <= 60:
        seat_factor = 1.0
    else:
        seat_factor = 0.9

    hours_to_departure = max(((flight.departure_time - datetime.utcnow()).total_seconds()) / 3600.0, 0.0)
    if hours_to_departure <= 6:
        time_factor = 1.5
    elif hours_to_departure <= 24:
        time_factor = 1.2
    elif hours_to_departure <= 72:
        time_factor = 1.0
    else:
        time_factor = 0.85

    tier_map = {"standard": 1.0, "economy": 0.95, "premium": 1.35}
    tier_mult = tier_map.get((flight.pricing_tier or "standard").lower(), 1.0)

    price = base * demand_factor * seat_factor * time_factor * tier_mult
    return round(price, 2)

def record_fare(db: Session, flight_id: int, price: float):
    try:
        fh = FareHistoryModel(flight_id=flight_id, price=price)
        db.add(fh)
        db.flush()
    except Exception:
        db.rollback()

# Background simulator (updates DB)
_stop_event = threading.Event()

def background_simulator(interval_seconds: int = 30):
    while not _stop_event.is_set():
        db = SessionLocal()
        try:
            rows = db.query(FlightModel).all()
            for f in rows:
                f.simulated_demand = max(0, min(100, (f.simulated_demand or 50) + random.randint(-8, 10)))
                if random.random() < 0.12 and f.available_seats > 0:
                    dec = random.randint(1, min(3, f.available_seats))
                    f.available_seats = max(0, f.available_seats - dec)
                elif random.random() > 0.995:
                    f.available_seats = min(f.total_seats, f.available_seats + 1)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
        _stop_event.wait(interval_seconds)

@app.on_event("startup")
def start_background():
    threading.Thread(target=background_simulator, args=(30,), daemon=True).start()

@app.on_event("shutdown")
def stop_background():
    _stop_event.set()

# ---------- DB booking endpoints (transaction-safe) ----------
@app.post("/db/booking", response_model=DBBookingResponse, status_code=status.HTTP_201_CREATED)
def db_create_booking(req: DBBookingRequest, db: Session = Depends(get_db)):
    try:
        with db.begin():
            flight = db.query(FlightModel).with_for_update().filter(FlightModel.flight_id == req.flight_id).first()
            if not flight:
                raise HTTPException(status_code=404, detail="Flight not found")
            if flight.available_seats <= 0:
                raise HTTPException(status_code=400, detail="No seats available")

            # reserve seat
            flight.available_seats = flight.available_seats - 1
            db.flush()

            # create or reuse passenger by email if provided
            passenger = None
            if req.passenger_email:
                passenger = db.query(PassengerModel).filter(func.lower(PassengerModel.email) == req.passenger_email.lower()).first()
            if not passenger:
                passenger = PassengerModel(
                    full_name=req.passenger_name,
                    email=req.passenger_email,
                    phone=req.passenger_phone
                )
                db.add(passenger)
                db.flush()

            price_per_seat = dynamic_pricing_from_flight(flight)
            total_price = price_per_seat

            # simulate payment
            if req.force_payment_success is None:
                payment_success = random.choice([True]*8 + [False]*2)
            else:
                payment_success = bool(req.force_payment_success)

            if not payment_success:
                raise HTTPException(status_code=402, detail="Payment failed (simulated)")

            pnr = generate_pnr()
            booking = BookingModel(
                flight_id=flight.flight_id,
                passenger_id=passenger.passenger_id,
                seat_number=req.seat_number,
                status="Confirmed",
                pnr=pnr,
                price_per_seat=price_per_seat,
                total_price=total_price
            )
            db.add(booking)
            db.flush()

            record_fare(db, flight.flight_id, price_per_seat)

            return DBBookingResponse(
                booking_id=booking.booking_id,
                pnr=booking.pnr,
                flight_id=booking.flight_id,
                passenger_id=booking.passenger_id,
                seat_number=booking.seat_number,
                price_per_seat=float(booking.price_per_seat),
                total_price=float(booking.total_price),
                status=booking.status,
                booking_date=booking.booking_date
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Booking failed: {str(e)}")

@app.post("/db/bookings/{pnr}/pay", response_model=DBBookingResponse)
def db_pay_booking(pnr: str, force_success: Optional[bool] = None, db: Session = Depends(get_db)):
    booking = db.query(BookingModel).filter(BookingModel.pnr == pnr).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status == "Confirmed":
        return DBBookingResponse(
            booking_id=booking.booking_id,
            pnr=booking.pnr,
            flight_id=booking.flight_id,
            passenger_id=booking.passenger_id,
            seat_number=booking.seat_number,
            price_per_seat=float(booking.price_per_seat),
            total_price=float(booking.total_price),
            status=booking.status,
            booking_date=booking.booking_date
        )
    payment_success = random.choice([True, False]) if force_success is None else bool(force_success)
    booking.status = "Confirmed" if payment_success else "PAYMENT_FAILED"
    db.commit()
    return DBBookingResponse(
        booking_id=booking.booking_id,
        pnr=booking.pnr,
        flight_id=booking.flight_id,
        passenger_id=booking.passenger_id,
        seat_number=booking.seat_number,
        price_per_seat=float(booking.price_per_seat),
        total_price=float(booking.total_price),
        status=booking.status,
        booking_date=booking.booking_date
    )

@app.delete("/db/booking/{pnr}")
def db_cancel_booking(pnr: str, db: Session = Depends(get_db)):
    try:
        with db.begin():
            booking = db.query(BookingModel).filter(BookingModel.pnr == pnr).with_for_update().first()
            if not booking:
                raise HTTPException(status_code=404, detail="Booking not found")
            if booking.status == "Cancelled":
                raise HTTPException(status_code=400, detail="Already cancelled")
            flight = db.query(FlightModel).filter(FlightModel.flight_id == booking.flight_id).with_for_update().first()
            if not flight:
                raise HTTPException(status_code=500, detail="Associated flight not found")
            flight.available_seats = min(flight.total_seats, flight.available_seats + 1)
            booking.status = "Cancelled"
            db.add(booking); db.add(flight)
        return {"message": "Booking cancelled", "pnr": pnr}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cancellation failed: {str(e)}")

@app.get("/db/booking/{pnr}", response_model=DBBookingResponse)
def db_get_booking(pnr: str, db: Session = Depends(get_db)):
    booking = db.query(BookingModel).filter(BookingModel.pnr == pnr).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return DBBookingResponse(
        booking_id=booking.booking_id,
        pnr=booking.pnr,
        flight_id=booking.flight_id,
        passenger_id=booking.passenger_id,
        seat_number=booking.seat_number,
        price_per_seat=float(booking.price_per_seat) if booking.price_per_seat is not None else 0.0,
        total_price=float(booking.total_price) if booking.total_price is not None else 0.0,
        status=booking.status,
        booking_date=booking.booking_date
    )

@app.get("/db/bookings", response_model=List[DBBookingResponse])
def db_list_bookings(limit: int = 100, db: Session = Depends(get_db)):
    rows = db.query(BookingModel).order_by(BookingModel.booking_date.desc()).limit(limit).all()
    out = []
    for b in rows:
        out.append(DBBookingResponse(
            booking_id=b.booking_id,
            pnr=b.pnr,
            flight_id=b.flight_id,
            passenger_id=b.passenger_id,
            seat_number=b.seat_number,
            price_per_seat=float(b.price_per_seat) if b.price_per_seat is not None else 0.0,
            total_price=float(b.total_price) if b.total_price is not None else 0.0,
            status=b.status,
            booking_date=b.booking_date
        ))
    return out

@app.get("/db/dynamic_price/{flight_id}")
def db_dynamic_price(flight_id: int, db: Session = Depends(get_db)):
    flight = db.query(FlightModel).filter(FlightModel.flight_id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    price = dynamic_pricing_from_flight(flight)
    record_fare(db, flight.flight_id, price)
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
        "total_seats": flight.total_seats
    }
# End of file
