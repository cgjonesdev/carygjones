(function () {
  "use strict";

  const AUTH_SESSION = "jobSearchAdminAuth";

  async function sha256(text) {
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
    return Array.from(new Uint8Array(buf))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }

  async function loadAdminConfig() {
    const resp = await fetch("config.json");
    if (!resp.ok) return {};
    return resp.json();
  }

  function isAuthed() {
    return sessionStorage.getItem(AUTH_SESSION) === "1";
  }

  function setAuthed(password) {
    sessionStorage.setItem(AUTH_SESSION, "1");
    if (password) {
      sessionStorage.setItem("jobSearchAdminApiKey", password);
    }
  }

  function clearAuth() {
    sessionStorage.removeItem(AUTH_SESSION);
    sessionStorage.removeItem("jobSearchAdminApiKey");
  }

  function getApiKey() {
    return sessionStorage.getItem("jobSearchAdminApiKey") || "";
  }

  function authRequired(config) {
    return Boolean(config && config.passwordHash);
  }

  function isLocalAdminHost() {
    const host = location.hostname;
    return host === "localhost" || host === "127.0.0.1";
  }

  function localSyncBase() {
    const port = Number(new URLSearchParams(location.search).get("syncPort") || "8765");
    return `http://127.0.0.1:${port}`;
  }

  function isLocalSyncApi(base) {
    const value = String(base || "");
    return /^https?:\/\/(?:127\.0\.0\.1|localhost):\d+/.test(value);
  }

  function loadDashboardSettings() {
    try {
      return JSON.parse(localStorage.getItem("jobSearchAdmin") || "{}");
    } catch (_) {
      return {};
    }
  }

  function resolveApiBase(config) {
    if (config?.apiBase) {
      return String(config.apiBase).replace(/\/$/, "");
    }
    const saved = loadDashboardSettings();
    if (saved.apiBase) {
      return String(saved.apiBase).replace(/\/$/, "");
    }
    if (isLocalAdminHost()) {
      return localSyncBase();
    }
    return "";
  }

  function resolveApiKey(configApiBase) {
    const fromSession = getApiKey();
    if (fromSession) return fromSession;
    const saved = loadDashboardSettings();
    if (!configApiBase && saved.apiKey) return saved.apiKey;
    return "";
  }

  function showLoginScreen(config, onSuccess) {
    document.body.classList.add("login-mode");
    let overlay = document.getElementById("login-overlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "login-overlay";
      overlay.innerHTML = `
        <div class="login-card panel">
          <h2>Admin login</h2>
          <p class="hint">Enter the admin password to continue.</p>
          <label for="login-password">Password</label>
          <input id="login-password" type="password" autocomplete="current-password">
          <div class="btn-row">
            <button id="login-submit" class="btn btn-primary" type="button">Sign in</button>
          </div>
          <div id="login-error" class="status-bar err" hidden></div>
        </div>`;
      document.body.appendChild(overlay);
    }

    const main = document.querySelector("main");
    if (main) main.hidden = true;

    const submit = () => {
      void (async () => {
        const pwd = document.getElementById("login-password").value;
        const err = document.getElementById("login-error");
        const hash = await sha256(pwd);
        if (hash !== config.passwordHash) {
          err.hidden = false;
          err.textContent = "Incorrect password.";
          return;
        }
        setAuthed(pwd);
        overlay.remove();
        document.body.classList.remove("login-mode");
        if (main) main.hidden = false;
        onSuccess(pwd);
      })();
    };

    document.getElementById("login-submit").onclick = submit;
    document.getElementById("login-password").onkeydown = (e) => {
      if (e.key === "Enter") submit();
    };
    document.getElementById("login-password").focus();
  }

  async function requireAuth(onSuccess) {
    const config = await loadAdminConfig();
    if (!authRequired(config)) {
      onSuccess(getApiKey(), config);
      return config;
    }
    if (isAuthed()) {
      onSuccess(getApiKey(), config);
      return config;
    }
    showLoginScreen(config, (pwd) => onSuccess(pwd, config));
    return config;
  }

  async function fetchWithAuth(url, options = {}) {
    const key = getApiKey();
    const headers = { ...(options.headers || {}) };
    if (key) headers["X-Admin-Key"] = key;
    return fetch(url, { ...options, headers });
  }

  function normalizeAdminLink(url) {
    const raw = String(url ?? "");
    if (raw.startsWith("/api/applications/")) {
      const match = raw.match(/\/api\/applications\/([^/]+)/);
      return match ? `app.html?slug=${encodeURIComponent(match[1])}` : raw;
    }
    if (raw.startsWith("/admin/")) return raw.slice("/admin/".length);
    return raw;
  }

  function buildApplicationLinks(meta, slug) {
    const s = slug || meta?.slug || "";
    const appBase = `app.html?slug=${encodeURIComponent(s)}`;
    const links = [];
    if (meta?.apply_url) links.push({ label: "Apply", url: meta.apply_url });
    if (meta?.interview_url) links.push({ label: "Interview", url: meta.interview_url });
    if (meta?.gmail_url) links.push({ label: "Gmail", url: meta.gmail_url });
    links.push(
      { label: "Resume", url: `${appBase}&doc=resume` },
      { label: "Cover", url: `${appBase}&doc=cover` },
      { label: "JD", url: `${appBase}&doc=jd` },
      { label: "Settings", url: appBase }
    );
    return links;
  }

  function escapeHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(s) {
    return escapeHtml(s).replace(/'/g, "&#39;");
  }

  function linksHtml(links) {
    if (!links || !links.length) return "—";
    return links
      .map((l) => {
        const href = normalizeAdminLink(l.url);
        const internal = href.startsWith("app.html");
        const target = internal ? "" : ' target="_blank" rel="noopener"';
        return `<a href="${escapeAttr(href)}"${target}>${escapeHtml(l.label)}</a>`;
      })
      .join("");
  }

  async function downloadApplicationFile(apiBase, slug, filename) {
    const base = String(apiBase || "").replace(/\/$/, "");
    if (!base) throw new Error("Cloud Run API is required to download files.");
    const url = `${base}/api/applications/${encodeURIComponent(slug)}/${encodeURIComponent(filename)}`;
    const resp = await fetchWithAuth(url);
    if (!resp.ok) {
      let detail = resp.statusText;
      try {
        const data = await resp.json();
        detail = data.detail || detail;
      } catch (_) {
        /* ignore */
      }
      throw new Error(detail || `Download failed (${resp.status})`);
    }
    const blob = await resp.blob();
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(objectUrl);
  }

  window.AdminAuth = {
    requireAuth,
    getApiKey,
    clearAuth,
    isAuthed,
    loadAdminConfig,
    authRequired,
    isLocalAdminHost,
    localSyncBase,
    isLocalSyncApi,
    resolveApiBase,
    resolveApiKey,
    fetchWithAuth,
    normalizeAdminLink,
    buildApplicationLinks,
    linksHtml,
    downloadApplicationFile,
  };
})();
