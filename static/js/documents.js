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
            const reviewQueue = payload.reviewQueue || { results: [] };
            const diagnostics = payload.diagnostics || { results: [] };

            hydrateVehicleProfiles(bikeDashboard.bike_profiles || []);
            renderDocumentSummary(statementUploads, loanUploads, bikeDashboard.bike_documents || [], careerFiles, creditUploads);
            renderStatementUploads(statementUploads);
            renderLoanUploads(loanUploads);
            renderVehicleDocuments(bikeDashboard.bike_documents || []);
            renderCareerFiles(careerFiles);
            renderCreditUploads(creditUploads);
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
        reviewQueue: "Review queue",
        diagnostics: "Diagnostics",
    };
    return labels[key] || key;
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

function renderDocumentSummary(statementUploads, loanUploads, vehicleDocuments, resumes, creditUploads) {
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
    Alfred.setTextIfChanged("documentCenterMeta", statementUploads.length || loanUploads.length || vehicleDocuments.length || resumes.length || creditUploads.length
        ? `${statementUploads.length} statements | ${loanUploads.length} loan docs | ${vehicleDocuments.length} vehicle docs | ${resumes.length} career files | ${creditUploads.length} credit reports tracked`
        : "No recent uploads yet.");

    const cards = [
        { label: "Statements", value: statementUploads.length, copy: "Uploaded financial statements tracked here" },
        { label: "Loan Docs", value: loanUploads.length, copy: "Imported sanction letters, schedules, and statements" },
        { label: "Vehicle Docs", value: vehicleDocuments.length, copy: "Compliance and service-supporting files" },
        { label: "Career Files", value: resumes.length, copy: "Resume-based career intelligence inputs" },
        { label: "Credit Reports", value: creditUploads.length, copy: "Uploaded bureau reports retained with parser status" },
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
        return `
            <div class="mini-card timeline-card">
                <div class="d-flex justify-content-between gap-3 align-items-start">
                    <div>
                        <div class="fw-semibold">${Alfred.escapeHtml(item.file_name)}</div>
                        <div class="muted small">${Alfred.escapeHtml(formatDocType(item.scope))} | ${(Number(item.parse_confidence || 0) * 100).toFixed(0)}% | ${Alfred.escapeHtml(item.parser_status || "unknown")}</div>
                        <div class="small mt-2">${Alfred.escapeHtml(item.summary || "")}</div>
                        ${item.notes ? `<div class="small mt-2">${Alfred.escapeHtml(item.notes)}</div>` : ""}
                        ${acceptedCorrections ? `<div class="small mt-2"><strong>Accepted correction:</strong><div class="mt-1">${acceptedCorrections}</div></div>` : ""}
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
                                    <input
                                        id="${formId}-${field.name}"
                                        name="${field.name}"
                                        type="${field.type === "number" ? "number" : (field.type === "date" ? "date" : "text")}"
                                        class="form-control"
                                        value="${Alfred.escapeHtml(String(getReviewFieldValue(state, field.name, item.fields?.[field.name] ?? "")))}"
                                    >
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

window.retryReviewItem = retryReviewItem;
window.deleteDocumentCenterItem = deleteDocumentCenterItem;
window.submitDocumentCorrection = submitDocumentCorrection;
