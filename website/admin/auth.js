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

  /** Local admin copies live under website/admin/apps/ — use those on localhost, not Cloud Run. */
  function preferLocalAppFiles() {
    return isLocalAdminHost();
  }

  function localSyncBase() {
    const port = Number(new URLSearchParams(location.search).get("syncPort") || "8765");
    const host =
      location.hostname === "localhost" || location.hostname === "127.0.0.1"
        ? location.hostname
        : "127.0.0.1";
    return `http://${host}:${port}`;
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

  /** Same default as scripts/serve_admin_local.sh */
  const DEFAULT_LOCAL_PROTOCOL_API =
    "https://job-search-admin-416806702268.us-west1.run.app";

  function resolveProtocolApiBase(config) {
    if (config?.apiBase) {
      return String(config.apiBase).replace(/\/$/, "");
    }
    const saved = loadDashboardSettings();
    if (saved.apiBase) {
      return String(saved.apiBase).replace(/\/$/, "");
    }
    if (isLocalAdminHost()) {
      return DEFAULT_LOCAL_PROTOCOL_API.replace(/\/$/, "");
    }
    return "";
  }

  let cachedSameOriginApi = null;

  async function probeSameOriginApi() {
    if (cachedSameOriginApi !== null) return cachedSameOriginApi;
    try {
      const resp = await fetch("/api/health", { credentials: "same-origin" });
      if (resp.ok) {
        cachedSameOriginApi = window.location.origin;
        return cachedSameOriginApi;
      }
    } catch (_) {
      /* not served from unified admin API */
    }
    cachedSameOriginApi = "";
    return "";
  }

  async function resolveUnifiedApiBase(config) {
    const same = await probeSameOriginApi();
    if (same) return same;
    return resolveProtocolApiBase(config);
  }

  /** Cloud Run URL for protocols/drafts (from deploy config). */
  function resolveApiBase(config) {
    return resolveProtocolApiBase(config);
  }

  async function isLocalSyncReachable() {
    if (!isLocalAdminHost()) return false;
    try {
      const resp = await fetch(`${localSyncBase()}/api/health`);
      return resp.ok;
    } catch (_) {
      return false;
    }
  }

  /** Where application settings PATCH should go — unified API on same host, else legacy local sync. */
  async function resolveSaveApiBase(config) {
    const same = await probeSameOriginApi();
    if (same) return same;
    if (isLocalAdminHost()) {
      return (await isLocalSyncReachable()) ? localSyncBase() : "";
    }
    const cloud = resolveProtocolApiBase(config);
    const key = resolveApiKey(true);
    if (cloud && key) {
      return cloud;
    }
    return "";
  }

  function saveBlockedMessage(config) {
    if (isLocalAdminHost()) {
      return "Start ./scripts/serve_admin_local.sh (unified GCS API) or set ADMIN_LEGACY=1 for the old sync server.";
    }
    if (resolveProtocolApiBase(config)) {
      return "Saving requires signing in on the admin dashboard (same password as Cloud Run).";
    }
    return "Saving requires the Cloud Run API (set ADMIN_API_BASE_URL and redeploy).";
  }

  /** True when saves go to the unified admin API (local uvicorn or Cloud Run), not legacy :8765 sync. */
  function usesUnifiedGcsApi(apiBase) {
    const base = String(apiBase || "").replace(/\/$/, "");
    if (!base) return false;
    if (base === window.location.origin.replace(/\/$/, "")) return true;
    return !isLocalSyncApi(base);
  }

  function formatSaveStatus(data, label = "Settings") {
    if (data?.gcs_warning) {
      return `${label} saved — ${data.gcs_warning}`;
    }
    if (data?.saved_to_gcs === true || usesUnifiedGcsApi(data?.api_base)) {
      return `${label} saved to GCS.`;
    }
    if (data?.saved_to_gcs === false || data?.gcs_error) {
      return data.gcs_error || `${label} could not reach GCS — check GCS_BUCKET and retry.`;
    }
    if (isLocalSyncApi(data?.api_base)) {
      return data?.saved_to_gcs
        ? `${label} saved to GCS.`
        : `${label} could not reach GCS — check GCS_BUCKET on the sync server.`;
    }
    return `${label} saved to GCS.`;
  }

  function resolveApiKey(_configApiBase) {
    const fromSession = getApiKey();
    if (fromSession) return fromSession;
    const saved = loadDashboardSettings();
    return saved.apiKey || "";
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
    const headers = { ...(options.headers || {}) };
    if (!isLocalSyncApi(url)) {
      const key = resolveApiKey(true);
      if (key) headers["X-Admin-Key"] = key;
    }
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
    const applyUrl = applyUrlFromMeta(meta, s);
    if (applyUrl) links.push({ label: "Apply", url: applyUrl });
    if (meta?.interview_url) links.push({ label: "Interview", url: meta.interview_url });
    if (meta?.gmail_url) links.push({ label: "Gmail", url: meta.gmail_url });
    links.push(
      { label: "Resume", url: `${appBase}&doc=resume` },
      { label: "Cover", url: `${appBase}&doc=cover` },
      { label: "JD", url: `${appBase}&doc=jd` },
      { label: "Prep", url: `${appBase}#interview-prep` },
      { label: "Settings", url: appBase }
    );
    return links;
  }

  function isLikelyInvalidApplyUrl(url) {
    const raw = String(url || "").trim();
    if (!raw) return false;
    if (/\.(png|jpe?g|gif|webp|svg|ico)(\?|#|$)/i.test(raw)) return true;
    if (/ashbyhq\.com\/api\/images\//i.test(raw)) return true;
    return false;
  }

  function applyUrlFromMeta(meta, slug) {
    const direct = String(meta?.apply_url || "").trim();
    if (direct && !isLikelyInvalidApplyUrl(direct)) return direct;
    for (const link of meta?.links || []) {
      if (String(link?.label || "").toLowerCase() === "apply" && link?.url) {
        const candidate = String(link.url).trim();
        if (candidate && !isLikelyInvalidApplyUrl(candidate)) return candidate;
      }
    }
    return "";
  }

  function isLinkedInApply(url) {
    return Boolean(url && /linkedin\.com/i.test(url));
  }

  function isFreelancerApp(meta, slug) {
    const method = String(meta?.apply_method || "").toLowerCase();
    if (method === "freelancer") return true;
    return String(slug || meta?.slug || "").startsWith("freelancer_");
  }

  function isIndeedApp(meta, slug) {
    const method = String(meta?.apply_method || "").toLowerCase();
    if (method === "indeed") return true;
    if (String(slug || meta?.slug || "").startsWith("indeed_")) return true;
    const url = String(applyUrlFromMeta(meta, slug) || "").toLowerCase();
    return url.includes("indeed.com/viewjob") || url.includes("cts.indeed.com");
  }

  function isCraigslistApp(meta, slug) {
    const method = String(meta?.apply_method || "").toLowerCase();
    if (method === "craigslist") return true;
    if (String(slug || meta?.slug || "").startsWith("craigslist_")) return true;
    const company = String(meta?.company || "").toLowerCase();
    const url = String(applyUrlFromMeta(meta, slug) || "").toLowerCase();
    return company.includes("craigslist") || url.includes("craigslist.org");
  }

  function isEmailApply(meta, slug) {
    const method = String(meta?.apply_method || "").toLowerCase();
    if (/email|reply|proposal|recruiter/.test(method)) return true;
    const url = applyUrlFromMeta(meta, slug);
    if (!url) return true;
    return /mailto:/i.test(url);
  }

  function resolveApplyAction(meta, slug, formApplyUrl) {
    const s = slug || meta?.slug || "";
    let applyUrl = String(formApplyUrl ?? applyUrlFromMeta(meta, s)).trim();
    if (isLikelyInvalidApplyUrl(applyUrl)) applyUrl = "";
    const ctx = { ...(meta || {}), apply_url: applyUrl, slug: s };

    if (isFreelancerApp(ctx, s)) {
      if (!applyUrl) {
        return { type: "none", hint: "Add a Freelancer posting URL in settings to apply." };
      }
      return { type: "link", label: "Bid on Freelancer", url: applyUrl, external: true };
    }

    if (isCraigslistApp(ctx, s)) {
      if (applyUrl) {
        return { type: "link", label: "Open Craigslist posting", url: applyUrl, external: true };
      }
      return {
        type: "link",
        label: "View Craigslist reply",
        url: `app.html?slug=${encodeURIComponent(s)}&doc=reply`,
      };
    }

    if (isIndeedApp(ctx, s)) {
      if (!applyUrl) {
        return { type: "none", hint: "Add an Indeed job URL in settings to apply." };
      }
      return { type: "link", label: "Apply on Indeed", url: applyUrl, external: true };
    }

    if (applyUrl && !isEmailApply(ctx, s)) {
      return {
        type: "link",
        label: isLinkedInApply(applyUrl) ? "Easy Apply on LinkedIn" : "Apply on job portal",
        url: applyUrl,
        external: true,
      };
    }

    return { type: "draft", label: "Apply via Gmail draft" };
  }

  function normalizeNavUrl(url) {
    const raw = String(url || "").trim();
    if (!raw) return "";
    if (/^(https?:|mailto:|tel:)/i.test(raw)) return raw;
    if (raw.startsWith("//")) return `https:${raw}`;
    if (raw.startsWith("app.html") || raw.startsWith("#") || raw.startsWith("/admin/")) return raw;
    return `https://${raw}`;
  }

  function isInternalNavUrl(url) {
    const u = String(url || "").trim();
    return u.startsWith("app.html") || u.startsWith("#") || u.startsWith("/admin/");
  }

  /** Open job portals — fall back to same-tab navigation when popups are blocked. */
  function openExternalUrl(url) {
    const target = normalizeNavUrl(url);
    if (!target) return false;
    if (isInternalNavUrl(target)) {
      window.location.href = target;
      return true;
    }
    let opened = false;
    try {
      const popup = window.open(target, "_blank", "noopener,noreferrer");
      if (popup) {
        try {
          opened = !popup.closed;
        } catch (_) {
          opened = true;
        }
      }
    } catch (_) {
      opened = false;
    }
    if (!opened) {
      window.location.assign(target);
    }
    return true;
  }

  function configureApplyLink(el, url, label) {
    if (!el) return;
    const target = normalizeNavUrl(url);
    if (!target) {
      el.hidden = true;
      return;
    }
    if (label) el.textContent = label;
    el.hidden = false;
    if (el.tagName === "A") {
      el.href = target;
      if (isInternalNavUrl(target)) {
        el.removeAttribute("target");
        el.removeAttribute("rel");
        el.onclick = null;
        return;
      }
      el.target = "_blank";
      el.rel = "noopener noreferrer";
      el.onclick = null;
      return;
    }
    bindNavLink(el, target);
  }

  function bindNavLink(el, url) {
    if (!el) return;
    const target = normalizeNavUrl(url);
    if (el.tagName === "A") {
      configureApplyLink(el, target);
      return;
    }
    el.onclick = (e) => {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
      e.preventDefault();
      openExternalUrl(target);
    };
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
        const external = !internal && href && !href.startsWith("#");
        const target = internal ? "" : ' target="_blank" rel="noopener"';
        const cls = external ? ' class="external-nav-link"' : "";
        return `<a href="${escapeAttr(normalizeNavUrl(href))}"${cls}${target}>${escapeHtml(l.label)}</a>`;
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

  const CURSOR_DEEPLINK_BASE = "cursor://anysphere.cursor-deeplink/prompt";
  const CURSOR_WEB_LINK_BASE = "https://cursor.com/link/prompt";

  function buildInterviewPrepPrompt(meta, mode) {
    const slug = String(meta?.slug || "").trim();
    const company = String(meta?.company || slug).trim();
    const client = String(meta?.client || "").trim();
    const role = String(meta?.role || "").trim();
    const status = String(meta?.status || meta?.settings?.status || "").trim();
    const notes = String(meta?.notes || meta?.settings?.notes || "").trim();
    const interviewUrl = String(meta?.interview_url || "").trim();

    const contextLines = [
      `Slug: ${slug}`,
      company ? `Company: ${company}` : "",
      client ? `Client: ${client}` : "",
      role ? `Role: ${role}` : "",
      status ? `Status: ${status}` : "",
      interviewUrl ? `Interview link: ${interviewUrl}` : "",
      notes ? `Notes: ${notes}` : "",
    ].filter(Boolean);

    const shared = [
      "Follow tools/interview/.prompt completely.",
      "",
      ...contextLines,
      "",
      "Read applications/" +
        slug +
        "/meta.json, jd.txt, resume.html and any existing interview/prep/* + interview/sessions/*_mock.md.",
      "After creating or updating prep files, run: python scripts/build_admin_data.py --slug " + slug,
      "Ensure interview prep shows at http://localhost:8080/admin/app.html?slug=" +
        slug +
        "#interview-prep",
    ].join("\n");

    if (mode === "mock") {
      return [
        `prep mock for ${company}`,
        "",
        shared,
        "",
        "Start with a pre-flight block (when, format, links table), then ask behavioral Q1 only.",
        "Wait for my answer before scoring. Interactive — one question at a time.",
      ].join("\n");
    }

    if (mode === "full") {
      return [
        `Full ${company} mock interview`,
        "",
        shared,
        "",
        "Run full mock per tools/interview/.prompt: behavioral → technical → design/scoping → one coding problem if applicable.",
        "Interactive — one question at a time; wait for answers before scoring.",
      ].join("\n");
    }

    return [
      `run interview prep for ${slug}`,
      "",
      shared,
      "",
      "Create or refresh interview/prep/" +
        slug +
        ".md, .html, interview/sessions/" +
        slug +
        "_mock.md, and coding drill if role warrants it.",
      "Show pre-flight, then start interactive mock with behavioral Q1.",
    ].join("\n");
  }

  function cursorPromptDeeplink(text) {
    const url = new URL(CURSOR_DEEPLINK_BASE);
    url.searchParams.set("text", text);
    return url.toString();
  }

  function cursorPromptWebLink(text) {
    const url = new URL(CURSOR_WEB_LINK_BASE);
    url.searchParams.set("text", text);
    return url.toString();
  }

  async function launchCursorInterviewPrep(meta, mode) {
    const prompt = buildInterviewPrepPrompt(meta, mode);
    if (prompt.length > 7800) {
      throw new Error("Prompt too long for Cursor deeplink — shorten notes in meta.json.");
    }
    let copied = false;
    try {
      await navigator.clipboard.writeText(prompt);
      copied = true;
    } catch (_) {
      /* clipboard optional */
    }
    const appLink = cursorPromptDeeplink(prompt);
    const webLink = cursorPromptWebLink(prompt);
    const anchor = document.createElement("a");
    anchor.href = appLink;
    anchor.style.display = "none";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    return { copied, appLink, webLink, prompt };
  }

  window.AdminCursor = {
    buildInterviewPrepPrompt,
    cursorPromptDeeplink,
    cursorPromptWebLink,
    launchCursorInterviewPrep,
  };

  window.AdminAuth = {
    requireAuth,
    getApiKey,
    clearAuth,
    isAuthed,
    loadAdminConfig,
    authRequired,
    isLocalAdminHost,
    preferLocalAppFiles,
    localSyncBase,
    isLocalSyncApi,
    resolveApiBase,
    resolveProtocolApiBase,
    resolveUnifiedApiBase,
    probeSameOriginApi,
    resolveSaveApiBase,
    isLocalSyncReachable,
    usesUnifiedGcsApi,
    formatSaveStatus,
    saveBlockedMessage,
    resolveApiKey,
    DEFAULT_LOCAL_PROTOCOL_API,
    fetchWithAuth,
    normalizeAdminLink,
    buildApplicationLinks,
    applyUrlFromMeta,
    isLikelyInvalidApplyUrl,
    isFreelancerApp,
    isIndeedApp,
    isCraigslistApp,
    resolveApplyAction,
    normalizeNavUrl,
    openExternalUrl,
    configureApplyLink,
    bindNavLink,
    linksHtml,
    downloadApplicationFile,
  };
})();
