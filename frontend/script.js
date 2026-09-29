function applyStoredTheme() {
  const saved = localStorage.getItem("skybook-theme");
  document.documentElement.dataset.theme =
    saved === "dark" || saved === "light" || saved === "system" ? saved : "system";
}

applyStoredTheme();

const configuredApi = localStorage.getItem("API_URL");
const API = (configuredApi || window.location.origin || "http://127.0.0.1:8000").replace(/\/$/, "");

const flightList = document.querySelector("#flightList");
const statusMessage = document.querySelector("#status");
const bookingList = document.querySelector("#bookingList");
const authLink = document.querySelector("#authLink");
let currentUser = null;
let selectedCabinClass = "Economy";
let currentSeatMap = null;

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
  const response = await fetch(`${API}${path}`, { credentials: "include", ...options });
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

  flightList.innerHTML = flights.map((flight) => '<article class="flight-card">' +
    '<div><div class="airline">' + escapeHtml(flight.airline) + '</div><div class="flight-number">' + escapeHtml(flight.flight_number) + '</div></div>' +
    '<div><div class="route">' + escapeHtml(flight.source) + ' <span>→</span> ' + escapeHtml(flight.destination) + '</div>' +
    '<div class="flight-number">' + escapeHtml(new Date(flight.departure_time).toLocaleString()) + ' · ' + flight.duration_minutes + ' min · ' + flight.available_seats + ' seats left</div></div>' +
    '<div class="fare-options">' +
      '<div class="cabin-result"><div><span class="tier">Economy</span><strong>' + formatMoney(flight.economy_price) + '</strong><small>Standard cabin</small></div>' +
      '<button class="ghost-btn book-btn" data-flight-id="' + flight.flight_id + '" data-flight-name="' + escapeHtml(flight.airline + " " + flight.flight_number) + '" data-cabin="Economy">Book</button></div>' +
      '<div class="cabin-result premium-result"><div><span class="tier">Premium</span><strong>' + formatMoney(flight.premium_price) + '</strong><small>Premium front zone</small></div>' +
      '<button class="ghost-btn book-btn" data-flight-id="' + flight.flight_id + '" data-flight-name="' + escapeHtml(flight.airline + " " + flight.flight_number) + '" data-cabin="Premium">Book</button></div>' +
    '</div></article>').join("");
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

function redirectToSignIn(flightId, flightName, cabinClass) {
  const returnUrl = new URL("/", window.location.origin);
  returnUrl.searchParams.set("flight", flightId);
  returnUrl.searchParams.set("flightName", flightName);
  returnUrl.searchParams.set("cabin", cabinClass);
  window.location.href = `/login?return=${encodeURIComponent(returnUrl.pathname + returnUrl.search)}`;
}

async function openBooking(flightId, flightName, cabinClass) {
  document.querySelector("#bookingForm").reset();
  document.querySelector("#flightId").value = flightId;
  document.querySelector("#modalFlight").textContent = flightName;
  document.querySelector("#bookingStatus").textContent = "";
  try {
    const flight = (await getFlights()).find((item) => item.flight_id === flightId);
    if (!flight) throw new Error("Flight details could not be loaded.");
    document.querySelector("#modalEconomyPrice").textContent = formatMoney(flight.economy_price);
    document.querySelector("#modalPremiumPrice").textContent = formatMoney(flight.premium_price);
    selectedCabinClass = cabinClass || "Economy";
    document.querySelector("#cabinClass").value = selectedCabinClass;
    currentSeatMap = await apiRequest("/db/flights/" + flightId + "/seats");
    document.querySelector("#modal").classList.remove("hidden");
    selectCabin(selectedCabinClass);
  } catch (error) {
    showStatus(error.message, true);
  }
}

function renderSeatMap(seatData) {
  const map = document.querySelector("#seatMap");
  const booked = new Set(seatData.booked_seats || []);
  const selectedSeat = document.querySelector("#seatNumber").value;
  const rows = Math.ceil(seatData.total_seats / 5);
  const html = [];
  for (let row = 1; row <= rows; row += 1) {
    const cabin = row >= seatData.premium_start_row ? "Premium" : "Economy";
    html.push('<div class="seat-row-label">' + row + '</div>');
    ["A","B","C","D","E"].forEach((letter) => {
      const seat = row + letter;
      const isBooked = booked.has(seat);
      const isActive = cabin === selectedCabinClass;
      const isSelected = selectedSeat === seat;
      const classes = "seat " + (isBooked ? "booked" : isSelected ? "selected" : "available") + (!isActive && !isBooked ? " cabin-disabled" : "");
      const disabled = isBooked || !isActive;
      html.push('<button type="button" class="' + classes + '" data-seat="' + seat + '"' + (disabled ? " disabled" : "") + '>' + letter + '</button>');
    });
  }
  map.innerHTML = html.join("");
  document.querySelector("#seatPickerHint").textContent = selectedCabinClass + " seats are selectable; booked seats are disabled.";
  document.querySelector("#selectedSeatLabel").textContent = selectedSeat ? "Selected seat " + selectedSeat : "No seat selected";
  map.querySelectorAll(".seat:not(.booked):not(.cabin-disabled)").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelector("#seatNumber").value = button.dataset.seat;
      renderSeatMap(seatData);
    });
  });
}

function selectCabin(cabinClass) {
  selectedCabinClass = cabinClass;
  document.querySelector("#cabinClass").value = cabinClass;
  const currentSeat = document.querySelector("#seatNumber").value;
  if (currentSeat && currentSeatMap) {
    const row = Number(currentSeat.slice(0, -1));
    const currentSeatCabin = row >= currentSeatMap.premium_start_row ? "Premium" : "Economy";
    if (currentSeatCabin !== cabinClass) document.querySelector("#seatNumber").value = "";
  }
  document.querySelectorAll(".cabin-choice").forEach((button) => {
    button.classList.toggle("active", button.dataset.cabin === cabinClass);
  });
  if (currentSeatMap) renderSeatMap(currentSeatMap);
}

function closeBookingModal() {
  document.querySelector("#modal").classList.add("hidden");
}

async function submitBooking(event) {
  event.preventDefault();
  const bookingStatus = document.querySelector("#bookingStatus");
  const selectedSeat = document.querySelector("#seatNumber").value;
  if (!selectedSeat) { bookingStatus.textContent = "Please select an available seat."; bookingStatus.style.color = "#b42318"; return; }
  bookingStatus.textContent = "Processing simulated payment…";
  try {
    const booking = await apiRequest("/db/booking", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        flight_id: Number(document.querySelector("#flightId").value),
        cabin_class: selectedCabinClass,
        passenger_name: document.querySelector("#passengerName").value,
        passenger_email: document.querySelector("#passengerEmail").value || null,
        passenger_phone: document.querySelector("#passengerPhone").value || null,
        seat_number: selectedSeat,
        force_payment_success: true,
      }),
    });
    bookingStatus.textContent = "Booking confirmed. PNR: " + booking.pnr;
    bookingStatus.style.color = "#087443";
    await loadFlights();
    await loadBookings();
  } catch (error) {
    bookingStatus.textContent = error.message;
    bookingStatus.style.color = "#b42318";
  }
}

async function loadBookings() {
  if (!currentUser) {
    bookingList.innerHTML = '<div class="status">Sign in to view your bookings.</div>';
    return;
  }
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
          <b>PNR ${escapeHtml(booking.pnr)} · ${escapeHtml(booking.cabin_class || "Economy")}</b>
          <div class="muted">
            Flight #${booking.flight_id} · Seat ${escapeHtml(booking.seat_number || "—")}
            · ${escapeHtml(new Date(booking.booking_date).toLocaleString())}
          </div>
        </div>
        <div>
          <b>${formatMoney(booking.total_price)}</b>
          <div class="confirmed">${escapeHtml(booking.status)}</div>
          ${booking.status === "Confirmed" ? `
            <button class="ghost-btn cancel-btn" data-pnr="${escapeHtml(booking.pnr)}">Cancel</button>
          ` : ""}
          <button class="danger-btn delete-user-booking" data-pnr="${escapeHtml(booking.pnr)}">Delete</button>
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
  if (!button) return;
  if (!currentUser) {
    redirectToSignIn(Number(button.dataset.flightId), button.dataset.flightName, button.dataset.cabin || "Economy");
    return;
  }
  openBooking(Number(button.dataset.flightId), button.dataset.flightName, button.dataset.cabin || "Economy");
});

document.querySelector("#modalEconomyChoice").addEventListener("click", () => selectCabin("Economy"));
document.querySelector("#modalPremiumChoice").addEventListener("click", () => selectCabin("Premium"));
document.querySelector("#closeModal").addEventListener("click", closeBookingModal);
document.querySelector("#modal").addEventListener("click", (event) => {
  if (event.target.id === "modal") {
    closeBookingModal();
  }
});
document.querySelector("#bookingForm").addEventListener("submit", submitBooking);
document.querySelector("#bookingList").addEventListener("click", async (event) => {
  const cancelButton = event.target.closest(".cancel-btn");
  const deleteButton = event.target.closest(".delete-user-booking");
  if (cancelButton) {
    await cancelBooking(cancelButton.dataset.pnr);
    return;
  }
  if (!deleteButton) return;
  const pnr = deleteButton.dataset.pnr;
  if (!window.confirm("WARNING: Permanently delete booking " + pnr + "? This removes the booking and related details from the database. This cannot be undone.")) return;
  const typed = window.prompt("Final confirmation: type DELETE to permanently remove booking " + pnr + ".");
  if (typed !== "DELETE") return;
  try {
    await apiRequest("/db/booking/" + encodeURIComponent(pnr) + "/delete", {method:"DELETE"});
    await loadBookings();
    await loadFlights();
    window.alert("Booking " + pnr + " was permanently deleted from the database.");
  } catch (error) {
    window.alert(error.message);
  }
});
document.querySelector("#loadBookings").addEventListener("click", loadBookings);

loadFlights();


async function signOut() {
  try {
    await apiRequest("/auth/logout", { method: "POST" });
  } finally {
    window.location.href = "/";
  }
}

async function loadCurrentUser() {
  try {
    currentUser = await apiRequest("/auth/me");
    document.querySelector("#settingsLink").classList.remove("hidden");
    document.querySelector("#adminLink").classList.toggle("hidden", currentUser.role !== "admin");
    authLink.textContent = "Sign out";
    authLink.href = "#";
    authLink.addEventListener("click", async (event) => {
      event.preventDefault();
      await signOut();
    });
  } catch (_error) {
    currentUser = null;
    document.querySelector("#settingsLink").classList.add("hidden");
    document.querySelector("#adminLink").classList.add("hidden");
    authLink.textContent = "Sign in";
    authLink.href = "/login?return=%2F";
  }
}

async function resumePendingBooking() {
  const params = new URLSearchParams(window.location.search);
  const flightId = params.get("flight");
  if (!flightId || !currentUser) {
    return;
  }
  const flight = await getFlights();
  const selected = flight.find((item) => item.flight_id === Number(flightId));
  if (selected) {
    openBooking(
      selected.flight_id,
      selected.airline + " " + selected.flight_number,
      params.get("cabin") || "Economy",
    );
    window.history.replaceState({}, document.title, "/");
  }
}

(async function initializeAccountUi() {
  await loadCurrentUser();
  await loadBookings();
  await resumePendingBooking();
})();
