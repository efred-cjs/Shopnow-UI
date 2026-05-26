const feedback = document.getElementById("feedback");
const authView = document.getElementById("auth-view");
const appView = document.getElementById("app-view");
const tokenPreview = document.getElementById("token-preview");
const sessionTitle = document.getElementById("session-title");
const profileName = document.getElementById("profile-name");
const profileEmail = document.getElementById("profile-email");
const profileAddress = document.getElementById("profile-address");
const profilePhone = document.getElementById("profile-phone");
const clientesCount = document.getElementById("clientes-count");
const productosCount = document.getElementById("productos-count");
const inventarioCount = document.getElementById("inventario-count");
const pedidosCount = document.getElementById("pedidos-count");
const clientesBody = document.getElementById("clientes-body");
const productosBody = document.getElementById("productos-body");
const inventarioBody = document.getElementById("inventario-body");
const pedidosBody = document.getElementById("pedidos-body");
const clienteForm = document.getElementById("cliente-form");
const productoForm = document.getElementById("producto-form");
const inventarioForm = document.getElementById("inventario-form");
const pedidoForm = document.getElementById("pedido-form");
const tokenKey = "shopnowui_token";
const localFrontendPorts = new Set(["3000", "5173", "5500", "5501"]);
const defaultLocalApiBase = "http://127.0.0.1:8000";

const apiBase =
  window.SHOPNOW_API_BASE ||
  (window.location.protocol === "file:" || localFrontendPorts.has(window.location.port) ? defaultLocalApiBase : "");

let summaryState = {
  clientes: [],
  productos: [],
  inventario: [],
  pedidos: [],
  cliente_actual: null,
};

function showAuthView() {
  authView.hidden = false;
  appView.hidden = true;
}

function showAppView() {
  authView.hidden = true;
  appView.hidden = false;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatCurrency(value) {
  const amount = Number(value ?? 0);
  return `$${amount.toFixed(2)}`;
}

function formatDate(value) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("es-MX", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

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

function clearToken() {
  localStorage.removeItem(tokenKey);
  tokenPreview.textContent = "Sin token.";
}

function resetCounts() {
  clientesCount.textContent = "0";
  productosCount.textContent = "0";
  inventarioCount.textContent = "0";
  pedidosCount.textContent = "0";
}

function clearTables() {
  clientesBody.innerHTML = '<tr><td colspan="6">Inicia sesion para ver clientes.</td></tr>';
  productosBody.innerHTML = '<tr><td colspan="5">Inicia sesion para ver productos.</td></tr>';
  inventarioBody.innerHTML = '<tr><td colspan="6">Inicia sesion para ver inventario.</td></tr>';
  pedidosBody.innerHTML = '<tr><td colspan="7">Inicia sesion para ver pedidos.</td></tr>';
}

function clearProfile() {
  sessionTitle.textContent = "Sin sesion iniciada";
  profileName.textContent = "Sin sesion";
  profileEmail.textContent = "-";
  profileAddress.textContent = "-";
  profilePhone.textContent = "-";
}

function clearProtectedState() {
  summaryState = {
    clientes: [],
    productos: [],
    inventario: [],
    pedidos: [],
    cliente_actual: null,
  };
  clearProfile();
  resetCounts();
  clearTables();
  populateEntitySelects();
  resetForms();
  showAuthView();
}

function statusPill(activeOrState) {
  const normalized = String(activeOrState ?? "").trim().toUpperCase();
  if (normalized === "TRUE" || normalized === "ACTIVO") {
    return '<span class="status-pill active">Activo</span>';
  }
  if (normalized === "FALSE" || normalized === "INACTIVO") {
    return '<span class="status-pill inactive">Inactivo</span>';
  }
  if (normalized === "COMPLETADO") {
    return '<span class="status-pill completed">Completado</span>';
  }
  if (normalized === "PENDIENTE") {
    return '<span class="status-pill pending">Pendiente</span>';
  }
  return `<span class="status-pill completed">${escapeHtml(normalized || "COMPLETADO")}</span>`;
}

async function apiRequest(path, options = {}, requireAuth = false) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (requireAuth) {
    const token = getToken();
    if (!token) {
      throw new Error("No hay sesion activa.");
    }
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${apiBase}${path}`, {
    ...options,
    headers,
  });

  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearToken();
      clearProtectedState();
    }
    const detail =
      response.status === 404
        ? `No encontre ${path}. Revisa que FastAPI este corriendo en ${apiBase || window.location.origin}.`
        : data && typeof data.detail === "string"
          ? data.detail
          : "Ocurrio un error en la solicitud.";
    throw new Error(detail);
  }

  return data;
}

function renderProfile(cliente) {
  if (!cliente) {
    clearProfile();
    return;
  }

  sessionTitle.textContent = `Sesion activa de ${cliente.nombre}`;
  profileName.textContent = cliente.nombre;
  profileEmail.textContent = cliente.correo;
  profileAddress.textContent = cliente.direccion;
  profilePhone.textContent = cliente.telefono;
}

function renderClientes(clientes) {
  clientesCount.textContent = String(clientes.length);

  if (!clientes.length) {
    clientesBody.innerHTML = '<tr><td colspan="6">No hay clientes registrados.</td></tr>';
    return;
  }

  clientesBody.innerHTML = clientes
    .map(
      (cliente) => `
        <tr>
          <td>${cliente.id_cliente}</td>
          <td>${escapeHtml(cliente.nombre)}</td>
          <td>${escapeHtml(cliente.correo)}</td>
          <td>${escapeHtml(cliente.telefono)}</td>
          <td>${statusPill(cliente.activo ? "ACTIVO" : "INACTIVO")}</td>
          <td>
            <div class="row-actions">
              <button class="table-action" data-action="edit-cliente" data-id="${cliente.id_cliente}">Editar</button>
              <button class="table-action ${cliente.activo ? "negative" : "positive"}" data-action="toggle-cliente" data-id="${cliente.id_cliente}">
                ${cliente.activo ? "Desactivar" : "Reactivar"}
              </button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
}

function renderProductos(productos) {
  productosCount.textContent = String(productos.length);

  if (!productos.length) {
    productosBody.innerHTML = '<tr><td colspan="5">No hay productos registrados.</td></tr>';
    return;
  }

  productosBody.innerHTML = productos
    .map(
      (producto) => `
        <tr>
          <td>${producto.id_producto}</td>
          <td>${escapeHtml(producto.descripcion)}</td>
          <td>${formatCurrency(producto.precio)}</td>
          <td>${statusPill(producto.activo ? "ACTIVO" : "INACTIVO")}</td>
          <td>
            <div class="row-actions">
              <button class="table-action" data-action="edit-producto" data-id="${producto.id_producto}">Editar</button>
              <button class="table-action ${producto.activo ? "negative" : "positive"}" data-action="toggle-producto" data-id="${producto.id_producto}">
                ${producto.activo ? "Desactivar" : "Reactivar"}
              </button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
}

function renderInventario(inventario) {
  inventarioCount.textContent = String(inventario.length);

  if (!inventario.length) {
    inventarioBody.innerHTML = '<tr><td colspan="6">No hay inventario registrado.</td></tr>';
    return;
  }

  inventarioBody.innerHTML = inventario
    .map(
      (item) => `
        <tr>
          <td>${item.id_producto}</td>
          <td>${escapeHtml(item.descripcion)}</td>
          <td>${item.precio != null ? formatCurrency(item.precio) : "-"}</td>
          <td>${item.cantidad}</td>
          <td>${statusPill(item.activo ? "ACTIVO" : "INACTIVO")}</td>
          <td>
            <div class="row-actions">
              <button class="table-action warning" data-action="load-inventario" data-id="${item.id_producto}">Editar stock</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
}

function renderPedidos(pedidos) {
  pedidosCount.textContent = String(pedidos.length);

  if (!pedidos.length) {
    pedidosBody.innerHTML = '<tr><td colspan="7">No hay pedidos registrados.</td></tr>';
    return;
  }

  pedidosBody.innerHTML = pedidos
    .map(
      (pedido) => `
        <tr>
          <td>${pedido.id_pedido}</td>
          <td>${escapeHtml(pedido.cliente_nombre)}</td>
          <td>${escapeHtml(pedido.producto_descripcion)}</td>
          <td>${pedido.cantidad}</td>
          <td>${formatCurrency(pedido.costo)}</td>
          <td>${statusPill(pedido.estado)}</td>
          <td>${escapeHtml(formatDate(pedido.created_at))}</td>
        </tr>
      `,
    )
    .join("");
}

function buildOptions(options, placeholder) {
  if (!options.length) {
    return `<option value="">${placeholder}</option>`;
  }

  return [
    `<option value="">${placeholder}</option>`,
    ...options.map((option) => `<option value="${option.value}">${escapeHtml(option.label)}</option>`),
  ].join("");
}

function populateEntitySelects() {
  const inventoryProductSelect = inventarioForm.elements.id_producto;
  const orderClientSelect = pedidoForm.elements.id_cliente;
  const orderProductSelect = pedidoForm.elements.id_producto;

  const previousInventoryValue = inventoryProductSelect.value;
  const previousClientValue = orderClientSelect.value;
  const previousProductValue = orderProductSelect.value;

  const activeProducts = summaryState.productos.filter((producto) => producto.activo);
  const activeClients = summaryState.clientes.filter((cliente) => cliente.activo);
  const inventoryMap = new Map(summaryState.inventario.map((item) => [item.id_producto, item]));

  inventoryProductSelect.innerHTML = buildOptions(
    activeProducts.map((producto) => ({
      value: producto.id_producto,
      label: `[${producto.id_producto}] ${producto.descripcion}`,
    })),
    "Selecciona un producto",
  );

  orderClientSelect.innerHTML = buildOptions(
    activeClients.map((cliente) => ({
      value: cliente.id_cliente,
      label: `[${cliente.id_cliente}] ${cliente.nombre}`,
    })),
    "Selecciona un cliente",
  );

  orderProductSelect.innerHTML = buildOptions(
    activeProducts.map((producto) => {
      const stock = inventoryMap.get(producto.id_producto)?.cantidad ?? 0;
      return {
        value: producto.id_producto,
        label: `[${producto.id_producto}] ${producto.descripcion} | Stock ${stock}`,
      };
    }),
    "Selecciona un producto",
  );

  inventoryProductSelect.value = previousInventoryValue;
  orderClientSelect.value = previousClientValue;
  orderProductSelect.value = previousProductValue;
}

function renderSummary(summary) {
  summaryState = summary;
  showAppView();
  renderProfile(summary.cliente_actual);
  renderClientes(summary.clientes);
  renderProductos(summary.productos);
  renderInventario(summary.inventario);
  renderPedidos(summary.pedidos);
  populateEntitySelects();
}

function resetClientForm() {
  clienteForm.reset();
  clienteForm.elements.id_cliente.value = "";
  clienteForm.elements.activo.checked = true;
}

function resetProductForm() {
  productoForm.reset();
  productoForm.elements.id_producto.value = "";
  productoForm.elements.activo.checked = true;
}

function resetInventoryForm() {
  inventarioForm.reset();
  inventarioForm.elements.modo.value = "alta";
}

function resetPedidoForm() {
  pedidoForm.reset();
}

function resetForms() {
  resetClientForm();
  resetProductForm();
  resetInventoryForm();
  resetPedidoForm();
}

function hydrateClientForm(id) {
  const cliente = summaryState.clientes.find((item) => item.id_cliente === id);
  if (!cliente) {
    return;
  }

  clienteForm.elements.id_cliente.value = cliente.id_cliente;
  clienteForm.elements.nombre.value = cliente.nombre;
  clienteForm.elements.correo.value = cliente.correo;
  clienteForm.elements.telefono.value = cliente.telefono;
  clienteForm.elements.direccion.value = cliente.direccion;
  clienteForm.elements.activo.checked = Boolean(cliente.activo);
  showSection("clientes");
}

function hydrateProductForm(id) {
  const producto = summaryState.productos.find((item) => item.id_producto === id);
  if (!producto) {
    return;
  }

  productoForm.elements.id_producto.value = producto.id_producto;
  productoForm.elements.descripcion.value = producto.descripcion;
  productoForm.elements.precio.value = producto.precio;
  productoForm.elements.activo.checked = Boolean(producto.activo);
  showSection("productos");
}

function hydrateInventoryForm(idProducto) {
  const item = summaryState.inventario.find((entry) => entry.id_producto === idProducto);
  if (!item) {
    return;
  }

  inventarioForm.elements.modo.value = "fijar";
  inventarioForm.elements.id_producto.value = String(item.id_producto);
  inventarioForm.elements.cantidad.value = String(item.cantidad);
  showSection("inventario");
}

function showSection(sectionName) {
  document.querySelectorAll(".section-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.sectionTarget === sectionName);
  });

  document.querySelectorAll(".entity-section").forEach((section) => {
    section.classList.toggle("active", section.dataset.section === sectionName);
  });
}

async function hydrateSession() {
  const token = getToken();
  if (!token) {
    clearProtectedState();
    return;
  }

  tokenPreview.textContent = token;

  try {
    const summary = await apiRequest("/panel/resumen", {}, true);
    renderSummary(summary);
  } catch (error) {
    clearToken();
    clearProtectedState();
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

document.querySelectorAll(".section-button").forEach((button) => {
  button.addEventListener("click", () => showSection(button.dataset.sectionTarget));
});

document.getElementById("register-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  hideFeedback();

  const payload = Object.fromEntries(new FormData(event.currentTarget).entries());

  try {
    const data = await apiRequest("/registro", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setToken(data.token);
    await hydrateSession();
    showFeedback("Usuario registrado. Sesion activa.");
    event.currentTarget.reset();
  } catch (error) {
    showFeedback(error.message, "error");
  }
});

document.getElementById("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  hideFeedback();

  const payload = Object.fromEntries(new FormData(event.currentTarget).entries());

  try {
    const data = await apiRequest("/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setToken(data.token);
    await hydrateSession();
    showFeedback("Sesion iniciada.");
    event.currentTarget.reset();
  } catch (error) {
    showFeedback(error.message, "error");
  }
});

document.getElementById("token-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  hideFeedback();

  const token = String(new FormData(event.currentTarget).get("token") || "").trim();
  if (!token) {
    showFeedback("Pega un token valido para continuar.", "error");
    return;
  }

  setToken(token);
  await hydrateSession();
  if (getToken()) {
    showFeedback("Token cargado. El panel ya se conecto con la API unificada.");
  }
});

clienteForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideFeedback();

  const id = clienteForm.elements.id_cliente.value.trim();
  const payload = {
    nombre: clienteForm.elements.nombre.value.trim(),
    correo: clienteForm.elements.correo.value.trim(),
    telefono: clienteForm.elements.telefono.value.trim(),
    direccion: clienteForm.elements.direccion.value.trim(),
    activo: clienteForm.elements.activo.checked,
  };

  try {
    await apiRequest(id ? `/clientes/${id}` : "/clientes", {
      method: id ? "PATCH" : "POST",
      body: JSON.stringify(payload),
    }, true);
    await hydrateSession();
    resetClientForm();
    showFeedback(id ? "Cliente actualizado correctamente." : "Cliente creado correctamente.");
  } catch (error) {
    showFeedback(error.message, "error");
  }
});

productoForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideFeedback();

  const id = productoForm.elements.id_producto.value.trim();
  const payload = {
    descripcion: productoForm.elements.descripcion.value.trim(),
    precio: Number(productoForm.elements.precio.value),
    activo: productoForm.elements.activo.checked,
  };

  try {
    await apiRequest(id ? `/productos/${id}` : "/productos", {
      method: id ? "PATCH" : "POST",
      body: JSON.stringify(payload),
    }, true);
    await hydrateSession();
    resetProductForm();
    showFeedback(id ? "Producto actualizado correctamente." : "Producto creado correctamente.");
  } catch (error) {
    showFeedback(error.message, "error");
  }
});

inventarioForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideFeedback();

  const mode = inventarioForm.elements.modo.value;
  const idProducto = Number(inventarioForm.elements.id_producto.value);
  const cantidad = Number(inventarioForm.elements.cantidad.value);

  if (!idProducto && idProducto !== 0) {
    showFeedback("Selecciona un producto para continuar.", "warning");
    return;
  }

  try {
    if (mode === "alta") {
      await apiRequest("/inventario/alta", {
        method: "POST",
        body: JSON.stringify({ id_producto: idProducto, cantidad_inicial: cantidad }),
      }, true);
    } else if (mode === "sumar") {
      await apiRequest(`/inventario/${idProducto}/agregar`, {
        method: "PATCH",
        body: JSON.stringify({ cantidad }),
      }, true);
    } else {
      await apiRequest(`/inventario/${idProducto}`, {
        method: "PATCH",
        body: JSON.stringify({ cantidad }),
      }, true);
    }

    await hydrateSession();
    resetInventoryForm();
    showFeedback("Inventario actualizado correctamente.");
  } catch (error) {
    showFeedback(error.message, "error");
  }
});

pedidoForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideFeedback();

  const payload = {
    id_cliente: Number(pedidoForm.elements.id_cliente.value),
    id_producto: Number(pedidoForm.elements.id_producto.value),
    cantidad: Number(pedidoForm.elements.cantidad.value),
  };

  try {
    await apiRequest("/pedidos", {
      method: "POST",
      body: JSON.stringify(payload),
    }, true);
    await hydrateSession();
    resetPedidoForm();
    showFeedback("Pedido registrado y stock descontado correctamente.");
  } catch (error) {
    showFeedback(error.message, "error");
  }
});

clientesBody.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) {
    return;
  }

  const id = Number(button.dataset.id);
  const action = button.dataset.action;

  try {
    if (action === "edit-cliente") {
      hydrateClientForm(id);
      return;
    }

    if (action === "toggle-cliente") {
      const cliente = summaryState.clientes.find((item) => item.id_cliente === id);
      if (!cliente) {
        return;
      }

      if (cliente.activo) {
        await apiRequest(`/clientes/${id}`, { method: "DELETE" }, true);
      } else {
        await apiRequest(`/clientes/${id}`, {
          method: "PATCH",
          body: JSON.stringify({ activo: true }),
        }, true);
      }

      await hydrateSession();
      showFeedback("Estado del cliente actualizado.");
    }
  } catch (error) {
    showFeedback(error.message, "error");
  }
});

productosBody.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) {
    return;
  }

  const id = Number(button.dataset.id);
  const action = button.dataset.action;

  try {
    if (action === "edit-producto") {
      hydrateProductForm(id);
      return;
    }

    if (action === "toggle-producto") {
      const producto = summaryState.productos.find((item) => item.id_producto === id);
      if (!producto) {
        return;
      }

      if (producto.activo) {
        await apiRequest(`/productos/${id}`, { method: "DELETE" }, true);
      } else {
        await apiRequest(`/productos/${id}`, {
          method: "PATCH",
          body: JSON.stringify({ activo: true }),
        }, true);
      }

      await hydrateSession();
      showFeedback("Estado del producto actualizado.");
    }
  } catch (error) {
    showFeedback(error.message, "error");
  }
});

inventarioBody.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button || button.dataset.action !== "load-inventario") {
    return;
  }

  hydrateInventoryForm(Number(button.dataset.id));
});

document.getElementById("refresh-button").addEventListener("click", async () => {
  hideFeedback();
  await hydrateSession();
  if (getToken()) {
    showFeedback("Datos actualizados desde el servicio unificado.");
  }
});

document.getElementById("logout-button").addEventListener("click", () => {
  hideFeedback();
  clearToken();
  clearProtectedState();
  showFeedback("Sesion cerrada.");
});

document.getElementById("cliente-reset").addEventListener("click", resetClientForm);
document.getElementById("producto-reset").addEventListener("click", resetProductForm);
document.getElementById("inventario-reset").addEventListener("click", resetInventoryForm);
document.getElementById("pedido-reset").addEventListener("click", resetPedidoForm);

clearProtectedState();
hydrateSession();
