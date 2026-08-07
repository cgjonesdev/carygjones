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
    if (!links || !links.length) return "—";
    return links
      .map((l) => `<a href="${escapeAttr(l.url)}" target="_blank" rel="noopener">${escapeHtml(l.label)}</a>`)
      .join("");
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

  function renderApplicationsTable(tbody, rows) {
    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty">No applications found.</td></tr>`;
      return;
    }
    tbody.innerHTML = rows
      .map(
        (r) => `<tr>
          <td><a href="app.html?slug=${escapeAttr(r.slug)}">${escapeHtml(r.slug)}</a></td>
          <td>${escapeHtml(r.company || "—")}</td>
          <td>${escapeHtml(r.role || "—")}</td>
          <td>${r.match_score ?? "—"}</td>
          <td>${badge(r.status)}</td>
          <td>${escapeHtml(r.updated || "—")}</td>
          <td class="links-cell">${linkHtml(r.links)}</td>
        </tr>`
      )
      .join("");
  }

  function phaseLinks(row) {
    const links = [];
    if (row.apply_url) links.push({ label: "Apply", url: row.apply_url });
    if (row.gmail_url) links.push({ label: "Gmail", url: row.gmail_url });
    if (row.slug) {
      links.push({ label: "Resume", url: `app.html?slug=${row.slug}&doc=resume` });
    }
    return links;
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
        parts.push(`<p class="hint" style="margin-top:0.5rem">Skipped</p>`);
        parts.push(
          renderOutputTable(phase.skipped, (r) => {
            const links = phaseLinks(r);
            if (r.gmail_url) links.push({ label: "Gmail", url: r.gmail_url });
            return links;
          })
        );
      }

      if (Array.isArray(phase.errors) && phase.errors.length) {
        parts.push(`<p class="hint" style="margin-top:0.5rem">Errors</p>`);
        parts.push(
          renderOutputTable(
            phase.errors.map((e) => ({
              slug: e.slug || "—",
              company: "—",
              score: "—",
              reason: e.error || e.message || JSON.stringify(e),
            })),
            () => []
          )
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

  async function loadApplications() {
    const tbody = document.getElementById("apps-table-body");
    try {
      if (state.apiBase) {
        const data = await apiFetch("/api/applications");
        state.applications = data.applications || [];
      } else {
        const resp = await fetch("data/applications.json");
        if (!resp.ok) throw new Error("Missing data/applications.json — run scripts/build_admin_data.py");
        const data = await resp.json();
        state.applications = data.applications || [];
      }
      renderApplicationsTable(tbody, state.applications);
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty">${escapeHtml(err.message)}</td></tr>`;
    }
  }

  async function loadProtocolRun() {
    const container = document.getElementById("protocol-output");
    try {
      if (state.apiBase) {
        state.protocolRun = await apiFetch("/api/protocols/latest");
      } else {
        const resp = await fetch("data/latest_protocol_run.json");
        if (resp.ok) state.protocolRun = await resp.json();
      }
      renderProtocolOutputs(container, state.protocolRun);
    } catch (err) {
      container.innerHTML = `<p class="empty">${escapeHtml(err.message)}</p>`;
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
    document.getElementById("btn-refresh").addEventListener("click", () => {
      loadApplications();
      loadProtocolRun();
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
      if (!state.apiKey) state.apiKey = AdminAuth.getApiKey();
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
