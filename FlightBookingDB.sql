-- PostgreSQL bootstrap schema for Flight Booking Simulator.
-- Render creates the database itself; run this script only when manually
-- creating the application schema in an existing PostgreSQL database.

DROP TABLE IF EXISTS FareHistory CASCADE;
DROP TABLE IF EXISTS Payments CASCADE;
DROP TABLE IF EXISTS Bookings CASCADE;
DROP TABLE IF EXISTS Passengers CASCADE;
DROP TABLE IF EXISTS Flights CASCADE;
DROP TABLE IF EXISTS Airlines CASCADE;

CREATE TABLE "Airlines" (
    airline_id SERIAL PRIMARY KEY,
    airline_name VARCHAR(100) NOT NULL,
    contact_number VARCHAR(20),
    email VARCHAR(100)
);

CREATE TABLE "Flights" (
    flight_id SERIAL PRIMARY KEY,
    airline_id INTEGER NOT NULL REFERENCES "Airlines"(airline_id),
    flight_number VARCHAR(20) NOT NULL UNIQUE,
    source VARCHAR(50) NOT NULL,
    destination VARCHAR(50) NOT NULL,
    departure_time TIMESTAMP NOT NULL,
    arrival_time TIMESTAMP NOT NULL,
    total_seats INTEGER NOT NULL,
    available_seats INTEGER NOT NULL,
    base_fare NUMERIC(10,2) DEFAULT 3000.00,
    pricing_tier VARCHAR(20) DEFAULT 'standard',
    simulated_demand INTEGER DEFAULT 50
);

CREATE TABLE "Passengers" (
    passenger_id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    gender CHAR(1),
    age INTEGER,
    email VARCHAR(100),
    phone VARCHAR(20)
);

CREATE TABLE "Bookings" (
    booking_id SERIAL PRIMARY KEY,
    flight_id INTEGER NOT NULL REFERENCES "Flights"(flight_id),
    passenger_id INTEGER NOT NULL REFERENCES "Passengers"(passenger_id),
    booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    seat_number VARCHAR(5),
    status VARCHAR(20) DEFAULT 'Confirmed',
    pnr VARCHAR(20) UNIQUE,
    price_per_seat NUMERIC(10,2),
    total_price NUMERIC(12,2)
);

CREATE TABLE "Payments" (
    payment_id SERIAL PRIMARY KEY,
    booking_id INTEGER NOT NULL REFERENCES "Bookings"(booking_id),
    amount NUMERIC(12,2) NOT NULL,
    payment_status VARCHAR(20) DEFAULT 'Success',
    payment_method VARCHAR(30) DEFAULT 'Simulated',
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE "FareHistory" (
    id SERIAL PRIMARY KEY,
    flight_id INTEGER NOT NULL REFERENCES "Flights"(flight_id),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    price NUMERIC(10,2) NOT NULL
);

INSERT INTO "Airlines" (airline_name, contact_number, email) VALUES
('Air India', '9876543210', 'contact@airindia.com'),
('IndiGo', '9988776655', 'contact@goindigo.in'),
('SpiceJet', '8877665544', 'contact@spicejet.com');

INSERT INTO "Flights"
(airline_id, flight_number, source, destination, departure_time, arrival_time,
 total_seats, available_seats, base_fare, pricing_tier, simulated_demand)
VALUES
((SELECT airline_id FROM "Airlines" WHERE airline_name = 'IndiGo'),
 '6E203', 'Delhi', 'Mumbai', CURRENT_TIMESTAMP + INTERVAL '6 hours',
 CURRENT_TIMESTAMP + INTERVAL '8 hours', 180, 150, 4000, 'standard', 60),
((SELECT airline_id FROM "Airlines" WHERE airline_name = 'Air India'),
 'AI440', 'Delhi', 'Chennai', CURRENT_TIMESTAMP + INTERVAL '12 hours',
 CURRENT_TIMESTAMP + INTERVAL '15 hours', 220, 200, 4500, 'economy', 30),
((SELECT airline_id FROM "Airlines" WHERE airline_name = 'SpiceJet'),
 'SG789', 'Bangalore', 'Kolkata', CURRENT_TIMESTAMP + INTERVAL '18 hours',
 CURRENT_TIMESTAMP + INTERVAL '21 hours', 150, 100, 3800, 'premium', 80);
