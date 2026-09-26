import os
import random
import threading

from .database import FlightModel, SessionLocal


class FlightAvailabilitySimulator:
    """Adjust demo demand and seat availability in a background thread."""

    def __init__(self, interval_seconds: int = 30):
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread = None

    def start(self) -> None:
        if os.getenv("DISABLE_BACKGROUND_SIMULATOR", "").lower() in {"1", "true", "yes"}:
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="flight-simulator",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._thread = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self._update_flights()
            self._stop_event.wait(self.interval_seconds)

    def _update_flights(self) -> None:
        db = SessionLocal()
        try:
            flights = db.query(FlightModel).all()
            for flight in flights:
                flight.simulated_demand = max(
                    0,
                    min(100, (flight.simulated_demand or 50) + random.randint(-8, 10)),
                )
                self._update_seat_availability(flight)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    @staticmethod
    def _update_seat_availability(flight: FlightModel) -> None:
        if random.random() < 0.12 and flight.available_seats > 0:
            seats_to_remove = random.randint(1, min(3, flight.available_seats))
            flight.available_seats = max(0, flight.available_seats - seats_to_remove)
        elif random.random() > 0.995:
            flight.available_seats = min(flight.total_seats, flight.available_seats + 1)
