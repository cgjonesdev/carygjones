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
      await loadApplications();
      await loadProtocolRun();
      renderActionable();
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

  async function apiFetch(path, options = {}) {
    const url = apiUrl(path);
    if (!url) throw new Error("Protocol API URL is not configured (set GitHub variable ADMIN_API_BASE_URL and redeploy).");
    const headers = { ...(options.headers || {}) };
    if (state.apiKey) headers["X-Admin-Key"] = state.apiKey;
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
    const s = (status || "unknown").toLowerCase();
    return `<span class="badge badge-${s.replace(/[^a-z]/g, "") || "ready"}">${escapeHtml(status || "—")}</span>`;
  }

  const INTEREST_SCORE = 80;
  const DONE_STATUSES = new Set(["applied", "skipped", "rejected", "offer"]);

  function settingsUrl(slug) {
    return `app.html?slug=${encodeURIComponent(slug)}`;
  }

  function isLinkedInApply(url) {
    return Boolean(url && /linkedin\.com/i.test(url));
  }

  function isEmailApply(app) {
    const method = String(app.apply_method || "").toLowerCase();
    if (/email|reply|proposal|recruiter/.test(method)) return true;
    if (!app.apply_url) return true;
    if (/mailto:/i.test(app.apply_url)) return true;
    return false;
  }

  function classifyApplicationAction(app) {
    const status = String(app.status || "ready").toLowerCase();
    if (DONE_STATUSES.has(status)) return null;

    const score = Number(app.match_score ?? -1);
    const appSettings = settingsUrl(app.slug);
    const subtitle = [app.company || app.slug, app.role, score >= 0 ? `score ${score}` : ""]
      .filter(Boolean)
      .join(" · ");

    if (status === "interview") {
      return {
        priority: 1,
        kind: "interview",
        title: "Interview prep",
        detail: subtitle,
        primary: app.interview_url
          ? { label: "Interview link", url: app.interview_url, external: true }
          : { label: "Open application", url: appSettings },
        secondary: { label: "Settings", url: appSettings },
      };
    }

    if (score < INTEREST_SCORE) return null;

    if (app.gmail_draft_id) {
      return {
        priority: 2,
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
      const title = isLinkedInApply(app.apply_url)
        ? "Easy Apply on LinkedIn"
        : "Apply on job portal";
      return {
        priority: 3,
        kind: "apply",
        title,
        detail: subtitle,
        primary: { label: "Apply", url: app.apply_url, external: true },
        secondary: { label: "Cover letter", url: `${appSettings}&doc=cover` },
      };
    }

    return {
      priority: 4,
      kind: "email",
      title: "Create Gmail draft",
      detail: `${subtitle}${subtitle ? " · " : ""}email apply`,
      primary: { label: "Settings & draft", url: appSettings },
      secondary: app.gmail_url
        ? { label: "Recruiter email", url: app.gmail_url, external: true }
        : null,
    };
  }

  function collectProtocolActionables(run) {
    if (!run?.phases) return [];
    const items = [];
    for (const phase of run.phases) {
      if (phase.error) {
        items.push({
          priority: 0,
          kind: "protocol-error",
          title: `Fix ${phase.phase || "protocol"} error`,
          detail: phase.error,
          primary: { label: "Run protocols", url: "#run-protocols" },
        });
      }
      for (const err of phase.errors || []) {
        items.push({
          priority: 0,
          kind: "protocol-error",
          title: "Protocol error",
          detail: err.error || err.message || JSON.stringify(err),
          primary: { label: "Run protocols", url: "#run-protocols" },
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
    items.sort((a, b) => {
      if (a.priority !== b.priority) return a.priority - b.priority;
      return Number(b.score ?? -1) - Number(a.score ?? -1);
    });
    return items;
  }

  function renderActionable() {
    const container = document.getElementById("actionable-list");
    if (!container) return;

    const items = collectActionables(state.applications, state.protocolRun);
    if (!items.length) {
      container.innerHTML =
        '<p class="empty">Nothing urgent right now. Run protocols or check Applications below.</p>';
      return;
    }

    container.innerHTML = `<ul class="action-list">${items
      .map((item) => {
        const secondary = item.secondary
          ? `<a class="btn" href="${escapeAttr(item.secondary.url)}"${
              item.secondary.external ? ' target="_blank" rel="noopener"' : ""
            }>${escapeHtml(item.secondary.label)}</a>`
          : "";
        return `<li class="action-item action-${escapeAttr(item.kind)}">
          <div class="action-copy">
            <strong>${escapeHtml(item.title)}</strong>
            <span class="action-detail">${escapeHtml(item.detail || item.slug || "")}</span>
          </div>
          <div class="action-buttons btn-row">
            <a class="btn btn-primary" href="${escapeAttr(item.primary.url)}"${
              item.primary.external ? ' target="_blank" rel="noopener"' : ""
            }>${escapeHtml(item.primary.label)}</a>
            ${secondary}
          </div>
        </li>`;
      })
      .join("")}</ul>`;
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
      if (app?.slug) bySlug.set(app.slug, app);
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

  async function loadApplications() {
    const tbody = document.getElementById("apps-table-body");
    let staticApps = [];
    try {
      staticApps = await loadStaticApplications();
    } catch (_) {
      /* static bundle optional when API-only */
    }

    try {
      if (state.apiBase) {
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
          } else {
            throw err;
          }
        }
      } else if (staticApps.length) {
        state.applications = staticApps;
      } else {
        throw new Error("Missing data/applications.json — run scripts/build_admin_data.py");
      }
      renderApplicationsTable(tbody, state.applications);
      renderActionable();
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty">${escapeHtml(err.message)}</td></tr>`;
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
      if (state.apiBase) {
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
      } else {
        state.protocolRun = staticRun;
      }
      renderProtocolOutputs(container, state.protocolRun);
      renderActionable();
    } catch (err) {
      container.innerHTML = `<p class="empty">${escapeHtml(err.message)}</p>`;
      renderActionable();
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

  function bindUi() {
    const apiInput = document.getElementById("api-base");
    const keyInput = document.getElementById("api-key");
    const runStatus = document.getElementById("run-status");
    const jdStatus = document.getElementById("jd-status");

    configureSettingsPanel();
    configureLocalSyncPanel();

    document.getElementById("save-settings").addEventListener("click", () => {
      if (!state.configApiBase) {
        state.apiBase = apiInput.value.trim().replace(/\/$/, "");
      }
      state.apiKey = keyInput.value.trim();
      saveSettings();
      loadApplications();
      loadProtocolRun();
      setStatus(
        runStatus,
        state.apiBase ? `API: ${state.apiBase}` : "Read-only mode (static JSON).",
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
      loadApplications();
      loadProtocolRun();
      renderActionable();
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
    if (apiKeyFromLogin) {
      state.apiKey = apiKeyFromLogin;
    } else {
      loadSettings();
      state.apiKey = AdminAuth.resolveApiKey(state.configApiBase);
    }
    bindUi();
    if (state.apiBase) {
      setStatus(document.getElementById("run-status"), `API: ${state.apiBase}`, "ok");
    }
    await loadApplications();
    await loadProtocolRun();
  }

  async function init() {
    await loadConfig();
    AdminAuth.requireAuth((apiKey) => boot(apiKey));
  }

  document.addEventListener("DOMContentLoaded", init);
})();
