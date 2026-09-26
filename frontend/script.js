const configuredApi = localStorage.getItem("API_URL");
const API = (configuredApi || window.location.origin || "http://127.0.0.1:8000").replace(/\/$/, "");

const flightList = document.querySelector("#flightList");
const statusMessage = document.querySelector("#status");
const bookingList = document.querySelector("#bookingList");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatMoney(value) {
  return `₹${Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function showStatus(message, isError = false) {
  statusMessage.textContent = message;
  statusMessage.style.color = isError ? "#b42318" : "#667085";
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "The request could not be completed.");
  }

  return data;
}

async function getFlights(params = {}) {
  const query = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value) {
      query.set(key, value);
    }
  }

  const suffix = query.toString() ? `?${query}` : "";
  return apiRequest(`/flights${suffix}`);
}

function renderFlights(flights) {
  if (!flights.length) {
    flightList.innerHTML = '<div class="status">No flights found.</div>';
    return;
  }

  flightList.innerHTML = flights.map((flight) => `
    <article class="flight-card">
      <div>
        <div class="airline">${escapeHtml(flight.airline)}</div>
        <div class="flight-number">${escapeHtml(flight.flight_number)}</div>
      </div>
      <div>
        <div class="route">
          ${escapeHtml(flight.source)} <span>→</span> ${escapeHtml(flight.destination)}
        </div>
        <div class="flight-number">
          ${escapeHtml(new Date(flight.departure_time).toLocaleString())}
          · ${flight.duration_minutes} min · ${flight.available_seats} seats left
        </div>
      </div>
      <div class="fare">
        <strong>${formatMoney(flight.dynamic_price)}</strong>
        <span class="tier">${escapeHtml(flight.pricing_tier)}</span>
      </div>
      <button
        class="primary-btn book-btn"
        data-flight-id="${flight.flight_id}"
        data-flight-name="${escapeHtml(`${flight.airline} ${flight.flight_number}`)}"
        data-price="${flight.dynamic_price}"
      >
        Book
      </button>
    </article>
  `).join("");
}

async function loadFlights() {
  try {
    showStatus("Loading live fares…");
    renderFlights(await getFlights());
    showStatus("Fares calculated from current seat, demand and departure data.");
  } catch (error) {
    showStatus(`${error.message} — make sure FastAPI is running.`, true);
    flightList.innerHTML = "";
  }
}

function openBooking(flightId, flightName, price) {
  document.querySelector("#bookingForm").reset();
  document.querySelector("#flightId").value = flightId;
  document.querySelector("#modalFlight").textContent = `${flightName} · ${formatMoney(price)} / seat`;
  document.querySelector("#bookingStatus").textContent = "";
  document.querySelector("#modal").classList.remove("hidden");
}

function closeBookingModal() {
  document.querySelector("#modal").classList.add("hidden");
}

async function submitBooking(event) {
  event.preventDefault();
  const bookingStatus = document.querySelector("#bookingStatus");
  bookingStatus.textContent = "Processing simulated payment…";

  const requestBody = {
    flight_id: Number(document.querySelector("#flightId").value),
    passenger_name: document.querySelector("#passengerName").value,
    passenger_email: document.querySelector("#passengerEmail").value || null,
    passenger_phone: document.querySelector("#passengerPhone").value || null,
    seat_number: document.querySelector("#seatNumber").value || null,
    force_payment_success: true,
  };

  try {
    const booking = await apiRequest("/db/booking", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody),
    });

    bookingStatus.textContent = `Booking confirmed. PNR: ${booking.pnr}`;
    bookingStatus.style.color = "#087443";
    await loadFlights();
    await loadBookings();
  } catch (error) {
    bookingStatus.textContent = error.message;
    bookingStatus.style.color = "#b42318";
  }
}

async function loadBookings() {
  bookingList.innerHTML = '<div class="status">Loading…</div>';

  try {
    const bookings = await apiRequest("/db/bookings");
    if (!bookings.length) {
      bookingList.innerHTML = '<div class="status">No bookings yet.</div>';
      return;
    }

    bookingList.innerHTML = bookings.map((booking) => `
      <div class="booking-card">
        <div>
          <b>PNR ${escapeHtml(booking.pnr)}</b>
          <div class="muted">
            Flight #${booking.flight_id} · Seat ${escapeHtml(booking.seat_number || "—")}
            · ${escapeHtml(new Date(booking.booking_date).toLocaleString())}
          </div>
        </div>
        <div>
          <b>${formatMoney(booking.total_price)}</b>
          <div class="confirmed">${escapeHtml(booking.status)}</div>
          ${booking.status === "Confirmed" ? `
            <button class="ghost-btn cancel-btn" data-pnr="${escapeHtml(booking.pnr)}">
              Cancel
            </button>
          ` : ""}
        </div>
      </div>
    `).join("");
  } catch (error) {
    bookingList.innerHTML = `<div class="status">${escapeHtml(error.message)}</div>`;
  }
}

async function cancelBooking(pnr) {
  if (!window.confirm(`Cancel booking ${pnr}?`)) {
    return;
  }

  try {
    await apiRequest(`/db/booking/${encodeURIComponent(pnr)}`, { method: "DELETE" });
    await loadBookings();
    await loadFlights();
  } catch (error) {
    window.alert(error.message);
  }
}

document.querySelector("#searchForm").addEventListener("submit", async (event) => {
  event.preventDefault();

  try {
    showStatus("Searching…");
    const flights = await getFlights({
      origin: document.querySelector("#origin").value.trim(),
      destination: document.querySelector("#destination").value.trim(),
      date: document.querySelector("#date").value,
    });
    renderFlights(flights);
    showStatus("Search complete.");
  } catch (error) {
    showStatus(error.message, true);
    flightList.innerHTML = "";
  }
});

document.querySelector("#sort").addEventListener("change", async (event) => {
  try {
    renderFlights(await getFlights({ sort_by: event.target.value }));
  } catch (error) {
    showStatus(error.message, true);
  }
});

document.querySelector("#refreshBtn").addEventListener("click", loadFlights);

document.querySelector("#flightList").addEventListener("click", (event) => {
  const button = event.target.closest(".book-btn");
  if (!button) {
    return;
  }

  openBooking(
    Number(button.dataset.flightId),
    button.dataset.flightName,
    Number(button.dataset.price),
  );
});

document.querySelector("#closeModal").addEventListener("click", closeBookingModal);
document.querySelector("#modal").addEventListener("click", (event) => {
  if (event.target.id === "modal") {
    closeBookingModal();
  }
});
document.querySelector("#bookingForm").addEventListener("submit", submitBooking);
document.querySelector("#bookingList").addEventListener("click", (event) => {
  const button = event.target.closest(".cancel-btn");
  if (button) {
    cancelBooking(button.dataset.pnr);
  }
});
document.querySelector("#loadBookings").addEventListener("click", loadBookings);

loadFlights();
