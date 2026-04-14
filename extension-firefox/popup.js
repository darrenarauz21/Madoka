const api = typeof browser !== "undefined" ? browser : chrome;

const dot        = document.getElementById("dot");
const statusText = document.getElementById("status-text");
const list       = document.getElementById("list");
const mainToggle = document.getElementById("main-toggle");
const toggleText = document.getElementById("toggle-text");
const banner     = document.getElementById("disabled-banner");
const githubLink = document.getElementById("github-link");
const clearBtn   = document.getElementById("clear-btn");
const btnSettings = document.getElementById("btn-settings");
const settingsPanel = document.getElementById("settings-panel");
const notifToggle = document.getElementById("notif-toggle");
const notifDesc   = document.getElementById("notif-desc");
const autoToggle  = document.getElementById("auto-toggle");
const silentToggle = document.getElementById("silent-toggle");

// ── Ajustes: abrir/cerrar panel ───────────────────────────────────────────────
btnSettings.addEventListener("click", () => {
  const isOpen = settingsPanel.classList.toggle("open");
  btnSettings.classList.toggle("open", isOpen);
});

// ── Toggle principal ON/OFF ───────────────────────────────────────────────────
api.storage.local.get("enabled", ({ enabled = true }) => {
  mainToggle.checked = enabled;
  updateMainToggleUI(enabled);
});

mainToggle.addEventListener("change", () => {
  const val = mainToggle.checked;
  api.storage.local.set({ enabled: val });
  api.runtime.sendMessage({ type: "toggle", value: val });
  updateMainToggleUI(val);
});

function updateMainToggleUI(enabled) {
  toggleText.textContent = enabled ? "Activo" : "Inactivo";
  banner.style.display   = enabled ? "none" : "block";
}

// ── Ajuste: notificaciones ────────────────────────────────────────────────────
async function refreshNotifState() {
  const { notifEnabled = true } = await api.storage.local.get("notifEnabled");
  const perm = Notification.permission;

  if (perm === "denied") {
    notifToggle.checked  = false;
    notifToggle.disabled = true;
    notifDesc.textContent = "Bloqueadas en el sistema — actívalas en Configuración de Windows";
    notifDesc.className   = "setting-desc warn";
    return;
  }

  notifToggle.disabled = false;
  notifToggle.checked  = notifEnabled && perm === "granted";

  if (perm === "granted") {
    notifDesc.textContent = notifEnabled ? "Activadas" : "Desactivadas";
    notifDesc.className   = notifEnabled ? "setting-desc ok" : "setting-desc";
  } else {
    // "default" — nunca pedido
    notifToggle.checked   = false;
    notifDesc.textContent = "No configuradas — activa para habilitar alertas";
    notifDesc.className   = "setting-desc warn";
  }
}

notifToggle.addEventListener("change", async () => {
  if (notifToggle.checked) {
    // Pedir permiso si no está concedido
    if (Notification.permission !== "granted") {
      notifToggle.disabled = true;
      notifDesc.textContent = "Solicitando permiso...";
      const result = await Notification.requestPermission();
      notifToggle.disabled = false;
      if (result === "granted") {
        await api.storage.local.set({ notifEnabled: true });
        // Notificación de prueba
        new Notification("✅ Madoka Scanner", {
          body: "Las notificaciones están activas.",
          icon: api.runtime.getURL("icon48.png")
        });
      } else {
        notifToggle.checked = false;
        await api.storage.local.set({ notifEnabled: false });
      }
    } else {
      await api.storage.local.set({ notifEnabled: true });
    }
  } else {
    await api.storage.local.set({ notifEnabled: false });
  }
  await refreshNotifState();
});

// ── Ajuste: auto-analizar ─────────────────────────────────────────────────────
api.storage.local.get("autoAnalyze", ({ autoAnalyze = true }) => {
  autoToggle.checked = autoAnalyze;
});
autoToggle.addEventListener("change", () => {
  api.storage.local.set({ autoAnalyze: autoToggle.checked });
});

// ── Ajuste: solo alertar en riesgo ────────────────────────────────────────────
api.storage.local.get("silentOk", ({ silentOk = false }) => {
  silentToggle.checked = silentOk;
});
silentToggle.addEventListener("change", () => {
  api.storage.local.set({ silentOk: silentToggle.checked });
});

// ── Estado del servidor ───────────────────────────────────────────────────────
api.runtime.sendMessage({ type: "check_server" }, ({ online } = {}) => {
  if (online) {
    dot.className    = "dot ok";
    statusText.textContent = "Servidor activo";
    githubLink.style.display = "none";
  } else {
    dot.className    = "dot error";
    statusText.textContent = "Servidor offline — ejecuta: python madoka.py start";
    githubLink.style.display = "inline";
  }
});

// ── Historial ─────────────────────────────────────────────────────────────────
chrome.storage.local.get("history", ({ history = [] }) => renderHistory(history));

function renderHistory(history) {
  if (!history || history.length === 0) {
    list.innerHTML = '<div class="empty">Sin análisis aún</div>';
    return;
  }
  list.innerHTML = history.slice(0, 12).map(entry => {
    const chipClass = entry.suspicious ? "chip-bad"
                    : entry.mismatch   ? "chip-warn"
                    :                    "chip-ok";
    const chipText  = entry.suspicious ? "⚠ Sospechoso"
                    : entry.mismatch   ? "⚠ No coincide"
                    :                    "✓ OK";
    const scoreText = entry.score > 0 ? `${entry.score}%` : "";
    const time = new Date(entry.time).toLocaleString("es", {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
    });
    return `<div class="item">
      <div class="item-name" title="${entry.filePath}">${entry.fileName}</div>
      <div class="item-meta">
        <span class="chip ${chipClass}">${chipText}</span>
        <span>${entry.desc || entry.label}</span>
        ${scoreText ? `<span>${scoreText}</span>` : ""}
        <span style="margin-left:auto;font-size:10px">${time}</span>
      </div>
    </div>`;
  }).join("");
}

clearBtn.addEventListener("click", () => {
  api.storage.local.set({ history: [] });
  list.innerHTML = '<div class="empty">Historial limpiado</div>';
});

// ── Init ──────────────────────────────────────────────────────────────────────
refreshNotifState();
