document.addEventListener("DOMContentLoaded", () => {
    const root = document.getElementById("projectDetailsRoot");
    if (!root) {
        return;
    }
    loadProjectDetails();
    Alfred.enableLiveRefresh("project-details-live", loadProjectDetails, { rootId: "projectDetailsRoot", interactionHoldMs: 4200 });
});

function loadProjectDetails() {
    const root = document.getElementById("projectDetailsRoot");
    if (!root) {
        return Promise.resolve();
    }
    const apiUrl = root.dataset.projectDetailsApi || "/api/project-details/";
    return Alfred.fetchJSON(apiUrl)
        .then(payload => {
            renderClock(payload.clock || {});
            renderSummaryCards(payload.summary_cards || []);
            renderOperationalMetrics(payload.operational_metrics || []);
            renderGuardrails(payload.guardrails || {});
            renderCacheHealth(payload.cache_health || {});
            renderBrowserCoverage(payload.browser_coverage || {});
            renderLearningSnapshot(payload.learning_snapshot || {});
            renderInProgressTracks(payload.in_progress_tracks || []);
            renderCompletedTracks(payload.completed_tracks || []);
            renderReportRows("projectDetailsReportLibrary", payload.report_library || [], item => `
                <div class="data-row">
                    <div class="data-label">${Alfred.escapeHtml(formatDateTimeValue(item.created_at))}</div>
                    <div class="data-value">${Alfred.escapeHtml(item.file_path || "")}</div>
                </div>
            `, "No generated report artifacts are stored yet.");
            renderReportRows("projectDetailsDeveloperQueue", payload.developer_queue || [], item => `
                <div class="data-row">
                    <div class="data-label">${Alfred.escapeHtml(`${item.username || ""} | ${item.module || ""} | ${item.severity || ""}`)}</div>
                    <div class="data-value">${Alfred.escapeHtml(item.title || "")} <span class="muted small">${Alfred.escapeHtml(formatDateTimeValue(item.created_at))}</span></div>
                </div>
            `, "No open developer escalations are waiting right now.");
            renderReportRows("projectDetailsAutoTicketActivity", payload.auto_ticket_activity || [], item => `
                <div class="data-row">
                    <div class="data-label">${Alfred.escapeHtml(`${item.module || ""} | ${formatDateTimeValue(item.created_at)}`)}</div>
                    <div class="data-value">${Alfred.escapeHtml(item.title || "")} <span class="muted small">${Alfred.escapeHtml(item.resolution_summary || "")}</span></div>
                </div>
            `, "No ALFRED auto-resolutions are stored yet.");
            Alfred.clearPageAlert("projectDetailsRoot");
        })
        .catch(error => {
            Alfred.upsertPageAlert("projectDetailsRoot", error.message || "Unable to refresh project details.");
        });
}

function renderClock(clock) {
    setText("projectDetailsClockTime", clock.local_time || "--:--");
    setText("projectDetailsClockLabel", `${clock.local_date || ""}${clock.timezone ? ` | ${clock.timezone}` : ""}`.trim());
    setText("projectDetailsClockUtc", `UTC: ${clock.generated_at_utc || ""}`.trim());
}

function renderSummaryCards(cards) {
    const container = document.getElementById("projectDetailsSummaryCards");
    if (!container) {
        return;
    }
    Alfred.setHTMLIfChanged(container, cards.map(card => `
        <article class="hero-signal project-hero-signal">
            <p class="hero-signal-label">${Alfred.escapeHtml(card.label || "")}</p>
            <p class="hero-signal-value">${Alfred.escapeHtml(String(card.value ?? ""))}</p>
            <p class="hero-signal-meta">${Alfred.escapeHtml(card.copy || "")}</p>
        </article>
    `).join(""));
}

function renderOperationalMetrics(items) {
    const container = document.getElementById("projectDetailsOperationalMetrics");
    if (!container) {
        return;
    }
    Alfred.setHTMLIfChanged(container, items.map(item => `
        <div class="data-row">
            <div class="data-label">${Alfred.escapeHtml(item.label || "")}</div>
            <div class="data-value">${Alfred.escapeHtml(String(item.value ?? ""))} <span class="muted small">${Alfred.escapeHtml(item.copy || "")}</span></div>
        </div>
    `).join(""));
}

function renderGuardrails(guardrails) {
    const refreshHealth = guardrails.refresh_health || {};
    const proofContract = guardrails.proof_contract || {};
    const metrics = document.getElementById("projectDetailsGuardrailMetrics");
    if (metrics) {
        const rows = [
            { label: "Circuit threshold", value: `${guardrails.circuit_failure_threshold ?? 0} failures` },
            { label: "Breaker window", value: `${guardrails.circuit_open_minutes ?? 0} minutes` },
            { label: "Refresh batch size", value: `${guardrails.refresh_batch_size ?? 0} records` },
            { label: "Refresh lookahead", value: `${guardrails.stale_lookahead_hours ?? 0} hours` },
        ];
        if (Object.keys(refreshHealth).length) {
            rows.push(
                {
                    label: "Refresh health",
                    value: `${refreshHealth.fresh_records ?? 0}/${refreshHealth.active_records ?? 0}`,
                    copy: "fresh active evidence records",
                },
                {
                    label: "Watchlist by state",
                    value: String(refreshHealth.watchlist_records ?? 0),
                    copy: `watchlist | ${refreshHealth.stale_records ?? 0} stale | ${refreshHealth.failed_records ?? 0} failed | ${refreshHealth.rejected_records ?? 0} rejected | ${refreshHealth.due_records ?? 0} due`,
                },
                {
                    label: "Scheduled candidates",
                    value: String(refreshHealth.scheduled_candidate_records ?? 0),
                    copy: `${refreshHealth.stale_lookahead_hours ?? guardrails.stale_lookahead_hours ?? 0}h lookahead | batch ${refreshHealth.scheduled_refresh_batch_size ?? guardrails.refresh_batch_size ?? 0}`,
                },
                {
                    label: "Capacity gap",
                    value: String(refreshHealth.capacity_gap_records ?? 0),
                    copy: refreshHealth.scheduled_refresh_healthy ? "scheduled refresh can drain the current candidate set" : "scheduled refresh is still gated",
                },
                {
                    label: "Last refresh attempt",
                    value: refreshHealth.last_refresh_attempt_at || "not recorded",
                    copy: `last success ${refreshHealth.last_refresh_success_at || "not recorded"}`,
                },
            );
        }
        if (Object.keys(proofContract).length) {
            rows.push(
                {
                    label: "Proof contract coverage",
                    value: `${proofContract.covered_surface_count ?? 0}/${proofContract.surface_count ?? 0}`,
                    copy: "recommendation and relationship-adjacent surfaces",
                },
                {
                    label: "Required refresh path",
                    value: proofContract.scheduled_refresh || "refresh_due_records",
                    copy: "before new advisory signals ship",
                },
            );
        }
        Alfred.setHTMLIfChanged(metrics, rows.map(renderDataRow).join(""));
    }

    const proofBlock = document.getElementById("projectDetailsProofContractBlock");
    if (proofBlock && Array.isArray(proofContract.surfaces)) {
        Alfred.setHTMLIfChanged(proofBlock, `
            <h3 class="compact-section-title">Proof Contract Coverage</h3>
            <p class="page-section-copy mb-2">${Alfred.escapeHtml(proofContract.summary || "")}</p>
            <div class="chip-row">
                ${proofContract.surfaces.map(surface => `<span class="chip-neutral">${Alfred.escapeHtml(surface.label || "")} | ${Alfred.escapeHtml(surface.surface_type || "")}</span>`).join("")}
            </div>
        `);
    }

    const refreshBlock = document.getElementById("projectDetailsRefreshScopeBlock");
    if (refreshBlock) {
        const perScope = Array.isArray(refreshHealth.per_scope) ? refreshHealth.per_scope : [];
        Alfred.setHTMLIfChanged(refreshBlock, `
            <h3 class="compact-section-title">Evidence Refresh By Scope</h3>
            <p class="page-section-copy mb-2">${Alfred.escapeHtml(refreshHealth.summary || "No active evidence scopes tracked yet.")}</p>
            ${perScope.length ? `
                <div class="chip-row">
                    ${perScope.map(scope => `<span class="chip-neutral">${Alfred.escapeHtml(scope.scope || "")} | ${Alfred.escapeHtml(`${scope.fresh_records ?? 0}/${scope.active_records ?? 0}`)} fresh | ${Alfred.escapeHtml(String(scope.watchlist_records ?? 0))} watchlist | ${Alfred.escapeHtml(String(scope.scheduled_candidate_records ?? 0))} queued</span>`).join("")}
                </div>
            ` : `<div class="empty-state">No active evidence scopes tracked yet.</div>`}
        `);
    }

    const faultList = document.getElementById("projectDetailsGuardrailFaults");
    if (faultList && Array.isArray(guardrails.fault_tolerance)) {
        Alfred.setHTMLIfChanged(faultList, guardrails.fault_tolerance.map(item => `<li class="insight-item">${Alfred.escapeHtml(item || "")}</li>`).join(""));
    }
}

function renderCacheHealth(cacheHealth) {
    const container = document.getElementById("projectDetailsCacheHealthBlock");
    if (!container) {
        return;
    }
    const namespaces = Array.isArray(cacheHealth.namespaces) ? cacheHealth.namespaces : [];
    Alfred.setHTMLIfChanged(container, `
        <h3 class="compact-section-title">Cache Health By Namespace</h3>
        <p class="page-section-copy mb-2">${Alfred.escapeHtml(cacheHealth.summary || "No materialized cache namespaces are registered yet.")}</p>
        ${namespaces.length ? `
            <div class="chip-row">
                ${namespaces.map(namespace => `
                    <span class="chip-neutral">
                        ${Alfred.escapeHtml(namespace.namespace || "")} | ${Alfred.escapeHtml(String(namespace.hit_rate_pct ?? 0))}% hit | ${Alfred.escapeHtml(String(namespace.average_generation_latency_ms ?? 0))} ms | ${Alfred.escapeHtml(namespace.last_cache_status || "unobserved")}
                    </span>
                `).join("")}
            </div>
        ` : `<div class="empty-state">No materialized cache namespaces are registered yet.</div>`}
    `);
}

function renderBrowserCoverage(browserCoverage) {
    const container = document.getElementById("projectDetailsBrowserCoverageBlock");
    if (!container) {
        return;
    }
    const proofSummary = browserCoverage.proof_summary || {};
    const localProofs = Array.isArray(browserCoverage.local_proofs) ? browserCoverage.local_proofs : [];
    const ciProofs = Array.isArray(browserCoverage.ci_proofs) ? browserCoverage.ci_proofs : [];
    const chips = [
        browserCoverage.implementation_status || "Implemented",
        browserCoverage.maturity_status || "Browser-driver gated",
        `CI summary | ${browserCoverage.ci_summary_artifact || "not recorded"}`,
        `artifacts | ${browserCoverage.artifact_dir || "artifacts/browser"}`,
        `workflow | ${browserCoverage.ci_workflow || ".github/workflows/browser-regression.yml"}`,
    ];
    const proofRows = [...localProofs, ...ciProofs].map(proof => `
        <div class="data-row">
            <div class="data-label">${Alfred.escapeHtml(`${proof.expected_run_context === "ci" ? "CI" : "Local"} browser proof | ${proof.label || ""}`)}</div>
            <div class="data-value">${Alfred.escapeHtml(proof.state || "missing")} <span class="muted small">${Alfred.escapeHtml(`${proof.summary_path || ""} | skips ${proof.skipped_count ?? "not recorded"}`)}</span></div>
        </div>
    `).join("");
    Alfred.setHTMLIfChanged(container, `
        <h3 class="compact-section-title">Browser Driver Proof</h3>
        <p class="page-section-copy mb-2">${Alfred.escapeHtml(proofSummary.summary || "No browser regression summary has been recorded yet.")}</p>
        <div class="chip-row">
            ${chips.map(item => `<span class="chip-neutral">${Alfred.escapeHtml(item)}</span>`).join("")}
        </div>
        <div class="data-stack mt-3">
            ${proofRows || `<div class="empty-state">No browser proof lanes are configured yet.</div>`}
        </div>
    `);
}

function renderDataRow(item) {
    return `
        <div class="data-row">
            <div class="data-label">${Alfred.escapeHtml(item.label || "")}</div>
            <div class="data-value">${Alfred.escapeHtml(String(item.value ?? ""))}${item.copy ? ` <span class="muted small">${Alfred.escapeHtml(item.copy)}</span>` : ""}</div>
        </div>
    `;
}

function renderLearningSnapshot(snapshot) {
    const overallProgress = normalizePercent(snapshot.overall_progress);
    setText("projectDetailsLearningSummary", snapshot.summary || "");
    setText("projectDetailsLearningCompletionSummary", snapshot.completion_summary || "");
    setText("projectDetailsOverallProgressValue", `${overallProgress}%`);
    const bar = document.getElementById("projectDetailsOverallProgressBar");
    if (bar) {
        setProgressBar(bar, overallProgress);
    }
    const container = document.getElementById("projectDetailsLearningTracks");
    if (!container) {
        return;
    }
    Alfred.setHTMLIfChanged(container, (snapshot.tracks || []).map(track => renderProgressCard(track, "learning-track-card", track.blocker_label || "Still blocked by", "blocker")).join(""));
}

function renderInProgressTracks(items) {
    const container = document.getElementById("projectDetailsInProgressTracks");
    if (!container) {
        return;
    }
    Alfred.setHTMLIfChanged(container, items.map(item => renderProgressCard(item, "mini-card", "Next focus", "next_focus", "status-guarded")).join(""));
}

function renderCompletedTracks(items) {
    const container = document.getElementById("projectDetailsCompletedTracks");
    if (!container) {
        return;
    }
    Alfred.setHTMLIfChanged(container, items.map(item => renderProgressCard(item, "mini-card", "Maintenance focus", "maintenance_focus", "status-good")).join(""));
}

function renderProgressCard(item, className, footerLabel, footerKey, statusClass = "status-guarded") {
    const progress = normalizePercent(item.progress);
    const effectiveStatusClass = progress >= 100 ? "status-good" : statusClass;
    const signals = Array.isArray(item.signals) ? item.signals : [];
    const maturityGates = Array.isArray(item.maturity_gates) ? item.maturity_gates : [];
    const completionActions = Array.isArray(item.completion_actions) ? item.completion_actions : [];
    const maturityStatus = item.maturity_status || "";
    const maturityStatusClass = item.blocked_by_real_data ? "status-guarded" : "status-stable";
    return `
        <div class="${className}">
            <div class="d-flex justify-content-between align-items-start gap-3 mb-2">
                <div class="fw-semibold">${Alfred.escapeHtml(item.title || "")}</div>
                <div class="d-flex flex-wrap justify-content-end gap-2">
                    ${maturityStatus ? `<span class="status-pill ${maturityStatusClass}">${Alfred.escapeHtml(maturityStatus)}</span>` : ""}
                    <span class="status-pill ${Alfred.escapeHtml(effectiveStatusClass)}">${progress}%</span>
                </div>
            </div>
            <div class="progress alfred-progress mb-2">
                <div class="progress-bar" role="progressbar" style="width: ${progress}%;" aria-valuenow="${progress}" aria-valuemin="0" aria-valuemax="100"></div>
            </div>
            <p class="muted small mb-2">${Alfred.escapeHtml(item.detail || "")}</p>
            ${signals.length ? `<div class="chip-row mb-2">${signals.map(signal => `<span class="chip-neutral">${Alfred.escapeHtml(signal)}</span>`).join("")}</div>` : ""}
            ${maturityGates.length ? `<div class="chip-row mb-2">${maturityGates.map(gate => `<span class="chip-neutral">${Alfred.escapeHtml(gate)}</span>`).join("")}</div>` : ""}
            ${completionActions.length ? `
                <div class="muted small mb-1"><strong>Completion actions:</strong></div>
                <ul class="completion-action-list mb-2">
                    ${completionActions.map(action => `<li>${Alfred.escapeHtml(action)}</li>`).join("")}
                </ul>
            ` : ""}
            <div class="muted small"><strong>${Alfred.escapeHtml(footerLabel)}:</strong> ${Alfred.escapeHtml(item[footerKey] || "")}</div>
        </div>
    `;
}

function normalizePercent(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
        return 0;
    }
    return Math.max(0, Math.min(100, Math.round(numeric)));
}

function setProgressBar(bar, progress) {
    const width = `${progress}%`;
    if (bar.style.width !== width) {
        bar.style.width = width;
    }
    if (bar.getAttribute("aria-valuenow") !== String(progress)) {
        bar.setAttribute("aria-valuenow", String(progress));
    }
}

function renderReportRows(containerId, items, rowRenderer, emptyMessage) {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }
    if (!items.length) {
        Alfred.setHTMLIfChanged(container, `<div class="empty-state">${Alfred.escapeHtml(emptyMessage)}</div>`);
        return;
    }
    Alfred.setHTMLIfChanged(container, `<div class="data-stack">${items.map(item => rowRenderer(item)).join("")}</div>`);
}

function setText(id, value) {
    Alfred.setTextIfChanged(id, value);
}

function formatDateTimeValue(value) {
    if (!value) {
        return "";
    }
    try {
        return Alfred.formatDateTime(value);
    } catch (error) {
        return String(value);
    }
}
