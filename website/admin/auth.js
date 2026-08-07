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

  window.AdminAuth = {
    requireAuth,
    getApiKey,
    clearAuth,
    isAuthed,
    loadAdminConfig,
    authRequired,
  };
})();
