# ✈️ Flight Booking Simulator

SkyBook is a small FastAPI flight-booking application with a browser frontend, PostgreSQL/SQLite persistence, dynamic fares, simulated payments, and seat management.

## Architecture

The repository keeps the deployment entrypoint at `FlightBooking_backend.py` so the existing Render configuration does not need to change. The implementation is split by responsibility:

```text
FlightBooking_backend.py        compatibility entrypoint
flight_booking/
├── api.py                      FastAPI routes and HTTP behavior
├── database.py                 SQLAlchemy models, connection, and seed data
├── pricing.py                  flight fare calculations and PNR generation
├── schemas.py                  API request/response models
└── simulator.py                background demand and seat simulation
frontend/
├── index.html                  application page
├── script.js                   browser API and booking interactions
├── style.css                   application styles
├── 404.html                    themed HTML 404 page
└── favicon.svg                 SkyBook favicon
migrations/                     PostgreSQL schema migration
FlightBookingDB.sql             standalone PostgreSQL bootstrap schema
render.yaml                     Render web service and database definition
.github/workflows/              regression checks
```

There is deliberately no generic `utils` or service layer. Shared behavior stays next to the flight-booking concept it belongs to.

## Features

- Search flights by origin, destination, and date
- Dynamic pricing based on demand, remaining seats, and departure time
- Database-backed flight inventory
- Seat format validation and duplicate-seat protection
- Simulated payment with transaction rollback on failure
- Booking confirmation with a PNR
- Booking history
- Booking cancellation with seat restoration
- Reuse of a seat after cancellation
- Fare history recording
- PDF receipt generation
- Background demand/availability simulation in the running application
- Deterministic tests with the background simulator disabled
- Starter flights created automatically when the database is empty

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

The older in-memory demonstration endpoints remain available under `/legacy/` for compatibility.

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

Open `http://127.0.0.1:8000`.

When `DATABASE_URL` is not set, the application uses `flight_booking.db` with SQLite. A PostgreSQL URL is accepted through either `DATABASE_URL` or `POSTGRES_URL`.

## Testing

The regression suite checks the real booking workflow:

- Python compilation
- JavaScript syntax
- API health
- starter-data creation
- flight retrieval and search
- CORS behavior
- invalid seat rejection
- payment-failure rollback
- successful booking and payment record
- duplicate-seat rejection
- cancellation and seat restoration
- seat reuse after cancellation
- PDF receipt generation

Run the same checks locally:

```bash
pip install -r requirements.txt
pip install pytest
python -m compileall -q FlightBooking_backend.py flight_booking tests
node --check frontend/script.js
python -m pytest -q
```

Tests use one isolated SQLite database and an autouse fixture, so the suite is safe to run as one pytest process. `DISABLE_BACKGROUND_SIMULATOR=1` prevents the demo simulator from changing inventory while assertions are running.

## Render deployment

`render.yaml` defines the existing Render web service and Postgres database. The web service keeps this start command:

```text
uvicorn FlightBooking_backend:app --host 0.0.0.0 --port $PORT
```

The application converts Render's `postgresql://` connection string to SQLAlchemy's `postgresql+psycopg2://` dialect because the project installs `psycopg2-binary`.

Render serves the frontend from the same FastAPI service, so there is no second frontend deployment to keep synchronized.

The database tables are created by SQLAlchemy at application startup. `FlightBookingDB.sql` is provided for manual PostgreSQL setup; Render does not need it during a normal deploy.

The free Render Postgres plan is suitable for the project's demo/development deployment and has a limited lifetime.

## Database migration

`migrations/001_booking_seat_reuse.sql` allows a cancelled seat to be cleared from a booking while retaining the booking record for history. A cancelled seat can therefore be booked again without creating a duplicate active seat assignment.

## Deployment safety

The Render service tracks `main` and auto-deploys repository changes. The application entrypoint and Render start command are intentionally unchanged by the code-organization refactor, so restructuring the Python modules does not require a deployment configuration migration.
