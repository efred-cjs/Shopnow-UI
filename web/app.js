const feedback = document.getElementById("feedback");
const tokenPreview = document.getElementById("token-preview");
const clientesList = document.getElementById("clientes-list");
const profileName = document.getElementById("profile-name");
const profileEmail = document.getElementById("profile-email");
const profileAddress = document.getElementById("profile-address");
const profilePhone = document.getElementById("profile-phone");
const tokenKey = "rabbitcode_token";

function showFeedback(message, type = "success") {
  feedback.textContent = message;
  feedback.className = `feedback ${type}`;
}

function hideFeedback() {
  feedback.className = "feedback hidden";
  feedback.textContent = "";
}

function setToken(token) {
  localStorage.setItem(tokenKey, token);
  tokenPreview.textContent = token;
}

function getToken() {
  return localStorage.getItem(tokenKey);
}

function clearProfile() {
  profileName.textContent = "Sin sesion";
  profileEmail.textContent = "-";
  profileAddress.textContent = "-";
  profilePhone.textContent = "-";
  clientesList.innerHTML = "<li>Inicia sesion para ver clientes desde <code>/clientes_seguro</code>.</li>";
}

function clearToken() {
  localStorage.removeItem(tokenKey);
  tokenPreview.textContent = "Todavia no hay token cargado.";
  clearProfile();
}

function renderProfile(cliente) {
  profileName.textContent = cliente.nombre;
  profileEmail.textContent = cliente.correo;
  profileAddress.textContent = cliente.direccion;
  profilePhone.textContent = cliente.telefono;
}

function renderClientes(clientes) {
  if (!clientes.length) {
    clientesList.innerHTML = "<li>No hay clientes registrados.</li>";
    return;
  }

  clientesList.innerHTML = clientes
    .map((cliente) => `<li><strong>${cliente.nombre}</strong> • ${cliente.correo} • ${cliente.telefono}</li>`)
    .join("");
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  let data;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const detail = data && typeof data.detail === "string" ? data.detail : "Ocurrio un error en la solicitud.";
    throw new Error(detail);
  }

  return data;
}

async function hydrateSession() {
  const token = getToken();
  if (!token) {
    clearProfile();
    return;
  }

  tokenPreview.textContent = token;

  try {
    const perfil = await apiRequest("/perfil", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    renderProfile(perfil.cliente);

    const clientes = await apiRequest("/clientes_seguro", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    renderClientes(clientes);
  } catch (error) {
    clearToken();
    showFeedback(error.message, "error");
  }
}

document.querySelectorAll(".tab-button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab-button").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.remove("active"));

    button.classList.add("active");
    document.querySelector(`[data-panel="${button.dataset.tab}"]`).classList.add("active");
    hideFeedback();
  });
});

document.getElementById("register-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  hideFeedback();

  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form.entries());

  try {
    const data = await apiRequest("/registro", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setToken(data.token);
    renderProfile(data.cliente);
    showFeedback("Usuario registrado. Token generado y sesion iniciada.");
    await hydrateSession();
    event.currentTarget.reset();
  } catch (error) {
    showFeedback(error.message, "error");
  }
});

document.getElementById("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  hideFeedback();

  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form.entries());

  try {
    const data = await apiRequest("/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setToken(data.token);
    renderProfile(data.cliente);
    showFeedback("Sesion iniciada. El token ya quedo cargado.");
    await hydrateSession();
    event.currentTarget.reset();
  } catch (error) {
    showFeedback(error.message, "error");
  }
});

document.getElementById("token-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  hideFeedback();

  const form = new FormData(event.currentTarget);
  const token = String(form.get("token") || "").trim();

  if (!token) {
    showFeedback("Pega un token valido para continuar.", "error");
    return;
  }

  setToken(token);
  await hydrateSession();
  showFeedback("Token cargado. Si es valido, la sesion ya quedo activa.");
});

document.getElementById("refresh-button").addEventListener("click", async () => {
  hideFeedback();
  await hydrateSession();
  if (getToken()) {
    showFeedback("Sesion refrescada desde la API.");
  }
});

document.getElementById("logout-button").addEventListener("click", () => {
  hideFeedback();
  clearToken();
  showFeedback("Sesion cerrada localmente.");
});

hydrateSession();
