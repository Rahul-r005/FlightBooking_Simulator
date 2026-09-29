
function passwordState(value) {
  return {
    length: value.length >= 8,
    letter: /[A-Za-z]/.test(value),
    number: /\d/.test(value),
  };
}

function renderPasswordRules(container, value, confirmation = null) {
  if (!container) return;
  const state = passwordState(value);
  const items = [
    ["At least 8 characters", state.length],
    ["At least 1 letter", state.letter],
    ["At least 1 number", state.number],
  ];
  if (confirmation !== null) {
    items.push(["Passwords match", value.length > 0 && value === confirmation]);
  }
  container.innerHTML = items.map(([label, ok]) =>
    '<div class="' + (ok ? "password-rule ok" : "password-rule missing") + '">' +
    '<span aria-hidden="true">' + (ok ? "✓" : "•") + "</span>" + label + "</div>"
  ).join("");
  return items.every(([, ok]) => ok);
}

function setupPasswordToggle(button) {
  const target = document.querySelector("#" + button.dataset.target);
  if (!target) return;
  button.addEventListener("click", () => {
    const showing = target.type === "text";
    target.type = showing ? "password" : "text";
    button.textContent = showing ? "◉" : "◌";
    button.setAttribute("aria-label", showing ? "Show password" : "Hide password");
    button.setAttribute("title", showing ? "Show password" : "Hide password");
  });
}

async function submitAuth(path, body) {
  const response = await fetch(path, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    credentials: "include",
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "The request could not be completed.");
  return data;
}

function returnUrl() {
  const value = new URLSearchParams(window.location.search).get("return");
  return value && value.startsWith("/") ? value : "/";
}

document.querySelectorAll(".password-toggle").forEach(setupPasswordToggle);

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
  const password = document.querySelector("#password");
  const confirm = document.querySelector("#confirmPassword");
  const rules = document.querySelector("#passwordRules");
  const submit = registerForm.querySelector('button[type="submit"]');

  function validateRegisterForm() {
    const strong = renderPasswordRules(rules, password.value, confirm.value);
    const match = password.value.length > 0 && password.value === confirm.value;
    submit.disabled = !(strong && match && registerForm.checkValidity());
  }

  [password, confirm, document.querySelector("#fullName"), document.querySelector("#email")].forEach((el) => {
    el.addEventListener("input", validateRegisterForm);
  });
  validateRegisterForm();

  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    validateRegisterForm();
    if (submit.disabled) return;
    statusElement.textContent = "Creating your account…";
    try {
      await submitAuth("/auth/register", {
        full_name: document.querySelector("#fullName").value,
        email: document.querySelector("#email").value,
        password: password.value,
        confirm_password: confirm.value,
      });
      window.location.href = returnUrl();
    } catch (error) {
      statusElement.textContent = error.message;
      statusElement.style.color = "#b42318";
    }
  });
}
