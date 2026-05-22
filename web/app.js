const feedback = document.getElementById("feedback");
const tokenPreview = document.getElementById("token-preview");
const profileName = document.getElementById("profile-name");
const profileEmail = document.getElementById("profile-email");
const profileAddress = document.getElementById("profile-address");
const profilePhone = document.getElementById("profile-phone");
const clientesList = document.getElementById("clientes-list");
const productosList = document.getElementById("productos-list");
const inventarioList = document.getElementById("inventario-list");
const pedidosList = document.getElementById("pedidos-list");
const clientesCount = document.getElementById("clientes-count");
const productosCount = document.getElementById("productos-count");
const inventarioCount = document.getElementById("inventario-count");
const pedidosCount = document.getElementById("pedidos-count");
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

function setListState(element, message) {
  element.innerHTML = `<li>${message}</li>`;
}

function resetDashboard() {
  clientesCount.textContent = "0";
  productosCount.textContent = "0";
  inventarioCount.textContent = "0";
  pedidosCount.textContent = "0";
  setListState(clientesList, "Inicia sesion para ver los clientes.");
  setListState(productosList, "Inicia sesion para ver productos.");
  setListState(inventarioList, "Inicia sesion para ver inventario.");
  setListState(pedidosList, "Inicia sesion para ver pedidos.");
}

function clearProfile() {
  profileName.textContent = "Sin sesion";
  profileEmail.textContent = "-";
  profileAddress.textContent = "-";
  profilePhone.textContent = "-";
  resetDashboard();
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

function renderCollection(element, countElement, items, formatter, emptyMessage) {
  countElement.textContent = String(items.length);

  if (!items.length) {
    setListState(element, emptyMessage);
    return;
  }

  element.innerHTML = items.map((item) => `<li>${formatter(item)}</li>`).join("");
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

    const resumen = await apiRequest("/panel/resumen", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    renderCollection(
      clientesList,
      clientesCount,
      resumen.clientes,
      (cliente) => `<strong>${cliente.nombre}</strong> | ${cliente.correo} | ${cliente.telefono}`,
      "No hay clientes registrados.",
    );
    renderCollection(
      productosList,
      productosCount,
      resumen.productos,
      (producto) => `<strong>#${producto.id_producto}</strong> | ${producto.descripcion} | $${producto.costo}`,
      "No hay productos registrados.",
    );
    renderCollection(
      inventarioList,
      inventarioCount,
      resumen.inventario,
      (item) => `<strong>Producto ${item.id_producto}</strong> | Stock disponible: ${item.cantidad}`,
      "No hay inventario registrado.",
    );
    renderCollection(
      pedidosList,
      pedidosCount,
      resumen.pedidos,
      (pedido) =>
        `<strong>Pedido ${pedido.id_pedido}</strong> | Cliente ${pedido.id_cliente} | Producto ${pedido.id_producto} | Cantidad ${pedido.cantidad} | Total $${pedido.costo}`,
      "No hay pedidos registrados.",
    );
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
    showFeedback("Usuario registrado. El panel completo ya quedo disponible.");
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
    showFeedback("Sesion iniciada. Ya puedes ver clientes, productos, inventario y pedidos.");
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
  if (getToken()) {
    showFeedback("Token cargado. El dashboard ya se conecto con los demas servicios.");
  }
});

document.getElementById("refresh-button").addEventListener("click", async () => {
  hideFeedback();
  await hydrateSession();
  if (getToken()) {
    showFeedback("Datos actualizados desde clientes, productos, inventario y pedidos.");
  }
});

document.getElementById("logout-button").addEventListener("click", () => {
  hideFeedback();
  clearToken();
  showFeedback("Sesion cerrada localmente.");
});

hydrateSession();
