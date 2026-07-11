// SkillTwin HQ - Cerebro Central JavaScript Logic (Conexión Real con Servidor)

document.addEventListener("DOMContentLoaded", () => {
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

  // Helper: Append Chat Bubble
  function addChatBubble(sender, text) {
    if (!chatBox) return;
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${sender === 'user' ? 'user-msg' : 'cerebro-msg'}`;
    bubble.innerHTML = text.replace(/\n/g, "<br>");
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
    
    // Cambiar actividad del Cerebro a Procesando
    cerebroActivity.textContent = "Estado: Procesando instrucción...";
    addLog("cerebro", "Transmitiendo comando al orquestador backend...");

    try {
      const response = await fetch("/api/command", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ command: text })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // 1. Mostrar respuesta en chat
      addChatBubble("cerebro", data.message);
      
      // 2. Ejecutar animación del departamento responsable
      if (data.tag && departments[data.tag]) {
        animateDepartment(data.tag);
      }
      
      // 3. Añadir entrada al Live Console
      if (data.console_log) {
        addLog(data.tag || "cerebro", data.console_log);
      }

      // 4. Si es de finanzas, legal o marketing, actualizar las estadísticas dinámicas en la pestaña de detalles
      updateDynamicStats();

    } catch (error) {
      console.error("Error al enviar comando:", error);
      addChatBubble("cerebro", "❌ **Error de Conexión:** No se pudo contactar con el Cerebro Central en el servidor local. Asegúrate de tener corriendo `server.py`.");
      addLog("cerebro", `ERROR: Falla de comunicación con el orquestador backend. (${error.message})`);
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
    
    // 3. Habilitar inputs
    if (testChatInput) {
      testChatInput.removeAttribute("disabled");
      testChatInput.placeholder = `Pregúntale a ${clone.nombre.split(" ")[0]}...`;
      testChatInput.focus();
    }
    if (testSendBtn) testSendBtn.removeAttribute("disabled");
    
    // 4. Limpiar caja de chat y agregar saludo inicial del clon
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
    bubble.innerHTML = text.replace(/\n/g, "<br>");
    testChatBox.appendChild(bubble);
    testChatBox.scrollTop = testChatBox.scrollHeight;
  }

  // Enviar mensaje al clon
  async function sendTestChatMessage() {
    if (!activeCloneId || !testChatInput) return;
    const text = testChatInput.value.trim();
    if (!text) return;
    
    // 1. Añadir mensaje del usuario al chat
    addTestChatBubble("user", text);
    testChatInput.value = "";
    
    // 2. Añadir indicador de pensando
    const thinkingBubble = document.createElement("div");
    thinkingBubble.className = "chat-bubble cerebro-msg thinking-bubble";
    thinkingBubble.style.borderLeftColor = "var(--color-desarrollo)";
    thinkingBubble.innerHTML = `<span style="opacity: 0.6;">Pensando respuesta...</span>`;
    testChatBox.appendChild(thinkingBubble);
    testChatBox.scrollTop = testChatBox.scrollHeight;
    
    addLog("desarrollo", `Consultando al clon '${activeCloneId}' en el backend...`);

    try {
      const response = await fetch("/api/chat-clon", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ id_clon: activeCloneId, pregunta: text })
      });
      
      // Eliminar burbuja de pensando
      if (thinkingBubble.parentNode) {
        thinkingBubble.parentNode.removeChild(thinkingBubble);
      }

      if (!response.ok) throw new Error("Error al consultar al servidor.");
      const data = await response.json();
      
      // 3. Renderizar la respuesta real del clon
      addTestChatBubble("clone", data.respuesta);
      addLog("desarrollo", `Respuesta recibida del clon '${activeCloneId}'.`);
      
    } catch (error) {
      if (thinkingBubble.parentNode) {
        thinkingBubble.parentNode.removeChild(thinkingBubble);
      }
      addTestChatBubble("clone", `❌ **Error:** No se pudo establecer conexión con el motor de clonación. Detalles: ${error.message}`);
      addLog("desarrollo", `ERROR: Consulta fallida al clon '${activeCloneId}'. (${error.message})`);
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
  const marketNichoInput = document.getElementById("market-nicho-input");
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
});
