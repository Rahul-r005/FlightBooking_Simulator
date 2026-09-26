from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from FlightBooking_backend import (
    AirlineModel,
    BookingModel,
    FlightModel,
    PaymentModel,
    SessionLocal,
    app,
)


def create_test_flight() -> int:
    db = SessionLocal()
    airline = AirlineModel(airline_name="Test Air")
    db.add(airline)
    db.flush()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    flight = FlightModel(
        airline_id=airline.airline_id,
        flight_number="TA101",
        source="Delhi",
        destination="Mumbai",
        departure_time=now + timedelta(hours=24),
        arrival_time=now + timedelta(hours=26),
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
    return flight_id


def sign_in(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "correct-horse-battery",
        },
    )
    assert response.status_code == 201, response.text


def test_unauthenticated_booking_is_rejected():
    flight_id = create_test_flight()
    with TestClient(app) as client:
        response = client.post(
            "/db/booking",
            json={
                "flight_id": flight_id,
                "passenger_name": "Blocked User",
                "seat_number": "1A",
                "force_payment_success": True,
            },
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Please sign in to continue."


def test_backend_flow():
    flight_id = create_test_flight()

    with TestClient(app) as client:
        sign_in(client)
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

        invalid_seat = client.post(
            "/db/booking",
            json={
                "flight_id": flight_id,
                "passenger_name": "Test User",
                "seat_number": "99Z",
                "force_payment_success": True,
            },
        )
        assert invalid_seat.status_code == 400

        payment_failure = client.post(
            "/db/booking",
            json={
                "flight_id": flight_id,
                "passenger_name": "Test User",
                "seat_number": "1A",
                "force_payment_success": False,
            },
        )
        assert payment_failure.status_code == 402

        db = SessionLocal()
        assert db.get(FlightModel, flight_id).available_seats == 10
        db.close()

        booking = client.post(
            "/db/booking",
            json={
                "flight_id": flight_id,
                "passenger_name": "Test User",
                "passenger_email": "test@example.com",
                "seat_number": "1A",
                "force_payment_success": True,
            },
        )
        assert booking.status_code == 201, booking.text
        payload = booking.json()
        assert payload["seat_number"] == "1A"
        assert payload["user_id"] > 0

        db = SessionLocal()
        assert db.query(PaymentModel).filter(PaymentModel.booking_id == payload["booking_id"]).count() == 1
        assert db.get(FlightModel, flight_id).available_seats == 9
        db.close()

        duplicate = client.post(
            "/db/booking",
            json={
                "flight_id": flight_id,
                "passenger_name": "Another User",
                "seat_number": "1A",
                "force_payment_success": True,
            },
        )
        assert duplicate.status_code == 409

        cancelled = client.delete(f"/db/booking/{payload['pnr']}")
        assert cancelled.status_code == 200

        db = SessionLocal()
        assert db.get(FlightModel, flight_id).available_seats == 10
        booking_record = db.query(BookingModel).filter(BookingModel.pnr == payload["pnr"]).first()
        assert booking_record.seat_number is None
        assert booking_record.status == "Cancelled"
        db.close()

        reused = client.post(
            "/db/booking",
            json={
                "flight_id": flight_id,
                "passenger_name": "Replacement User",
                "seat_number": "1A",
                "force_payment_success": True,
            },
        )
        assert reused.status_code == 201, reused.text

        pdf = client.post("/receipt/pdf", json={"pnr": reused.json()["pnr"]})
        assert pdf.status_code == 200
        assert pdf.headers["content-type"].startswith("application/pdf")
        assert pdf.content.startswith(b"%PDF")
