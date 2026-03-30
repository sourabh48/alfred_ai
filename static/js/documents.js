document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("documentCenterRoot")) {
        return;
    }

    document.getElementById("documentStatementForm").addEventListener("submit", submitStatementUpload);
    document.getElementById("documentLoanForm").addEventListener("submit", submitLoanUpload);
    document.getElementById("documentVehicleForm").addEventListener("submit", submitVehicleDocument);
    document.getElementById("documentServiceForm").addEventListener("submit", submitServiceDocument);
    document.getElementById("documentResumeForm").addEventListener("submit", submitResumeDocument);

    loadDocumentCenter();
    Alfred.enableLiveRefresh("documents-live", loadDocumentCenter, { rootId: "documentCenterRoot" });
});

function loadDocumentCenter() {
    return Promise.all([
        Alfred.fetchJSON("/api/expenses/uploads/"),
        Alfred.fetchJSON("/api/mobility/bike-service-dashboard/"),
        Alfred.fetchJSON("/api/career/dashboard/"),
    ])
        .then(([statementUploads, bikeDashboard, careerDashboard]) => {
            hydrateVehicleProfiles(bikeDashboard.bike_profiles || []);
            renderDocumentSummary(statementUploads || [], bikeDashboard.bike_documents || [], careerDashboard.latest_resume ? [careerDashboard.latest_resume] : []);
            renderStatementUploads(statementUploads || []);
            renderVehicleDocuments(bikeDashboard.bike_documents || []);
            renderCareerFiles(careerDashboard.latest_resume ? [careerDashboard.latest_resume] : []);
            Alfred.clearPageAlert("documentCenterRoot");
        })
        .catch(error => {
            Alfred.upsertPageAlert("documentCenterRoot", error.message, "danger");
        });
}

function hydrateVehicleProfiles(profiles) {
    ["documentVehicleProfile", "documentServiceProfile"].forEach(id => {
        const target = document.getElementById(id);
        target.innerHTML = profiles.length
            ? profiles.map(profile => `<option value="${profile.id}">${Alfred.escapeHtml(profile.display_name)}</option>`).join("")
            : `<option value="">Add a vehicle profile first</option>`;
    });
}

function renderDocumentSummary(statementUploads, vehicleDocuments, resumes) {
    const recentConfidence = [
        ...statementUploads.map(item => Number(item.parse_confidence || 0)),
        ...vehicleDocuments.map(item => Number(item.parse_confidence || 0)),
        ...resumes.map(item => Number(item.parse_confidence || 0)),
    ].filter(value => value > 0);
    const avgConfidence = recentConfidence.length
        ? Math.round((recentConfidence.reduce((sum, value) => sum + value, 0) / recentConfidence.length) * 100)
        : 0;

    document.getElementById("documentConfidenceValue").textContent = `${avgConfidence}%`;
    document.getElementById("documentCenterMeta").textContent = statementUploads.length || vehicleDocuments.length || resumes.length
        ? `${statementUploads.length} statements | ${vehicleDocuments.length} vehicle docs | ${resumes.length} career files tracked`
        : "No recent uploads yet.";

    const cards = [
        { label: "Statements", value: statementUploads.length, copy: "Uploaded financial statements tracked here" },
        { label: "Vehicle Docs", value: vehicleDocuments.length, copy: "Compliance and service-supporting files" },
        { label: "Career Files", value: resumes.length, copy: "Resume-based career intelligence inputs" },
        { label: "Parser Avg", value: `${avgConfidence}%`, copy: "Average parser confidence across recent uploads" },
    ];
    document.getElementById("documentCenterCards").innerHTML = cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${Alfred.escapeHtml(card.label)}</p>
            <h2 class="metric-value">${Alfred.escapeHtml(String(card.value))}</h2>
            <p class="metric-caption">${Alfred.escapeHtml(card.copy)}</p>
        </article>
    `).join("");
}

function renderStatementUploads(items) {
    const target = document.getElementById("documentStatementList");
    if (!items.length) {
        target.innerHTML = `<div class="empty-state">No uploaded statements yet.</div>`;
        return;
    }

    target.innerHTML = items.slice(0, 8).map(item => `
        <div class="mini-card">
            <div class="fw-semibold">${Alfred.escapeHtml(item.file_name)}</div>
            <div class="muted small">${Alfred.escapeHtml((item.source || "").replaceAll("_", " "))} | ${(Number(item.parse_confidence || 0) * 100).toFixed(0)}% | ${Alfred.formatDateTime(item.uploaded_at)}</div>
            <div class="muted small mt-2">${Alfred.escapeHtml(item.parser_status_label || item.parser_status || "Unknown")} | ${Alfred.formatNumber(item.imported_count || 0, 0)} imported rows</div>
        </div>
    `).join("");
}

function renderVehicleDocuments(items) {
    const target = document.getElementById("documentVehicleList");
    if (!items.length) {
        target.innerHTML = `<div class="empty-state">No vehicle documents uploaded yet.</div>`;
        return;
    }

    target.innerHTML = items.slice(0, 8).map(item => `
        <div class="mini-card">
            <div class="fw-semibold">${Alfred.escapeHtml(item.document_type_label || item.document_type)}</div>
            <div class="muted small">${Alfred.escapeHtml(item.bike_name || item.bike_profile_name || "Vehicle")} | ${(Number(item.parse_confidence || 0) * 100).toFixed(0)}% | ${Alfred.formatDateTime(item.created_at)}</div>
            <div class="muted small mt-2">${Alfred.escapeHtml(item.verification_status_label || item.verification_status || "Unknown")}${item.expiry_date ? ` | Expires ${Alfred.formatDate(item.expiry_date)}` : ""}</div>
        </div>
    `).join("");
}

function renderCareerFiles(items) {
    const target = document.getElementById("documentResumeList");
    if (!items.length) {
        target.innerHTML = `<div class="empty-state">No career files uploaded yet.</div>`;
        return;
    }

    target.innerHTML = items.map(item => `
        <div class="mini-card">
            <div class="fw-semibold">${Alfred.escapeHtml(item.file_name || "Resume")}</div>
            <div class="muted small">${(Number(item.parse_confidence || 0) * 100).toFixed(0)}% | ${Alfred.escapeHtml(item.parser_status_label || item.parser_status || "Unknown")}</div>
            <div class="muted small mt-2">${Alfred.escapeHtml(item.summary || "")}</div>
        </div>
    `).join("");
}

function submitStatementUpload(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = new FormData(form);
    Alfred.fetchJSON("/api/expenses/import-statement/", { method: "POST", body: payload })
        .then(data => {
            form.reset();
            showFormFeedback("documentStatementFeedback", `${data.detail} ${data.upload?.parser_status_label || ""}`.trim(), "success");
            loadDocumentCenter();
        })
        .catch(error => showFormFeedback("documentStatementFeedback", error.message, "danger"));
}

function submitLoanUpload(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = new FormData(form);
    Alfred.fetchJSON("/api/loans/import-pdf/", { method: "POST", body: payload })
        .then(data => {
            form.reset();
            showFormFeedback(
                "documentLoanFeedback",
                `${data.message || "Loan document processed."} ${data.document_type ? `Type: ${data.document_type.replaceAll("_", " ")}.` : ""} ${data.parse_confidence ? `Confidence ${(Number(data.parse_confidence) * 100).toFixed(0)}%.` : ""}`.trim(),
                "success"
            );
        })
        .catch(error => showFormFeedback("documentLoanFeedback", error.message, "danger"));
}

function submitVehicleDocument(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = new FormData(form);
    Alfred.fetchJSON("/api/mobility/bike-documents/upload/", { method: "POST", body: payload })
        .then(() => {
            form.reset();
            showFormFeedback("documentVehicleFeedback", "Vehicle document uploaded and parsed.", "success");
            loadDocumentCenter();
        })
        .catch(error => showFormFeedback("documentVehicleFeedback", error.message, "danger"));
}

function submitServiceDocument(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = new FormData(form);
    Alfred.fetchJSON("/api/mobility/bike-services/import/", { method: "POST", body: payload })
        .then(() => {
            form.reset();
            showFormFeedback("documentServiceFeedback", "Service bill imported and converted into a service log.", "success");
            loadDocumentCenter();
        })
        .catch(error => showFormFeedback("documentServiceFeedback", error.message, "danger"));
}

function submitResumeDocument(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = new FormData(form);
    Alfred.fetchJSON("/api/career/resumes/upload/", { method: "POST", body: payload })
        .then(data => {
            form.reset();
            const resume = data.resume || {};
            const confidence = resume.parse_confidence != null ? ` Confidence ${(Number(resume.parse_confidence || 0) * 100).toFixed(0)}%.` : "";
            const status = resume.parser_status_label ? ` Status: ${resume.parser_status_label}.` : "";
            showFormFeedback("documentResumeFeedback", `Resume uploaded.${status}${confidence}`.trim(), resume.parser_status === "parsed" ? "success" : "warning");
            loadDocumentCenter();
        })
        .catch(error => showFormFeedback("documentResumeFeedback", error.message, "danger"));
}

function showFormFeedback(elementId, message, tone) {
    const target = document.getElementById(elementId);
    target.className = `alert alert-${tone} mb-0`;
    target.textContent = message;
    target.classList.remove("d-none");
}
