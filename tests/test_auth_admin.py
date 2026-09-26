from fastapi.testclient import TestClient

from FlightBooking_backend import BookingModel, SessionLocal, UserModel, app


def register(client: TestClient, email: str, name: str) -> None:
    response = client.post(
        "/auth/register",
        json={
            "full_name": name,
            "email": email,
            "password": "correct-horse-battery",
        },
    )
    assert response.status_code == 201, response.text


def promote(email: str) -> None:
    db = SessionLocal()
    user = db.query(UserModel).filter(UserModel.email == email).first()
    user.role = "admin"
    db.commit()
    db.close()


def test_non_admin_cannot_access_admin_routes():
    with TestClient(app) as client:
        register(client, "user@example.com", "Regular User")
        assert client.get("/admin").status_code == 403
        assert client.get("/admin/accounts").status_code == 403


def test_admin_can_manage_accounts_and_cancel_booking():
    with TestClient(app) as client:
        register(client, "admin@example.com", "Admin User")
        promote("admin@example.com")
        client.post("/auth/logout")

        register(client, "customer@example.com", "Customer User")
        flight = client.get("/flights").json()[0]

        booking = client.post(
            "/db/booking",
            json={
                "flight_id": flight["flight_id"],
                "passenger_name": "Customer User",
                "passenger_email": "customer@example.com",
                "seat_number": "3A",
                "force_payment_success": True,
            },
        )
        assert booking.status_code == 201, booking.text
        pnr = booking.json()["pnr"]
        client.post("/auth/logout")

        login = client.post(
            "/auth/login",
            json={
                "email": "admin@example.com",
                "password": "correct-horse-battery",
            },
        )
        assert login.status_code == 200, login.text

        accounts = client.get("/admin/accounts")
        assert accounts.status_code == 200
        assert any(account["email"] == "customer@example.com" for account in accounts.json())

        all_bookings = client.get("/admin/bookings")
        assert all_bookings.status_code == 200
        assert any(item["pnr"] == pnr for item in all_bookings.json())

        cancellation = client.post(f"/admin/bookings/{pnr}/cancel")
        assert cancellation.status_code == 200, cancellation.text
        assert cancellation.json()["notification_created"] is True

        db = SessionLocal()
        booking_record = db.query(BookingModel).filter(BookingModel.pnr == pnr).first()
        assert booking_record.status == "Cancelled"
        assert booking_record.seat_number is None
        db.close()

        client.post("/auth/logout")
        customer_login = client.post(
            "/auth/login",
            json={
                "email": "customer@example.com",
                "password": "correct-horse-battery",
            },
        )
        assert customer_login.status_code == 200
        notifications = client.get("/notifications")
        assert notifications.status_code == 200
        assert any(pnr in item["message"] for item in notifications.json())
