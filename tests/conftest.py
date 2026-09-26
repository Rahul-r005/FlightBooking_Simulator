import os

import pytest

os.environ["DATABASE_URL"] = "sqlite:///./test_flight_booking.db"
os.environ["DISABLE_BACKGROUND_SIMULATOR"] = "1"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:5500"
os.environ["ENVIRONMENT"] = "development"

from FlightBooking_backend import Base, engine


@pytest.fixture(autouse=True)
def reset_test_database():
    engine.dispose()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()
