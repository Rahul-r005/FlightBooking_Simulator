# ✈️ Flight Booking Simulator

A self-contained FastAPI flight-booking simulator with a browser frontend and database-backed dynamic pricing.

## Current architecture

- **Frontend:** HTML, CSS and JavaScript in `frontend/`
- **Backend:** FastAPI in `FlightBooking_backend.py`
- **ORM:** SQLAlchemy
- **Production database:** Render Postgres
- **Local fallback:** SQLite (`flight_booking.db`)
- **Deployment:** Render Blueprint in `render.yaml`
- **Tests:** pytest + FastAPI TestClient

The application serves the frontend and API from the same FastAPI web service.

## Features

- Search flights by origin, destination and date
- Dynamic pricing based on demand, seat availability and time to departure
- Database-backed flight inventory
- Seat validation and duplicate-seat protection
- Simulated payment
- Booking confirmation with PNR
- Booking history
- Booking cancellation with seat restoration
- Cancelled seats can be booked again
- Dynamic fare history
- PDF receipt endpoint
- Background demand/availability simulation
- Starter flight data is created automatically when an empty database is detected

## API

### Health
`GET /health`

### Flights
- `GET /flights`
- `GET /flights/search`
- `GET /db/flights`
- `GET /db/flights/{flight_id}`
- `GET /db/dynamic_price/{flight_id}`

### Booking
- `POST /db/booking`
- `GET /db/bookings`
- `GET /db/booking/{pnr}`
- `DELETE /db/booking/{pnr}`
- `POST /db/bookings/{pnr}/pay`
- `POST /receipt/pdf`

The older in-memory demonstration endpoints remain under `/legacy/`.

## Local development

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn FlightBooking_backend:app --reload
```

Open:

```
http://127.0.0.1:8000
```

When `DATABASE_URL` is not provided, the application uses local SQLite automatically.

## Render deployment

The repository contains `render.yaml`, which defines:

1. A free Render Python web service.
2. A free Render Postgres database.
3. An internal `DATABASE_URL` connection from the web service to the Postgres database.

Render's Blueprint `fromDatabase.connectionString` provides the Postgres connection string to the service. The application explicitly converts Render's `postgresql://` URL to SQLAlchemy's `postgresql+psycopg2://` dialect because the project installs `psycopg2-binary`.

To deploy, connect the repository to Render and create a new Blueprint instance from `render.yaml`.

## Verification

The CI workflow in `.github/workflows/recovery-tests.yml` checks:

- Python compilation
- JavaScript syntax
- API health
- automatic starter-data creation
- flight retrieval
- booking
- seat availability changes
- booking cancellation
- seat reuse after cancellation
- duplicate-seat rejection

Run locally:

```bash
pip install -r requirements.txt
pip install pytest
python -m compileall -q FlightBooking_backend.py tests
node --check frontend/script.js
python -m pytest -q
```

## Database notes

The application creates its SQLAlchemy tables automatically at startup. `FlightBookingDB.sql` is a standalone PostgreSQL bootstrap script for manual database setup; Render deployment does not require running it.

Free Render Postgres instances have a limited lifetime, so the deployment is intended for development/demo use rather than durable production storage.

## Project structure

```text
.
├── FlightBooking_backend.py
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── tests/
│   └── test_recovery.py
├── migrations/
│   └── 001_booking_seat_reuse.sql
├── FlightBookingDB.sql
├── requirements.txt
├── render.yaml
└── .github/workflows/recovery-tests.yml
```
