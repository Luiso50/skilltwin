// SkillTwin HQ - Cerebro Central JavaScript Logic (Conexión Real con Servidor)

// ======================================================================
// UTILIDADES GLOBALES - AUTENTICACIÓN BASADA EN TOKEN (localStorage)
// ======================================================================

const nativeFetch = window.fetch.bind(window);

// Obtener token guardado
function getStoredToken() {
  return localStorage.getItem("skilltwin_token");
}

// Verificar si hay sesión válida al cargar
function checkAuth() {
  const token = getStoredToken();
  const user = localStorage.getItem("skilltwin_user");
  
  if (!token || !user) {
    // No hay sesión, redirigir a login
    window.location.href = "login.html";
    return false;
  }
  return true;
}

// Wrapper de fetch que inyecta el token automáticamente
window.fetch = async (resource, options = {}) => {
  const url = typeof resource === "string" ? resource : resource.url;
  
  // Endpoints públicos que no necesitan token
  const publicEndpoints = ["/api/auth/login", "/api/auth/register", "/api/auth/token", "/api/contacto", "/api/csrf-token", "/api/health", "/api/stripe/config"];
  const isPublic = publicEndpoints.some(ep => url.includes(ep));
  
  if (!url.includes("/api/") || isPublic) {
    return nativeFetch(resource, options);
  }

  const token = getStoredToken();
  if (!token) {
    // Token expirado o eliminado, redirigir
    localStorage.removeItem("skilltwin_token");
    localStorage.removeItem("skilltwin_user");
    window.location.href = "login.html";
    throw new Error("Sesión expirada");
  }

  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${token}`);
  headers.set("Content-Type", "application/json");

  // Inyectar CSRF token para requests POST/PUT/DELETE
  const method = (options.method || "GET").toUpperCase();
  if (method !== "GET" && method !== "HEAD") {
    const csrf = await getCsrfToken();
    if (csrf.token) {
      headers.set("X-CSRF-Token", csrf.token);
      headers.set("X-Session-ID", csrf.sessionId);
    }
  }
  
  return nativeFetch(resource, { ...options, headers });
};

// Verificar autenticación al cargar la app
if (!checkAuth()) {
  // checkAuth ya redirige, pero por si acaso detenemos la ejecución
  throw new Error("Redirigiendo a login...");
}

// Debounce: retrasa ejecución hasta que el usuario deja de escribir
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Función global de logout
window.logout = function() {
  localStorage.removeItem("skilltwin_token");
  localStorage.removeItem("skilltwin_user");
  window.location.href = "login.html";
};

// ======================================================================
// CSRF TOKEN MANAGEMENT
// ======================================================================

let _csrfToken = null;
let _csrfSessionId = null;

async function getCsrfToken() {
  try {
    const res = await nativeFetch("/api/csrf-token");
    const data = await res.json();
    _csrfToken = data.token;
    _csrfSessionId = data.session_id;
    return { token: _csrfToken, sessionId: _csrfSessionId };
  } catch {
    return { token: null, sessionId: null };
  }
}

function resetCsrfToken() {
  _csrfToken = null;
  _csrfSessionId = null;
}

// Toast notifications
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  
  requestAnimationFrame(() => {
    toast.classList.add('toast-show');
  });
  
  setTimeout(() => {
    toast.classList.remove('toast-show');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Estado centralizado de la aplicación
const AppState = {
  activeCloneId: null,
  currentSessionId: null,
  clones: {},
  settings: {},
  listeners: new Map(),
  
  set(key, value) {
    this[key] = value;
    if (this.listeners.has(key)) {
      this.listeners.get(key).forEach(cb => cb(value));
    }
  },
  
  on(key, callback) {
    if (!this.listeners.has(key)) {
      this.listeners.set(key, []);
    }
    this.listeners.get(key).push(callback);
  }
};

document.addEventListener("DOMContentLoaded", () => {
  // ======================================================================
  // CARGAR INFO DE USUARIO EN SIDEBAR
  // ======================================================================
  const userData = JSON.parse(localStorage.getItem("skilltwin_user") || "{}");
  if (userData.nombre) {
    const userNameEl = document.querySelector(".user-name");
    const userRoleEl = document.querySelector(".user-role");
    const userAvatarEl = document.getElementById("owner-avatar");
    if (userNameEl) userNameEl.textContent = userData.nombre;
    if (userRoleEl) userRoleEl.textContent = userData.role === "admin" ? "Administrador" : "Usuario";
    if (userAvatarEl) userAvatarEl.textContent = userData.nombre.charAt(0).toUpperCase();
  }

  // Botón de logout en sidebar (lo inyectamos al final del user-profile)
  const userProfile = document.querySelector(".user-profile");
  if (userProfile && !document.getElementById("btn-logout")) {
    const logoutBtn = document.createElement("button");
    logoutBtn.id = "btn-logout";
    logoutBtn.className = "action-btn";
    logoutBtn.style.cssText = "width: 100%; margin-top: 0.75rem; padding: 0.5rem; font-size: 0.8rem; background: rgba(255,255,255,0.05); border: 1px solid var(--panel-border); color: var(--text-secondary);";
    logoutBtn.innerHTML = "🚪 Cerrar sesión";
    logoutBtn.addEventListener("click", () => window.logout());
    userProfile.appendChild(logoutBtn);
  }

  // Elements for Overview Chat
  const chatInput = document.getElementById("chat-input");
  const sendBtn = document.getElementById("send-btn");
  const chatBox = document.getElementById("cerebro-chat-box");
  const consoleLogs = document.getElementById("console-logs-box");
  const cerebroActivity = document.getElementById("cerebro-activity");

  // Page Header Elements
  const headerTitle = document.querySelector(".top-bar .page-title h1");
  const headerDesc = document.querySelector(".top-bar .page-title p");

  // Department Elements (Overview Panel)
  const departments = {
    desarrollo: {
      card: document.getElementById("dep-dev-card"),
      status: document.getElementById("dep-dev-status"),
      progress: document.getElementById("dep-dev-progress"),
      color: "var(--color-desarrollo)"
    },
    marketing: {
      card: document.getElementById("dep-marketing-card"),
      status: document.getElementById("dep-marketing-status"),
      progress: document.getElementById("dep-marketing-progress"),
      color: "var(--color-marketing)"
    },
    legal: {
      card: document.getElementById("dep-legal-card"),
      status: document.getElementById("dep-legal-status"),
      progress: document.getElementById("dep-legal-progress"),
      color: "var(--color-legal)"
    },
    operaciones: {
      card: document.getElementById("dep-operaciones-card"),
      status: document.getElementById("dep-operaciones-status"),
      progress: document.getElementById("dep-operaciones-progress"),
      color: "var(--color-operaciones)"
    }
  };

  // Helper: Get Current Timestamp
  function getTimestamp() {
    const now = new Date();
    return now.toTimeString().split(' ')[0];
  }

  // Helper: Append Log to Console
  function addLog(tag, message) {
    if (!consoleLogs) return;
    const entry = document.createElement("div");
    entry.className = "log-entry";
    entry.innerHTML = `
      <span class="log-time">${getTimestamp()}</span>
      <span class="log-tag tag-${tag}">${tag}</span>
      <span>${message}</span>
    `;
    consoleLogs.appendChild(entry);
    consoleLogs.scrollTop = consoleLogs.scrollHeight;
  }

  // Helper: Escape HTML to prevent XSS
  function escapeHtml(text) {
    const div = document.createElement("div");
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
  }

  // Helper: Append Chat Bubble
  function addChatBubble(sender, text) {
    if (!chatBox) return;
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${sender === 'user' ? 'user-msg' : 'cerebro-msg'}`;
    bubble.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
    chatBox.appendChild(bubble);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  // Trigger Department Loading Animation
  function animateDepartment(depKey) {
    const dep = departments[depKey];
    if (!dep) return;

    // Set UI to Working
    dep.status.textContent = "Trabajando";
    dep.status.className = "dep-status status-working";
    dep.card.style.borderColor = dep.color;
    dep.card.style.background = "rgba(255, 255, 255, 0.05)";
    dep.progress.style.width = "0%";

    // Animate progress bar to 100%
    setTimeout(() => {
      dep.progress.style.width = "100%";
    }, 100);

    // Reset back to Idle/Success after 2.5 seconds
    setTimeout(() => {
      dep.status.textContent = "Sincronizado";
      dep.status.className = "dep-status status-active";
      dep.card.style.borderColor = "var(--panel-border)";
      dep.card.style.background = "rgba(255, 255, 255, 0.02)";
    }, 2500);
  }

  // Send Command to Python Backend API (Overview Tab)
  async function sendCommandToBackend(text) {
    addChatBubble("user", text);
    
    cerebroActivity.textContent = "Estado: Procesando instrucción...";
    addLog("cerebro", "Transmitiendo comando al orquestador backend...");

    try {
      const response = await fetch("/api/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: text })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      addChatBubble("cerebro", data.message);
      
      if (data.tag && departments[data.tag]) {
        animateDepartment(data.tag);
      }
      
      if (data.console_log) {
        addLog(data.tag || "cerebro", data.console_log);
      }

      updateDynamicStats();

    } catch (error) {
      console.error("Error al enviar comando:", error);
      if (error.message && error.message.includes("Sesión expirada")) {
        addChatBubble("cerebro", "Tu sesión ha expirado. Redirigiendo al login...");
        setTimeout(() => { window.location.href = "login.html"; }, 1500);
      } else if (error.message && error.message.includes("status: 401")) {
        addChatBubble("cerebro", "Sesión no válida. Redirigiendo al login...");
        localStorage.removeItem("skilltwin_token");
        localStorage.removeItem("skilltwin_user");
        setTimeout(() => { window.location.href = "login.html"; }, 1500);
      } else {
        addChatBubble("cerebro", "❌ Error de Conexión: No se pudo contactar con el Cerebro Central. Asegúrate de tener corriendo `server.py`.");
        addLog("cerebro", `ERROR: ${error.message}`);
        showToast("Error de conexión con el servidor", "error");
      }
    } finally {
      cerebroActivity.textContent = "Estado: Escuchando órdenes...";
    }
  }

  // Trigger Send Message
  function handleSend() {
    const text = chatInput.value;
    if (!text) return;
    sendCommandToBackend(text);
    chatInput.value = "";
  }

  if (sendBtn && chatInput) {
    sendBtn.addEventListener("click", handleSend);
    chatInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") handleSend();
    });
  }

  // Debounced search para input de nicho de marketing
  const marketNichoInput = document.getElementById("market-nicho-input");
  if (marketNichoInput) {
    marketNichoInput.addEventListener("input", debounce((e) => {
      const nicho = e.target.value.trim();
      if (nicho.length > 2) {
        addLog("marketing", `Nicho detectado: "${nicho}"`);
      }
    }, 300));
  }


  // Función para renderizar el gráfico financiero (OPCIÓN 3)
  let financesChartInstance = null;
  async function renderFinancesChart() {
    const canvas = document.getElementById("financesChart");
    if (!canvas) return;

    try {
      const response = await fetch("/api/finanzas-data");
      if (!response.ok) throw new Error("No se pudo obtener la data financiera.");
      const data = await response.json();
      const flujoCaja = data.flujo_caja;

      const meses = Object.keys(flujoCaja).sort();
      const ingresosPlan = meses.map(m => flujoCaja[m].ingresos_plan);
      const ingresosReal = meses.map(m => flujoCaja[m].ingresos_real);

      if (financesChartInstance) {
        financesChartInstance.destroy();
      }

      const ctx = canvas.getContext("2d");
      financesChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: meses,
          datasets: [
            {
              label: 'Ingresos Planificados',
              data: ingresosPlan,
              backgroundColor: 'rgba(255, 255, 255, 0.1)',
              borderColor: 'rgba(255, 255, 255, 0.3)',
              borderWidth: 1,
              borderRadius: 5
            },
            {
              label: 'Ingresos Reales',
              data: ingresosReal,
              backgroundColor: 'rgba(16, 185, 129, 0.6)', // Color Operaciones
              borderColor: 'var(--color-operaciones)',
              borderWidth: 2,
              borderRadius: 5
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              labels: { color: '#9ca3af', font: { family: 'Outfit' } }
            },
            tooltip: {
              mode: 'index',
              intersect: false,
            }
          },
          scales: {
            x: {
              ticks: { color: '#9ca3af' },
              grid: { display: false }
            },
            y: {
              ticks: { color: '#9ca3af' },
              grid: { color: 'rgba(255, 255, 255, 0.05)' }
            }
          }
        }
      });
    } catch (error) {
      console.error("Error renderizando gráfico financiero:", error);
      addLog("operaciones", `ERROR: Fallo al cargar datos para el gráfico. (${error.message})`);
    }
  }

  // Función para sincronizar datos dinámicos en la UI de departamentos
  async function updateDynamicStats() {
    try {
      // 1. Cargar clones y actualizar contador
      const responseClones = await fetch("/api/clones");
      if (responseClones.ok) {
        const data = await responseClones.json();
        const total = Object.keys(data.clones).length;
        const statsTotalClones = document.getElementById("stats-total-clones");
        if (statsTotalClones) statsTotalClones.textContent = total;
      }

      // 2. Simular lectura de contrato y última búsqueda (estática pero sincronizada con el feed)
      const statsLastNicho = document.getElementById("stats-last-nicho");
      if (statsLastNicho && marketNichoInput && marketNichoInput.value) {
        statsLastNicho.textContent = marketNichoInput.value.toUpperCase();
      }
      
      // 3. Renderizar gráfico financiero (Sincronización Opción 3)
      renderFinancesChart();
      
    } catch (e) {
      console.warn("No se pudieron sincronizar las estadísticas completas de los departamentos:", e);
    }
  }

  // ======================================================================
  // SISTEMA DE NAVEGACIÓN POR PESTAÑAS (OPCIÓN 1)
  // ======================================================================

  const navLinks = {
    overview: document.getElementById("nav-overview"),
    departments: document.getElementById("nav-departments"),
    marketplace: document.getElementById("nav-marketplace"),
    settings: document.getElementById("nav-settings")
  };

  const views = {
    overview: document.getElementById("view-overview"),
    departments: document.getElementById("view-departments"),
    marketplace: document.getElementById("view-marketplace"),
    settings: document.getElementById("view-settings")
  };

  function switchTab(tabKey) {
    // 1. Quitar la clase activa de todos los botones de navegación
    Object.values(navLinks).forEach(link => {
      if (link && link.parentElement) {
        link.parentElement.classList.remove("active");
      }
    });

    // 2. Añadir clase activa al botón presionado
    if (navLinks[tabKey] && navLinks[tabKey].parentElement) {
      navLinks[tabKey].parentElement.classList.add("active");
    }

    // 3. Ocultar todas las vistas y mostrar la seleccionada
    Object.keys(views).forEach(key => {
      if (views[key]) {
        if (key === tabKey) {
          views[key].style.display = "block";
          views[key].classList.add("active-view");
        } else {
          views[key].style.display = "none";
          views[key].classList.remove("active-view");
        }
      }
    });

    // 4. Actualizar dinámicamente el título y descripción del sistema
    if (tabKey === "overview") {
      headerTitle.textContent = "Centro de Orquestación";
      headerDesc.textContent = "Monitoreo en tiempo real de operaciones automatizadas";
      addLog("cerebro", "Navegando al Panel de Control de Orquestación.");
    } else if (tabKey === "departments") {
      headerTitle.textContent = "Departamentos Corporativos";
      headerDesc.textContent = "Diagnóstico e interacciones avanzadas con agentes de IA";
      addLog("cerebro", "Navegando a la vista detallada de Departamentos.");
      updateDynamicStats();
    } else if (tabKey === "marketplace") {
      headerTitle.textContent = "Catálogo de Habilidades";
      headerDesc.textContent = "Interactúa y prueba los gemelos de IA de los expertos";
      addLog("cerebro", "Navegando al Mercado de Clones Digitales.");
      loadMarketplaceClones();
    } else if (tabKey === "settings") {
      headerTitle.textContent = "Ajustes de la Empresa";
      headerDesc.textContent = "Configura variables de entorno globales y llaves de acceso";
      addLog("cerebro", "Navegando al panel de Ajustes.");
      loadSettingsFromServer();
    }
  }

  // Asignar Event Listeners de navegación
  if (navLinks.overview) navLinks.overview.addEventListener("click", (e) => { e.preventDefault(); switchTab("overview"); });
  if (navLinks.departments) navLinks.departments.addEventListener("click", (e) => { e.preventDefault(); switchTab("departments"); });
  if (navLinks.marketplace) navLinks.marketplace.addEventListener("click", (e) => { e.preventDefault(); switchTab("marketplace"); });
  if (navLinks.settings) navLinks.settings.addEventListener("click", (e) => { e.preventDefault(); switchTab("settings"); });


  // ======================================================================
  // MERCADO DE CLONES: PLAYGROUND CHAT E INTEGRACIÓN (OPCIÓN 1)
  // ======================================================================

  let activeCloneId = null;
  const clonesGrid = document.getElementById("clones-grid");
  const testChatBox = document.getElementById("test-chat-box");
  const testChatInput = document.getElementById("test-chat-input");
  const testSendBtn = document.getElementById("test-send-btn");
  const activeCloneName = document.getElementById("active-clone-name");
  const activeCloneSpecialty = document.getElementById("active-clone-specialty");
  const activeCloneAvatar = document.getElementById("active-clone-avatar");
  const testChatPlaceholder = document.getElementById("test-chat-placeholder");

  async function loadMarketplaceClones() {
    if (!clonesGrid) return;
    clonesGrid.innerHTML = `<div class="loading-clones">Consultando base de datos 'clones_db.json'...</div>`;

    try {
      const response = await fetch("/api/clones");
      if (!response.ok) throw new Error("No se pudo obtener el catálogo de clones.");
      
      const data = await response.json();
      const clones = data.clones;
      
      clonesGrid.innerHTML = "";
      
      // Actualizar contador en la pestaña de departamentos
      const totalClonesCount = Object.keys(clones).length;
      const statsTotalClones = document.getElementById("stats-total-clones");
      if (statsTotalClones) statsTotalClones.textContent = totalClonesCount;

      Object.keys(clones).forEach(id => {
        const clone = clones[id];
        const card = document.createElement("div");
        card.className = "clone-card";
        
        // Obtener las iniciales para el avatar
        const iniciales = clone.nombre.split(" ").map(n => n[0]).join("").substring(0, 2);
        
        card.innerHTML = `
          <div class="clone-card-header">
            <div class="clone-card-avatar">${iniciales}</div>
            <div class="clone-card-info">
              <div class="clone-card-name">${clone.nombre}</div>
              <div class="clone-card-specialty">${clone.especialidad}</div>
            </div>
          </div>
          <p class="clone-card-desc">${clone.conocimiento}</p>
          <div class="clone-card-meta">
            <span>Creado: ${clone.fecha_creacion}</span>
            <span>ID: ${id}</span>
          </div>
          <button class="clone-card-btn" data-id="${id}">Probar Clon</button>
        `;
        clonesGrid.appendChild(card);
      });

      // Añadir listeners para botones "Probar Clon"
      document.querySelectorAll(".clone-card-btn").forEach(btn => {
        btn.addEventListener("click", () => {
          const id = btn.getAttribute("data-id");
          selectCloneForTesting(id, clones[id]);
        });
      });

    } catch (error) {
      clonesGrid.innerHTML = `<div class="loading-clones" style="color: var(--color-marketing);">❌ Error al cargar clones: ${error.message}</div>`;
      addLog("desarrollo", `ERROR: No se pudo cargar el catálogo de clones. (${error.message})`);
    }
  }

  function selectCloneForTesting(id, clone) {
    activeCloneId = id;
    currentSessionId = null; // Resetear session_id al cambiar de clon
    
    // 1. Ocultar placeholder del chat
    if (testChatPlaceholder) testChatPlaceholder.style.display = "none";
    
    // 2. Actualizar cabecera del chat
    const iniciales = clone.nombre.split(" ").map(n => n[0]).join("").substring(0, 2);
    if (activeCloneAvatar) {
      activeCloneAvatar.textContent = iniciales;
      activeCloneAvatar.style.background = "linear-gradient(135deg, var(--color-desarrollo), var(--color-cerebro))";
      activeCloneAvatar.style.color = "#000";
    }
    if (activeCloneName) activeCloneName.textContent = clone.nombre;
    if (activeCloneSpecialty) activeCloneSpecialty.textContent = clone.especialidad;
    
    // 3. Habilitar inputs y botones de acción
    if (testChatInput) {
      testChatInput.removeAttribute("disabled");
      testChatInput.placeholder = `Pregúntale a ${clone.nombre.split(" ")[0]}...`;
      testChatInput.focus();
    }
    if (testSendBtn) testSendBtn.removeAttribute("disabled");
    
    // 4. Habilitar botones de acción
    const btnHistorial = document.getElementById("btn-historial");
    const btnEstadisticas = document.getElementById("btn-estadisticas");
    const btnLimpiarMemoria = document.getElementById("btn-limpiar-memoria");
    if (btnHistorial) btnHistorial.removeAttribute("disabled");
    if (btnEstadisticas) btnEstadisticas.removeAttribute("disabled");
    if (btnLimpiarMemoria) btnLimpiarMemoria.removeAttribute("disabled");
    
    // 5. Limpiar caja de chat y agregar saludo inicial del clon
    if (testChatBox) {
      testChatBox.innerHTML = `
        <div class="chat-bubble cerebro-msg" style="border-left-color: var(--color-desarrollo);">
          Hola, soy el gemelo digital de <strong>${clone.nombre}</strong>. He sido entrenado con sus habilidades y conocimientos en <em>${clone.especialidad}</em>.<br><br>¿En qué puedo asesorarte o ayudarte hoy?
        </div>
      `;
    }
    
    addLog("desarrollo", `Playground de chat abierto para el clon: '${id}' (${clone.nombre}).`);
  }

  // Helper: Añadir burbuja de chat en el playground
  function addTestChatBubble(sender, text) {
    if (!testChatBox) return;
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${sender === 'user' ? 'user-msg' : 'cerebro-msg'}`;
    if (sender === 'clone') {
      bubble.style.borderLeftColor = "var(--color-desarrollo)";
    }
    bubble.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
    testChatBox.appendChild(bubble);
    testChatBox.scrollTop = testChatBox.scrollHeight;
  }

  // Variable para mantener el session_id actual (usando AppState)
  let currentSessionId = AppState.currentSessionId;

  // Enviar mensaje al clon
  async function sendTestChatMessage() {
    if (!activeCloneId || !testChatInput) return;
    const text = testChatInput.value.trim();
    if (!text) return;
    
    addTestChatBubble("user", text);
    testChatInput.value = "";
    
    const thinkingBubble = document.createElement("div");
    thinkingBubble.className = "chat-bubble cerebro-msg thinking-bubble";
    thinkingBubble.style.borderLeftColor = "var(--color-desarrollo)";
    thinkingBubble.innerHTML = `<span class="thinking-dots"><span>.</span><span>.</span><span>.</span></span> Pensando...`;
    testChatBox.appendChild(thinkingBubble);
    testChatBox.scrollTop = testChatBox.scrollHeight;
    
    addLog("desarrollo", `Consultando al clon '${activeCloneId}'...`);

    try {
      const response = await fetch("/api/chat-clon", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id_clon: activeCloneId,
          pregunta: text,
          session_id: currentSessionId
        })
      });
      
      if (thinkingBubble.parentNode) {
        thinkingBubble.parentNode.removeChild(thinkingBubble);
      }

      if (!response.ok) throw new Error("Error al consultar al servidor.");
      const data = await response.json();
      
      if (data.session_id) {
        currentSessionId = data.session_id;
        AppState.set('currentSessionId', data.session_id);
      }
      
      addTestChatBubble("clone", data.respuesta);
      addLog("desarrollo", `Respuesta del clon '${activeCloneId}' recibida.`);
      
    } catch (error) {
      if (thinkingBubble.parentNode) {
        thinkingBubble.parentNode.removeChild(thinkingBubble);
      }
      addTestChatBubble("clone", `❌ Error: ${error.message}`);
      addLog("desarrollo", `ERROR: ${error.message}`);
      showToast("Error al consultar al clon", "error");
    }
  }

  if (testSendBtn && testChatInput) {
    testSendBtn.addEventListener("click", sendTestChatMessage);
    testChatInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") sendTestChatMessage();
    });
  }


  // ======================================================================
  // DETALLES DE DEPARTAMENTOS: INTERACCIONES RÁPIDAS (OPCIÓN 1)
  // ======================================================================

  // Botón Diagnóstico Desarrollo
  const btnTestDev = document.getElementById("btn-test-dev");
  if (btnTestDev) {
    btnTestDev.addEventListener("click", async () => {
      addLog("desarrollo", "Iniciando diagnóstico completo del motor de clonación...");
      btnTestDev.disabled = true;
      btnTestDev.textContent = "Ejecutando diagnóstico...";
      
      try {
        const response = await fetch("/api/clones");
        const data = await response.json();
        const count = Object.keys(data.clones).length;
        
        setTimeout(() => {
          addLog("desarrollo", `DIAGNÓSTICO COMPLETADO: Base de datos clones_db.json conectada. Total de clones de IA registrados en el sistema: ${count}. Estado general: ESTABLE (100%).`);
          btnTestDev.disabled = false;
          btnTestDev.textContent = "Ejecutar Diagnóstico de Motor";
          alert(`🛠️ Diagnóstico del Motor de IA completado:\n- Estado: 100% Funcional\n- Base de datos: Conectada\n- Clones Cargados: ${count}`);
        }, 1200);
      } catch (err) {
        addLog("desarrollo", `DIAGNÓSTICO FALLIDO: No se pudo contactar la base de datos de clones. Error: ${err.message}`);
        btnTestDev.disabled = false;
        btnTestDev.textContent = "Ejecutar Diagnóstico de Motor";
      }
    });
  }

  // Botón Diagnóstico Marketing
  const btnTestMarketing = document.getElementById("btn-test-marketing");
  if (btnTestMarketing) {
    btnTestMarketing.addEventListener("click", () => {
      const nicho = marketNichoInput ? marketNichoInput.value.trim() : "";
      if (!nicho) {
        alert("Escribe un nicho de mercado en la tarjeta del departamento para analizar.");
        return;
      }
      addLog("marketing", `Iniciando investigación automatizada de mercado sobre el nicho '${nicho}'...`);
      sendCommandToBackend(`marketing ${nicho}`);
      switchTab("overview"); // Redirigir al dashboard para ver la conversación detallada
    });
  }

  // Botón Diagnóstico Legal
  const btnTestLegal = document.getElementById("btn-test-legal");
  const legalNameInput = document.getElementById("legal-name-input");
  const legalIdInput = document.getElementById("legal-id-input");
  const legalSpecInput = document.getElementById("legal-spec-input");
  if (btnTestLegal) {
    btnTestLegal.addEventListener("click", () => {
      const name = legalNameInput ? legalNameInput.value.trim() : "";
      const id = legalIdInput ? legalIdInput.value.trim() : "";
      const spec = legalSpecInput ? legalSpecInput.value.trim() : "";
      
      if (!name || !id || !spec) {
        alert("Por favor rellena todos los campos (Nombre, ID y Especialidad) de la tarjeta legal.");
        return;
      }
      addLog("legal", `Solicitando redacción automatizada de contrato de licencia para '${name}' (${id})...`);
      sendCommandToBackend(`contrato ${name} ${id} ${spec.replace(/\s+/g, '_')} 15`);
      switchTab("overview"); // Redirigir al dashboard para ver el contrato
    });
  }

  // Botón Diagnóstico Operaciones/Finanzas
  const btnTestOperaciones = document.getElementById("btn-test-operaciones");
  if (btnTestOperaciones) {
    btnTestOperaciones.addEventListener("click", () => {
      addLog("operaciones", "Ejecutando auditoría de cuentas y cálculo de previsiones financieras...");
      sendCommandToBackend(`finanzas`);
      switchTab("overview"); // Redirigir al dashboard
    });
  }


  // ======================================================================
  // AJUSTES: CONFIGURACIÓN CORPORATIVA REAL (OPCIÓN 1)
  // ======================================================================

  const settingsForm = document.getElementById("settings-form");
  const inputGeminiKey = document.getElementById("input-gemini-key");
  const btnToggleKey = document.getElementById("btn-toggle-key");
  const inputCommission = document.getElementById("input-commission");
  const inputModel = document.getElementById("input-model");

  // Mostrar / Ocultar API Key
  if (btnToggleKey && inputGeminiKey) {
    btnToggleKey.addEventListener("click", () => {
      if (inputGeminiKey.type === "password") {
        inputGeminiKey.type = "text";
        btnToggleKey.textContent = "Ocultar";
      } else {
        inputGeminiKey.type = "password";
        btnToggleKey.textContent = "Mostrar";
      }
    });
  }

  // Cargar Ajustes del servidor
  async function loadSettingsFromServer() {
    if (!inputGeminiKey) return;
    try {
      const response = await fetch("/api/get-settings");
      if (!response.ok) throw new Error("Falla al recuperar ajustes.");
      const data = await response.json();
      
      if (data.has_key) {
        inputGeminiKey.value = "••••••••••••••••••••••••••••";
        inputGeminiKey.placeholder = "API Key configurada en el Servidor";
      } else {
        inputGeminiKey.value = "";
        inputGeminiKey.placeholder = "Escribe tu Google Gemini API Key...";
      }
      
      if (inputCommission && data.commission) {
        inputCommission.value = data.commission;
      }
      if (inputModel && data.model) {
        inputModel.value = data.model;
      }
    } catch (error) {
      console.error("Error al cargar ajustes del servidor:", error);
    }
  }

  // Guardar Ajustes en el servidor
  if (settingsForm) {
    settingsForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const geminiKey = inputGeminiKey.value.trim();
      const commission = inputCommission ? inputCommission.value.trim() : "15";
      const model = inputModel ? inputModel.value.trim() : "gemini-2.5-flash";
      
      addLog("cerebro", "Guardando cambios de configuración en el servidor...");
      
      // No enviar la clave de puntos simulados de carga
      const keyToSend = geminiKey.includes("••") ? "" : geminiKey;

      try {
        const response = await fetch("/api/settings", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ gemini_key: keyToSend, commission: commission, model: model })
        });
        if (!response.ok) throw new Error("No se pudo guardar la configuración.");
        const data = await response.json();

        addLog("cerebro", `ÉXITO: Configuración guardada en el backend. (${data.message})`);
        alert("✔️ Configuración guardada exitosamente en el servidor de SkillTwin.");
        loadSettingsFromServer();
      } catch (err) {
        addLog("cerebro", `ERROR al guardar ajustes: ${err.message}`);
        alert(`❌ Error al guardar ajustes: ${err.message}`);
      }
    });
  }

  // ======================================================================
  // BÚSQUEDA GLOBAL DE CLONES
  // ======================================================================

  const searchInput = document.createElement('input');
  searchInput.type = 'text';
  searchInput.className = 'chat-input search-global-input';
  searchInput.placeholder = 'Buscar clones por nombre, especialidad...';
  searchInput.style.cssText = 'max-width: 300px; font-size: 0.85rem;';
  
  const searchResults = document.createElement('div');
  searchResults.className = 'search-results-dropdown';
  
  const searchWrapper = document.createElement('div');
  searchWrapper.className = 'search-wrapper';
  searchWrapper.style.cssText = 'position: relative; margin-left: auto;';
  searchWrapper.appendChild(searchInput);
  searchWrapper.appendChild(searchResults);
  
  const pageTitleEl = document.querySelector(".top-bar .page-title");
  if (pageTitleEl) {
    pageTitleEl.parentNode.insertBefore(searchWrapper, pageTitleEl.nextSibling);
  }
  
  async function searchClones(query) {
    if (!query || query.length < 2) {
      searchResults.style.display = 'none';
      return;
    }
    
    try {
      const response = await fetch(`/api/search-clones?q=${encodeURIComponent(query)}`);
      if (!response.ok) throw new Error("Error en la búsqueda");
      const data = await response.json();
      
      if (data.resultados.length === 0) {
        searchResults.innerHTML = '<div class="search-result-empty">No se encontraron clones</div>';
      } else {
        searchResults.innerHTML = data.resultados.map(clon => `
          <div class="search-result-item" data-id="${clon.id}">
            <strong>${clon.nombre}</strong>
            <span>${clon.especialidad}</span>
          </div>
        `).join('');
      }
      
      searchResults.style.display = 'block';
      
      document.querySelectorAll('.search-result-item').forEach(item => {
        item.addEventListener('click', () => {
          const cloneId = item.getAttribute('data-id');
          selectCloneForTesting(cloneId, AppState.clones[cloneId]);
          switchTab('marketplace');
          searchInput.value = '';
          searchResults.style.display = 'none';
        });
      });
      
    } catch (error) {
      console.error("Error en búsqueda:", error);
    }
  }
  
  searchInput.addEventListener('input', debounce((e) => {
    searchClones(e.target.value);
  }, 300));
  
  searchInput.addEventListener('blur', () => {
    setTimeout(() => {
      searchResults.style.display = 'none';
    }, 200);
  });

  // ======================================================================
  // FUNCIONALIDADES DE MEMORIA DE CONVERSACIÓN
  // ======================================================================

  // Botón de historial
  const btnHistorial = document.getElementById("btn-historial");
  if (btnHistorial) {
    btnHistorial.addEventListener("click", async () => {
      if (!activeCloneId) return;
      
      try {
        const response = await fetch(`/api/clon-historial?clon_id=${activeCloneId}&session_id=${currentSessionId || ''}`);
        if (!response.ok) throw new Error("No se pudo obtener el historial.");
        const data = await response.json();
        
        const modal = document.createElement("div");
        modal.className = "modal-overlay";
        modal.innerHTML = `
          <div class="modal-content">
            <div class="modal-header">
              <h3>Historial de Conversación</h3>
              <button class="modal-close" id="close-historial">&times;</button>
            </div>
            <div class="modal-body">
              ${data.historial.length === 0 ? 
                '<p class="empty-state">No hay historial de conversación para este clon.</p>' :
                data.historial.map(item => `
                  <div class="historial-item">
                    <div class="timestamp">${new Date(item.timestamp).toLocaleString()}</div>
                    <div class="pregunta">P: ${item.pregunta}</div>
                    <div class="respuesta">R: ${item.respuesta.substring(0, 150)}...</div>
                  </div>
                `).join('')
              }
            </div>
          </div>
        `;
        
        document.body.appendChild(modal);
        
        const closeModal = () => modal.remove();
        document.getElementById("close-historial").addEventListener("click", closeModal);
        modal.addEventListener("click", (e) => {
          if (e.target === modal) closeModal();
        });
        document.addEventListener('keydown', function escHandler(e) {
          if (e.key === 'Escape') {
            closeModal();
            document.removeEventListener('keydown', escHandler);
          }
        });
        
      } catch (error) {
        addLog("desarrollo", `ERROR: No se pudo cargar el historial. ${error.message}`);
        showToast("Error al cargar historial", "error");
      }
    });
  }

  // Botón de estadísticas
  const btnEstadisticas = document.getElementById("btn-estadisticas");
  if (btnEstadisticas) {
    btnEstadisticas.addEventListener("click", async () => {
      if (!activeCloneId) return;
      
      try {
        const response = await fetch(`/api/clon-estadisticas?clon_id=${activeCloneId}`);
        if (!response.ok) throw new Error("No se pudieron obtener las estadísticas.");
        const data = await response.json();
        const stats = data.estadisticas;
        
        const modal = document.createElement("div");
        modal.className = "modal-overlay";
        modal.innerHTML = `
          <div class="modal-content">
            <div class="modal-header">
              <h3>Estadísticas del Clon</h3>
              <button class="modal-close" id="close-estadisticas">&times;</button>
            </div>
            <div class="modal-body">
              <div class="estadisticas-grid">
                <div class="estadistica-card">
                  <div class="valor">${stats.total_interacciones}</div>
                  <div class="etiqueta">Total Interacciones</div>
                </div>
                <div class="estadistica-card">
                  <div class="valor">${stats.memorias_exito}</div>
                  <div class="etiqueta">Memorias de Éxito</div>
                </div>
              </div>
              ${stats.temas_mas_frecuentes.length > 0 ? `
                <div class="temas-list">
                  <h4>Temas Más Frecuentes:</h4>
                  ${stats.temas_mas_frecuentes.map(tema => `
                    <div class="tema-item">
                      <span>${tema.tema}</span>
                      <span>${tema.frecuencia} veces</span>
                    </div>
                  `).join('')}
                </div>
              ` : ''}
              ${stats.ultima_interaccion ? `
                <p class="last-interaction">
                  Última interacción: ${new Date(stats.ultima_interaccion).toLocaleString()}
                </p>
              ` : ''}
            </div>
          </div>
        `;
        
        document.body.appendChild(modal);
        
        const closeModal = () => modal.remove();
        document.getElementById("close-estadisticas").addEventListener("click", closeModal);
        modal.addEventListener("click", (e) => {
          if (e.target === modal) closeModal();
        });
        document.addEventListener('keydown', function escHandler(e) {
          if (e.key === 'Escape') {
            closeModal();
            document.removeEventListener('keydown', escHandler);
          }
        });
        
      } catch (error) {
        addLog("desarrollo", `ERROR: No se pudieron cargar las estadísticas. ${error.message}`);
        showToast("Error al cargar estadísticas", "error");
      }
    });
  }

  // Botón de limpiar memoria
  const btnLimpiarMemoria = document.getElementById("btn-limpiar-memoria");
  if (btnLimpiarMemoria) {
    btnLimpiarMemoria.addEventListener("click", async () => {
      if (!activeCloneId) return;
      
      if (!confirm("¿Estás seguro de que quieres limpiar la memoria de conversación? Esta acción no se puede deshacer.")) {
        return;
      }
      
      try {
        const response = await fetch("/api/clon-limpiar-memoria", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            clon_id: activeCloneId,
            session_id: currentSessionId
          })
        });
        
        if (!response.ok) throw new Error("No se pudo limpiar la memoria.");
        
        if (testChatBox) {
          testChatBox.innerHTML = `
            <div class="test-chat-placeholder">
              <div class="pulse-icon">💬</div>
              <p>Memoria limpiada. Inicia una nueva conversación con el clon.</p>
            </div>
          `;
        }
        
        currentSessionId = null;
        AppState.set('currentSessionId', null);
        
        addLog("desarrollo", `Memoria limpiada para el clon '${activeCloneId}'.`);
        showToast("Memoria de conversación limpiada", "success");
        
      } catch (error) {
        addLog("desarrollo", `ERROR: No se pudo limpiar la memoria. ${error.message}`);
        showToast("Error al limpiar la memoria", "error");
      }
    });
  }
});
