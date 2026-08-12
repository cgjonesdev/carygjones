(function () {
  "use strict";

  const LS_KEY = "jobSearchAdmin";

  const state = {
    apiBase: "",
    apiKey: "",
    configApiBase: false,
    pagesBase: ".",
    repoBase: "",
    applications: [],
    protocolRun: null,
    running: false,
  };

  function loadSettings() {
    try {
      const saved = JSON.parse(localStorage.getItem(LS_KEY) || "{}");
      if (!state.configApiBase && saved.apiBase) {
        state.apiBase = saved.apiBase;
      }
      state.apiKey = saved.apiKey || "";
    } catch (_) {
      /* ignore */
    }
  }

  function saveSettings() {
    localStorage.setItem(
      LS_KEY,
      JSON.stringify({
        apiBase: state.configApiBase ? "" : state.apiBase,
        apiKey: state.apiKey,
      })
    );
  }

  async function loadConfig() {
    try {
      const cfg = await AdminAuth.loadAdminConfig();
      state.pagesBase = cfg.pagesBase || ".";
      state.repoBase = cfg.repoBase || "";
      state.passwordProtected = AdminAuth.authRequired(cfg);
      if (cfg.apiBase) {
        state.apiBase = String(cfg.apiBase).replace(/\/$/, "");
        state.configApiBase = true;
      } else {
        loadSettings();
        state.apiBase = AdminAuth.resolveProtocolApiBase(cfg);
      }
    } catch (_) {
      /* static fallback */
    }
  }

  function isLocalAdminHost() {
    const host = location.hostname;
    return host === "localhost" || host === "127.0.0.1";
  }

  function localSyncBase() {
    const port = Number(new URLSearchParams(location.search).get("syncPort") || "8765");
    return `http://127.0.0.1:${port}`;
  }

  function configureLocalSyncPanel() {
    const wrap = document.getElementById("local-sync-wrap");
    if (!wrap) return;
    wrap.hidden = !isLocalAdminHost();
  }

  const LOCAL_APP_SYNC_THROTTLE_MS = 90_000;
  let localAppSyncPromise = null;

  async function loadApplicationsFromLocalSync() {
    if (!isLocalAdminHost() || !(await AdminAuth.isLocalSyncReachable())) return null;
    try {
      const resp = await fetch(`${AdminAuth.localSyncBase()}/api/applications`);
      if (!resp.ok) return null;
      const data = await resp.json();
      return data.applications || null;
    } catch (_) {
      return null;
    }
  }

  async function syncLocalApplicationsFromGcs(force = false) {
    if (!isLocalAdminHost() || !(await AdminAuth.isLocalSyncReachable())) return false;
    const throttleKey = "jobSearchAdminAppSyncAt";
    const last = Number(sessionStorage.getItem(throttleKey) || 0);
    if (!force && Date.now() - last < LOCAL_APP_SYNC_THROTTLE_MS) {
      return false;
    }
    const resp = await fetch(`${AdminAuth.localSyncBase()}/api/sync`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ inbox: false, applications: true, rebuild_admin_data: true }),
    });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      throw new Error(data.error || data.detail || resp.statusText);
    }
    sessionStorage.setItem(throttleKey, String(Date.now()));
    return true;
  }

  async function resolveLocalApplications(staticApps) {
    if (!AdminAuth.isLocalAdminHost() || !(await AdminAuth.isLocalSyncReachable())) {
      return staticApps;
    }
    const liveApps = await loadApplicationsFromLocalSync();
    if (liveApps?.length) {
      return mergeApplicationsBySlug(liveApps, staticApps);
    }
    return staticApps;
  }

  function backgroundSyncLocalApplications() {
    if (localAppSyncPromise) return localAppSyncPromise;
    localAppSyncPromise = (async () => {
      if (!isLocalAdminHost() || !(await AdminAuth.isLocalSyncReachable())) return;
      const statusEl = document.getElementById("local-sync-status");
      try {
        const didSync = await syncLocalApplicationsFromGcs(false);
        if (!didSync) return;
        if (statusEl) setStatus(statusEl, "Refreshing from GCS…", "running");
        const staticApps = await loadStaticApplications().catch(() => [...state.applications]);
        const liveApps = await loadApplicationsFromLocalSync();
        if (liveApps?.length) {
          state.applications = mergeApplicationsBySlug(liveApps, staticApps);
          paintDashboard();
        }
        if (statusEl) setStatus(statusEl, "Applications synced from GCS.", "ok");
      } catch (err) {
        showDataSourceWarning(`Background GCS sync: ${err.message}`);
      } finally {
        localAppSyncPromise = null;
      }
    })();
    return localAppSyncPromise;
  }

  async function pullFromGcsLocal() {
    const statusEl = document.getElementById("local-sync-status");
    if (!isLocalAdminHost()) {
      setStatus(statusEl, "Local GCS pull only works on localhost.", "err");
      return;
    }
    setStatus(statusEl, "Pulling from GCS…", "running");
    try {
      const resp = await fetch(`${localSyncBase()}/api/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ inbox: true, applications: true, rebuild_admin_data: true }),
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) throw new Error(data.error || data.detail || resp.statusText);
      setStatus(statusEl, (data.sync_stdout || "Sync complete.") + " Reloading…", "ok");
      sessionStorage.setItem("jobSearchAdminAppSyncAt", String(Date.now()));
      await loadDashboardData();
    } catch (err) {
      const hint =
        err.message === "Failed to fetch"
          ? "Start ./scripts/serve_admin_local.sh (or run local_sync_server.py in another terminal)."
          : err.message;
      setStatus(statusEl, hint, "err");
    }
  }

  function configureSettingsPanel() {
    const panel = document.getElementById("api-settings-panel");
    const apiBaseField = document.getElementById("api-base-wrap");
    const hint = document.getElementById("api-settings-hint");
    const apiInput = document.getElementById("api-base");
    const keyInput = document.getElementById("api-key");

    apiInput.value = state.apiBase;
    keyInput.value = state.apiKey;

    if (state.configApiBase) {
      if (apiBaseField) apiBaseField.hidden = true;
      if (hint) {
        hint.textContent = `Protocol API: ${state.apiBase} (from deploy config)`;
      }
      panel.classList.add("panel-compact");
    } else if (isLocalAdminHost()) {
      if (hint) {
        hint.textContent =
          "Local dev: sign in (or Save password) to run protocols on Cloud Run. API URL is filled automatically unless you override it below.";
      }
      if (!apiInput.value && state.apiBase) {
        apiInput.value = state.apiBase;
      }
    } else if (!state.apiBase) {
      if (hint) {
        hint.textContent =
          "Read-only mode until ADMIN_API_BASE_URL is set in GitHub repo variables and the site is redeployed.";
      }
    }
    if (state.passwordProtected && document.getElementById("api-key-wrap")) {
      document.getElementById("api-key-wrap").hidden = true;
    }
  }

  function apiUrl(path) {
    const base = (state.apiBase || "").replace(/\/$/, "");
    return base ? `${base}${path}` : "";
  }

  async function apiFetch(path, options = {}, apiBaseOverride) {
    const base = (apiBaseOverride || state.apiBase || "").replace(/\/$/, "");
    const url = base ? `${base}${path}` : "";
    if (!url) {
      const hint = AdminAuth.isLocalAdminHost()
        ? "Fill in Protocol API URL under Connection (or restart ./scripts/serve_admin_local.sh)."
        : "Set GitHub variable ADMIN_API_BASE_URL and redeploy.";
      throw new Error(`Protocol API URL is not configured (${hint})`);
    }
    const headers = { ...(options.headers || {}) };
    const key = AdminAuth.resolveApiKey(state.configApiBase);
    if (key && !apiBaseOverride) headers["X-Admin-Key"] = key;
    if (options.body && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }
    const resp = await fetch(url, { ...options, headers });
    const text = await resp.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch (_) {
      data = { raw: text };
    }
    if (!resp.ok) {
      throw new Error(data?.detail || data?.error || resp.statusText || "Request failed");
    }
    return data;
  }

  function setStatus(el, message, kind) {
    el.textContent = message || "";
    el.className = "status-bar" + (kind ? ` ${kind}` : "");
  }

  function linkHtml(links) {
    return AdminAuth.linksHtml(links);
  }

  function appLinks(row) {
    return AdminAuth.buildApplicationLinks(row, row.slug);
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

  function badge(status) {
    const raw = String(status ?? "unknown")
      .trim()
      .toLowerCase();
    const label = STATUS_LABELS[raw] || status || "—";
    const cls = raw.replace(/[^a-z0-9_]/g, "").replace(/_/g, "") || "ready";
    return `<span class="badge badge-${escapeAttr(cls)}">${escapeHtml(label)}</span>`;
  }

  const STATUS_LABELS = {
    ready: "Ready",
    application_in_progress: "Application in progress",
    applied: "Applied",
    waiting_on_response: "Waiting on response",
    needs_rate_confirmation: "Needs rate confirmation",
    interview: "Interview scheduled",
    screening_interview_complete: "Screening interview complete",
    in_technical_interviews: "In technical interviews",
    technical_interviews_complete: "Technical interviews complete",
    in_final_interviews: "In final interviews",
    final_interviews_complete: "Final interviews complete",
    offer: "Offer",
    rejected: "Rejected",
    skipped: "Skipped",
  };

  const INTEREST_SCORE = 80;
  const FREELANCER_INTEREST_SCORE = 70;
  const CRAIGSLIST_INTEREST_SCORE = 60;
  const INDEED_INTEREST_SCORE = 70;
  const BACKLOG_SCORE = 60;
  const DONE_STATUSES = new Set(["applied", "skipped", "rejected", "offer"]);
  const WAITING_STATUSES = new Set(["waiting_on_response"]);
  const INTERVIEW_STATUSES = new Set([
    "interview",
    "screening_interview_complete",
    "in_technical_interviews",
    "technical_interviews_complete",
    "in_final_interviews",
    "final_interviews_complete",
  ]);

  function applicationStatus(app) {
    return String(app?.status ?? "ready")
      .trim()
      .toLowerCase();
  }

  function isDoneApplication(app) {
    return DONE_STATUSES.has(applicationStatus(app));
  }

  function mergeApplicationRecord(apiApp, staticApp) {
    if (!apiApp) return staticApp;
    if (!staticApp) return apiApp;

    const apiStatus = applicationStatus(apiApp);
    const staticStatus = applicationStatus(staticApp);
    const merged = { ...staticApp, ...apiApp };

    if (DONE_STATUSES.has(staticStatus)) {
      merged.status = staticApp.status;
      merged.updated = staticApp.updated || merged.updated;
    } else if (DONE_STATUSES.has(apiStatus)) {
      merged.status = apiApp.status;
      merged.updated = apiApp.updated || merged.updated;
    } else     if ((staticApp.updated || "") > (apiApp.updated || "")) {
      merged.status = staticApp.status ?? merged.status;
      merged.updated = staticApp.updated;
    }

    if (!merged.interview_prep?.length && staticApp.interview_prep?.length) {
      merged.interview_prep = staticApp.interview_prep;
    }
    if (!merged.interview_url && staticApp.interview_url) {
      merged.interview_url = staticApp.interview_url;
    }
    if (!merged.gmail_url && staticApp.gmail_url) {
      merged.gmail_url = staticApp.gmail_url;
    }
    if (!merged.links?.length && staticApp.links?.length) {
      merged.links = staticApp.links;
    }

    return merged;
  }

  const QUADRANTS = [
    {
      id: "do",
      title: "Do first",
      subtitle: "Urgent · Important",
      hint: "Interviews and blockers — handle before anything else.",
    },
    {
      id: "schedule",
      title: "Schedule",
      subtitle: "Important · Not urgent",
      hint: "Block time for drafts, email replies, and portal applies.",
    },
    {
      id: "quick",
      title: "Quick wins",
      subtitle: "Urgent · Less effort",
      hint: "One-click applies, Freelancer bids, Craigslist replies, Indeed jobs, and fast sends.",
    },
    {
      id: "later",
      title: "Later",
      subtitle: "Important · Someday",
      hint: "Worth keeping on radar — review when the top rows are clear.",
    },
  ];

  const QUADRANT_PREVIEW = 6;

  function settingsUrl(slug) {
    return `app.html?slug=${encodeURIComponent(slug)}`;
  }

  function isLinkedInApply(url) {
    return Boolean(url && /linkedin\.com/i.test(url));
  }

  function isFreelancerApp(app) {
    const method = String(app.apply_method || "").toLowerCase();
    if (method === "freelancer") return true;
    return String(app.slug || "").startsWith("freelancer_");
  }

  function isCraigslistApp(app) {
    const method = String(app.apply_method || "").toLowerCase();
    if (method === "craigslist") return true;
    if (String(app.slug || "").startsWith("craigslist_")) return true;
    const company = String(app.company || "").toLowerCase();
    const url = String(app.apply_url || "").toLowerCase();
    return company.includes("craigslist") || url.includes("craigslist.org");
  }

  function isIndeedApp(app) {
    const method = String(app.apply_method || "").toLowerCase();
    if (method === "indeed") return true;
    if (String(app.slug || "").startsWith("indeed_")) return true;
    const url = String(app.apply_url || "").toLowerCase();
    return url.includes("indeed.com/viewjob") || url.includes("cts.indeed.com");
  }

  function minActionScore(app) {
    if (isFreelancerApp(app)) return FREELANCER_INTEREST_SCORE;
    if (isCraigslistApp(app)) return CRAIGSLIST_INTEREST_SCORE;
    if (isIndeedApp(app)) return INDEED_INTEREST_SCORE;
    return INTEREST_SCORE;
  }

  function isEmailApply(app) {
    const method = String(app.apply_method || "").toLowerCase();
    if (/email|reply|proposal|recruiter/.test(method)) return true;
    if (!app.apply_url) return true;
    if (/mailto:/i.test(app.apply_url)) return true;
    return false;
  }

  function classifyApplicationAction(app) {
    const status = applicationStatus(app);
    if (DONE_STATUSES.has(status) || WAITING_STATUSES.has(status)) return null;

    const score = Number(app.match_score ?? -1);
    const appSettings = settingsUrl(app.slug);
    const subtitle = [app.company || app.slug, app.role, score >= 0 ? `score ${score}` : ""]
      .filter(Boolean)
      .join(" · ");

    if (INTERVIEW_STATUSES.has(status)) {
      const action = {
        priority: 1,
        quadrant: "do",
        kind: "interview",
        title: STATUS_LABELS[status] || "Interview prep",
        detail: subtitle,
        primary: app.interview_url
          ? { label: "Interview link", url: app.interview_url, external: true }
          : { label: "Open application", url: appSettings },
        secondary:
          (app.interview_prep && app.interview_prep.length) || app.interview_url
            ? { label: "Prep guide", url: `${appSettings}#interview-prep` }
            : { label: "Settings", url: appSettings },
      };
      if (AdminAuth.isLocalAdminHost()) {
        action.cursor = {
          label: "Mock in Cursor",
          mode: "mock",
          slug: app.slug,
          company: app.company,
          role: app.role,
          client: app.client,
          status: app.status,
          notes: app.notes,
          interview_url: app.interview_url,
        };
      }
      return action;
    }

    if (status === "needs_rate_confirmation") {
      return {
        priority: 2,
        quadrant: "schedule",
        kind: "rate",
        title: "Confirm rate",
        detail: subtitle,
        primary: { label: "Open settings", url: appSettings },
        secondary: app.gmail_url
          ? { label: "Gmail thread", url: app.gmail_url, external: true }
          : null,
      };
    }

    const minScore = minActionScore(app);
    if (score < minScore) return null;

    if (isFreelancerApp(app)) {
      return {
        priority: 2,
        quadrant: "quick",
        kind: "freelancer-bid",
        title: "Submit Freelancer bid",
        detail: subtitle,
        primary: app.apply_url
          ? { label: "Bid on Freelancer", url: app.apply_url, external: true }
          : { label: "Open application", url: appSettings },
        secondary: { label: "Copy bid text", url: `${appSettings}&doc=bid` },
      };
    }

    if (isCraigslistApp(app)) {
      return {
        priority: 2,
        quadrant: "quick",
        kind: "craigslist-reply",
        title: "Send Craigslist reply",
        detail: subtitle,
        primary: app.apply_url
          ? { label: "Open posting", url: app.apply_url, external: true }
          : { label: "Open application", url: appSettings },
        secondary: { label: "Copy reply", url: `${appSettings}&doc=reply` },
      };
    }

    if (isIndeedApp(app)) {
      return {
        priority: 2,
        quadrant: "quick",
        kind: "indeed-apply",
        title: "Apply on Indeed",
        detail: subtitle,
        primary: app.apply_url
          ? { label: "Indeed job", url: app.apply_url, external: true }
          : { label: "Open application", url: appSettings },
        secondary: { label: "JD", url: `${appSettings}&doc=jd` },
      };
    }

    if (app.gmail_draft_id) {
      return {
        priority: 2,
        quadrant: "schedule",
        kind: "draft",
        title: "Review Gmail draft & send",
        detail: subtitle,
        primary: {
          label: "Gmail drafts",
          url: "https://mail.google.com/mail/u/0/#drafts",
          external: true,
        },
        secondary: { label: "Settings", url: appSettings },
      };
    }

    if (app.apply_url && !isEmailApply(app)) {
      const linkedin = isLinkedInApply(app.apply_url);
      const title = linkedin ? "Easy Apply on LinkedIn" : "Apply on job portal";
      return {
        priority: linkedin ? 3 : 3,
        quadrant: linkedin ? "quick" : "schedule",
        kind: "apply",
        title,
        detail: subtitle,
        primary: { label: "Apply", url: app.apply_url, external: true },
        secondary: { label: "Cover letter", url: `${appSettings}&doc=cover` },
      };
    }

    return {
      priority: 4,
      quadrant: "schedule",
      kind: "email",
      title: "Create Gmail draft",
      detail: `${subtitle}${subtitle ? " · " : ""}email apply`,
      primary: { label: "Settings & draft", url: appSettings },
      secondary: app.gmail_url
        ? { label: "Recruiter email", url: app.gmail_url, external: true }
        : null,
    };
  }

  function collectBacklogItems(applications) {
    const items = [];
    for (const app of sortApplicationsByScore(applications || [])) {
      const status = applicationStatus(app);
      if (DONE_STATUSES.has(status) || INTERVIEW_STATUSES.has(status) || WAITING_STATUSES.has(status)) continue;
      const score = Number(app.match_score ?? -1);
      const minScore = minActionScore(app);
      if (score < BACKLOG_SCORE || score >= minScore) continue;
      const subtitle = [app.company || app.slug, app.role, `score ${score}`]
        .filter(Boolean)
        .join(" · ");
      const backlogTitle = isFreelancerApp(app)
        ? "Review Freelancer fit"
        : isCraigslistApp(app)
          ? "Review Craigslist fit"
          : isIndeedApp(app)
            ? "Review Indeed fit"
            : "Review fit";
      items.push({
        quadrant: "later",
        kind: isFreelancerApp(app)
          ? "freelancer-backlog"
          : isCraigslistApp(app)
            ? "craigslist-backlog"
            : isIndeedApp(app)
              ? "indeed-backlog"
              : "backlog",
        title: backlogTitle,
        detail: subtitle,
        slug: app.slug,
        score,
        primary: { label: "Open", url: settingsUrl(app.slug) },
        secondary: { label: "Settings", url: settingsUrl(app.slug) },
      });
    }
    return items;
  }

  function collectProtocolActionables(run) {
    if (!run?.phases) return [];
    const items = [];
    for (const phase of run.phases) {
      if (phase.error) {
        items.push({
          priority: 0,
          quadrant: "do",
          kind: "protocol-error",
          title: `Fix ${phase.phase || "protocol"} error`,
          detail: phase.error,
          primary: { label: "Open admin", action: "open-admin" },
        });
      }
      for (const err of phase.errors || []) {
        items.push({
          priority: 0,
          quadrant: "do",
          kind: "protocol-error",
          title: "Protocol error",
          detail: err.error || err.message || JSON.stringify(err),
          primary: { label: "Open admin", action: "open-admin" },
        });
      }
    }
    return items;
  }

  function collectActionables(applications, protocolRun) {
    const items = collectProtocolActionables(protocolRun);
    for (const app of sortApplicationsByScore(applications || [])) {
      const action = classifyApplicationAction(app);
      if (action) {
        items.push({ ...action, slug: app.slug, score: app.match_score });
      }
    }
    for (const item of collectBacklogItems(applications)) {
      items.push(item);
    }
    items.sort((a, b) => {
      if (a.priority !== b.priority) return a.priority - b.priority;
      return Number(b.score ?? -1) - Number(a.score ?? -1);
    });
    return items;
  }

  function renderTodoCard(item) {
    const secondary = item.secondary
      ? `<a class="btn btn-sm" href="${escapeAttr(item.secondary.url)}"${
          item.secondary.external ? ' target="_blank" rel="noopener"' : ""
        }>${escapeHtml(item.secondary.label)}</a>`
      : "";
    const primary =
      item.primary?.action === "open-admin"
        ? `<button class="btn btn-primary btn-sm" type="button" data-open-admin>${escapeHtml(item.primary.label)}</button>`
        : `<a class="btn btn-primary btn-sm" href="${escapeAttr(item.primary.url)}"${
            item.primary.external ? ' target="_blank" rel="noopener"' : ""
          }>${escapeHtml(item.primary.label)}</a>`;
    return `<li class="todo-card action-${escapeAttr(item.kind)}">
      <div class="todo-card-copy">
        <strong>${escapeHtml(item.title)}</strong>
        <span class="todo-card-detail">${escapeHtml(item.detail || item.slug || "")}</span>
      </div>
      <div class="todo-card-actions">${primary}${secondary}</div>
    </li>`;
  }

  function renderQuadrantBody(list, quadrantId) {
    if (!list.length) return '<p class="quadrant-empty">Clear</p>';
    const preview = list.slice(0, QUADRANT_PREVIEW);
    const rest = list.slice(QUADRANT_PREVIEW);
    let html = `<ul class="todo-list">${preview.map(renderTodoCard).join("")}</ul>`;
    if (rest.length) {
      html += `<button type="button" class="btn btn-sm quadrant-show-more" data-show-quadrant="${escapeAttr(quadrantId)}">Show ${rest.length} more</button>`;
      html += `<ul class="todo-list quadrant-more" data-quadrant="${escapeAttr(quadrantId)}" hidden>${rest.map(renderTodoCard).join("")}</ul>`;
    }
    return html;
  }

  function renderActionable() {
    const board = document.getElementById("actionable-board");
    const summary = document.getElementById("actionable-summary");
    if (!board) return;

    const items = collectActionables(state.applications, state.protocolRun);
    const byQuadrant = Object.fromEntries(QUADRANTS.map((q) => [q.id, []]));
    for (const item of items) {
      const q = item.quadrant || "schedule";
      if (byQuadrant[q]) byQuadrant[q].push(item);
    }

    const total = items.length;
    const urgent = byQuadrant.do.length + byQuadrant.quick.length;
    if (summary) {
      summary.textContent = total
        ? `${urgent} urgent · ${total} total in queue`
        : "Queue clear";
    }

    if (!total) {
      board.innerHTML =
        '<p class="empty">Nothing in the queue. Open <strong>Admin</strong> to run protocols or pull from GCS.</p>';
      return;
    }

    board.innerHTML = QUADRANTS.map((q) => {
      const list = byQuadrant[q.id];
      return `<div class="quadrant quadrant-${q.id}">
        <header class="quadrant-header">
          <div>
            <h3>${escapeHtml(q.title)}</h3>
            <span class="quadrant-sub">${escapeHtml(q.subtitle)}</span>
          </div>
          <span class="quadrant-count">${list.length}</span>
        </header>
        <p class="quadrant-hint">${escapeHtml(q.hint)}</p>
        ${renderQuadrantBody(list, q.id)}
      </div>`;
    }).join("");
  }

  function sortApplicationsByScore(rows) {
    return [...rows].sort((a, b) => {
      const scoreA = a.match_score ?? a.score;
      const scoreB = b.match_score ?? b.score;
      const numA = scoreA == null || scoreA === "" ? -1 : Number(scoreA);
      const numB = scoreB == null || scoreB === "" ? -1 : Number(scoreB);
      if (numB !== numA) return numB - numA;
      const updatedCmp = String(b.updated || "").localeCompare(String(a.updated || ""));
      if (updatedCmp !== 0) return updatedCmp;
      return String(a.slug || "").localeCompare(String(b.slug || ""));
    });
  }

  function filterApplications(query, limit = 12) {
    const q = query.trim().toLowerCase();
    if (!q || q.length < 2) return [];
    const terms = q.split(/\s+/).filter(Boolean);
    const matches = [];
    for (const app of state.applications || []) {
      const hay = [
        app.slug,
        app.company,
        app.role,
        app.location,
        app.status,
        app.apply_method,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      if (terms.every((term) => hay.includes(term))) {
        matches.push(app);
      }
    }
    return sortApplicationsByScore(matches.filter((app) => !isDoneApplication(app))).slice(0, limit);
  }

  function renderApplicationSearch() {
    const input = document.getElementById("app-search");
    const container = document.getElementById("app-search-results");
    if (!input || !container) return;

    const query = input.value.trim();
    if (query.length < 2) {
      container.hidden = true;
      container.innerHTML = "";
      return;
    }

    const rows = filterApplications(query);
    if (!rows.length) {
      container.hidden = false;
      container.innerHTML = `<div class="search-results-empty">
        <span class="search-results-empty-icon" aria-hidden="true">⌕</span>
        <p>No matches for <strong>${escapeHtml(query)}</strong></p>
        <span class="search-results-empty-hint">Try company name, role title, or status like “interview”</span>
      </div>`;
      return;
    }

    container.hidden = false;
    container.innerHTML = `<div class="search-results-header">${rows.length} match${rows.length === 1 ? "" : "es"}</div>
      <ul class="search-results-list">${rows
      .map((app) => {
        const subtitle = [app.role, app.location, app.match_score != null ? `score ${app.match_score}` : ""]
          .filter(Boolean)
          .join(" · ");
        const settingsUrl = `app.html?slug=${encodeURIComponent(app.slug)}`;
        return `<li class="search-result-item">
          <a class="search-result-main" href="${escapeAttr(settingsUrl)}">
            <span class="search-result-title">${escapeHtml(app.company || app.slug)}</span>
            <span class="search-result-detail">${escapeHtml(subtitle || app.slug)}</span>
            <span class="search-result-slug">${escapeHtml(app.slug)}</span>
          </a>
          <div class="search-result-aside">${badge(app.status)}<span class="search-result-arrow" aria-hidden="true">→</span></div>
        </li>`;
      })
      .join("")}</ul>`;
  }

  function bindApplicationSearch() {
    const input = document.getElementById("app-search");
    if (!input || input.dataset.bound) return;
    input.dataset.bound = "1";
    const field = input.closest(".search-field");
    let timer = null;
    const syncFieldState = () => {
      field?.classList.toggle("has-value", input.value.length > 0);
    };
    input.addEventListener("input", () => {
      syncFieldState();
      window.clearTimeout(timer);
      timer = window.setTimeout(renderApplicationSearch, 120);
    });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        input.value = "";
        syncFieldState();
        renderApplicationSearch();
      }
    });
    syncFieldState();
  }

  function renderApplicationsTable(tbody, rows) {
    const sorted = sortApplicationsByScore(rows);
    if (!sorted.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty">No applications found.</td></tr>`;
      return;
    }
    tbody.innerHTML = sorted
      .map(
        (r) => `<tr>
          <td><a href="app.html?slug=${escapeAttr(r.slug)}">${escapeHtml(r.slug)}</a></td>
          <td>${escapeHtml(r.company || "—")}</td>
          <td>${escapeHtml(r.role || "—")}</td>
          <td>${r.match_score ?? "—"}</td>
          <td>${badge(r.status)}</td>
          <td>${escapeHtml(r.updated || "—")}</td>
          <td class="links-cell">${linkHtml(appLinks(r))}</td>
        </tr>`
      )
      .join("");
  }

  function phaseLinks(row) {
    return AdminAuth.buildApplicationLinks(row, row.slug);
  }

  function renderProtocolOutputs(container, run) {
    if (!run || !run.phases) {
      container.innerHTML = `<p class="empty">No protocol run data yet.</p>`;
      return;
    }

    const parts = [];
    for (const phase of run.phases) {
      const name = phase.phase || "unknown";
      parts.push(`<h3 style="margin:1rem 0 0.5rem;font-size:1rem;">${escapeHtml(name)}</h3>`);

        if (phase.skipped === true) {
        parts.push(`<p class="hint">${escapeHtml(phase.reason || "Skipped")}</p>`);
        continue;
      }
      if (phase.error) {
        parts.push(`<p class="status-bar err">${escapeHtml(phase.error)}</p>`);
        continue;
      }

      const generated = phase.generated;
      if (Array.isArray(generated) && generated.length) {
        parts.push(renderOutputTable(generated, phaseLinks));
      } else if (generated && typeof generated === "object" && !Array.isArray(generated)) {
        parts.push(renderOutputTable([generated], phaseLinks));
      }

      if (Array.isArray(phase.skipped) && phase.skipped.length) {
        const skippedTable = renderOutputTable(phase.skipped, (r) => {
          const links = phaseLinks(r);
          if (r.gmail_url) links.push({ label: "Gmail", url: r.gmail_url });
          return links;
        });
        parts.push(
          `<details class="protocol-collapsible">
            <summary>Skipped (${phase.skipped.length})</summary>
            ${skippedTable}
          </details>`
        );
      }

      if (Array.isArray(phase.errors) && phase.errors.length) {
        const errorsTable = renderOutputTable(
          phase.errors.map((e) => ({
            slug: e.slug || "—",
            company: "—",
            score: "—",
            reason: e.error || e.message || JSON.stringify(e),
          })),
          () => []
        );
        parts.push(
          `<details class="protocol-collapsible">
            <summary>Errors (${phase.errors.length})</summary>
            ${errorsTable}
          </details>`
        );
      }

      if (phase.jobs && phase.jobs.length) {
        parts.push(`<p class="hint">${phase.jobs_found || phase.jobs.length} LinkedIn jobs</p>`);
        parts.push(
          renderOutputTable(
            phase.jobs.map((j) => ({
              slug: j.jobId || "—",
              company: j.company || j.companyName || "—",
              score: "—",
              reason: [j.title, j.location].filter(Boolean).join(" · "),
              apply_url: j.apply_url || j.jobUrl,
            })),
            (r) => {
              const links = [];
              if (r.apply_url) links.push({ label: "LinkedIn job", url: r.apply_url });
              return links;
            }
          )
        );
      }

      if (phase.applied_sync && Array.isArray(phase.applied_sync.meta_updated) && phase.applied_sync.meta_updated.length) {
        parts.push(`<p class="hint" style="margin-top:0.5rem">Marked applied from LinkedIn</p>`);
        parts.push(
          renderOutputTable(
            phase.applied_sync.meta_updated.map((row) => ({
              slug: row.slug,
              company: row.company || "—",
              score: "—",
              reason: `job ${row.job_id || "—"} → applied`,
            })),
            (r) => (r.slug ? AdminAuth.buildApplicationLinks({ slug: r.slug }, r.slug) : [])
          )
        );
      } else if (phase.applied_sync?.applied_list_error) {
        parts.push(
          `<p class="hint" style="margin-top:0.5rem">Applied search sync (legacy run): ${escapeHtml(phase.applied_sync.applied_list_error)}. Re-run LinkedIn search to refresh.</p>`
        );
      } else if (
        phase.applied_sync &&
        (phase.applied_sync.tracked_jobs_checked || phase.applied_sync.applied_jobs_fetched)
      ) {
        const bits = [];
        if (phase.applied_sync.tracked_jobs_checked) {
          bits.push(
            `Checked ${phase.applied_sync.tracked_jobs_checked} tracked job(s); ${phase.applied_sync.tracked_jobs_applied || 0} marked applied on LinkedIn`
          );
        }
        if (phase.applied_sync.applied_jobs_fetched) {
          bits.push(`${phase.applied_sync.applied_jobs_fetched} from custom search URL`);
        }
        parts.push(`<p class="hint" style="margin-top:0.5rem">${escapeHtml(bits.join(" · "))}</p>`);
      }
      if (phase.applied_sync?.tracked_errors?.length) {
        parts.push(
          `<p class="hint" style="margin-top:0.35rem">Tracked-job checks: ${escapeHtml(phase.applied_sync.tracked_errors.join("; "))}</p>`
        );
      }

      if (phase.exit_code !== undefined && phase.exit_code !== 0) {
        parts.push(`<p class="status-bar err">Gmail scan exit code ${phase.exit_code}</p>`);
      }

      if (phase.jobs_found !== undefined) {
        const cats = Array.isArray(phase.categories) ? phase.categories.join(", ") : "";
        const searchUrl = phase.search_url ? ` · ${phase.search_url}` : "";
        const label =
          phase.phase === "craigslist_scan"
            ? "Craigslist listings scanned"
            : phase.phase === "indeed_scan"
              ? "Indeed jobs scanned"
              : "Freelancer listings scanned";
        const extra =
          phase.phase === "indeed_scan"
            ? ` · ${phase.search_query || "—"} in ${phase.search_location || "—"}`
            : searchUrl
              ? ` · ${escapeHtml(searchUrl)}`
              : "";
        parts.push(
          `<p class="hint">${phase.jobs_found} ${label}${cats ? ` (${escapeHtml(cats)})` : ""}${extra} · threshold ${phase.min_score ?? "—"}%</p>`
        );
      }
      if (Array.isArray(phase.fetch_errors) && phase.fetch_errors.length) {
        parts.push(
          `<p class="status-bar err">${escapeHtml(phase.fetch_errors.join("; "))}</p>`
        );
      }
    }

    if (run.started_at) {
      parts.unshift(`<p class="hint">Run: ${escapeHtml(run.started_at)} · mode ${escapeHtml(run.mode || "—")}</p>`);
    }
    container.innerHTML = parts.join("");
  }

  function renderOutputTable(rows, linkFn) {
    return `<div class="table-wrap"><table>
      <thead><tr>
        <th>Slug</th><th>Company</th><th>Score</th><th>Reason</th><th>Links</th>
      </tr></thead>
      <tbody>${rows
        .map((r) => {
          const links = linkFn(r);
          return `<tr>
            <td>${escapeHtml(r.slug || "—")}</td>
            <td>${escapeHtml(r.company || "—")}</td>
            <td>${r.score ?? r.match_score ?? "—"}</td>
            <td>${escapeHtml(r.reason || "—")}</td>
            <td class="links-cell">${linkHtml(links)}</td>
          </tr>`;
        })
        .join("")}</tbody></table></div>`;
  }

  function mergeApplicationsBySlug(primary, secondary) {
    const bySlug = new Map();
    for (const app of secondary || []) {
      if (app?.slug) bySlug.set(app.slug, app);
    }
    for (const app of primary || []) {
      if (!app?.slug) continue;
      const existing = bySlug.get(app.slug);
      bySlug.set(app.slug, existing ? mergeApplicationRecord(app, existing) : app);
    }
    return Array.from(bySlug.values());
  }

  async function loadStaticApplications() {
    const resp = await fetch("data/applications.json");
    if (!resp.ok) return [];
    const data = await resp.json();
    return data.applications || [];
  }

  async function loadStaticProtocolRun() {
    const resp = await fetch("data/latest_protocol_run.json");
    if (!resp.ok) return null;
    return resp.json();
  }

  function showDataSourceWarning(message) {
    const runStatus = document.getElementById("run-status");
    if (runStatus && message) {
      setStatus(runStatus, message, "warn");
    }
  }

  function shouldFetchLiveApi() {
    if (!state.apiBase) return false;
    if (AdminAuth.isLocalAdminHost() && !state.apiKey) return false;
    return true;
  }

  function paintDashboard() {
    renderActionable();
    updateApplicationsCount(state.applications.length);
    renderApplicationSearch();
    renderApplicationsTableIfVisible();
  }

  function paintProtocolOutput() {
    const container = document.getElementById("protocol-output");
    if (container) renderProtocolOutputs(container, state.protocolRun);
  }

  function renderApplicationsTableIfVisible() {
    const panel = document.getElementById("applications-panel");
    const tbody = document.getElementById("apps-table-body");
    if (!tbody) return;
    if (panel && !panel.open) return;
    renderApplicationsTable(tbody, state.applications);
  }

  async function hydrateFromStatic() {
    const [staticApps, run] = await Promise.all([
      loadStaticApplications().catch(() => []),
      loadStaticProtocolRun().catch(() => null),
    ]);
    const apps = await resolveLocalApplications(staticApps);
    if (apps.length) {
      state.applications = apps;
    } else if (!state.applications.length) {
      throw new Error("Missing data/applications.json — run scripts/build_admin_data.py");
    }
    if (run) state.protocolRun = run;
    paintDashboard();
    paintProtocolOutput();
    void backgroundSyncLocalApplications();
  }

  async function refreshFromLiveApi() {
    if (!shouldFetchLiveApi()) return;

    const staticApps = [...state.applications];
    const staticRun = state.protocolRun;

    await Promise.all([
      (async () => {
        try {
          const data = await apiFetch("/api/applications");
          state.applications = mergeApplicationsBySlug(data.applications || [], staticApps);
        } catch (err) {
          if (staticApps.length) {
            state.applications = staticApps;
            const authHint =
              String(err.message || "").includes("401") ||
              String(err.message || "").toLowerCase().includes("invalid or missing")
                ? " Cloud Run admin-api-key must match your admin login password."
                : "";
            showDataSourceWarning(
              `Using deploy snapshot (${staticApps.length} apps). Live API: ${err.message}.${authHint}`
            );
          }
        }
      })(),
      (async () => {
        try {
          const run = await fetchProtocolRun();
          if (run) state.protocolRun = run;
        } catch (err) {
          if (staticRun) {
            state.protocolRun = staticRun;
            showDataSourceWarning(`Using cached protocol output. Live API: ${err.message}`);
          }
        }
      })(),
    ]);

    paintDashboard();
    paintProtocolOutput();
  }

  async function loadApplications() {
    const tbody = document.getElementById("apps-table-body");
    try {
      await hydrateFromStatic();
      await refreshFromLiveApi();
      if (tbody) renderApplicationsTable(tbody, state.applications);
    } catch (err) {
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="7" class="empty">${escapeHtml(err.message)}</td></tr>`;
      }
      renderActionable();
    }
  }

  async function loadProtocolRun() {
    const container = document.getElementById("protocol-output");
    let staticRun = null;
    try {
      staticRun = await loadStaticProtocolRun();
    } catch (_) {
      /* ignore */
    }

    try {
      if (shouldFetchLiveApi()) {
        try {
          state.protocolRun = await apiFetch("/api/protocols/latest");
        } catch (err) {
          if (staticRun) {
            state.protocolRun = staticRun;
            showDataSourceWarning(`Using cached protocol output. Live API: ${err.message}`);
          } else {
            throw err;
          }
        }
      } else if (staticRun) {
        state.protocolRun = staticRun;
      }
      if (container) renderProtocolOutputs(container, state.protocolRun);
      renderActionable();
    } catch (err) {
      if (container) container.innerHTML = `<p class="empty">${escapeHtml(err.message)}</p>`;
      renderActionable();
    }
  }

  async function loadDashboardData() {
    try {
      await hydrateFromStatic();
    } catch (err) {
      const board = document.getElementById("actionable-board");
      if (board) board.innerHTML = `<p class="empty">${escapeHtml(err.message)}</p>`;
      throw err;
    }
    void refreshFromLiveApi();
  }

  async function fetchProtocolRun() {
    if (AdminAuth.isLocalAdminHost() && (await AdminAuth.isLocalSyncReachable())) {
      try {
        const resp = await fetch(`${localSyncBase()}/api/protocols/latest`);
        if (resp.ok) return resp.json();
      } catch (_) {
        /* fall through to Cloud Run / static */
      }
    }
    if (shouldFetchLiveApi()) {
      return apiFetch("/api/protocols/latest");
    }
    return loadStaticProtocolRun();
  }

  async function localSyncSupportsProtocol(protocolKey) {
    try {
      const resp = await fetch(`${localSyncBase()}/api/health`);
      if (!resp.ok) return false;
      const data = await resp.json();
      return data?.protocols?.[protocolKey] === true;
    } catch (_) {
      return false;
    }
  }

  async function runLocalSideGigScan(endpoint, label, protocolKey, statusEl) {
    if (state.running) return;
    state.running = true;
    setStatus(statusEl, `Running ${label}…`, "running");
    document.querySelectorAll(".run-btn").forEach((b) => (b.disabled = true));
    try {
      if (!AdminAuth.isLocalAdminHost()) {
        const data = await apiFetch(endpoint, { method: "POST" });
        state.protocolRun = data;
        renderProtocolOutputs(document.getElementById("protocol-output"), data);
        const generated = (data.phases || []).flatMap((p) => p.generated || []);
        setStatus(statusEl, `${label} finished (${generated.length} new).`, "ok");
        await loadApplications();
        return;
      }

      const syncUp = await AdminAuth.isLocalSyncReachable();
      if (!syncUp) {
        throw new Error(
          `${label} runs locally — start ./scripts/serve_admin_local.sh (sync server on port 8765).`
        );
      }
      if (!(await localSyncSupportsProtocol(protocolKey))) {
        throw new Error(
          "Local sync server is outdated — restart ./scripts/serve_admin_local.sh (Ctrl+C, then run again)."
        );
      }
      const data = await apiFetch(endpoint, { method: "POST" }, localSyncBase());
      state.protocolRun = data;
      renderProtocolOutputs(document.getElementById("protocol-output"), data);
      const generated = (data.phases || []).flatMap((p) => p.generated || []);
      setStatus(statusEl, `${label} finished locally (${generated.length} new).`, "ok");
      await loadApplications();
    } catch (err) {
      const msg = String(err.message || err);
      if (msg === "Not found" || msg.includes("404")) {
        setStatus(
          statusEl,
          AdminAuth.isLocalAdminHost()
            ? `${label} route missing — restart ./scripts/serve_admin_local.sh to reload the sync server.`
            : `${label} route missing on Cloud Run — redeploy tools/cloud_run/service/cloud/deploy.sh.`,
          "err"
        );
      } else {
        setStatus(statusEl, msg, "err");
      }
    } finally {
      state.running = false;
      document.querySelectorAll(".run-btn").forEach((b) => (b.disabled = false));
    }
  }

  async function runFreelancerScan(statusEl) {
    return runLocalSideGigScan("/api/run/freelancer", "Freelancer scan", "freelancer", statusEl);
  }

  async function runCraigslistScan(statusEl) {
    return runLocalSideGigScan("/api/run/craigslist", "Craigslist LA gigs scan", "craigslist", statusEl);
  }

  async function runIndeedScan(statusEl) {
    if (state.running) return;
    state.running = true;
    setStatus(statusEl, "Running Indeed…", "running");
    document.querySelectorAll(".run-btn").forEach((b) => (b.disabled = true));
    try {
      let data;
      const syncUp =
        AdminAuth.isLocalAdminHost() && (await AdminAuth.isLocalSyncReachable());
      if (syncUp) {
        if (!(await localSyncSupportsProtocol("indeed"))) {
          throw new Error(
            "Local sync server is outdated — restart ./scripts/serve_admin_local.sh (Ctrl+C, then run again)."
          );
        }
        data = await apiFetch("/api/run/indeed", { method: "POST" }, localSyncBase());
      } else if (shouldFetchLiveApi()) {
        data = await apiFetch("/api/run/indeed", { method: "POST" });
      } else if (AdminAuth.isLocalAdminHost()) {
        throw new Error(
          "Indeed — start ./scripts/serve_admin_local.sh (sync server on port 8765) or save admin password for Cloud Run."
        );
      } else {
        throw new Error("Indeed requires Cloud Run API (set ADMIN_API_BASE_URL and sign in).");
      }
      state.protocolRun = data;
      renderProtocolOutputs(document.getElementById("protocol-output"), data);
      const generated = (data.phases || []).flatMap((p) => p.generated || []);
      setStatus(
        statusEl,
        syncUp ? `Indeed finished locally (${generated.length} new).` : `Indeed finished (${generated.length} new).`,
        "ok"
      );
      await loadApplications();
    } catch (err) {
      const msg = String(err.message || err);
      if (msg === "Not found" || msg.includes("404")) {
        setStatus(
          statusEl,
          AdminAuth.isLocalAdminHost()
            ? "Indeed route missing — restart ./scripts/serve_admin_local.sh to reload the sync server."
            : "Indeed route missing on Cloud Run — redeploy tools/cloud_run/service/cloud/deploy.sh.",
          "err"
        );
      } else {
        setStatus(statusEl, msg, "err");
      }
    } finally {
      state.running = false;
      document.querySelectorAll(".run-btn").forEach((b) => (b.disabled = false));
    }
  }

  async function runProtocol(endpoint, label, statusEl, parallel) {
    if (state.running) return;
    state.running = true;
    setStatus(statusEl, `Running ${label}…`, "running");
    document.querySelectorAll(".run-btn").forEach((b) => (b.disabled = true));
    try {
      const data = await apiFetch(endpoint, {
        method: "POST",
        body: JSON.stringify({ parallel: !!parallel }),
      });
      state.protocolRun = data;
      renderProtocolOutputs(document.getElementById("protocol-output"), data);
      setStatus(statusEl, `${label} finished.`, "ok");
      await loadApplications();
    } catch (err) {
      setStatus(statusEl, err.message, "err");
    } finally {
      state.running = false;
      document.querySelectorAll(".run-btn").forEach((b) => (b.disabled = false));
    }
  }

  async function submitManualJd(statusEl) {
    const jd = document.getElementById("jd-text").value.trim();
    const applyUrl = document.getElementById("jd-apply-url").value.trim() || null;
    const force = document.getElementById("jd-force").checked;
    if (jd.length < 80) {
      setStatus(statusEl, "Paste at least 80 characters of JD text.", "err");
      return;
    }
    if (state.running) return;
    state.running = true;
    setStatus(statusEl, "Scoring and generating…", "running");
    try {
      const data = await apiFetch("/api/jd/manual", {
        method: "POST",
        body: JSON.stringify({ jd_text: jd, apply_url: applyUrl, force }),
      });
      if (data.error) throw new Error(data.error);
      if (data.skipped) {
        setStatus(statusEl, `Skipped: ${data.reason} (score ${data.score})`, "warn");
      } else {
        setStatus(statusEl, `Generated ${data.generated?.slug} (score ${data.generated?.score})`, "ok");
      }
      await loadApplications();
      await loadProtocolRun();
    } catch (err) {
      setStatus(statusEl, err.message, "err");
    } finally {
      state.running = false;
    }
  }

  function updateApplicationsCount(n) {
    const el = document.getElementById("apps-count");
    if (el) el.textContent = `${n} total`;
  }

  function openAdminDrawer() {
    const drawer = document.getElementById("admin-drawer");
    const backdrop = document.getElementById("admin-drawer-backdrop");
    const toggle = document.getElementById("btn-admin-drawer");
    if (!drawer || !backdrop) return;
    drawer.hidden = false;
    backdrop.hidden = false;
    document.body.classList.add("admin-drawer-open");
    if (toggle) toggle.setAttribute("aria-expanded", "true");
    requestAnimationFrame(() => {
      drawer.classList.add("is-open");
      backdrop.classList.add("is-open");
    });
  }

  function closeAdminDrawer() {
    const drawer = document.getElementById("admin-drawer");
    const backdrop = document.getElementById("admin-drawer-backdrop");
    const toggle = document.getElementById("btn-admin-drawer");
    if (!drawer || !backdrop) return;
    drawer.classList.remove("is-open");
    backdrop.classList.remove("is-open");
    document.body.classList.remove("admin-drawer-open");
    if (toggle) toggle.setAttribute("aria-expanded", "false");
    window.setTimeout(() => {
      if (!drawer.classList.contains("is-open")) {
        drawer.hidden = true;
        backdrop.hidden = true;
      }
    }, 220);
  }

  function bindAdminDrawer() {
    document.getElementById("btn-admin-drawer")?.addEventListener("click", openAdminDrawer);
    document.getElementById("btn-admin-drawer-close")?.addEventListener("click", closeAdminDrawer);
    document.getElementById("admin-drawer-backdrop")?.addEventListener("click", closeAdminDrawer);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && document.body.classList.contains("admin-drawer-open")) {
        closeAdminDrawer();
      }
    });
  }

  function bindActionableBoard() {
    const board = document.getElementById("actionable-board");
    if (!board || board.dataset.bound) return;
    board.dataset.bound = "1";
    board.addEventListener("click", (e) => {
      if (e.target.closest("[data-open-admin]")) {
        openAdminDrawer();
        return;
      }
      const cursorBtn = e.target.closest("[data-cursor-prep]");
      if (cursorBtn && window.AdminCursor) {
        e.preventDefault();
        const runStatus = document.getElementById("run-status");
        try {
          const meta = JSON.parse(cursorBtn.getAttribute("data-cursor-meta") || "{}");
          const mode = cursorBtn.getAttribute("data-cursor-prep") || "mock";
          setStatus(runStatus, "Opening Cursor…", "running");
          void AdminCursor.launchCursorInterviewPrep(meta, mode)
            .then((result) => {
              setStatus(
                runStatus,
                `Cursor opened (${mode})${result.copied ? " · prompt copied to clipboard" : ""} — review and send in chat.`,
                "ok"
              );
            })
            .catch((err) => setStatus(runStatus, err.message, "err"));
        } catch (err) {
          setStatus(runStatus, err.message, "err");
        }
        return;
      }
      const btn = e.target.closest("[data-show-quadrant]");
      if (!btn) return;
      const q = btn.getAttribute("data-show-quadrant");
      board.querySelector(`.quadrant-more[data-quadrant="${q}"]`)?.removeAttribute("hidden");
      btn.remove();
    });
  }

  function bindUi() {
    const apiInput = document.getElementById("api-base");
    const keyInput = document.getElementById("api-key");
    const runStatus = document.getElementById("run-status");
    const jdStatus = document.getElementById("jd-status");

    configureSettingsPanel();
    configureLocalSyncPanel();
    bindAdminDrawer();
    bindActionableBoard();
    bindApplicationSearch();

    document.getElementById("applications-panel")?.addEventListener("toggle", (e) => {
      if (e.target.open) renderApplicationsTableIfVisible();
    });

    document.getElementById("save-settings").addEventListener("click", () => {
      if (!state.configApiBase) {
        const fromInput = apiInput.value.trim().replace(/\/$/, "");
        state.apiBase = fromInput || AdminAuth.resolveProtocolApiBase({});
      }
      const fromInputKey = keyInput.value.trim();
      state.apiKey = fromInputKey || AdminAuth.resolveApiKey(state.configApiBase);
      saveSettings();
      void loadDashboardData();
      setStatus(
        runStatus,
        state.apiBase
          ? `Connected to ${state.apiBase}${state.apiKey ? "" : " (add password to run protocols)"}`
          : "Read-only mode (static JSON).",
        state.apiBase ? "ok" : ""
      );
    });

    document.getElementById("btn-gmail").addEventListener("click", () =>
      runProtocol("/api/run/gmail", "Gmail scan", runStatus)
    );
    document.getElementById("btn-generate").addEventListener("click", () =>
      runProtocol("/api/run/generate", "Triage + generate", runStatus)
    );
    document.getElementById("btn-linkedin").addEventListener("click", () =>
      runProtocol("/api/run/linkedin", "LinkedIn search", runStatus)
    );
    document.getElementById("btn-indeed").addEventListener("click", () =>
      runIndeedScan(runStatus)
    );
    document.getElementById("btn-freelancer").addEventListener("click", () =>
      runFreelancerScan(document.getElementById("side-gig-status"))
    );
    document.getElementById("btn-craigslist").addEventListener("click", () =>
      runCraigslistScan(document.getElementById("side-gig-status"))
    );
    document.getElementById("btn-all-seq").addEventListener("click", () =>
      runProtocol("/api/run/all", "All protocols (sequential)", runStatus, false)
    );
    document.getElementById("btn-all-par").addEventListener("click", () =>
      runProtocol("/api/run/all", "All protocols (parallel)", runStatus, true)
    );

    document.getElementById("btn-jd-submit").addEventListener("click", () => submitManualJd(jdStatus));
    const pullGcs = document.getElementById("btn-pull-gcs");
    if (pullGcs) pullGcs.addEventListener("click", () => pullFromGcsLocal());
    document.getElementById("btn-refresh").addEventListener("click", () => {
      void loadDashboardData();
    });

    const signOut = document.getElementById("btn-sign-out");
    if (signOut) {
      signOut.hidden = !state.passwordProtected;
      signOut.addEventListener("click", () => {
        AdminAuth.clearAuth();
        location.reload();
      });
    }
  }

  async function boot(apiKeyFromLogin) {
    loadSettings();
    if (apiKeyFromLogin) {
      state.apiKey = apiKeyFromLogin;
    } else {
      state.apiKey = AdminAuth.resolveApiKey(state.configApiBase);
    }
    if (!state.apiBase && !state.configApiBase) {
      state.apiBase = AdminAuth.resolveProtocolApiBase({});
    }
    bindUi();
    if (state.apiBase) {
      setStatus(document.getElementById("run-status"), `API: ${state.apiBase}`, "ok");
    }
    try {
      await loadDashboardData();
    } catch (_) {
      /* hydrateFromStatic already surfaced error in board */
    }
  }

  async function init() {
    await loadConfig();
    AdminAuth.requireAuth((apiKey) => boot(apiKey));
  }

  document.addEventListener("DOMContentLoaded", init);
})();
