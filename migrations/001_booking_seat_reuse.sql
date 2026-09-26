-- Apply once to an existing flight_booking database created from the previous schema.
-- This preserves booking history while allowing a cancelled seat to be booked again.
USE flight_booking;
ALTER TABLE Bookings DROP INDEX uq_flight_seat;
ALTER TABLE Bookings MODIFY seat_number VARCHAR(5) NULL;
