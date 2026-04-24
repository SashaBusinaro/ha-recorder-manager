/**
 * Recorder Manager — Frontend Application
 *
 * Single-page app for managing HA recorder entity filters.
 */

(function () {
  "use strict";

  // ===== Base Path (injected by server from X-Ingress-Path) =====
  const BASE_PATH = document.body.dataset.ingressPath || "";

  // ===== State =====
  const state = {
    entities: [],
    filters: { include: {}, exclude: {} },
    sort: { key: "size_bytes", dir: "desc" },
    search: "",
    domainFilter: "",
    statusFilter: "",
    limit: 100,   // matches the <option selected> in index.html
    dirty: false,
  };

  // ===== DOM References =====
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const dom = {
    dbSize: $("#db-size"),
    totalRows: $("#total-rows"),
    entityCount: $("#entity-count"),
    searchInput: $("#search-input"),
    domainFilter: $("#domain-filter"),
    statusFilter: $("#status-filter"),
    limitSelect: $("#limit-select"),
    tbody: $("#entity-tbody"),
    btnRefresh: $("#btn-refresh"),
    btnApply: $("#btn-apply"),
    btnPreview: $("#btn-preview"),
    btnClearFilters: $("#btn-clear-filters"),
    filterCount: $("#filter-count"),
    modalOverlay: $("#modal-overlay"),
    btnCancelApply: $("#btn-cancel-apply"),
    btnConfirmApply: $("#btn-confirm-apply"),
    toastContainer: $("#toast-container"),
  };

  // ===== Tag Inputs =====
  const tagInputs = {
    "inc-entities": { values: [], type: "include", key: "entities" },
    "inc-domains": { values: [], type: "include", key: "domains" },
    "inc-globs": { values: [], type: "include", key: "entity_globs" },
    "exc-entities": { values: [], type: "exclude", key: "entities" },
    "exc-domains": { values: [], type: "exclude", key: "domains" },
    "exc-globs": { values: [], type: "exclude", key: "entity_globs" },
  };

  // ===== API Helper =====
  async function api(path, options = {}) {
    const resp = await fetch(BASE_PATH + path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      throw new Error(data.error || data.message || `HTTP ${resp.status}`);
    }
    return resp.json();
  }

  // ===== Data Loading =====
  async function loadEntities() {
    try {
      const qs = state.limit > 0 ? `?limit=${state.limit}` : "";
      const data = await api(`/api/entities${qs}`);
      state.entities = data.entities || [];
      populateDomainFilter();
      renderTable();
    } catch (err) {
      showToast("Failed to load entities: " + err.message, "error");
    }
  }

  async function loadOverview() {
    try {
      const data = await api("/api/db/overview");
      dom.dbSize.textContent = data.file_size_mb + " MB";
      dom.totalRows.textContent = formatNumber(data.total_rows);
      dom.entityCount.textContent = formatNumber(data.entity_count);
    } catch (err) {
      showToast("Failed to load DB overview: " + err.message, "error");
    }
  }

  async function loadFilters() {
    try {
      const data = await api("/api/filters");
      state.filters = data;
      syncTagInputsFromState();
      updateFilterCount();
    } catch (err) {
      showToast("Failed to load filters: " + err.message, "error");
    }
  }

  async function refresh() {
    dom.btnRefresh.disabled = true;
    try {
      await Promise.all([loadOverview(), loadFilters(), loadEntities()]);
      showToast("Data refreshed", "info");
    } catch (err) {
      showToast("Refresh failed: " + err.message, "error");
    } finally {
      dom.btnRefresh.disabled = false;
    }
  }

  // ===== Table Rendering =====
  function getFilteredEntities() {
    let list = state.entities;

    if (state.search) {
      const q = state.search.toLowerCase();
      list = list.filter(
        (e) =>
          e.entity_id.toLowerCase().includes(q) ||
          e.domain.toLowerCase().includes(q)
      );
    }

    if (state.domainFilter) {
      list = list.filter((e) => e.domain === state.domainFilter);
    }

    if (state.statusFilter) {
      list = list.filter((e) => e.filter_status === state.statusFilter);
    }

    // Sort
    const { key, dir } = state.sort;
    const mult = dir === "asc" ? 1 : -1;
    list.sort((a, b) => {
      let va = a[key];
      let vb = b[key];
      if (typeof va === "string") {
        return mult * va.localeCompare(vb);
      }
      return mult * (va - vb);
    });

    return list;
  }

  function renderTable() {
    const entities = getFilteredEntities();
    if (entities.length === 0) {
      dom.tbody.innerHTML = `
        <tr><td colspan="7" style="text-align:center;padding:40px;color:var(--color-text-secondary)">
          No entities found
        </td></tr>`;
      return;
    }

    dom.tbody.innerHTML = entities
      .map((e) => {
        const isExcluded = e.filter_status === "excluded";
        const statusClass = isExcluded ? "status-excluded" : "status-included";
        const rowClass = isExcluded ? "excluded-row" : "";
        const statusLabel = isExcluded ? "Excluded" : "Included";

        return `<tr class="${rowClass}">
          <td class="entity-id-cell">${escapeHtml(e.entity_id)}</td>
          <td class="domain-cell">${escapeHtml(e.domain)}</td>
          <td class="numeric-cell">${formatBytes(e.size_bytes)}</td>
          <td class="numeric-cell">${e.writes_per_minute.toFixed(2)}</td>
          <td><span class="status-badge ${statusClass}">${statusLabel}</span></td>
          <td class="reason-cell">${escapeHtml(e.filter_reason)}</td>
          <td>
            <div class="action-buttons">
              ${
                isExcluded
                  ? `<button class="btn btn-sm btn-include" data-action="include" data-entity="${escapeAttr(e.entity_id)}">Include</button>`
                  : `<button class="btn btn-sm btn-exclude" data-action="exclude" data-entity="${escapeAttr(e.entity_id)}">Exclude</button>`
              }
            </div>
          </td>
        </tr>`;
      })
      .join("");

    // Update sort indicators
    $$(".entity-table thead th").forEach((th) => {
      th.classList.remove("sort-asc", "sort-desc");
      if (th.dataset.sort === state.sort.key) {
        th.classList.add("sort-" + state.sort.dir);
      }
    });
  }

  function populateDomainFilter() {
    const domains = [
      ...new Set(state.entities.map((e) => e.domain)),
    ].sort();
    dom.domainFilter.innerHTML =
      '<option value="">All Domains</option>' +
      domains.map((d) => `<option value="${escapeAttr(d)}">${escapeHtml(d)}</option>`).join("");
  }

  // ===== Tag Input Management =====
  function initTagInputs() {
    Object.keys(tagInputs).forEach((id) => {
      const input = $(`#${id}-input`);
      const tagsContainer = $(`#${id}-tags`);

      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && input.value.trim()) {
          e.preventDefault();
          addTag(id, input.value.trim());
          input.value = "";
        }
        if (
          e.key === "Backspace" &&
          !input.value &&
          tagInputs[id].values.length
        ) {
          removeTag(id, tagInputs[id].values.length - 1);
        }
      });

      input.addEventListener("blur", () => {
        if (input.value.trim()) {
          addTag(id, input.value.trim());
          input.value = "";
        }
      });
    });
  }

  function addTag(inputId, value) {
    const config = tagInputs[inputId];
    if (config.values.includes(value)) return;
    config.values.push(value);
    renderTags(inputId);
    syncStateFromTagInputs();
    markDirty();
  }

  function removeTag(inputId, index) {
    tagInputs[inputId].values.splice(index, 1);
    renderTags(inputId);
    syncStateFromTagInputs();
    markDirty();
  }

  function renderTags(inputId) {
    const container = $(`#${inputId}-tags`);
    container.innerHTML = tagInputs[inputId].values
      .map(
        (v, i) =>
          `<span class="tag">${escapeHtml(v)}<button class="tag-remove" data-input="${inputId}" data-index="${i}">&times;</button></span>`
      )
      .join("");

    // Re-bind remove buttons
    container.querySelectorAll(".tag-remove").forEach((btn) => {
      btn.addEventListener("click", () => {
        removeTag(btn.dataset.input, parseInt(btn.dataset.index));
      });
    });
  }

  function syncTagInputsFromState() {
    Object.keys(tagInputs).forEach((id) => {
      const { type, key } = tagInputs[id];
      const section = state.filters[type] || {};
      tagInputs[id].values = [...(section[key] || [])];
      renderTags(id);
    });
  }

  function syncStateFromTagInputs() {
    state.filters.include = {};
    state.filters.exclude = {};

    Object.keys(tagInputs).forEach((id) => {
      const { type, key, values } = tagInputs[id];
      if (values.length > 0) {
        if (!state.filters[type]) state.filters[type] = {};
        state.filters[type][key] = [...values];
      }
    });

    updateFilterCount();
  }

  function updateFilterCount() {
    let count = 0;
    ["include", "exclude"].forEach((type) => {
      const section = state.filters[type] || {};
      ["entities", "domains", "entity_globs"].forEach((key) => {
        count += (section[key] || []).length;
      });
    });
    dom.filterCount.textContent = count + " rule" + (count !== 1 ? "s" : "");
  }

  // ===== Filter Actions =====
  function addEntityFilter(entityId, action) {
    const type = action === "include" ? "include" : "exclude";
    const oppositeType = action === "include" ? "exclude" : "include";

    // Add to target type
    if (!state.filters[type]) state.filters[type] = {};
    if (!state.filters[type].entities) state.filters[type].entities = [];
    if (!state.filters[type].entities.includes(entityId)) {
      state.filters[type].entities.push(entityId);
    }

    // Remove from opposite type if present
    if (state.filters[oppositeType]?.entities) {
      state.filters[oppositeType].entities = state.filters[
        oppositeType
      ].entities.filter((e) => e !== entityId);
    }

    syncTagInputsFromState();
    markDirty();
    previewFilters();
  }

  async function previewFilters() {
    try {
      const data = await api("/api/filters/preview", {
        method: "POST",
        body: JSON.stringify(state.filters),
      });

      // Update entity statuses in state
      const statusMap = {};
      data.entities.forEach((e) => {
        statusMap[e.entity_id] = {
          filter_status: e.status,
          filter_reason: e.reason,
        };
      });

      state.entities.forEach((e) => {
        if (statusMap[e.entity_id]) {
          e.filter_status = statusMap[e.entity_id].filter_status;
          e.filter_reason = statusMap[e.entity_id].filter_reason;
        }
      });

      renderTable();
    } catch (err) {
      showToast("Preview failed: " + err.message, "error");
    }
  }

  async function applyFilters() {
    dom.btnConfirmApply.disabled = true;
    dom.btnConfirmApply.textContent = "Applying...";

    try {
      const data = await api("/api/apply", {
        method: "POST",
        body: JSON.stringify(state.filters),
      });

      dom.modalOverlay.hidden = true;
      state.dirty = false;
      dom.btnApply.disabled = true;
      showToast(data.message || "Filters applied. Home Assistant is restarting.", "success");
    } catch (err) {
      dom.modalOverlay.hidden = true;
      showToast("Apply failed: " + err.message, "error");
    } finally {
      dom.btnConfirmApply.disabled = false;
      dom.btnConfirmApply.textContent = "Confirm & Restart";
    }
  }

  function markDirty() {
    state.dirty = true;
    dom.btnApply.disabled = false;
  }

  // ===== Toast Notifications =====
  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    dom.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transition = "opacity 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  // ===== Utilities =====
  function formatNumber(n) {
    return (n ?? 0).toLocaleString();
  }

  function formatBytes(bytes) {
    if (!bytes || bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function escapeAttr(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  // ===== Event Listeners =====
  function bindEvents() {
    // Sort headers
    $$(".entity-table thead th.sortable").forEach((th) => {
      th.addEventListener("click", () => {
        const key = th.dataset.sort;
        if (state.sort.key === key) {
          state.sort.dir = state.sort.dir === "asc" ? "desc" : "asc";
        } else {
          state.sort.key = key;
          state.sort.dir = key === "entity_id" || key === "domain" ? "asc" : "desc";
        }
        renderTable();
      });
    });

    // Search
    dom.searchInput.addEventListener("input", (e) => {
      state.search = e.target.value;
      renderTable();
    });

    // Domain filter
    dom.domainFilter.addEventListener("change", (e) => {
      state.domainFilter = e.target.value;
      renderTable();
    });

    // Status filter
    dom.statusFilter.addEventListener("change", (e) => {
      state.statusFilter = e.target.value;
      renderTable();
    });

    // Entity limit selector — triggers a server-side reload
    dom.limitSelect.addEventListener("change", async (e) => {
      state.limit = parseInt(e.target.value, 10);
      dom.btnRefresh.disabled = true;
      try {
        await loadEntities();
        const label = state.limit > 0 ? `Top ${state.limit} entities loaded` : "All entities loaded";
        showToast(label, "info");
      } finally {
        dom.btnRefresh.disabled = false;
      }
    });

    // Refresh
    dom.btnRefresh.addEventListener("click", refresh);

    // Preview
    dom.btnPreview.addEventListener("click", previewFilters);

    // Clear filters
    dom.btnClearFilters.addEventListener("click", () => {
      state.filters = { include: {}, exclude: {} };
      syncTagInputsFromState();
      updateFilterCount();
      markDirty();
      previewFilters();
    });

    // Apply button -> show modal
    dom.btnApply.addEventListener("click", () => {
      dom.modalOverlay.hidden = false;
    });

    // Modal cancel
    dom.btnCancelApply.addEventListener("click", () => {
      dom.modalOverlay.hidden = true;
    });

    // Modal confirm
    dom.btnConfirmApply.addEventListener("click", applyFilters);

    // Close modal on overlay click
    dom.modalOverlay.addEventListener("click", (e) => {
      if (e.target === dom.modalOverlay) {
        dom.modalOverlay.hidden = true;
      }
    });

    // Entity action buttons (delegated)
    dom.tbody.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-action]");
      if (!btn) return;
      addEntityFilter(btn.dataset.entity, btn.dataset.action);
    });
  }

  // ===== Setup Wizard & Banner =====

  const setupOverlay = $("#setup-overlay");
  const setupModal = $("#setup-modal");

  // All wizard step IDs
  const ALL_STEPS = [
    "wiz-mig-1", "wiz-mig-2", "wiz-mig-3",
    "wiz-fresh-1", "wiz-fresh-2",
  ];

  function wizShowOnly(stepId) {
    ALL_STEPS.forEach((id) => {
      const el = $(`#${id}`);
      if (el) el.hidden = id !== stepId;
    });
    setupOverlay.hidden = false;
  }

  // Make modal non-closable: remove backdrop-click behaviour
  let wizClosable = true;

  function wizLock() {
    wizClosable = false;
  }

  function wizHide() {
    setupOverlay.hidden = true;
    wizClosable = true;
  }

  // ---- Shared check-and-reboot flow ----
  async function wizRunCheckAndReboot(spinnerEl, successEl, errorEl, footerEl, backBtn, closeBtn, titleEl) {
    // Show spinner
    spinnerEl.hidden = false;
    successEl.hidden = true;
    errorEl.hidden = true;
    footerEl.hidden = true;
    if (titleEl) titleEl.textContent = "Checking Configuration\u2026";

    try {
      // Step 1: validate config
      const checkResp = await api("/api/setup/check", { method: "POST" });
      // checkResp.status === "ok"
      // Show success state
      spinnerEl.hidden = true;
      successEl.hidden = false;
      if (titleEl) titleEl.textContent = "Configuration Valid";
      footerEl.hidden = false;
      closeBtn.hidden = false;
      backBtn.hidden = true;

      // Step 2: trigger reboot (fire-and-forget from client side)
      api("/api/setup/reboot", { method: "POST" }).catch(() => {});

    } catch (err) {
      spinnerEl.hidden = true;
      errorEl.hidden = false;
      errorEl.textContent = "\u26a0 Validation failed: " + err.message +
        " — Please re-check your configuration.yaml and try again.";
      if (titleEl) titleEl.textContent = "Validation Failed";
      footerEl.hidden = false;
      backBtn.hidden = false;
      closeBtn.hidden = true;
    }
  }

  // ---- Migration wizard ----
  async function wizMigStart() {
    wizShowOnly("wiz-mig-2");
    wizLock();

    const spinner = $("#wiz-mig-copy-spinner");
    const done    = $("#wiz-mig-copy-done");
    const errBox  = $("#wiz-mig-copy-error");
    const footer  = $("#wiz-mig-2-footer");

    spinner.hidden = false;
    done.hidden = true;
    errBox.hidden = true;
    footer.hidden = true;

    try {
      await api("/api/migration/apply", { method: "POST" });
      spinner.hidden = true;
      done.hidden = false;
      footer.hidden = false;
    } catch (err) {
      spinner.hidden = true;
      errBox.hidden = false;
      errBox.textContent = "\u26a0 Copy failed: " + err.message;
      // Disable next, add a close button so user isn't permanently stuck
      footer.hidden = false;
      const nextBtn = $("#wiz-mig-2-next");
      if (nextBtn) nextBtn.disabled = true;
      let closeBtn = $("#wiz-mig-2-close");
      if (!closeBtn) {
        closeBtn = document.createElement("button");
        closeBtn.className = "btn btn-secondary";
        closeBtn.id = "wiz-mig-2-close";
        closeBtn.textContent = "Close";
        closeBtn.addEventListener("click", wizHide);
        footer.appendChild(closeBtn);
      }
      closeBtn.hidden = false;
    }
  }

  async function wizMigCheckReboot() {
    wizShowOnly("wiz-mig-3");
    await wizRunCheckAndReboot(
      $("#wiz-mig-3-spinner"),
      $("#wiz-mig-3-success"),
      $("#wiz-mig-3-error"),
      $("#wiz-mig-3-footer"),
      $("#wiz-mig-3-back"),
      $("#wiz-mig-3-close"),
      $("#wiz-mig-3-title"),
    );
  }

  // ---- Fresh-setup wizard ----
  async function wizFreshStart() {
    wizLock();
    // Create the default filter file (no-op if exists)
    api("/api/setup/init-default", { method: "POST" }).catch(() => {});
  }

  async function wizFreshCheckReboot() {
    wizShowOnly("wiz-fresh-2");
    await wizRunCheckAndReboot(
      $("#wiz-fresh-2-spinner"),
      $("#wiz-fresh-2-success"),
      $("#wiz-fresh-2-error"),
      $("#wiz-fresh-2-footer"),
      $("#wiz-fresh-2-back"),
      $("#wiz-fresh-2-close"),
      $("#wiz-fresh-2-title"),
    );
  }

  // ---- Banner & init ----
  async function wizCheckSetup() {
    try {
      const data = await api("/api/setup/status");
      if (data.setup_complete) return;

      const banner    = $("#setup-banner");
      const bannerMsg = $("#setup-banner-msg");
      const bannerCta = $("#setup-banner-cta");

      if (data.scenario === "migration") {
        bannerMsg.textContent =
          "Existing recorder configuration detected — use the Migration Wizard to import it.";
        bannerCta.textContent = "Start Migration";
        bannerCta.onclick = () => {
          banner.hidden = true;
          wizShowOnly("wiz-mig-1");
        };
      } else {
        bannerMsg.textContent =
          "Setup required — add include/exclude !include lines to your recorder: block in configuration.yaml.";
        bannerCta.textContent = "Start Setup";
        bannerCta.onclick = () => {
          banner.hidden = true;
          wizShowOnly("wiz-fresh-1");
        };
      }

      banner.hidden = false;
    } catch (err) {
      // Non-critical — silent failure
    }
  }

  function bindWizardEvents() {
    const b = (id, fn) => { const el = $(id); if (el) el.addEventListener("click", fn); };

    // Banner dismiss
    b("#setup-banner-dismiss", () => { $("#setup-banner").hidden = true; });

    // Migration wizard
    b("#wiz-mig-1-cancel", () => wizHide());
    b("#wiz-mig-1-next",   () => wizMigStart());
    b("#wiz-mig-2-next",   () => wizMigCheckReboot());
    b("#wiz-mig-3-back",   () => wizShowOnly("wiz-mig-2"));
    b("#wiz-mig-3-close",  () => wizHide());

    // Fresh-setup wizard
    b("#wiz-fresh-1-cancel", () => wizHide());
    b("#wiz-fresh-1-next",   () => wizFreshStart().then(wizFreshCheckReboot));
    b("#wiz-fresh-2-back",   () => wizShowOnly("wiz-fresh-1"));
    b("#wiz-fresh-2-close",  () => wizHide());

    // Backdrop click — only when closable
    if (setupOverlay) {
      setupOverlay.addEventListener("click", (e) => {
        if (wizClosable && e.target === setupOverlay) wizHide();
      });
    }
  }

  // ===== Initialization =====
  async function init() {
    bindEvents();
    bindWizardEvents();
    initTagInputs();
    await refresh();
    // Check setup status after initial load (non-blocking)
    wizCheckSetup();
  }

  // Start when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
