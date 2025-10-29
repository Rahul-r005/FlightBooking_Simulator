CREATE DATABASE flight_booking;

USE flight_booking;

CREATE TABLE Airlines (
    airline_id INT PRIMARY KEY AUTO_INCREMENT,
    airline_name VARCHAR(100) NOT NULL,
    contact_number VARCHAR(15),
    email VARCHAR(50)
);

CREATE TABLE Flights (
    flight_id INT PRIMARY KEY AUTO_INCREMENT,
    airline_id INT,
    flight_number VARCHAR(10) UNIQUE NOT NULL,
    source VARCHAR(50),
    destination VARCHAR(50),
    departure_time DATETIME,
    arrival_time DATETIME,
    total_seats INT,
    available_seats INT,
    FOREIGN KEY (airline_id) REFERENCES Airlines(airline_id)
);

CREATE TABLE Passengers (
    passenger_id INT PRIMARY KEY AUTO_INCREMENT,
    full_name VARCHAR(100),
    gender CHAR(1),
    age INT,
    email VARCHAR(50),
    phone VARCHAR(15)
);

CREATE TABLE Bookings (
    booking_id INT PRIMARY KEY AUTO_INCREMENT,
    flight_id INT,
    passenger_id INT,
    booking_date DATETIME DEFAULT NOW(),
    seat_number VARCHAR(5),
    status VARCHAR(20) DEFAULT 'Confirmed',
    FOREIGN KEY (flight_id) REFERENCES Flights(flight_id),
    FOREIGN KEY (passenger_id) REFERENCES Passengers(passenger_id)
);

--Insert
INSERT INTO Airlines (airline_name, contact_number, email) VALUES
('Air India', '9876543210', 'contact@airindia.com'),
('IndiGo', '9988776655', 'contact@goindigo.in'),
('DEccan Air','8866654522', 'contact@deccanair.com');

INSERT INTO Flights (airline_id, flight_number, source, destination, departure_time, arrival_time, total_seats, available_seats)
VALUES 
(1, 'AI202', 'Delhi', 'Mumbai', '2025-10-10 08:00:00', '2025-10-10 10:15:00', 180, 160),
(2, '6E305', 'Chennai', 'Bangalore', '2025-10-10 09:30:00', '2025-10-10 10:45:00', 150, 145);

INSERT INTO Passengers (full_name, gender, age, email, phone) VALUES 
('Rahul R', 'M', 20, 'rahul@gmail.com', '9998887776'),
('Prabha R', 'M', 22, 'prabga@gmail.com', '8887776665'),
('Sanjay G', 'M', 32, 'sanjau@gmail.com', '7776688441');

INSERT INTO Bookings (flight_id, passenger_id, seat_number) VALUES 
(1, 1, '12A'),
(2, 2, '8B'),
(3, 3, '12C');

--Viewing data
SELECT * FROM Airlines;
SELECT * FROM Flights;
SELECT * FROM Passengers;
SELECT * FROM Bookings;
SELECT * FROM Payments;

-- filtering data
SELECT * FROM Flights WHERE source = 'Delhi';
SELECT * FROM Flights WHERE total_seats > 150;

--Sorting data
SELECT flight_number, source, destination, departure_time FROM Flights ORDER BY departure_time ASC;
SELECT full_name, age FROM Passengers ORDER BY full_name DESC;

--Aggregate functions
SELECT COUNT(*) AS total_flights FROM Flights;


--GROUP BY and HAVING
SELECT flight_id, COUNT(booking_id) AS total_bookings FROM Bookings GROUP BY flight_id;
SELECT flight_id, COUNT(*) AS num_bookings FROM Bookings GROUP BY flight_id HAVING COUNT(*) > 1;

--Joins
-- Passengers with their booking status
SELECT P.full_name, B.seat_number, B.status FROM Passengers P
INNER JOIN Bookings B ON P.passenger_id = B.passenger_id;

-- Flights with their airlines
SELECT F.flight_number, A.airline_name, F.source, F.destination FROM Flights F
INNER JOIN Airlines A ON F.airline_id = A.airline_id;

-- Passengers with flight details
SELECT P.full_name, F.flight_number, F.source, F.destination, B.seat_number FROM Passengers P
JOIN Bookings B ON P.passenger_id = B.passenger_id
JOIN Flights F ON B.flight_id = F.flight_id;

--ALTER, UPDATE, DELETE
ALTER TABLE Flights ADD COLUMN flight_status VARCHAR(20) DEFAULT 'On Time';
-- add base_fare, pricing_tier, and simulated_demand columns
ALTER TABLE Flights
  ADD COLUMN base_fare DECIMAL(10,2) DEFAULT 3000.00,
  ADD COLUMN pricing_tier VARCHAR(20) DEFAULT 'standard',
  ADD COLUMN simulated_demand INT DEFAULT 50; 

--Transactions
START TRANSACTION;
INSERT INTO Bookings (flight_id, passenger_id, seat_number) VALUES (1, 1, '14C');
UPDATE Flights SET available_seats = available_seats - 1 WHERE flight_id = 1;
COMMIT;

-- ROLLBACK;
