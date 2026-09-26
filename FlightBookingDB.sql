CREATE DATABASE IF NOT EXISTS flight_booking CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE flight_booking;
SET FOREIGN_KEY_CHECKS=0;
DROP TABLE IF EXISTS FareHistory;
DROP TABLE IF EXISTS Payments;
DROP TABLE IF EXISTS Bookings;
DROP TABLE IF EXISTS Passengers;
DROP TABLE IF EXISTS Flights;
DROP TABLE IF EXISTS Airlines;
SET FOREIGN_KEY_CHECKS=1;

CREATE TABLE Airlines (
 airline_id INT PRIMARY KEY AUTO_INCREMENT,
 airline_name VARCHAR(100) NOT NULL,
 contact_number VARCHAR(20),
 email VARCHAR(100)
);
CREATE TABLE Flights (
 flight_id INT PRIMARY KEY AUTO_INCREMENT,
 airline_id INT NOT NULL,
 flight_number VARCHAR(20) NOT NULL UNIQUE,
 source VARCHAR(50) NOT NULL,
 destination VARCHAR(50) NOT NULL,
 departure_time DATETIME NOT NULL,
 arrival_time DATETIME NOT NULL,
 total_seats INT NOT NULL,
 available_seats INT NOT NULL,
 flight_status VARCHAR(20) DEFAULT 'On Time',
 base_fare DECIMAL(10,2) DEFAULT 3000.00,
 pricing_tier VARCHAR(20) DEFAULT 'standard',
 simulated_demand INT DEFAULT 50,
 FOREIGN KEY (airline_id) REFERENCES Airlines(airline_id)
);
CREATE TABLE Passengers (
 passenger_id INT PRIMARY KEY AUTO_INCREMENT,
 full_name VARCHAR(100) NOT NULL,
 gender CHAR(1),
 age INT,
 email VARCHAR(100),
 phone VARCHAR(20)
);
CREATE TABLE Bookings (
 booking_id INT PRIMARY KEY AUTO_INCREMENT,
 flight_id INT NOT NULL,
 passenger_id INT NOT NULL,
 booking_date DATETIME DEFAULT CURRENT_TIMESTAMP,
 seat_number VARCHAR(5) NULL,
 status VARCHAR(20) DEFAULT 'Confirmed',
 pnr VARCHAR(20) NOT NULL UNIQUE,
 price_per_seat DECIMAL(10,2) NOT NULL,
 total_price DECIMAL(12,2) NOT NULL,
 FOREIGN KEY (flight_id) REFERENCES Flights(flight_id),
 FOREIGN KEY (passenger_id) REFERENCES Passengers(passenger_id)
);
CREATE TABLE Payments (
 payment_id INT PRIMARY KEY AUTO_INCREMENT,
 booking_id INT NOT NULL,
 amount DECIMAL(12,2) NOT NULL,
 payment_status VARCHAR(20) DEFAULT 'Success',
 payment_method VARCHAR(30) DEFAULT 'Simulated',
 payment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (booking_id) REFERENCES Bookings(booking_id)
);
CREATE TABLE FareHistory (
 id INT PRIMARY KEY AUTO_INCREMENT,
 flight_id INT NOT NULL,
 recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
 price DECIMAL(10,2) NOT NULL,
 FOREIGN KEY (flight_id) REFERENCES Flights(flight_id)
);
INSERT INTO Airlines (airline_name,contact_number,email) VALUES
('Air India','9876543210','contact@airindia.com'),
('IndiGo','9988776655','contact@goindigo.in'),
('SpiceJet','8877665544','contact@spicejet.com');
INSERT INTO Flights
(airline_id,flight_number,source,destination,departure_time,arrival_time,total_seats,available_seats,flight_status,base_fare,pricing_tier,simulated_demand)
VALUES
(2,'6E203','Delhi','Mumbai',DATE_ADD(NOW(),INTERVAL 6 HOUR),DATE_ADD(NOW(),INTERVAL 8 HOUR),180,150,'On Time',4000,'standard',60),
(1,'AI440','Delhi','Chennai',DATE_ADD(NOW(),INTERVAL 12 HOUR),DATE_ADD(NOW(),INTERVAL 15 HOUR),220,200,'On Time',4500,'economy',30),
(3,'SG789','Bangalore','Kolkata',DATE_ADD(NOW(),INTERVAL 18 HOUR),DATE_ADD(NOW(),INTERVAL 21 HOUR),150,100,'On Time',3800,'premium',80);
