const statusElement = document.querySelector("#adminStatus");
const accountList = document.querySelector("#accountList");
const bookingList = document.querySelector("#bookingList");

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
        ${booking.status === "Confirmed" ? `<button class="ghost-btn cancel-admin" data-pnr="${escapeHtml(booking.pnr)}">Cancel booking</button>` : ""}
      </div>
    </article>
  `).join("");
}

async function loadAccounts(query = "") {
  renderAccounts(await apiRequest(`/admin/accounts?q=${encodeURIComponent(query)}`));
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
  const button = event.target.closest(".cancel-admin");
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

document.querySelector("#signOut").addEventListener("click", async (event) => {
  event.preventDefault();
  await apiRequest("/auth/logout", {method: "POST"});
  window.location.href = "/";
});

Promise.all([loadAccounts(), loadBookings()]).catch((error) => showStatus(error.message, true));
