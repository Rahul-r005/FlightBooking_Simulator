✈️ Flight Booking Simulator with Dynamic Pricing
A FastAPI-based web application built using Python, React, HTML, and CSS, designed to simulate flight bookings with dynamic pricing logic instead of fixed ticket prices.
Developed as part of an internship, this project focuses on backend logic, frontend interaction, and a realistic airline-like booking simulation.

🎥 Project Overview
🌟 Features
🔐 Secure user authentication (Signup, Login, Logout)
🛫 Search and book flights with dynamically changing prices
💸 Prices vary based on seat availability, time to departure, and demand
🧾 Displays booking details and ticket confirmation after simulated payment
🔁 Supports both one-way and round-trip bookings
📜 Allows users to view and manage their booking history
🧑‍💼 Admin panel for managing flights, users, and dynamic pricing logic
💻 Responsive and clean UI built with React
🧩 Fully self-contained — no external airline APIs required
🧩 Tech Stack
Frontend
HTML
CSS
JS

Backend
FastAPI (Python Framework)

Database
MySQL

Development Tools
Visual Studio Code
Git & GitHub
SQLAlchemy / Pydantic (for database models and validation)

🏗️ System Architecture
The project follows a Three-Tier Architecture:

1️⃣ Presentation Layer (Frontend)
Built using HTML,CSS and JS
Provides real-time flight data and dynamic price updates

2️⃣ Application Layer (Backend - FastAPI)
Handles authentication, flight search, and booking logic
Implements dynamic pricing algorithms and seat availability tracking
Exposes RESTful APIs consumed by the frontend

3️⃣ Data Layer (Database - MySQL)
Stores user, flight, and booking information
Maintains transaction details and price adjustments
Flow:
User → Frontend → FastAPI Endpoints → MySQL Database → JSON Response → Rendered UI

🧠 Future Scope
💡 Coupon Code System — Apply discounts during booking (in progress)
💬 Email Notifications — Send booking and payment confirmations
🔁 Refund Module — Handle flight cancellations and refunds
🧭 Real API Integration — Connect with live airline APIs like Amadeus or Skyscanner
📊 Admin Dashboard — Visualize bookings, pricing trends, and demand analytics
⚡ Justification
🧱 Fully self-contained — no real airline data required
🧠 Demonstrates real-world dynamic pricing and booking logic
📱 Built with React frontend and FastAPI backend
🧩 Modular and extensible — easy to adapt for research or academic purposes
