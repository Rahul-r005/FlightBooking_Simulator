// ---------------------- Helper Functions ----------------------
function showSection(sectionId) {
  document.querySelectorAll("section").forEach(sec => sec.classList.add("hidden"));
  document.getElementById(sectionId).classList.remove("hidden");
}

// ---------------------- SEARCH FUNCTIONALITY ----------------------
document.getElementById("searchForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const origin = document.getElementById("origin").value.trim();
  const destination = document.getElementById("destination").value.trim();
  const date = document.getElementById("date").value;

  if (!origin || !destination || !date) {
    alert("Please fill all fields.");
    return;
  }

  showSection("results-section");
  const resultsDiv = document.getElementById("results");
  resultsDiv.innerHTML = "<p>Loading flights...</p>";

  try {
    const response = await fetch(`http://127.0.0.1:8000/flights/search?origin=${origin}&destination=${destination}&date=${date}`);
    const flights = await response.json();

    if (flights.length === 0) {
      resultsDiv.innerHTML = "<p>No flights found for the selected route.</p>";
      return;
    }

    resultsDiv.innerHTML = flights.map(f => `
      <div class="flight-card">
        <h3>${f.airline} - ${f.flight_number}</h3>
        <p>${f.origin} → ${f.destination}</p>
        <p>Departure: ${f.departure_time}</p>
        <p>Duration: ${f.duration}</p>
        <p>💰 Price: ₹${f.dynamic_price}</p>
        <button onclick="bookFlight('${f.flight_id}', ${f.dynamic_price}, '${f.flight_number}')">Book Now</button>
      </div>
    `).join("");
  } catch (error) {
    resultsDiv.innerHTML = "<p>⚠️ Error fetching flights. Check backend connection.</p>";
    console.error(error);
  }
});

document.getElementById("backToSearch").addEventListener("click", () => {
  showSection("search-section");
});

// ---------------------- BOOKING FUNCTIONALITY ----------------------
let selectedFlight = null;

function bookFlight(id, price, flightNumber) {
  selectedFlight = { id, price, flightNumber };
  showSection("booking-section");
}

document.getElementById("bookingForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  if (!selectedFlight) {
    alert("Please select a flight first.");
    showSection("search-section");
    return;
  }

  const passenger = {
    name: document.getElementById("name").value.trim(),
    email: document.getElementById("email").value.trim(),
    age: parseInt(document.getElementById("age").value)
  };

  try {
    const response = await fetch("http://127.0.0.1:8000/book", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        flight_id: selectedFlight.id,
        passenger,
        price: selectedFlight.price
      })
    });

    if (!response.ok) throw new Error("Booking failed");

    const data = await response.json();
    localStorage.setItem("bookingInfo", JSON.stringify(data));
    showConfirmation(data);
  } catch (error) {
    alert("Booking failed. Check backend connection.");
    console.error(error);
  }
});

document.getElementById("backToResults").addEventListener("click", () => {
  showSection("results-section");
});

// ---------------------- CONFIRMATION FUNCTIONALITY ----------------------
function showConfirmation(data) {
  showSection("confirmation-section");

  const div = document.getElementById("details");
  div.innerHTML = `
    <p><strong>PNR:</strong> ${data.pnr}</p>
    <p><strong>Flight:</strong> ${data.flight_number}</p>
    <p><strong>Passenger:</strong> ${data.passenger.name}</p>
    <p><strong>Price:</strong> ₹${data.price}</p>
  `;
}

document.getElementById("downloadJson").addEventListener("click", () => {
  const booking = JSON.parse(localStorage.getItem("bookingInfo"));
  const blob = new Blob([JSON.stringify(booking, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "booking_receipt.json";
  a.click();
});

document.getElementById("downloadPdf").addEventListener("click", async () => {
  const booking = JSON.parse(localStorage.getItem("bookingInfo"));
  try {
    const response = await fetch("http://127.0.0.1:8000/receipt/pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(booking)
    });
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "booking_receipt.pdf";
    a.click();
  } catch (error) {
    alert("Failed to download PDF. Check backend.");
  }
});

document.getElementById("backToHome").addEventListener("click", () => {
  location.reload();
});
