const api = typeof browser !== "undefined" ? browser : chrome;

const SERVER_URL     = "http://localhost:5050/analyze";
const PING_URL       = "http://localhost:5050/ping";
const MAGIKA_INSTALL = "https://github.com/google/magika?tab=readme-ov-file#installation";

function log(...a)  { console.log("[Madoka]", ...a); }
function warn(...a) { console.warn("[Madoka]", ...a); }

// ── Helpers de storage ────────────────────────────────────────────────────────
async function getSetting(key, def) {
  const r = await api.storage.local.get(key);
  return r[key] !== undefined ? r[key] : def;
}

// ── Notificar respetando ajuste del usuario ───────────────────────────────────
async function notify(id, options) {
  const notifEnabled = await getSetting("notifEnabled", true);
  if (!notifEnabled) return;
  try { api.notifications.create(id, options); } catch(e) { warn("notify:", e.message); }
}

// ── Verificar servidor ────────────────────────────────────────────────────────
async function checkServerOnStartup() {
  try {
    const r = await fetch(PING_URL, { signal: AbortSignal.timeout(3000) });
    if (!r.ok) throw new Error();
    setIcon("active");
  } catch {
    setIcon("inactive");
    notify("madoka-offline", {
      type: "basic", iconUrl: "icon48.png",
      title: "Madoka — Servidor no disponible",
      message: "El servidor local no responde. Haz clic para ver instrucciones.",
      priority: 2
    });
  }
}

api.notifications.onClicked.addListener((id) => {
  if (id === "madoka-offline") {
    api.tabs.create({ url: MAGIKA_INSTALL });
    api.notifications.clear("madoka-offline");
  }
});

api.runtime.onStartup.addListener(checkServerOnStartup);
api.runtime.onInstalled.addListener(checkServerOnStartup);

// ── Estado / ícono ────────────────────────────────────────────────────────────
function setIcon(state) {
  const badge = state === "active" ? "" : state === "disabled" ? "OFF" : "!";
  const color  = state === "active" ? "#22c55e" : state === "disabled" ? "#6b7280" : "#ef4444";
  const actionApi = api.browserAction || api.action;
  actionApi?.setBadgeText({ text: badge });
  actionApi?.setBadgeBackgroundColor({ color });
}

// ── Listener de descargas ─────────────────────────────────────────────────────
log("Listener de descargas activo");

api.downloads.onChanged.addListener(async (delta) => {
  if (!delta.state || delta.state.current !== "complete") return;

  const enabled     = await getSetting("enabled",     true);
  const autoAnalyze = await getSetting("autoAnalyze", true);
  if (!enabled || !autoAnalyze) return;

  const items = await api.downloads.search({ id: delta.id });
  const item  = items?.[0];
  if (!item) return;

  const filePath = item.filename;
  const fileName = filePath.split(/[\\/]/).pop();
  log("Descarga completa:", fileName);

  notify(`scanning-${delta.id}`, {
    type: "basic", iconUrl: "icon48.png",
    title: "Madoka — Analizando...",
    message: `Verificando: ${fileName}`, priority: 0
  });

  try {
    const response = await fetch(SERVER_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: filePath }),
      signal: AbortSignal.timeout(15000)
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result = await response.json();

    const score      = Math.round((result.score || 0) * 100);
    const label      = result.label || "Desconocido";
    const desc       = result.description || label;
    const mismatch   = result.extension_mismatch;
    const suspicious = result.suspicious;
    const declaredExt = result.declared_extension;
    const isRisk     = suspicious || mismatch;

    // Si "solo alertar en riesgo" está activo, silenciar archivos normales
    const silentOk = await getSetting("silentOk", false);

    api.notifications.clear(`scanning-${delta.id}`);

    if (!isRisk && silentOk) {
      log("Archivo OK — notificación silenciada por ajuste");
    } else {
      let title, message;
      if (suspicious) {
        title   = "⚠️ Madoka — Tipo ejecutable detectado";
        message = `${fileName}\nTipo real: ${desc}\nRevisa antes de abrir.`;
      } else if (mismatch) {
        title   = "⚠️ Madoka — Extensión no coincide";
        message = `${fileName}\nExtensión .${declaredExt} pero contenido: ${desc}`;
      } else {
        title   = "✅ Madoka — Archivo verificado";
        message = `${fileName}\nTipo: ${desc} (${score}% confianza)`;
      }

      notify(`result-${delta.id}`, {
        type: "basic", iconUrl: "icon48.png",
        title, message,
        priority: isRisk ? 2 : 1,
        requireInteraction: isRisk
      });
    }

    saveToHistory({ fileName, filePath, label, desc, score, mismatch, suspicious, time: Date.now() });
    setIcon("active");
    log("Resultado:", label, score + "%");

  } catch(e) {
    warn("Error:", e.message);
    api.notifications.clear(`scanning-${delta.id}`);
    notify(`error-${delta.id}`, {
      type: "basic", iconUrl: "icon48.png",
      title: "Madoka — Servidor no disponible",
      message: "Asegúrate de que el servidor está corriendo.\n(python madoka.py start)",
      priority: 1
    });
    setIcon("inactive");
  }
});

// ── Mensajes desde popup ──────────────────────────────────────────────────────
api.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "toggle") {
    api.storage.local.set({ enabled: msg.value });
    setIcon(msg.value ? "active" : "disabled");
    sendResponse({ ok: true });
  }
  if (msg.type === "check_server") {
    fetch(PING_URL, { signal: AbortSignal.timeout(3000) })
      .then(r => { sendResponse({ online: r.ok }); setIcon(r.ok ? "active" : "inactive"); })
      .catch(()  => { sendResponse({ online: false }); setIcon("inactive"); });
    return true;
  }
});

async function saveToHistory(entry) {
  const { history = [] } = await api.storage.local.get("history");
  history.unshift(entry);
  if (history.length > 50) history.pop();
  await api.storage.local.set({ history });
}
