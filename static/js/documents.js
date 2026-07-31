document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("documentCenterRoot")) {
        return;
    }

    document.getElementById("documentStatementForm").addEventListener("submit", submitStatementUpload);
    document.getElementById("documentLoanForm").addEventListener("submit", submitLoanUpload);
    document.getElementById("documentVehicleForm").addEventListener("submit", submitVehicleDocument);
    document.getElementById("documentServiceForm").addEventListener("submit", submitServiceDocument);
    document.getElementById("documentResumeForm").addEventListener("submit", submitResumeDocument);
    document.getElementById("documentCreditForm").addEventListener("submit", submitCreditDocument);
    document.getElementById("documentChatGPTImportForm").addEventListener("submit", submitChatGPTImport);

    loadDocumentCenter();
    Alfred.enableLiveRefresh("documents-live", loadDocumentCenter, { rootId: "documentCenterRoot", interactionHoldMs: 4500 });
});

const reviewQueueState = new Map();
const documentCenterCache = new Map();

const documentCenterResources = [
    { key: "statementUploads", url: "/api/expenses/uploads/", fallback: [] },
    { key: "loanUploads", url: "/api/loans/import-uploads/", fallback: [] },
    { key: "bikeDashboard", url: "/api/mobility/bike-service-dashboard/", fallback: { bike_profiles: [], bike_documents: [] } },
    { key: "careerFiles", url: "/api/career/resumes/", fallback: [] },
    { key: "creditUploads", url: "/api/integrations/credit-score/uploads/", fallback: [] },
    { key: "chatgptImports", url: "/api/reports/chatgpt-imports/", fallback: [] },
    { key: "reviewQueue", url: "/api/documents/review-queue/", fallback: { results: [] } },
    { key: "diagnostics", url: "/api/documents/diagnostics/", fallback: { results: [] } },
];

function loadDocumentCenter() {
    return Promise.all(documentCenterResources.map(loadDocumentResource))
        .then(results => {
            const payload = Object.fromEntries(results.map(result => [result.key, result.data]));
            const failures = results.filter(result => result.error);

            const statementUploads = payload.statementUploads || [];
            const loanUploads = payload.loanUploads || [];
            const bikeDashboard = payload.bikeDashboard || { bike_profiles: [], bike_documents: [] };
            const careerFiles = payload.careerFiles || [];
            const creditUploads = payload.creditUploads || [];
            const chatgptImports = documentCenterItems(payload.chatgptImports || []);
            const reviewQueue = payload.reviewQueue || { results: [] };
            const diagnostics = payload.diagnostics || { results: [] };

            hydrateVehicleProfiles(bikeDashboard.bike_profiles || []);
            renderDocumentSummary(statementUploads, loanUploads, bikeDashboard.bike_documents || [], careerFiles, creditUploads, chatgptImports);
            renderStatementUploads(statementUploads);
            renderLoanUploads(loanUploads);
            renderVehicleDocuments(bikeDashboard.bike_documents || []);
            renderCareerFiles(careerFiles);
            renderCreditUploads(creditUploads);
            renderChatGPTImports(chatgptImports);
            renderReviewQueue(reviewQueue.results || []);
            renderDiagnostics(diagnostics.results || []);

            if (failures.length) {
                failures.forEach(result => {
                    Alfred.logClientIssue({
                        module: "documents",
                        category: "api",
                        scope: result.key,
                        eventType: "panel_refresh_failure",
                        severity: "warning",
                        message: result.error.message,
                        payload: { url: result.url },
                    });
                });
                Alfred.upsertPageAlert(
                    "documentCenterRoot",
                    `Some document panels could not refresh. Showing the last successful data where available. Failed: ${failures.map(result => result.label).join(", ")}.`,
                    "warning"
                );
                return;
            }

            Alfred.clearPageAlert("documentCenterRoot");
        })
        .catch(error => {
            Alfred.logClientIssue({
                module: "documents",
                category: "visualization",
                scope: "document_center",
                eventType: "render_failure",
                severity: "error",
                message: error.message,
            });
            Alfred.upsertPageAlert("documentCenterRoot", error.message, "danger");
        });
}

function loadDocumentResource(resource) {
    return Alfred.fetchJSON(resource.url)
        .then(data => {
            documentCenterCache.set(resource.key, data);
            return {
                ...resource,
                label: documentCenterLabel(resource.key),
                data,
                error: null,
            };
        })
        .catch(error => {
            const cached = documentCenterCache.has(resource.key)
                ? documentCenterCache.get(resource.key)
                : resource.fallback;
            return {
                ...resource,
                label: documentCenterLabel(resource.key),
                data: cached,
                error: new Error(`${documentCenterLabel(resource.key)}: ${error.message}`),
            };
        });
}

function documentCenterLabel(key) {
    const labels = {
        statementUploads: "Statements",
        loanUploads: "Loan docs",
        bikeDashboard: "Vehicle docs",
        careerFiles: "Career files",
        creditUploads: "Credit reports",
        chatgptImports: "ChatGPT imports",
        reviewQueue: "Review queue",
        diagnostics: "Diagnostics",
    };
    return labels[key] || key;
}

function documentCenterItems(payload) {
    if (Array.isArray(payload)) {
        return payload;
    }
    if (Array.isArray(payload?.results)) {
        return payload.results;
    }
    return [];
}

function setDocumentCenterBusy(isBusy) {
    const root = document.getElementById("documentCenterRoot");
    if (!root) {
        return;
    }
    root.dataset.liveRefreshBusy = isBusy ? "true" : "false";
}

function reviewQueueKey(scope, id) {
    return `${scope}:${id}`;
}

function snapshotReviewQueueState() {
    const container = document.getElementById("documentReviewQueue");
    if (!container) {
        return;
    }
    container.querySelectorAll("details[data-review-key]").forEach(details => {
        const key = details.dataset.reviewKey;
        if (!key) {
            return;
        }
        const form = details.querySelector("form");
        const state = reviewQueueState.get(key) || {};
        const nextState = {
            ...state,
            open: details.open,
        };
        if (form) {
            nextState.values = {
                ...(state.values || {}),
                ...Object.fromEntries(new FormData(form).entries()),
            };
            const activeElement = document.activeElement;
            if (activeElement instanceof Element && form.contains(activeElement) && activeElement.name) {
                nextState.activeField = activeElement.name;
            }
        }
        reviewQueueState.set(key, nextState);
    });
}

function pruneReviewQueueState(activeKeys) {
    Array.from(reviewQueueState.keys()).forEach(key => {
        if (!activeKeys.has(key)) {
            reviewQueueState.delete(key);
        }
    });
}

function getReviewFieldValue(state, fieldName, fallbackValue) {
    if (state?.values && Object.prototype.hasOwnProperty.call(state.values, fieldName)) {
        return state.values[fieldName];
    }
    return fallbackValue ?? "";
}

function formatReviewFieldValue(field, value) {
    if (field?.type === "json") {
        if (typeof value === "string") {
            return value;
        }
        if (value === null || value === undefined || value === "") {
            return "";
        }
        try {
            return JSON.stringify(value, null, 2);
        } catch (_error) {
            return String(value);
        }
    }
    return String(value ?? "");
}

function hydrateVehicleProfiles(profiles) {
    ["documentVehicleProfile", "documentServiceProfile"].forEach(id => {
        Alfred.syncSelectOptions(id, profiles, {
            includeBlank: !profiles.length,
            blankLabel: "Add a vehicle profile first",
            getValue: profile => profile.id,
            getLabel: profile => profile.display_name,
            disableWhenEmpty: true,
        });
    });
}

function renderDocumentSummary(statementUploads, loanUploads, vehicleDocuments, resumes, creditUploads, chatgptImports = []) {
    const recentConfidence = [
        ...statementUploads.map(item => Number(item.parse_confidence || 0)),
        ...loanUploads.map(item => Number(item.parse_confidence || 0)),
        ...vehicleDocuments.map(item => Number(item.parse_confidence || 0)),
        ...resumes.map(item => Number(item.parse_confidence || 0)),
        ...creditUploads.map(item => Number(item.parse_confidence || 0)),
    ].filter(value => value > 0);
    const avgConfidence = recentConfidence.length
        ? Math.round((recentConfidence.reduce((sum, value) => sum + value, 0) / recentConfidence.length) * 100)
        : 0;

    Alfred.setTextIfChanged("documentConfidenceValue", `${avgConfidence}%`);
    Alfred.setTextIfChanged("documentCenterMeta", statementUploads.length || loanUploads.length || vehicleDocuments.length || resumes.length || creditUploads.length || chatgptImports.length
        ? `${statementUploads.length} statements | ${loanUploads.length} loan docs | ${vehicleDocuments.length} vehicle docs | ${resumes.length} career files | ${creditUploads.length} credit reports | ${chatgptImports.length} chat imports tracked`
        : "No recent uploads yet.");

    const cards = [
        { label: "Statements", value: statementUploads.length, copy: "Uploaded financial statements tracked here" },
        { label: "Loan Docs", value: loanUploads.length, copy: "Imported sanction letters, schedules, and statements" },
        { label: "Vehicle Docs", value: vehicleDocuments.length, copy: "Compliance and service-supporting files" },
        { label: "Career Files", value: resumes.length, copy: "Resume-based career intelligence inputs" },
        { label: "Credit Reports", value: creditUploads.length, copy: "Uploaded bureau reports retained with parser status" },
        { label: "Chat Imports", value: chatgptImports.length, copy: "Imported ChatGPT context retained for review" },
        { label: "Parser Avg", value: `${avgConfidence}%`, copy: "Average parser confidence across recent uploads" },
    ];
    Alfred.setHTMLIfChanged("documentCenterCards", cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${Alfred.escapeHtml(card.label)}</p>
            <h2 class="metric-value">${Alfred.escapeHtml(String(card.value))}</h2>
            <p class="metric-caption">${Alfred.escapeHtml(card.copy)}</p>
        </article>
    `).join(""));
}

function renderStatementUploads(items) {
    const target = document.getElementById("documentStatementList");
    if (!items.length) {
        Alfred.setHTMLIfChanged(target, `<div class="empty-state">No uploaded statements yet.</div>`);
        return;
    }

    Alfred.setHTMLIfChanged(target, items.slice(0, 10).map(item => {
        const importedCount = Number(item.imported_count || 0);
        const previewInfo = statementPreviewInfo(item);
        const summary = previewInfo
            ? previewInfo
            : (importedCount
                ? `${Alfred.formatNumber(importedCount, 0)} imported row${importedCount === 1 ? "" : "s"}`
                : "Metadata retained for review");
        const institution = item.bank_name || item.institution_name || "Unknown institution";
        const period = item.statement_start || item.statement_end
            ? `${item.statement_start || "?"} to ${item.statement_end || "?"}`
            : "Statement period not recovered";
        return `
            <div class="mini-card">
                <div class="fw-semibold">${Alfred.escapeHtml(item.file_name)}</div>
                <div class="muted small">${Alfred.escapeHtml((item.source || "").replaceAll("_", " "))} | ${(Number(item.parse_confidence || 0) * 100).toFixed(0)}% | ${Alfred.formatDateTime(item.uploaded_at)}</div>
                <div class="muted small mt-2">${Alfred.escapeHtml(item.parser_status_label || item.parser_status || "Unknown")} | ${Alfred.escapeHtml(summary)}</div>
                <div class="muted small">${Alfred.escapeHtml(institution)}${item.account_number ? ` | ${Alfred.escapeHtml(maskAccount(item.account_number))}` : ""}</div>
                <div class="muted small">${Alfred.escapeHtml(period)}</div>
                ${item.extracted_payload?.background_retry?.state ? `<div class="small mt-2">Background retry: ${Alfred.escapeHtml(item.extracted_payload.background_retry.state)}</div>` : ""}
                ${item.parser_notes ? `<div class="small mt-2">${Alfred.escapeHtml(item.parser_notes)}</div>` : ""}
                <div class="list-actions mt-3">
                    <button class="btn btn-sm btn-outline-primary" type="button" onclick="retryReviewItem('statement_document', ${item.id})">Retry</button>
                    <button class="btn btn-sm btn-outline-danger" type="button" onclick="deleteDocumentCenterItem('statement_document', ${item.id})">Delete</button>
                </div>
            </div>
        `;
    }).join(""));
}

function renderLoanUploads(items) {
    const target = document.getElementById("documentLoanList");
    if (!items.length) {
        Alfred.setHTMLIfChanged(target, `<div class="empty-state">No uploaded loan documents yet.</div>`);
        return;
    }

    Alfred.setHTMLIfChanged(target, items.slice(0, 10).map(item => {
        const linkedLoans = Array.isArray(item.linked_loans) ? item.linked_loans : [];
        const summary = linkedLoans.length
            ? `${linkedLoans.length} loan record${linkedLoans.length === 1 ? "" : "s"} linked`
            : "Saved for review";
        return `
            <div class="mini-card">
                <div class="fw-semibold">${Alfred.escapeHtml(item.file_name || "Loan document")}</div>
                <div class="muted small">${Alfred.escapeHtml(formatDocType(item.document_type || "other"))} | ${(Number(item.parse_confidence || 0) * 100).toFixed(0)}% | ${Alfred.formatDateTime(item.created_at)}</div>
                <div class="muted small mt-2">${Alfred.escapeHtml(item.parser_status_label || item.parser_status || "Unknown")} | ${Alfred.escapeHtml(summary)}</div>
                <div class="small mt-2">${Alfred.escapeHtml(item.summary || "")}</div>
                <div class="list-actions mt-3">
                    <button class="btn btn-sm btn-outline-primary" type="button" onclick="retryReviewItem('loan_document', ${item.id})">Retry</button>
                    <button class="btn btn-sm btn-outline-danger" type="button" onclick="deleteDocumentCenterItem('loan_document', ${item.id})">Delete</button>
                </div>
            </div>
        `;
    }).join(""));
}

function renderVehicleDocuments(items) {
    const target = document.getElementById("documentVehicleList");
    if (!items.length) {
        Alfred.setHTMLIfChanged(target, `<div class="empty-state">No vehicle documents uploaded yet.</div>`);
        return;
    }

    Alfred.setHTMLIfChanged(target, items.slice(0, 10).map(item => `
        <div class="mini-card">
            <div class="fw-semibold">${Alfred.escapeHtml(item.document_type_label || item.document_type)}</div>
            <div class="muted small">${Alfred.escapeHtml(item.bike_name || item.bike_profile_name || "Vehicle")} | ${(Number(item.parse_confidence || 0) * 100).toFixed(0)}% | ${Alfred.formatDateTime(item.created_at)}</div>
            <div class="muted small mt-2">${Alfred.escapeHtml(item.verification_status_label || item.verification_status || "Unknown")}${item.expiry_date ? ` | Expires ${Alfred.formatDate(item.expiry_date)}` : ""}</div>
            <div class="list-actions mt-3">
                <button class="btn btn-sm btn-outline-primary" type="button" onclick="retryReviewItem('vehicle_document', ${item.id})">Retry</button>
                <button class="btn btn-sm btn-outline-danger" type="button" onclick="deleteDocumentCenterItem('vehicle_document', ${item.id})">Delete</button>
            </div>
        </div>
    `).join(""));
}

function renderCareerFiles(items) {
    const target = document.getElementById("documentResumeList");
    if (!items.length) {
        Alfred.setHTMLIfChanged(target, `<div class="empty-state">No career files uploaded yet.</div>`);
        return;
    }

    Alfred.setHTMLIfChanged(target, items.slice(0, 10).map(item => `
        <div class="mini-card">
            <div class="fw-semibold">${Alfred.escapeHtml(item.file_name || "Resume")}</div>
            <div class="muted small">${(Number(item.parse_confidence || 0) * 100).toFixed(0)}% | ${Alfred.escapeHtml(item.parser_status_label || item.parser_status || "Unknown")}${item.created_at ? ` | ${Alfred.formatDateTime(item.created_at)}` : ""}</div>
            <div class="muted small mt-2">${Alfred.escapeHtml(item.summary || "")}</div>
            <div class="list-actions mt-3">
                <button class="btn btn-sm btn-outline-primary" type="button" onclick="retryReviewItem('resume_document', ${item.id})">Retry</button>
                <button class="btn btn-sm btn-outline-danger" type="button" onclick="deleteDocumentCenterItem('resume_document', ${item.id})">Delete</button>
            </div>
        </div>
    `).join(""));
}

function renderCreditUploads(items) {
    const target = document.getElementById("documentCreditList");
    if (!items.length) {
        Alfred.setHTMLIfChanged(target, `<div class="empty-state">No credit reports uploaded yet.</div>`);
        return;
    }

    Alfred.setHTMLIfChanged(target, items.slice(0, 10).map(item => `
        <div class="mini-card">
            <div class="fw-semibold">${Alfred.escapeHtml(item.file_name || "Credit report")}</div>
            <div class="muted small">${Alfred.escapeHtml(item.bureau || "Unknown bureau")} | ${(Number(item.parse_confidence || 0) * 100).toFixed(0)}% | ${Alfred.formatDateTime(item.uploaded_at)}</div>
            <div class="muted small mt-2">${Alfred.escapeHtml(item.parser_status || "Unknown")}${item.score ? ` | Score ${Alfred.escapeHtml(String(item.score))}` : " | Awaiting verified score extraction"}</div>
            ${item.parser_notes ? `<div class="small mt-2">${Alfred.escapeHtml(item.parser_notes)}</div>` : ""}
            <div class="list-actions mt-3">
                <button class="btn btn-sm btn-outline-primary" type="button" onclick="retryReviewItem('credit_report', ${item.id})">Retry</button>
                <button class="btn btn-sm btn-outline-danger" type="button" onclick="deleteDocumentCenterItem('credit_report', ${item.id})">Delete</button>
            </div>
        </div>
    `).join(""));
}

function renderChatGPTImports(items) {
    const target = document.getElementById("documentChatGPTImportList");
    if (!target) {
        return;
    }
    if (!items.length) {
        Alfred.setHTMLIfChanged(target, `<div class="empty-state">No ChatGPT imports saved yet.</div>`);
        return;
    }

    Alfred.setHTMLIfChanged(target, items.slice(0, 8).map(item => {
        const modules = Array.isArray(item.detected_modules) ? item.detected_modules : [];
        const moduleChips = modules.slice(0, 5).map(module => `
            <span class="chip-neutral">${Alfred.escapeHtml(formatDocType(module.module || "context"))} ${Math.round(Number(module.confidence || 0) * 100)}%</span>
        `).join("");
        const payload = item.parsed_payload || {};
        const sourceMeta = [
            item.import_type_label || formatDocType(item.import_type || "chat_transcript"),
            item.status_label || formatDocType(item.status || "review_ready"),
            payload.message_count ? `${Alfred.formatNumber(payload.message_count, 0)} messages` : "",
            payload.word_count ? `${Alfred.formatNumber(payload.word_count, 0)} words` : "",
        ].filter(Boolean).join(" | ");
        return `
            <div class="mini-card">
                <div class="fw-semibold">${Alfred.escapeHtml(item.title || "ChatGPT import")}</div>
                <div class="muted small">${Alfred.escapeHtml(item.source_label || "ChatGPT")} | ${Alfred.escapeHtml(sourceMeta)} | ${Alfred.formatDateTime(item.created_at)}</div>
                ${moduleChips ? `<div class="chip-row mt-2">${moduleChips}</div>` : ""}
                <div class="small mt-2">${Alfred.escapeHtml(item.summary || item.preview || "Saved for review.")}</div>
            </div>
        `;
    }).join(""));
}

function renderDiagnostics(items) {
    const target = document.getElementById("documentDiagnosticsList");
    if (!items.length) {
        Alfred.setHTMLIfChanged(target, `<div class="empty-state">No document or visualization issues have been logged recently.</div>`);
        return;
    }

    Alfred.setHTMLIfChanged(target, items.map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between gap-3 align-items-start">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(formatDocType(item.module || "general"))} | ${Alfred.escapeHtml(formatDocType(item.event_type || "event"))}</div>
                    <div class="muted small">${Alfred.escapeHtml(item.severity || "info")} | ${Alfred.formatDateTime(item.created_at)}</div>
                </div>
                <div class="alfred-chip">${Alfred.escapeHtml(formatDocType(item.category || "document"))}</div>
            </div>
            <div class="small mt-2">${Alfred.escapeHtml(item.message || "")}</div>
            ${item.file_name ? `<div class="muted small mt-2">${Alfred.escapeHtml(item.file_name)}</div>` : ""}
            ${item.payload?.parser_status ? `<div class="muted small mt-1">Status: ${Alfred.escapeHtml(item.payload.parser_status)} | Confidence: ${Alfred.escapeHtml(String(Math.round(Number(item.payload.parse_confidence || 0) * 100)))}%</div>` : ""}
        </div>
    `).join(""));
}

function renderReviewQueue(items) {
    const target = document.getElementById("documentReviewQueue");
    snapshotReviewQueueState();
    if (!items.length) {
        pruneReviewQueueState(new Set());
        Alfred.setHTMLIfChanged(target, `<div class="empty-state">No low-confidence uploads are waiting for review right now.</div>`);
        return;
    }

    const activeKeys = new Set();
    Alfred.setHTMLIfChanged(target, items.map(item => {
        const key = reviewQueueKey(item.scope, item.id);
        activeKeys.add(key);
        const state = reviewQueueState.get(key) || {};
        const formId = `review-form-${item.scope}-${item.id}`;
        const retryState = item.background_retry?.state ? `Retry state: ${item.background_retry.state}` : "No queued retry state";
        const acceptedCorrections = formatAcceptedCorrections(item);
        const reviewArtifacts = renderReviewArtifacts(item.review_artifacts, formId, item.review_fields || []);
        return `
            <div class="mini-card timeline-card">
                <div class="d-flex justify-content-between gap-3 align-items-start">
                    <div>
                        <div class="fw-semibold">${Alfred.escapeHtml(item.file_name)}</div>
                        <div class="muted small">${Alfred.escapeHtml(formatDocType(item.scope))} | ${(Number(item.parse_confidence || 0) * 100).toFixed(0)}% | ${Alfred.escapeHtml(item.parser_status || "unknown")}</div>
                        <div class="small mt-2">${Alfred.escapeHtml(item.summary || "")}</div>
                        ${item.notes ? `<div class="small mt-2">${Alfred.escapeHtml(item.notes)}</div>` : ""}
                        ${acceptedCorrections ? `<div class="small mt-2"><strong>Accepted correction:</strong><div class="mt-1">${acceptedCorrections}</div></div>` : ""}
                        ${reviewArtifacts}
                        <div class="muted small mt-2">${Alfred.escapeHtml(retryState)}</div>
                    </div>
                    <div class="list-actions">
                        <button class="btn btn-sm btn-outline-primary" type="button" onclick="retryReviewItem('${item.scope}', ${item.id})">Retry</button>
                        <button class="btn btn-sm btn-outline-danger" type="button" onclick="deleteDocumentCenterItem('${item.scope}', ${item.id})">Delete</button>
                    </div>
                </div>
                <details class="mt-3" data-review-key="${Alfred.escapeHtml(key)}"${state.open ? " open" : ""}>
                    <summary class="small fw-semibold">Accept correction</summary>
                    <form id="${formId}" class="soft-grid mt-3" onsubmit="submitDocumentCorrection(event, '${item.scope}', ${item.id})">
                        <div class="row g-3">
                            ${(item.review_fields || []).map(field => `
                                <div class="col-md-6">
                                    <label class="form-label" for="${formId}-${field.name}">${Alfred.escapeHtml(field.label)}</label>
                                    ${field.type === "json"
                                        ? `
                                            <textarea
                                                id="${formId}-${field.name}"
                                                name="${field.name}"
                                                class="form-control"
                                                rows="5"
                                            >${Alfred.escapeHtml(formatReviewFieldValue(field, getReviewFieldValue(state, field.name, item.fields?.[field.name] ?? "")))}</textarea>
                                        `
                                        : `
                                            <input
                                                id="${formId}-${field.name}"
                                                name="${field.name}"
                                                type="${field.type === "number" ? "number" : (field.type === "date" ? "date" : "text")}"
                                                class="form-control"
                                                value="${Alfred.escapeHtml(formatReviewFieldValue(field, getReviewFieldValue(state, field.name, item.fields?.[field.name] ?? "")))}"
                                            >
                                        `}
                                </div>
                            `).join("")}
                        </div>
                        <div class="mt-3">
                            <button class="btn btn-sm btn-primary" type="submit">Save Correction</button>
                        </div>
                    </form>
                </details>
            </div>
        `;
    }).join(""));
    pruneReviewQueueState(activeKeys);
    items.forEach(item => {
        const key = reviewQueueKey(item.scope, item.id);
        const state = reviewQueueState.get(key);
        if (!state?.activeField) {
            return;
        }
        const details = Array.from(target.querySelectorAll("details[data-review-key]"))
            .find(node => node.dataset.reviewKey === key);
        const input = details?.querySelector(`[name="${state.activeField}"]`);
        if (input instanceof HTMLElement && document.activeElement !== input) {
            input.focus({ preventScroll: true });
        }
    });
}

function submitStatementUpload(event) {
    event.preventDefault();
    const form = event.currentTarget;
    runBatchUpload({
        form,
        fileFieldName: "statement",
        feedbackId: "documentStatementFeedback",
        emptyMessage: "Choose at least one statement PDF first.",
        pendingText: "Uploading...",
        itemLabel: "statement",
        successVerb: "processed",
        uploadFile: (_file, payload, uploadContext) => Alfred.uploadJSON("/api/expenses/import-statement/", {
            method: "POST",
            body: payload,
            onUploadState: uploadContext?.reportProgress,
        }),
        summarizeResults: summarizeStatementBatch,
        onSuccess: loadDocumentCenter,
    });
}

function submitLoanUpload(event) {
    event.preventDefault();
    const form = event.currentTarget;
    runBatchUpload({
        form,
        fileFieldName: "file",
        feedbackId: "documentLoanFeedback",
        emptyMessage: "Choose at least one loan PDF first.",
        pendingText: "Importing...",
        itemLabel: "loan document",
        successVerb: "processed",
        uploadFile: (_file, payload, uploadContext) => Alfred.uploadJSON("/api/loans/import-pdf/", {
            method: "POST",
            body: payload,
            onUploadState: uploadContext?.reportProgress,
        }),
        summarizeResults: summarizeLoanBatch,
        onSuccess: loadDocumentCenter,
    });
}

function submitVehicleDocument(event) {
    event.preventDefault();
    const form = event.currentTarget;
    runBatchUpload({
        form,
        fileFieldName: "document_file",
        feedbackId: "documentVehicleFeedback",
        emptyMessage: "Choose at least one vehicle document first.",
        pendingText: "Uploading...",
        itemLabel: "vehicle document",
        successVerb: "uploaded",
        uploadFile: (_file, payload, uploadContext) => Alfred.uploadJSON("/api/mobility/bike-documents/upload/", {
            method: "POST",
            body: payload,
            onUploadState: uploadContext?.reportProgress,
        }),
        summarizeResults: results => Alfred.summarizeUploadBatch(results, { itemLabel: "vehicle document", successVerb: "uploaded" }),
        onSuccess: loadDocumentCenter,
    });
}

function submitServiceDocument(event) {
    event.preventDefault();
    const form = event.currentTarget;
    runBatchUpload({
        form,
        fileFieldName: "service_file",
        feedbackId: "documentServiceFeedback",
        emptyMessage: "Choose at least one service bill or work note first.",
        pendingText: "Importing...",
        itemLabel: "service file",
        successVerb: "imported",
        uploadFile: (_file, payload, uploadContext) => Alfred.uploadJSON("/api/mobility/bike-services/import/", {
            method: "POST",
            body: payload,
            onUploadState: uploadContext?.reportProgress,
        }),
        summarizeResults: summarizeServiceBatch,
        onSuccess: loadDocumentCenter,
    });
}

function submitResumeDocument(event) {
    event.preventDefault();
    const form = event.currentTarget;
    runBatchUpload({
        form,
        fileFieldName: "resume",
        feedbackId: "documentResumeFeedback",
        emptyMessage: "Choose at least one resume or CV file first.",
        pendingText: "Uploading...",
        itemLabel: "career file",
        successVerb: "uploaded",
        uploadFile: (_file, payload, uploadContext) => Alfred.uploadJSON("/api/career/resumes/upload/", {
            method: "POST",
            body: payload,
            onUploadState: uploadContext?.reportProgress,
        }),
        summarizeResults: summarizeResumeBatch,
        onSuccess: loadDocumentCenter,
    });
}

function submitCreditDocument(event) {
    event.preventDefault();
    const form = event.currentTarget;
    runBatchUpload({
        form,
        fileFieldName: "report",
        feedbackId: "documentCreditFeedback",
        emptyMessage: "Choose at least one credit report file first.",
        pendingText: "Uploading...",
        itemLabel: "credit report",
        successVerb: "uploaded",
        uploadFile: (_file, payload, uploadContext) => Alfred.uploadJSON("/api/integrations/credit-score/upload-report/", {
            method: "POST",
            body: payload,
            onUploadState: uploadContext?.reportProgress,
        }),
        summarizeResults: summarizeCreditBatch,
        onSuccess: loadDocumentCenter,
    });
}

function submitChatGPTImport(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const rawText = String(form.elements.raw_text?.value || "").trim();
    if (!rawText) {
        showFormFeedback("documentChatGPTFeedback", "Paste a ChatGPT dashboard, transcript, or exported conversation JSON first.", "warning");
        return;
    }

    const submitButton = form.querySelector("button[type='submit']");
    if (submitButton) {
        submitButton.disabled = true;
    }
    setDocumentCenterBusy(true);
    showFormFeedback("documentChatGPTFeedback", "Importing chat context...", "info");

    Alfred.fetchJSON("/api/reports/chatgpt-imports/", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(new FormData(form).entries())),
    })
        .then(result => {
            form.reset();
            document.getElementById("documentChatGPTSource").value = "ChatGPT";
            showFormFeedback("documentChatGPTFeedback", `Imported ${result.title || "ChatGPT context"} for review.`, "success");
            return loadDocumentCenter();
        })
        .catch(error => {
            Alfred.logClientIssue({
                module: "documents",
                category: "api",
                scope: "chatgpt_import",
                eventType: "chatgpt_import_failure",
                severity: "warning",
                message: error.message,
            });
            showFormFeedback("documentChatGPTFeedback", error.message, "danger");
        })
        .finally(() => {
            setDocumentCenterBusy(false);
            if (submitButton) {
                submitButton.disabled = false;
            }
        });
}

function runBatchUpload(config) {
    const { form, fileFieldName, feedbackId, emptyMessage, pendingText, uploadFile, summarizeResults, onSuccess } = config;
    const fileInput = form.elements[fileFieldName];
    const files = Array.from(fileInput?.files || []);
    if (!files.length) {
        showFormFeedback(feedbackId, emptyMessage, "warning");
        return;
    }

    const submitButton = form.querySelector("button[type='submit']");
    if (submitButton) {
        submitButton.disabled = true;
    }

    Alfred.showUploadProgress(feedbackId, {
        phase: "preparing",
        percent: 0,
        current: 1,
        total: files.length,
    });

    Alfred.uploadFilesSequentially(
        files,
        (file, uploadContext) => uploadFile(file, Alfred.buildSingleFileFormData(form, fileFieldName, file), uploadContext),
        {
            onProgress: state => Alfred.showUploadProgress(feedbackId, state),
        },
    )
        .then(results => {
            const summary = summarizeResults(results);
            if (summary.failed?.length) {
                Alfred.logClientIssue({
                    module: "documents",
                    category: "api",
                    scope: fileFieldName,
                    eventType: "batch_upload_failure",
                    severity: summary.succeeded.length ? "warning" : "error",
                    message: summary.message,
                });
            }
            if (summary.succeeded?.length) {
                form.reset();
                Promise.resolve(onSuccess ? onSuccess(results) : null).catch(() => {});
            }
            showFormFeedback(feedbackId, summary.message, summary.tone);
        })
        .finally(() => {
            if (submitButton) {
                submitButton.disabled = false;
            }
        });
}

function summarizeStatementBatch(results) {
    const summary = Alfred.summarizeUploadBatch(results, { itemLabel: "statement", successVerb: "processed" });
    const importedCount = summary.succeeded.reduce((sum, result) => sum + Number(result.data?.imported_count || 0), 0);
    const skippedCount = summary.succeeded.reduce((sum, result) => sum + Number(result.data?.skipped_count || 0), 0);
    const metadataOnly = summary.succeeded.filter(result => Number(result.data?.imported_count || 0) === 0).length;
    const partialImports = summary.succeeded.filter(result => result.data?.upload?.extracted_payload?.preview_only).length;
    const reviewNote = summary.succeeded
        .map(result => result.data?.parser_notes)
        .find(note => note && String(note).trim());
    const extras = [];

    if (summary.succeeded.length) {
        extras.push(`${Alfred.formatNumber(importedCount, 0)} transactions imported`);
    }
    if (skippedCount) {
        extras.push(`${Alfred.formatNumber(skippedCount, 0)} duplicates skipped`);
    }
    if (metadataOnly) {
        extras.push(`${metadataOnly} retained as metadata-only upload${metadataOnly === 1 ? "" : "s"}`);
    }
    if (partialImports) {
        extras.push(`${partialImports} partial OCR import${partialImports === 1 ? "" : "s"} still deepening in background`);
    }
    if (metadataOnly && reviewNote) {
        extras.push(String(reviewNote));
    }

    return appendBatchExtras(summary, extras);
}

function summarizeLoanBatch(results) {
    const summary = Alfred.summarizeUploadBatch(results, { itemLabel: "loan document", successVerb: "processed" });
    const totalLoans = summary.succeeded.reduce((sum, result) => sum + Number(result.data?.loans?.length || 0), 0);
    const reviewCount = summary.succeeded.filter(result => result.data?.upload?.parser_status !== "parsed").length;
    const documentTypes = [...new Set(
        summary.succeeded
            .map(result => result.data?.document_type)
            .filter(Boolean)
            .map(formatDocType)
    )];
    const extras = [];

    if (summary.succeeded.length) {
        extras.push(`${Alfred.formatNumber(totalLoans, 0)} loan record${totalLoans === 1 ? "" : "s"} created or updated`);
    }
    if (reviewCount) {
        extras.push(`${reviewCount} saved for review`);
    }
    if (documentTypes.length) {
        extras.push(`types: ${documentTypes.join(", ")}`);
    }

    return appendBatchExtras(summary, extras);
}

function summarizeServiceBatch(results) {
    const summary = Alfred.summarizeUploadBatch(results, { itemLabel: "service file", successVerb: "imported" });
    const createdLogs = summary.succeeded.filter(result => result.data?.service_record).length;
    return appendBatchExtras(summary, createdLogs ? [`${createdLogs} service log${createdLogs === 1 ? "" : "s"} created`] : []);
}

function summarizeResumeBatch(results) {
    const summary = Alfred.summarizeUploadBatch(results, { itemLabel: "career file", successVerb: "uploaded" });
    const parsedCount = summary.succeeded.filter(result => result.data?.resume?.parser_status === "parsed").length;
    const reviewCount = summary.succeeded.length - parsedCount;
    const extras = [];

    if (parsedCount) {
        extras.push(`${parsedCount} parsed cleanly`);
    }
    if (reviewCount) {
        extras.push(`${reviewCount} marked for review`);
    }

    return appendBatchExtras(summary, extras, reviewCount && !summary.failed.length ? "warning" : summary.tone);
}

function summarizeCreditBatch(results) {
    const summary = Alfred.summarizeUploadBatch(results, { itemLabel: "credit report", successVerb: "uploaded" });
    const parsedCount = summary.succeeded.filter(result => result.data?.upload?.parser_status === "parsed").length;
    const reviewCount = summary.succeeded.length - parsedCount;
    const scoreCount = summary.succeeded.filter(result => result.data?.score?.score).length;
    const extras = [];

    if (scoreCount) {
        extras.push(`${scoreCount} official score snapshot${scoreCount === 1 ? "" : "s"} created`);
    }
    if (reviewCount) {
        extras.push(`${reviewCount} retained for review`);
    }

    return appendBatchExtras(summary, extras, reviewCount && !summary.failed.length ? "warning" : summary.tone);
}

function appendBatchExtras(summary, extras, tone = summary.tone) {
    if (!extras.length) {
        return { ...summary, tone };
    }
    return {
        ...summary,
        tone,
        message: `${summary.message} ${extras.join(" | ")}.`,
    };
}

function formatDocType(value) {
    if (!value) {
        return "";
    }
    return String(value)
        .replaceAll("_", " ")
        .replace(/\b\w/g, match => match.toUpperCase());
}

function showFormFeedback(elementId, message, tone) {
    const target = document.getElementById(elementId);
    target.className = `alert alert-${tone} mb-0`;
    target.textContent = message;
    target.classList.remove("d-none");
}

function submitDocumentCorrection(event, scope, id) {
    event.preventDefault();
    const form = event.currentTarget;
    const corrections = Object.fromEntries(new FormData(form).entries());
    snapshotReviewQueueState();
    setDocumentCenterBusy(true);
    Alfred.fetchJSON("/api/documents/review-queue/resolve/", {
        method: "POST",
        body: JSON.stringify({ scope, id, corrections }),
    })
        .then(() => loadDocumentCenter())
        .catch(error => {
            Alfred.logClientIssue({
                module: "documents",
                category: "api",
                scope,
                eventType: "correction_failure",
                severity: "error",
                message: error.message,
                payload: { document_id: id },
            });
            Alfred.upsertPageAlert("documentCenterRoot", error.message, "danger");
        })
        .finally(() => {
            setDocumentCenterBusy(false);
        });
}

function retryReviewItem(scope, id) {
    setDocumentCenterBusy(true);
    Alfred.fetchJSON("/api/documents/review-queue/retry/", {
        method: "POST",
        body: JSON.stringify({ scope, id }),
    })
        .then(() => loadDocumentCenter())
        .catch(error => {
            Alfred.logClientIssue({
                module: "documents",
                category: "api",
                scope,
                eventType: "retry_failure",
                severity: "error",
                message: error.message,
                payload: { document_id: id },
            });
            Alfred.upsertPageAlert("documentCenterRoot", error.message, "danger");
        })
        .finally(() => {
            setDocumentCenterBusy(false);
        });
}

function deleteDocumentCenterItem(scope, id) {
    if (!window.confirm("Delete this document and the data derived directly from it where ALFRED can track that linkage?")) {
        return;
    }
    setDocumentCenterBusy(true);
    Alfred.fetchJSON(`/api/documents/items/${scope}/${id}/`, { method: "DELETE" })
        .then(() => loadDocumentCenter())
        .catch(error => {
            Alfred.logClientIssue({
                module: "documents",
                category: "api",
                scope,
                eventType: "delete_failure",
                severity: "error",
                message: error.message,
                payload: { document_id: id },
            });
            Alfred.upsertPageAlert("documentCenterRoot", error.message, "danger");
        })
        .finally(() => {
            setDocumentCenterBusy(false);
        });
}

function maskAccount(value) {
    const digits = String(value || "").replace(/\D/g, "");
    if (digits.length < 4) {
        return value || "";
    }
    return `****${digits.slice(-4)}`;
}

function statementPreviewInfo(upload) {
    const payload = upload?.extracted_payload || {};
    const progress = payload.ocr_progress || {};
    const isPartial = Boolean(payload.preview_only || progress.is_partial);
    if (!isPartial) {
        return "";
    }
    const importedCount = Number(upload?.imported_count || payload.preview_transaction_count || 0);
    const processedPages = Number(progress.processed_pages || 0);
    const totalPages = Number(progress.total_pages || processedPages || 0);
    const parts = [];
    if (importedCount) {
        parts.push(`${Alfred.formatNumber(importedCount, 0)} preview row${importedCount === 1 ? "" : "s"} imported`);
    } else if (Number(payload.preview_transaction_count || 0)) {
        const previewCount = Number(payload.preview_transaction_count || 0);
        parts.push(`${Alfred.formatNumber(previewCount, 0)} OCR preview row${previewCount === 1 ? "" : "s"} detected`);
    } else {
        parts.push("partial OCR preview retained");
    }
    if (processedPages) {
        parts.push(`${processedPages}/${totalPages || processedPages} pages processed`);
    }
    return `Partial OCR import | ${parts.join(" | ")}`;
}

function formatAcceptedCorrections(item) {
    const corrections = item?.accepted_corrections || {};
    const entries = Object.entries(corrections).filter(([, value]) => value !== "" && value !== null && value !== undefined);
    if (!entries.length) {
        return "";
    }
    const labelMap = Object.fromEntries((item.review_fields || []).map(field => [field.name, field.label]));
    return entries.map(([key, value]) => {
        const label = labelMap[key] || formatDocType(key);
        return `<div><span class="muted">${Alfred.escapeHtml(label)}:</span> ${Alfred.escapeHtml(String(value))}</div>`;
    }).join("");
}

function renderReviewArtifacts(artifacts, formId = "", reviewFields = []) {
    if (!artifacts || (typeof artifacts === "object" && !Object.keys(artifacts).length)) {
        return "";
    }
    const steps = Array.isArray(artifacts.recovery_steps) ? artifacts.recovery_steps : [];
    const attempts = Array.isArray(artifacts.attempts) ? artifacts.attempts : [];
    const variants = Array.isArray(artifacts.attempted_variants) ? artifacts.attempted_variants : [];
    const pages = Array.isArray(artifacts.ocr_pages) ? artifacts.ocr_pages : [];
    const fieldCandidates = Array.isArray(artifacts.field_candidates) ? artifacts.field_candidates : [];
    const correctedFields = Array.isArray(artifacts.corrected_fields) ? artifacts.corrected_fields : [];
    const retryOutcome = artifacts.retry_outcome || {};
    const invoiceSummary = artifacts.invoice_summary || {};
    const overlaySummary = artifacts.overlay_summary || {};
    const editableFieldNames = new Set(reviewFields.map(field => field.name));
    const chips = [];
    if (artifacts.extraction_method) {
        chips.push(`<span class="chip-neutral">${Alfred.escapeHtml(formatDocType(String(artifacts.extraction_method).replace(/^repaired_/, "")))}</span>`);
    }
    if (artifacts.review_resolution) {
        chips.push(`<span class="chip-neutral">Resolution: ${Alfred.escapeHtml(formatDocType(artifacts.review_resolution))}</span>`);
    }
    steps.forEach(step => {
        if (step.step && step.status) {
            chips.push(`<span class="chip-neutral">${Alfred.escapeHtml(formatDocType(step.step))}: ${Alfred.escapeHtml(step.status)}</span>`);
        }
    });
    if (retryOutcome.state) {
        chips.push(`<span class="chip-neutral">Retry ${Alfred.escapeHtml(retryOutcome.state)}</span>`);
    }
    const noteLine = [
        attempts.length ? `${attempts.length} extractor path${attempts.length === 1 ? "" : "s"} scored` : "",
        variants.length ? `${variants.length} image variant${variants.length === 1 ? "" : "s"} tried` : "",
        pages.length ? `${pages.length} OCR page overlay${pages.length === 1 ? "" : "s"}` : "",
        fieldCandidates.length ? `${fieldCandidates.length} field candidate${fieldCandidates.length === 1 ? "" : "s"}` : "",
        correctedFields.length ? `${correctedFields.length} accepted correction${correctedFields.length === 1 ? "" : "s"}` : "",
        overlaySummary.low_confidence_regions ? `${overlaySummary.low_confidence_regions} low-confidence OCR region${Number(overlaySummary.low_confidence_regions) === 1 ? "" : "s"}` : "",
    ].filter(Boolean).join(" | ");
    const invoiceNote = invoiceSummary.line_item_count
        ? `Invoice signals: ${Alfred.formatNumber(invoiceSummary.line_item_count || 0, 0)} line item(s) | ${Alfred.formatNumber(invoiceSummary.parts_item_count || 0, 0)} part row(s) | ${Alfred.formatNumber(invoiceSummary.labour_item_count || 0, 0)} labour row(s)${invoiceSummary.recovered_edge_rows ? ` | ${Alfred.formatNumber(invoiceSummary.recovered_edge_rows, 0)} OCR edge row(s) recovered` : ""}${invoiceSummary.compact_ocr_rows ? ` | ${Alfred.formatNumber(invoiceSummary.compact_ocr_rows, 0)} compact row(s)` : ""}`
        : "";
    const candidateRows = fieldCandidates.slice(0, 8).map(candidate => {
        const fieldName = candidate.field_name || "";
        const canApply = formId && fieldName && editableFieldNames.has(fieldName);
        const source = [candidate.source || "", candidate.page ? `p${candidate.page}` : ""].filter(Boolean).join(" | ");
        return `
            <div class="d-flex justify-content-between gap-2 align-items-start border-top pt-2 mt-2">
                <div>
                    <div class="small"><strong>${Alfred.escapeHtml(candidate.label || formatDocType(candidate.field_type || "candidate"))}</strong>: ${Alfred.escapeHtml(String(candidate.value || ""))}</div>
                    <div class="muted small">${Alfred.escapeHtml(source)}${candidate.confidence ? ` | ${Math.round(Number(candidate.confidence || 0) * 100)}%` : ""}</div>
                    ${candidate.context ? `<div class="muted small">${Alfred.escapeHtml(candidate.context)}</div>` : ""}
                </div>
                ${canApply ? `<button class="btn btn-sm btn-outline-primary" type="button" data-form-id="${Alfred.escapeHtml(formId)}" data-field-name="${Alfred.escapeHtml(fieldName)}" data-field-value="${Alfred.escapeHtml(String(candidate.value || ""))}" onclick="fillReviewCandidate(this)">Use</button>` : ""}
            </div>
        `;
    }).join("");
    return `
        <details class="mt-3">
            <summary class="small fw-semibold">Review extraction evidence</summary>
            ${chips.length ? `<div class="chip-row mt-2">${chips.join("")}</div>` : ""}
            ${noteLine ? `<div class="muted small mt-2">${Alfred.escapeHtml(noteLine)}</div>` : ""}
            ${invoiceNote ? `<div class="muted small mt-2">${Alfred.escapeHtml(invoiceNote)}</div>` : ""}
            ${candidateRows ? `<div class="mt-2">${candidateRows}</div>` : ""}
            ${correctedFields.length ? `<div class="small mt-2"><strong>Accepted fields:</strong> ${correctedFields.map(item => Alfred.escapeHtml(formatDocType(item))).join(", ")}</div>` : ""}
            ${retryOutcome.retry_count ? `<div class="small mt-2"><strong>Retry outcome:</strong> attempt ${Alfred.escapeHtml(String(retryOutcome.retry_count))}${retryOutcome.resolution ? ` | ${Alfred.escapeHtml(formatDocType(retryOutcome.resolution))}` : ""}${retryOutcome.last_attempt_at ? ` | ${Alfred.escapeHtml(Alfred.formatDateTime(retryOutcome.last_attempt_at))}` : ""}</div>` : ""}
            ${artifacts.raw_text_excerpt ? `<pre class="small mt-2 mb-0" style="white-space: pre-wrap; overflow-wrap: anywhere;">${Alfred.escapeHtml(artifacts.raw_text_excerpt)}</pre>` : ""}
            ${attempts.length ? `<div class="small mt-2"><strong>Scored paths:</strong> ${attempts.map(item => `${Alfred.escapeHtml(item.method || "path")} ${Math.round(Number(item.quality || 0) * 100)}%`).join(" | ")}</div>` : ""}
            ${renderOcrOverlayPages(pages)}
        </details>
    `;
}

function fillReviewCandidate(button) {
    const form = document.getElementById(button?.dataset?.formId || "");
    if (!form) {
        return;
    }
    const field = form.querySelector(`[name="${button.dataset.fieldName}"]`);
    if (!field) {
        return;
    }
    field.value = button.dataset.fieldValue || "";
    field.dispatchEvent(new Event("input", { bubbles: true }));
    field.dispatchEvent(new Event("change", { bubbles: true }));
    field.focus({ preventScroll: true });
}

function renderOcrOverlayPages(pages) {
    if (!pages.length) {
        return "";
    }
    return `
        <div class="row g-3 mt-1">
            ${pages.map(page => {
                const width = Number(page.width || 0) || 1;
                const height = Number(page.height || 0) || 1;
                const boxes = (page.regions || []).map(region => {
                    const points = Array.isArray(region.bbox) ? region.bbox : [];
                    if (!points.length) {
                        return "";
                    }
                    const xs = points.map(point => Number(point[0] || 0));
                    const ys = points.map(point => Number(point[1] || 0));
                    const x = Math.min(...xs);
                    const y = Math.min(...ys);
                    const boxWidth = Math.max(...xs) - x;
                    const boxHeight = Math.max(...ys) - y;
                    const fieldMatches = Array.isArray(region.field_matches) ? region.field_matches : [];
                    const confidence = Number(region.confidence || 0);
                    const isLowConfidence = confidence > 0 && confidence < 0.55;
                    const fill = fieldMatches.length ? "rgba(37, 99, 235, 0.18)" : isLowConfidence ? "rgba(217, 119, 6, 0.18)" : "rgba(22, 163, 74, 0.15)";
                    const stroke = fieldMatches.length ? "rgba(37, 99, 235, 0.78)" : isLowConfidence ? "rgba(217, 119, 6, 0.78)" : "rgba(22, 163, 74, 0.65)";
                    return `<rect x="${((x / width) * 100).toFixed(2)}" y="${((y / height) * 100).toFixed(2)}" width="${((boxWidth / width) * 100).toFixed(2)}" height="${((boxHeight / height) * 100).toFixed(2)}" fill="${fill}" stroke="${stroke}" stroke-width="0.8"></rect>`;
                }).join("");
                const lines = (page.regions || []).slice(0, 3).map(region => {
                    const matches = Array.isArray(region.field_matches) && region.field_matches.length
                        ? ` | corrected: ${region.field_matches.map(item => formatDocType(item)).join(", ")}`
                        : "";
                    return `<div>${Alfred.escapeHtml(region.text || "")}${matches ? `<span class="muted">${Alfred.escapeHtml(matches)}</span>` : ""}</div>`;
                }).join("");
                return `
                    <div class="col-md-6">
                        <div class="mini-card h-100">
                            <div class="d-flex justify-content-between align-items-center gap-2">
                                <div class="fw-semibold small">Page ${Alfred.escapeHtml(String(page.page || 1))}</div>
                                <div class="muted small">${Alfred.escapeHtml(page.variant || "ocr")} ${page.rotation ? `| ${Alfred.escapeHtml(`${page.rotation}°`)}` : ""}</div>
                            </div>
                            <svg viewBox="0 0 100 140" class="w-100 mt-2" style="max-height: 10rem; border-radius: 0.8rem; background: linear-gradient(180deg, rgba(245,247,250,0.95), rgba(228,234,240,0.92));">
                                <rect x="7" y="5" width="86" height="130" rx="5" fill="rgba(255,255,255,0.95)" stroke="rgba(16,37,63,0.12)"></rect>
                                <g transform="translate(7 5) scale(0.86 0.93)">${boxes}</g>
                            </svg>
                            ${page.preview ? `<div class="small mt-2">${Alfred.escapeHtml(page.preview)}</div>` : ""}
                            ${lines ? `<div class="muted small mt-2">${lines}</div>` : ""}
                        </div>
                    </div>
                `;
            }).join("")}
        </div>
    `;
}

window.retryReviewItem = retryReviewItem;
window.deleteDocumentCenterItem = deleteDocumentCenterItem;
window.submitDocumentCorrection = submitDocumentCorrection;
window.fillReviewCandidate = fillReviewCandidate;
