function applyTheme(theme) {
  const root = document.documentElement;
  root.dataset.theme = theme;
}

function loadStoredTheme() {
  return localStorage.getItem("skybook-theme") || "system";
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    credentials: "include",
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "The request could not be completed.");
  }
  return data;
}

function showStatus(element, message, isError = false) {
  element.textContent = message;
  element.classList.toggle("error", isError);
}

async function loadSettings() {
  try {
    const user = await apiRequest("/auth/me");
    document.querySelector("#fullName").value = user.full_name;
    document.querySelector("#email").value = user.email;
    document.querySelector("#accountRole").textContent = user.role === "admin" ? "Administrator" : "Customer";
    document.querySelector("#notificationsEnabled").checked = Boolean(user.notifications_enabled);

    const themeSelect = document.querySelector("#themeSelect");
    themeSelect.value = loadStoredTheme();
    applyTheme(themeSelect.value);
  } catch (error) {
    window.location.href = "/login?return=%2Fsettings";
  }
}

document.querySelector("#profileForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const status = document.querySelector("#profileStatus");
  showStatus(status, "Saving…");
  try {
    await apiRequest("/auth/profile", {
      method: "PATCH",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        full_name: document.querySelector("#fullName").value.trim(),
      }),
    });
    showStatus(status, "Profile updated.");
  } catch (error) {
    showStatus(status, error.message, true);
  }
});

document.querySelector("#themeSelect").addEventListener("change", (event) => {
  localStorage.setItem("skybook-theme", event.target.value);
  applyTheme(event.target.value);
});

document.querySelector("#notificationsEnabled").addEventListener("change", async (event) => {
  const status = document.querySelector("#notificationStatus");
  try {
    await apiRequest("/auth/preferences", {
      method: "PATCH",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({notifications_enabled: event.target.checked}),
    });
    showStatus(status, event.target.checked ? "Booking notifications enabled." : "Booking notifications disabled.");
  } catch (error) {
    event.target.checked = !event.target.checked;
    showStatus(status, error.message, true);
  }
});

document.querySelector("#passwordForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const currentPassword = document.querySelector("#currentPassword").value;
  const newPassword = document.querySelector("#newPassword").value;
  const confirmPassword = document.querySelector("#confirmPassword").value;
  const status = document.querySelector("#passwordStatus");

  if (newPassword !== confirmPassword) {
    showStatus(status, "New passwords do not match.", true);
    return;
  }

  showStatus(status, "Changing password…");
  try {
    await apiRequest("/auth/password", {
      method: "PATCH",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({current_password: currentPassword, new_password: newPassword}),
    });
    event.target.reset();
    showStatus(status, "Password changed. Your current session is still active.");
  } catch (error) {
    showStatus(status, error.message, true);
  }
});

document.querySelector("#logoutButton").addEventListener("click", async () => {
  const button = document.querySelector("#logoutButton");
  button.disabled = true;
  button.textContent = "Logging out…";
  try {
    await apiRequest("/auth/logout", {method: "POST"});
  } finally {
    window.location.href = "/";
  }
});

applyTheme(loadStoredTheme());
loadSettings();
