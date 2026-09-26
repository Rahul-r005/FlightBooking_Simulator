import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    DECIMAL,
    ForeignKey,
    Index,
    Integer,
    String,
    create_engine,
    func,
    inspect,
    text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker


def _database_url() -> str:
    url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if not url:
        return "sqlite:///./flight_booking.db"
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


DATABASE_URL = _database_url()
engine_options = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
Base = declarative_base()


class UserModel(Base):
    __tablename__ = "Users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user", index=True)
    suspended = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime, server_default=func.now())


class SessionModel(Base):
    __tablename__ = "UserSessions"

    session_id = Column(Integer, primary_key=True, autoincrement=True)
    token_digest = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("Users.user_id"), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("UserModel")


class NotificationModel(Base):
    __tablename__ = "Notifications"

    notification_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("Users.user_id"), nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey("Bookings.booking_id"), nullable=True, index=True)
    message = Column(String(500), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    read = Column(Boolean, nullable=False, default=False)
    user = relationship("UserModel")


class AirlineModel(Base):
    __tablename__ = "Airlines"

    airline_id = Column(Integer, primary_key=True, autoincrement=True)
    airline_name = Column(String(100), nullable=False)
    contact_number = Column(String(20))
    email = Column(String(100))


class FlightModel(Base):
    __tablename__ = "Flights"

    flight_id = Column(Integer, primary_key=True, autoincrement=True)
    airline_id = Column(Integer, ForeignKey("Airlines.airline_id"), nullable=False)
    flight_number = Column(String(20), unique=True, nullable=False)
    source = Column(String(50), nullable=False, index=True)
    destination = Column(String(50), nullable=False, index=True)
    departure_time = Column(DateTime, nullable=False, index=True)
    arrival_time = Column(DateTime, nullable=False)
    total_seats = Column(Integer, nullable=False)
    available_seats = Column(Integer, nullable=False)
    base_fare = Column(DECIMAL(10, 2), default=3000.00)
    pricing_tier = Column(String(20), default="standard")
    simulated_demand = Column(Integer, default=50)
    airline = relationship("AirlineModel")
    bookings = relationship("BookingModel", back_populates="flight")


class PassengerModel(Base):
    __tablename__ = "Passengers"

    passenger_id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(100), nullable=False)
    gender = Column(String(1))
    age = Column(Integer)
    email = Column(String(100), index=True)
    phone = Column(String(20))
    bookings = relationship("BookingModel", back_populates="passenger")


class BookingModel(Base):
    __tablename__ = "Bookings"

    booking_id = Column(Integer, primary_key=True, autoincrement=True)
    flight_id = Column(Integer, ForeignKey("Flights.flight_id"), nullable=False, index=True)
    passenger_id = Column(Integer, ForeignKey("Passengers.passenger_id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("Users.user_id"), nullable=True, index=True)
    booking_date = Column(DateTime, server_default=func.now(), index=True)
    seat_number = Column(String(5), nullable=True)
    status = Column(String(20), default="Confirmed", index=True)
    pnr = Column(String(20), unique=True, nullable=True, index=True)
    price_per_seat = Column(DECIMAL(10, 2), nullable=True)
    total_price = Column(DECIMAL(12, 2), nullable=True)
    user = relationship("UserModel")
    flight = relationship("FlightModel", back_populates="bookings")
    passenger = relationship("PassengerModel", back_populates="bookings")


class PaymentModel(Base):
    __tablename__ = "Payments"

    payment_id = Column(Integer, primary_key=True, autoincrement=True)
    booking_id = Column(Integer, ForeignKey("Bookings.booking_id"), nullable=False, index=True)
    amount = Column(DECIMAL(12, 2), nullable=False)
    payment_status = Column(String(20), default="Success")
    payment_method = Column(String(30), default="Simulated")
    payment_date = Column(DateTime, server_default=func.now())


class FareHistoryModel(Base):
    __tablename__ = "FareHistory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    flight_id = Column(Integer, ForeignKey("Flights.flight_id"), nullable=False, index=True)
    recorded_at = Column(DateTime, server_default=func.now())
    price = Column(DECIMAL(10, 2), nullable=False)


def _add_missing_columns() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    if "Bookings" in table_names:
        booking_columns = {column["name"] for column in inspector.get_columns("Bookings")}
        if "user_id" not in booking_columns and "Users" in table_names:
            with engine.begin() as connection:
                connection.execute(text('ALTER TABLE "Bookings" ADD COLUMN user_id INTEGER'))
                if not DATABASE_URL.startswith("sqlite"):
                    connection.execute(
                        text(
                            'ALTER TABLE "Bookings" ADD CONSTRAINT fk_bookings_user '
                            'FOREIGN KEY (user_id) REFERENCES "Users" (user_id)'
                        )
                    )


def seed_initial_data() -> None:
    db = SessionLocal()
    try:
        if db.query(FlightModel).first():
            return

        airlines = {
            "Air India": AirlineModel(
                airline_name="Air India",
                contact_number="9876543210",
                email="contact@airindia.com",
            ),
            "IndiGo": AirlineModel(
                airline_name="IndiGo",
                contact_number="9988776655",
                email="contact@goindigo.in",
            ),
            "SpiceJet": AirlineModel(
                airline_name="SpiceJet",
                contact_number="8877665544",
                email="contact@spicejet.com",
            ),
        }
        db.add_all(airlines.values())
        db.flush()

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db.add_all(
            [
                FlightModel(
                    airline_id=airlines["IndiGo"].airline_id,
                    flight_number="6E203",
                    source="Delhi",
                    destination="Mumbai",
                    departure_time=now + timedelta(hours=6),
                    arrival_time=now + timedelta(hours=8),
                    total_seats=180,
                    available_seats=150,
                    base_fare=4000,
                    pricing_tier="standard",
                    simulated_demand=60,
                ),
                FlightModel(
                    airline_id=airlines["Air India"].airline_id,
                    flight_number="AI440",
                    source="Delhi",
                    destination="Chennai",
                    departure_time=now + timedelta(hours=12),
                    arrival_time=now + timedelta(hours=15),
                    total_seats=220,
                    available_seats=200,
                    base_fare=4500,
                    pricing_tier="economy",
                    simulated_demand=30,
                ),
                FlightModel(
                    airline_id=airlines["SpiceJet"].airline_id,
                    flight_number="SG789",
                    source="Bangalore",
                    destination="Kolkata",
                    departure_time=now + timedelta(hours=18),
                    arrival_time=now + timedelta(hours=21),
                    total_seats=150,
                    available_seats=100,
                    base_fare=3800,
                    pricing_tier="premium",
                    simulated_demand=80,
                ),
            ]
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()
    seed_initial_data()
