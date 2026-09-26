async function submitAuth(path, body) {
  const response = await fetch(path, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    credentials: "include",
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "The request could not be completed.");
  }
  return data;
}

function returnUrl() {
  const value = new URLSearchParams(window.location.search).get("return");
  return value && value.startsWith("/") ? value : "/";
}

const statusElement = document.querySelector("#authStatus");
const loginForm = document.querySelector("#loginForm");
const registerForm = document.querySelector("#registerForm");

if (loginForm) {
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    statusElement.textContent = "Signing in…";
    try {
      await submitAuth("/auth/login", {
        email: document.querySelector("#email").value,
        password: document.querySelector("#password").value,
      });
      window.location.href = returnUrl();
    } catch (error) {
      statusElement.textContent = error.message;
      statusElement.style.color = "#b42318";
    }
  });
}

if (registerForm) {
  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    statusElement.textContent = "Creating your account…";
    try {
      await submitAuth("/auth/register", {
        full_name: document.querySelector("#fullName").value,
        email: document.querySelector("#email").value,
        password: document.querySelector("#password").value,
      });
      window.location.href = returnUrl();
    } catch (error) {
      statusElement.textContent = error.message;
      statusElement.style.color = "#b42318";
    }
  });
}
