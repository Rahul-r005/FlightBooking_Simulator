from fastapi.testclient import TestClient

from FlightBooking_backend import app


def sign_in(client: TestClient, email: str = "recovery@example.com") -> None:
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Recovery User",
            "email": email,
            "password": "correct-horse-battery",
        },
    )
    assert response.status_code == 201, response.text


def test_health_and_seeded_flights():
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        response = client.get("/flights")
        assert response.status_code == 200
        assert len(response.json()) >= 3


def test_booking_cancellation_and_seat_reuse():
    with TestClient(app) as client:
        sign_in(client)
        flights = client.get("/flights").json()
        flight_id = flights[0]["flight_id"]
        available_before = flights[0]["available_seats"]

        booking = client.post(
            "/db/booking",
            json={
                "flight_id": flight_id,
                "passenger_name": "Test Passenger",
                "passenger_email": "test@example.com",
                "seat_number": "1A",
                "force_payment_success": True,
            },
        )
        assert booking.status_code == 201, booking.text
        pnr = booking.json()["pnr"]

        after_booking = client.get(f"/db/flights/{flight_id}").json()
        assert after_booking["available_seats"] == available_before - 1

        cancelled = client.delete(f"/db/booking/{pnr}")
        assert cancelled.status_code == 200, cancelled.text

        after_cancel = client.get(f"/db/flights/{flight_id}").json()
        assert after_cancel["available_seats"] == available_before

        notifications = client.get("/notifications")
        assert notifications.status_code == 200
        assert not any(pnr in item["message"] for item in notifications.json())

        reused = client.post(
            "/db/booking",
            json={
                "flight_id": flight_id,
                "passenger_name": "Second Passenger",
                "passenger_email": "second@example.com",
                "seat_number": "1A",
                "force_payment_success": True,
            },
        )
        assert reused.status_code == 201, reused.text
        client.delete(f"/db/booking/{reused.json()['pnr']}")


def test_duplicate_seat_is_rejected():
    with TestClient(app) as client:
        sign_in(client)
        flight_id = client.get("/flights").json()[0]["flight_id"]

        first = client.post(
            "/db/booking",
            json={
                "flight_id": flight_id,
                "passenger_name": "Seat Holder One",
                "seat_number": "2A",
                "force_payment_success": True,
            },
        )
        assert first.status_code == 201, first.text

        second = client.post(
            "/db/booking",
            json={
                "flight_id": flight_id,
                "passenger_name": "Seat Holder Two",
                "seat_number": "2A",
                "force_payment_success": True,
            },
        )
        assert second.status_code == 409, second.text
        client.delete(f"/db/booking/{first.json()['pnr']}")
