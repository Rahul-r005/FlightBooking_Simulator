import os
from pathlib import Path

# Keep the production demand/seat simulator disabled during deterministic tests.
os.environ["DISABLE_BACKGROUND_SIMULATOR"] = "1"

DB_FILE = Path("test_flight_booking.db")
if DB_FILE.exists():
    DB_FILE.unlink()

os.environ["DATABASE_URL"] = "sqlite:///./test_flight_booking.db"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:5500"

from fastapi.testclient import TestClient
from FlightBooking_backend import (
    app, Base, engine, SessionLocal,
    AirlineModel, FlightModel, BookingModel, PaymentModel,
)
from datetime import datetime, timedelta

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()
airline = AirlineModel(airline_name="Test Air")
db.add(airline)
db.flush()
flight = FlightModel(
    airline_id=airline.airline_id,
    flight_number="TA101",
    source="Delhi",
    destination="Mumbai",
    departure_time=datetime.utcnow() + timedelta(hours=24),
    arrival_time=datetime.utcnow() + timedelta(hours=26),
    total_seats=10,
    available_seats=10,
    base_fare=4000,
    pricing_tier="standard",
    simulated_demand=50,
)
db.add(flight)
db.commit()
flight_id = flight.flight_id
db.close()

def test_backend_flow():
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
    
        response = client.get("/flights")
        assert response.status_code == 200
        assert response.json()[0]["flight_number"] == "TA101"
    
        cors = client.options(
            "/flights",
            headers={
                "Origin": "http://localhost:5500",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert cors.status_code == 200
        assert cors.headers.get("access-control-allow-origin") == "http://localhost:5500"
    
        bad_seat = client.post("/db/booking", json={
            "flight_id": flight_id,
            "passenger_name": "Test User",
            "seat_number": "99Z",
            "force_payment_success": True,
        })
        assert bad_seat.status_code == 400
    
        booking = client.post("/db/booking", json={
            "flight_id": flight_id,
            "passenger_name": "Test User",
            "passenger_email": "test@example.com",
            "seat_number": "1A",
            "force_payment_success": True,
        })
        assert booking.status_code == 201, booking.text
        payload = booking.json()
        assert payload["seat_number"] == "1A"
    
        db = SessionLocal()
        assert db.query(PaymentModel).filter(PaymentModel.booking_id == payload["booking_id"]).count() == 1
        assert db.get(FlightModel, flight_id).available_seats == 9
        db.close()
    
        duplicate = client.post("/db/booking", json={
            "flight_id": flight_id,
            "passenger_name": "Another User",
            "seat_number": "1A",
            "force_payment_success": True,
        })
        assert duplicate.status_code == 409
    
        cancelled = client.delete(f"/db/booking/{payload['pnr']}")
        assert cancelled.status_code == 200
    
        db = SessionLocal()
        assert db.query(FlightModel).get(flight_id).available_seats == 10
        assert db.query(BookingModel).filter(BookingModel.pnr == payload["pnr"]).first().seat_number is None
        db.close()
    
        reused = client.post("/db/booking", json={
            "flight_id": flight_id,
            "passenger_name": "Replacement User",
            "seat_number": "1A",
            "force_payment_success": True,
        })
        assert reused.status_code == 201, reused.text
    
        pdf = client.post("/receipt/pdf", json={"pnr": reused.json()["pnr"]})
        assert pdf.status_code == 200
        assert pdf.headers["content-type"].startswith("application/pdf")
        assert pdf.content.startswith(b"%PDF")
    
