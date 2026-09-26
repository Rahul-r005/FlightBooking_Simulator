-- PostgreSQL migration for an existing Flight Booking Simulator database.
-- Allows a cancelled seat to be booked again while preserving booking history.

DROP INDEX IF EXISTS uq_flight_seat;

ALTER TABLE "Bookings"
    ALTER COLUMN seat_number DROP NOT NULL;
