from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import random

app = FastAPI(title="Flight Booking Simulator with Dynamic Pricing")


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
    return {"message": "Welcome to Flight Booking Sysrtem"}


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
    return {"status": "ok", "sevrer_time": datetime.utcnow().isoformat()}


@app.get("/simulate")
def simulate_demand():
    for f in flights:
        change = random.randint(-10, 10)
        f.demand = max(0, min(100, f.demand + change))
    return {"message": "Simulater demand updated", "flights": [f.dict() for f in flights]}
