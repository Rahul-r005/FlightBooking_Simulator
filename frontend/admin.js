const statusElement = document.querySelector("#adminStatus");
const accountList = document.querySelector("#accountList");
const bookingList = document.querySelector("#bookingList");
const flightList = document.querySelector("#flightList");
const timelineList = document.querySelector("#timelineList");

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {credentials: "include", ...options});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "The request could not be completed.");
  }
  return data;
}

function showStatus(message, isError = false) {
  statusElement.textContent = message;
  statusElement.style.color = isError ? "#b42318" : "#667085";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderAccounts(accounts) {
  if (!accounts.length) {
    accountList.innerHTML = '<div class="status">No accounts found.</div>';
    return;
  }
  accountList.innerHTML = accounts.map((account) => `
    <article class="admin-card">
      <div>
        <strong>${escapeHtml(account.full_name)}</strong>
        <div class="muted">${escapeHtml(account.email)} · ${account.booking_count} booking(s) · ${escapeHtml(account.role)}</div>
      </div>
      <div class="admin-actions">
        <button class="ghost-btn account-bookings" data-user-id="${account.user_id}">View bookings</button>
        <button class="ghost-btn account-status" data-user-id="${account.user_id}" data-suspended="${account.suspended}">
          ${account.suspended ? "Reactivate" : "Suspend"}
        </button>
      </div>
    </article>
  `).join("");
}

function renderFlights(flights) {
  if (!flights.length) { flightList.innerHTML = '<div class="status">No flights found.</div>'; return; }
  flightList.innerHTML = flights.map((flight) => '<article class="admin-card"><div><strong>' +
    escapeHtml(flight.flight_number) + ' · ' + escapeHtml(flight.airline) +
    '</strong><div class="muted">' + escapeHtml(flight.source) + ' → ' + escapeHtml(flight.destination) +
    ' · ' + escapeHtml(new Date(flight.departure_time).toLocaleString()) + ' → ' +
    escapeHtml(new Date(flight.arrival_time).toLocaleString()) + '</div><div class="muted">Seats: ' +
    (flight.total_seats - flight.available_seats) + '/' + flight.total_seats + ' occupied · ' +
    flight.available_seats + ' available · ' + flight.active_bookings + ' active booking(s)</div></div>' +
    '<div class="admin-actions"><button class="ghost-btn edit-flight" data-id="' + flight.flight_id +
    '" data-departure="' + flight.departure_time + '" data-arrival="' + flight.arrival_time +
    '" data-seats="' + flight.total_seats + '">Edit timeline</button><button class="ghost-btn delete-flight" data-id="' +
    flight.flight_id + '">Delete</button></div></article>').join('');
}
function renderTimeline(events) {
  if (!events.length) { timelineList.innerHTML = '<div class="status">No timeline events for this booking.</div>'; return; }
  timelineList.innerHTML = events.map((event) => '<article class="timeline-item"><strong>' +
    escapeHtml(event.action) + '</strong><div>' + escapeHtml(event.details) +
    '</div><small>' + escapeHtml(new Date(event.created_at).toLocaleString()) + '</small></article>').join('');
}
function renderBookings(bookings) {
  if (!bookings.length) {
    bookingList.innerHTML = '<div class="status">No bookings match the filter.</div>';
    return;
  }
  bookingList.innerHTML = bookings.map((booking) => `
    <article class="admin-card">
      <div>
        <strong>${escapeHtml(booking.pnr)}</strong>
        <div class="muted">
          ${escapeHtml(booking.flight_number)} · ${escapeHtml(booking.source)} → ${escapeHtml(booking.destination)}
          · ${escapeHtml(new Date(booking.departure_time).toLocaleString())}
        </div>
        <div class="muted">${escapeHtml(booking.passenger_name)} · ${escapeHtml(booking.passenger_email || "No email")} · Seat ${escapeHtml(booking.seat_number || "—")}</div>
      </div>
      <div class="admin-actions">
        <span class="status-pill">${escapeHtml(booking.status)}</span>
        ${booking.status === "Confirmed" ? `<button class="ghost-btn edit-booking" data-pnr="${escapeHtml(booking.pnr)}" data-seat="${escapeHtml(booking.seat_number || "")}">Edit seat</button><button class="ghost-btn cancel-admin" data-pnr="${escapeHtml(booking.pnr)}">Cancel</button>` : ""}
        <button class="ghost-btn timeline-booking" data-pnr="${escapeHtml(booking.pnr)}">Timeline</button>
        <button class="ghost-btn delete-booking" data-pnr="${escapeHtml(booking.pnr)}">Delete</button>
      </div>
    </article>
  `).join("");
}

async function loadAccounts(query = "") {
  renderAccounts(await apiRequest(`/admin/accounts?q=${encodeURIComponent(query)}`));
}

async function loadFlights() {
  const flights = await apiRequest("/admin/flights");
  renderFlights(flights);
  document.querySelector("#newBookingFlight").innerHTML = '<option value="">Select flight</option>' + flights.map((f) => '<option value="' + f.flight_id + '">' + escapeHtml(f.flight_number) + ' — ' + escapeHtml(f.source) + ' → ' + escapeHtml(f.destination) + ' (' + f.available_seats + ' seats)</option>').join("");
}
async function loadBookings() {
  const status = document.querySelector("#bookingStatus").value;
  const search = document.querySelector("#bookingSearch").value.trim();
  const query = new URLSearchParams();
  if (status) query.set("status", status);
  if (search) query.set("search", search);
  renderBookings(await apiRequest(`/admin/bookings?${query}`));
}

document.querySelector("#accountSearch").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await loadAccounts(document.querySelector("#accountQuery").value.trim());
  } catch (error) {
    showStatus(error.message, true);
  }
});

document.querySelector("#clearCancelledBookings").addEventListener("click", async () => {
  const statusSelect = document.querySelector("#bookingStatus");
  statusSelect.value = "upcoming";
  document.querySelector("#bookingSearch").value = "";
  try {
    await loadBookings();
    showStatus("Cancelled bookings cleared from the admin view. They remain in the database for history.");
  } catch (error) {
    showStatus(error.message, true);
  }
});

document.querySelector("#bookingFilter").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await loadBookings();
  } catch (error) {
    showStatus(error.message, true);
  }
});

accountList.addEventListener("click", async (event) => {
  const statusButton = event.target.closest(".account-status");
  const bookingsButton = event.target.closest(".account-bookings");
  try {
    if (statusButton) {
      const suspended = statusButton.dataset.suspended !== "true";
      await apiRequest(`/admin/accounts/${statusButton.dataset.userId}/status`, {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({suspended}),
      });
      await loadAccounts(document.querySelector("#accountQuery").value.trim());
      showStatus(suspended ? "Account suspended." : "Account reactivated.");
    }
    if (bookingsButton) {
      const bookings = await apiRequest(`/admin/accounts/${bookingsButton.dataset.userId}/bookings`);
      renderBookings(bookings);
      showStatus("Showing this customer's booking history.");
    }
  } catch (error) {
    showStatus(error.message, true);
  }
});

bookingList.addEventListener("click", async (event) => {
  const timelineButton = event.target.closest(".timeline-booking");
  const editButton = event.target.closest(".edit-booking");
  const deleteButton = event.target.closest(".delete-booking");
  const button = event.target.closest(".cancel-admin");
  if (timelineButton) { renderTimeline(await apiRequest("/admin/bookings/" + encodeURIComponent(timelineButton.dataset.pnr) + "/timeline")); showStatus("Booking timeline loaded."); return; }
  if (editButton) { const seat = window.prompt("New seat number (example: 12A):", editButton.dataset.seat); if (seat === null) return; await apiRequest("/admin/bookings/" + encodeURIComponent(editButton.dataset.pnr), {method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({seat_number:seat})}); await loadBookings(); await loadFlights(); showStatus("Seat updated and inventory synchronized."); return; }
  if (deleteButton) { if (!window.confirm("Delete this booking? Its seat will be returned to inventory.")) return; await apiRequest("/admin/bookings/" + encodeURIComponent(deleteButton.dataset.pnr), {method:"DELETE"}); await loadBookings(); await loadFlights(); showStatus("Booking deleted and inventory updated."); return; }
  if (!button) return;
  if (!window.confirm(`Cancel booking ${button.dataset.pnr}?`)) return;
  try {
    const result = await apiRequest(`/admin/bookings/${encodeURIComponent(button.dataset.pnr)}/cancel`, {
      method: "POST",
    });
    showStatus(result.message);
    await loadBookings();
  } catch (error) {
    showStatus(error.message, true);
  }
});


document.querySelector("#createBookingForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await apiRequest("/admin/bookings", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
      flight_id:Number(document.querySelector("#newBookingFlight").value),
      passenger_name:document.querySelector("#newPassengerName").value.trim(),
      passenger_email:document.querySelector("#newPassengerEmail").value.trim() || null,
      passenger_phone:document.querySelector("#newPassengerPhone").value.trim() || null,
      user_email:document.querySelector("#newCustomerEmail").value.trim() || null,
      seat_number:document.querySelector("#newSeat").value.trim()
    })});
    event.target.reset(); await loadBookings(); await loadFlights(); showStatus("Booking created and seat inventory updated.");
  } catch (error) { showStatus(error.message, true); }
});
flightList.addEventListener("click", async (event) => {
  const edit = event.target.closest(".edit-flight"), del = event.target.closest(".delete-flight");
  try {
    if (edit) {
      const departure = window.prompt("Departure (YYYY-MM-DDTHH:MM):", edit.dataset.departure.slice(0,16));
      if (departure === null) return;
      const arrival = window.prompt("Arrival (YYYY-MM-DDTHH:MM):", edit.dataset.arrival.slice(0,16));
      if (arrival === null) return;
      const seats = window.prompt("Total seats:", edit.dataset.seats);
      if (seats === null) return;
      await apiRequest("/admin/flights/" + edit.dataset.id, {method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({departure_time:departure,arrival_time:arrival,total_seats:Number(seats)})});
      await loadFlights(); await loadBookings(); showStatus("Flight timeline updated and seating inventory synchronized."); return;
    }
    if (del) {
      if (!window.confirm("Delete this flight? Flights with active bookings cannot be deleted.")) return;
      await apiRequest("/admin/flights/" + del.dataset.id, {method:"DELETE"}); await loadFlights(); showStatus("Flight deleted.");
    }
  } catch (error) { showStatus(error.message, true); }
});
document.querySelector("#refreshFlights").addEventListener("click", loadFlights);
document.querySelector("#signOut").addEventListener("click", async (event) => {
  event.preventDefault();
  await apiRequest("/auth/logout", {method: "POST"});
  window.location.href = "/";
});

Promise.all([loadAccounts(), loadBookings(), loadFlights()]).catch((error) => showStatus(error.message, true));
