let bikeServiceCostChart;
let bikeServiceMixChart;
let bikeServiceIssueChart;

const bikeState = {
    profiles: [],
    catalog: [],
};

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("bikeServiceRoot")) {
        return;
    }

    document.getElementById("bikeProfileForm").addEventListener("submit", submitBikeProfile);
    document.getElementById("bikeCatalogSelect").addEventListener("change", syncCatalogIntoProfileForm);
    document.getElementById("bikeServiceImportForm").addEventListener("submit", submitBikeServiceImport);
    document.getElementById("bikeServiceRecordForm").addEventListener("submit", submitBikeServiceRecord);
    document.getElementById("bikeIssueForm").addEventListener("submit", submitBikeIssue);
    document.getElementById("bikeDocumentForm").addEventListener("submit", submitBikeDocumentUpload);
    document.getElementById("bikeConditionForm").addEventListener("submit", submitBikeCondition);
    ["bikeServiceProfile", "bikeConditionProfile", "bikeIssueProfile"].forEach(id => {
        document.getElementById(id).addEventListener("change", syncSelectedProfileIntoForms);
    });

    setBikeServiceDefaults();
    loadBikeServiceDashboard();
    Alfred.enableLiveRefresh("bike-service-live", loadBikeServiceDashboard, { rootId: "bikeServiceRoot" });
});

function loadBikeServiceDashboard() {
    return Alfred.fetchJSON("/api/mobility/bike-service-dashboard/")
        .then(data => {
            bikeState.profiles = data.bike_profiles || [];
            bikeState.catalog = data.bike_catalog || [];
            showBikeServiceAlert("", "secondary");
            renderBikeServiceHero(data.summary || {});
            renderBikeServiceSummary(data.summary || {});
            renderBikeProfileList(bikeState.profiles);
            renderBikeProfile(data.bike_profile || {});
            renderBikeCompliance(data.document_compliance || []);
            renderServiceHistorySummary(data.service_history_summary || {});
            renderPartInsights(data.part_insights || []);
            renderBikeServiceTasks(data.pending_tasks || []);
            renderBikeServiceObservations(data.observations || [], data.suggestions || []);
            renderBikeServiceBrief(data.service_center_brief || {});
            renderBikeServiceLogs(data.bike_services || []);
            renderBikeIssues(data.bike_issues || []);
            renderBikeDocuments(data.bike_documents || []);
            renderBikeConditions(data.bike_conditions || []);
            hydrateBikeCatalog();
            hydrateBikeProfileSelectors();
            hydrateTravelPlanOptions(data.travel_plans || []);
            renderBikeCharts(data.charts || {});
        })
        .catch(error => showBikeServiceAlert(error.message, "danger"));
}

function renderBikeServiceHero(summary) {
    const nextValue = document.getElementById("bikeServiceNextValue");
    const nextMeta = document.getElementById("bikeServiceNextMeta");
    nextValue.textContent = summary.next_service_date ? Alfred.formatDate(summary.next_service_date) : "No due date";
    nextMeta.textContent = summary.next_service_km
        ? `Next checkpoint at ${Alfred.formatNumber(summary.next_service_km, 0)} km`
        : "Upload a service bill or log a manual service to activate due-date tracking.";
    document.getElementById("bikeServiceProjectionMeta").textContent = `Projected service cost: ${Alfred.formatCurrency(summary.projected_next_service_cost || 0)}`;
}

function renderBikeServiceSummary(summary) {
    const cards = [
        ["Lifetime Service Spend", Alfred.formatCurrency(summary.total_service_cost || 0), `${Alfred.formatNumber(summary.service_count || 0, 0)} service logs | ${Alfred.formatCurrency(summary.annual_service_cost || 0)} this year`],
        ["Trip Costing", Alfred.formatCurrency(summary.trip_cost_total || 0), `${Alfred.formatNumber(summary.trip_distance_total || 0, 1)} km | ${summary.trip_cost_per_km ? `${Alfred.formatCurrency(summary.trip_cost_per_km)} / km` : "No cost/km yet"}`],
        ["Compliance", `${Alfred.formatNumber(summary.document_compliance_score || 0, 0)}/100`, `${Alfred.formatNumber(summary.expiring_documents || 0, 0)} expiring | ${Alfred.formatNumber(summary.missing_required_documents || 0, 0)} missing required`],
        ["Mileage / Range", summary.expected_mileage_kmpl ? `${Alfred.formatNumber(summary.expected_mileage_kmpl, 1)} kmpl` : "No estimate", summary.estimated_range_km ? `${Alfred.formatNumber(summary.estimated_range_km, 0)} km per tank` : "Add a bike model to estimate range"],
    ];

    document.getElementById("bikeServiceSummaryCards").innerHTML = cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card[0]}</p>
            <h2 class="metric-value">${card[1]}</h2>
            <p class="metric-caption">${card[2]}</p>
        </article>
    `).join("");
}

function renderBikeProfileList(items) {
    const target = document.getElementById("bikeProfileList");
    target.innerHTML = items.length ? items.map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between gap-3 align-items-start">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.display_name)} ${item.is_primary ? `<span class="muted small">primary</span>` : ""}</div>
                    <div class="muted small">${Alfred.escapeHtml(item.vehicle_type_label || "Vehicle")} | ${Alfred.escapeHtml(item.make || "Unknown make")} | ${Alfred.escapeHtml(item.bike_class || "Unknown class")} | ${Alfred.escapeHtml(item.verification_status_label || "Custom")}</div>
                    <div class="muted small">${item.vehicle_number ? Alfred.escapeHtml(item.vehicle_number) : "Vehicle number not saved"}${item.expected_mileage_kmpl ? ` | ${Alfred.formatNumber(item.expected_mileage_kmpl, 1)} kmpl` : ""}</div>
                    <div class="muted small">${Alfred.escapeHtml(item.usage_pattern_label || "Personal / Lifestyle")}${item.estimated_market_value ? ` | ${Alfred.formatCurrency(item.estimated_market_value)}` : ""}</div>
                </div>
                <button class="btn btn-sm btn-outline-danger" type="button" onclick="deleteBikeProfile(${item.id})">Delete</button>
            </div>
        </div>
    `).join("") : `<div class="empty-state">No vehicle profiles saved yet. Add one to activate document parsing and vehicle-specific intelligence.</div>`;
}

function renderBikeProfile(profile) {
    const target = document.getElementById("bikeProfilePanel");
    const mods = profile.performance_modifications || [];
    const rows = [
        ["Vehicle", profile.bike_name || "Not set"],
        ["Vehicle type", profile.vehicle_type || "Not set"],
        ["Vehicle number", profile.vehicle_number || "Not set"],
        ["Make / class", [profile.make, profile.bike_class].filter(Boolean).join(" | ") || "No catalog match yet"],
        ["Usage", profile.usage_pattern || "Not set"],
        ["Market value", profile.estimated_market_value ? Alfred.formatCurrency(profile.estimated_market_value) : "Not set"],
        ["Utility income", profile.monthly_income_support ? Alfred.formatCurrency(profile.monthly_income_support) : "Not set"],
        ["Engine / tank", profile.engine_cc ? `${Alfred.formatNumber(profile.engine_cc, 0)} cc | ${Alfred.formatNumber(profile.fuel_tank_capacity_l || 0, 1)} L` : "Not available yet"],
        ["Expected mileage", profile.expected_mileage_kmpl ? `${Alfred.formatNumber(profile.expected_mileage_kmpl, 1)} kmpl` : "Heuristic unavailable"],
        ["Estimated range", profile.estimated_range_km ? `${Alfred.formatNumber(profile.estimated_range_km, 0)} km / tank` : "No range estimate"],
        ["Service interval", profile.service_interval_km ? `${Alfred.formatNumber(profile.service_interval_km, 0)} km | ${Alfred.formatNumber(profile.service_interval_days || 0, 0)} days` : "Not available"],
        ["Optimal cruising", profile.optimal_cruising_speed_kmph ? `${Alfred.formatNumber(profile.optimal_cruising_speed_kmph, 0)} km/h` : "No estimate"],
        ["Insurance", profile.insurance_expiry ? `${Alfred.formatDate(profile.insurance_expiry)} | ${profile.insurance_status}` : (profile.insurance_status || "Missing")],
        ["PUC", profile.puc_expiry ? `${Alfred.formatDate(profile.puc_expiry)} | ${profile.puc_status}` : (profile.puc_status || "Missing")],
        ["Registration", profile.registration_number ? `${Alfred.escapeHtml(profile.registration_number)} | ${profile.registration_status}` : (profile.registration_status || "Missing")],
        ["Condition", profile.condition_score ? `${Alfred.formatNumber(profile.condition_score, 0)}/100 | ${profile.condition_status}` : (profile.condition_status || "No data")],
    ];

    target.innerHTML = rows.map(([label, value]) => `
        <div class="data-row">
            <div class="data-label">${label}</div>
            <div class="data-value">${Alfred.escapeHtml(String(value))}</div>
        </div>
    `).join("") + `
        <div class="detail-item">${Alfred.escapeHtml(profile.condition_assessment || "Log a condition snapshot to generate an AI condition assessment.")}</div>
        <div class="detail-item">${Alfred.escapeHtml(profile.modification_impact_note || "No performance modification signal yet.")}</div>
        <div class="detail-item">${mods.length ? `Detected modification signals: ${Alfred.escapeHtml(mods.join(", "))}` : "No performance-oriented modification keywords detected in your current service history."}</div>
        ${profile.official_source_url ? `<div class="detail-item"><a href="${profile.official_source_url}" target="_blank" rel="noopener">Open ${Alfred.escapeHtml(profile.official_source_name || "official")} source</a></div>` : ""}
    `;
}

function renderBikeCompliance(items) {
    const target = document.getElementById("bikeComplianceList");
    target.innerHTML = items.length ? items.map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between gap-3 align-items-start">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.label)} ${item.required ? `<span class="muted small">required</span>` : ""}</div>
                    <div class="muted small">${item.document_number ? Alfred.escapeHtml(item.document_number) : "Document number not saved"}</div>
                    <div class="muted small">${item.expiry_date ? `Expiry ${Alfred.formatDate(item.expiry_date)}` : "No expiry tracked"}</div>
                    <div class="muted small mt-2">${Alfred.escapeHtml(item.note || "No verification note yet.")}</div>
                </div>
                <span class="status-pill ${documentStatusTone(item.status)}">${Alfred.escapeHtml(item.status_label || item.status || "Unknown")}</span>
            </div>
        </div>
    `).join("") : `<div class="empty-state">No document compliance records yet.</div>`;
}

function renderServiceHistorySummary(summary) {
    const target = document.getElementById("bikeServiceHistorySummary");
    target.innerHTML = [
        ["Service logs", Alfred.formatNumber(summary.total_service_logs || 0, 0)],
        ["Imported bills", Alfred.formatNumber(summary.imported_service_bills || 0, 0)],
        ["Manual logs", Alfred.formatNumber(summary.manual_service_logs || 0, 0)],
        ["Avg service cost", Alfred.formatCurrency(summary.average_service_cost || 0)],
        ["Vehicle docs", Alfred.formatNumber(summary.document_count || 0, 0)],
        ["Condition snapshots", Alfred.formatNumber(summary.condition_snapshot_count || 0, 0)],
        ["Recurring centers", (summary.recurring_centers || []).join(", ") || "No pattern yet"],
    ].map(([label, value]) => `
        <div class="data-row">
            <div class="data-label">${label}</div>
            <div class="data-value">${Alfred.escapeHtml(String(value))}</div>
        </div>
    `).join("") + `
        <div class="detail-item">${Alfred.escapeHtml(summary.history_note || "Service-history intelligence will appear once a bill or manual log is stored.")}</div>
    `;
}

function renderPartInsights(items) {
    const target = document.getElementById("bikePartImpactBoard");
    if (!items.length) {
        target.innerHTML = `<div class="empty-state">No part-impact intelligence is available yet. Import a service bill or create a fault report first.</div>`;
        return;
    }

    target.innerHTML = items.map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between align-items-start gap-3 mb-2">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.label)}</div>
                    <div class="muted small">${Alfred.escapeHtml(item.impact_area || "")}</div>
                </div>
                <span class="status-pill ${partStatusTone(item.status)}">${Alfred.escapeHtml(item.status_label || item.status || "Watch")}</span>
            </div>
            <div class="muted small mb-2">${Alfred.escapeHtml(item.performance_effect || "")}</div>
            <div class="chip-row mb-2">
                <span class="chip-neutral">Confidence ${Alfred.formatNumber((Number(item.confidence || 0) * 100), 0)}%</span>
                <span class="chip-neutral">${Alfred.formatNumber(item.service_count || 0, 0)} service hits</span>
                <span class="chip-neutral">${Alfred.formatNumber(item.issue_count || 0, 0)} issue signals</span>
                ${item.last_service_date ? `<span class="chip-neutral">Last ${Alfred.formatDate(item.last_service_date)}</span>` : `<span class="chip-neutral">No logged service yet</span>`}
            </div>
            ${item.days_since_service != null ? `<div class="muted small">Days since service: ${Alfred.formatNumber(item.days_since_service, 0)}</div>` : ""}
            ${item.km_since_service != null ? `<div class="muted small">Km since service: ${Alfred.formatNumber(item.km_since_service, 0)}</div>` : ""}
            <div class="muted small mt-2"><strong>Recommended action:</strong> ${Alfred.escapeHtml(item.recommended_action || "")}</div>
            <div class="muted small mt-2">${(item.evidence || []).map(entry => Alfred.escapeHtml(entry)).join(" | ")}</div>
        </div>
    `).join("");
}

function renderBikeDocuments(items) {
    const target = document.getElementById("bikeDocumentList");
    target.innerHTML = items.length ? items.map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between gap-3 align-items-start">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.document_type_label)} <span class="muted small">${Alfred.escapeHtml(item.bike_name)}</span></div>
                    <div class="muted small">${Alfred.escapeHtml(item.issuer || "Issuer not detected")}${item.document_number ? ` | ${Alfred.escapeHtml(item.document_number)}` : ""}</div>
                    <div class="muted small">${item.issue_date ? `Issued ${Alfred.formatDate(item.issue_date)}` : "Issue date not detected"}${item.expiry_date ? ` | Expires ${Alfred.formatDate(item.expiry_date)}` : ""}</div>
                    <div class="muted small">${Alfred.escapeHtml(item.verification_status_label)} | ${Alfred.escapeHtml(item.parser_status_label || "Parsed")}${item.parse_confidence ? ` | confidence ${Alfred.formatNumber(item.parse_confidence * 100, 0)}%` : ""}</div>
                    ${item.parser_notes ? `<div class="muted small mt-2">${Alfred.escapeHtml(item.parser_notes)}</div>` : ""}
                    ${item.document_url ? `<div class="mt-2"><a href="${item.document_url}" target="_blank" rel="noopener">Open document</a></div>` : ""}
                </div>
                <div class="text-end">
                    ${item.premium_amount ? `<strong>${Alfred.formatCurrency(item.premium_amount)}</strong><div class="muted small">premium/cost</div>` : ""}
                    <div class="mt-2"><button class="btn btn-sm btn-outline-danger" type="button" onclick="deleteBikeDocument(${item.id})">Delete</button></div>
                </div>
            </div>
        </div>
    `).join("") : `<div class="empty-state">No bike documents saved yet.</div>`;
}

function renderBikeConditions(items) {
    const target = document.getElementById("bikeConditionList");
    target.innerHTML = items.length ? items.map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between gap-3 align-items-start">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.bike_name)} <span class="muted small">${Alfred.escapeHtml(item.overall_status_label)}</span></div>
                    <div class="muted small">${formatMaybeDateTime(item.captured_at)}${item.odometer_km ? ` | ${Alfred.formatNumber(item.odometer_km, 0)} km` : ""}</div>
                    <div class="chip-row mt-2">
                        <span class="chip-neutral">Engine ${Alfred.escapeHtml(item.engine_status_label)}</span>
                        <span class="chip-neutral">Brakes ${Alfred.escapeHtml(item.brake_status_label)}</span>
                        <span class="chip-neutral">Tyres ${Alfred.escapeHtml(item.tyre_status_label)}</span>
                    </div>
                    ${item.ai_assessment ? `<div class="muted small mt-2">${Alfred.escapeHtml(item.ai_assessment)}</div>` : ""}
                </div>
                <div class="text-end">
                    <strong>${Alfred.formatNumber(item.overall_score || 0, 0)}/100</strong>
                    <div class="mt-2"><button class="btn btn-sm btn-outline-danger" type="button" onclick="deleteBikeCondition(${item.id})">Delete</button></div>
                </div>
            </div>
        </div>
    `).join("") : `<div class="empty-state">No bike condition snapshots yet.</div>`;
}

function renderBikeServiceTasks(tasks) {
    const target = document.getElementById("bikeServiceTasks");
    target.innerHTML = tasks.length ? tasks.map(task => `
        <div class="mini-card">
            <div class="d-flex justify-content-between gap-3">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(task.title)}</div>
                    <div class="muted small">${Alfred.escapeHtml(task.note || "")}</div>
                </div>
                <div class="text-end">
                    <span class="status-pill ${statusTone(task.priority)}">${Alfred.escapeHtml(task.priority || "low")}</span>
                    <div class="muted small mt-2">${task.due_at ? formatMaybeDateTime(task.due_at) : "No explicit due time"}</div>
                </div>
            </div>
        </div>
    `).join("") : `<div class="empty-state">No pending tasks. Upload a bill, document, or fault report to activate the planner.</div>`;
}

function renderBikeServiceObservations(observations, suggestions) {
    const target = document.getElementById("bikeServiceObservations");
    const items = observations.concat(suggestions).slice(0, 6);
    target.innerHTML = items.length ? items.map(item => `<div class="detail-item">${Alfred.escapeHtml(item)}</div>`).join("") : `<div class="empty-state">No observations yet.</div>`;
}

function renderBikeServiceBrief(brief) {
    const target = document.getElementById("bikeServiceBrief");
    const points = brief.talking_points || [];
    target.innerHTML = `
        <div class="detail-item">
            <div class="fw-semibold mb-2">Opening line</div>
            <div class="muted">${Alfred.escapeHtml(brief.opening || "No briefing available yet.")}</div>
        </div>
        <div class="detail-item">
            <div class="fw-semibold mb-2">What to tell the service center</div>
            ${points.length ? points.map(point => `<div class="muted small mb-2">${Alfred.escapeHtml(point)}</div>`).join("") : `<div class="muted">No active fault reports to brief yet.</div>`}
        </div>
        <div class="detail-item">
            <div class="fw-semibold">Projected linked issue cost</div>
            <div class="metric-value" style="font-size:1.5rem;">${Alfred.formatCurrency(brief.projected_total || 0)}</div>
        </div>
    `;
}

function renderBikeServiceLogs(items) {
    const target = document.getElementById("bikeServiceLogList");
    target.innerHTML = items.length ? items.map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between gap-3">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.bike_name)} <span class="muted small">${Alfred.escapeHtml(item.service_type_label)}</span></div>
                    <div class="muted small">${Alfred.formatDate(item.service_date)} | ${Alfred.formatNumber(item.odometer_km, 0)} km | ${Alfred.escapeHtml(item.service_center || "Service center not set")}</div>
                    <div class="muted small">${item.next_service_date ? `Next ${Alfred.formatDate(item.next_service_date)}` : "No next date"}${item.next_service_km ? ` | ${Alfred.formatNumber(item.next_service_km, 0)} km` : ""}</div>
                    <div class="muted small">${Alfred.escapeHtml(item.source_mode_label || "Manual")}${item.source_document_name ? ` | ${Alfred.escapeHtml(item.source_document_name)}` : ""}</div>
                    ${item.extracted_work_summary ? `<div class="muted small mt-2">${Alfred.escapeHtml(item.extracted_work_summary)}</div>` : ""}
                    ${item.notes ? `<div class="muted small mt-2">${Alfred.escapeHtml(item.notes)}</div>` : ""}
                </div>
                <div class="text-end">
                    <strong>${Alfred.formatCurrency(item.cost || 0)}</strong>
                    <div class="mt-2"><button class="btn btn-sm btn-outline-danger" type="button" onclick="deleteBikeServiceRecord(${item.id})">Delete</button></div>
                </div>
            </div>
        </div>
    `).join("") : `<div class="empty-state">No bike service logs yet.</div>`;
}

function renderBikeIssues(items) {
    const target = document.getElementById("bikeIssueBoard");
    target.innerHTML = items.length ? items.map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between gap-3 align-items-start">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.title)}</div>
                    <div class="chip-row mt-2">
                        <span class="chip-neutral">${Alfred.escapeHtml(item.system_label)}</span>
                        <span class="chip-neutral">${Alfred.escapeHtml(item.status_label)}</span>
                        <span class="chip-neutral">${Alfred.escapeHtml(item.severity_label)}</span>
                    </div>
                    <div class="muted small mt-2">${formatMaybeDateTime(item.reported_at)}${item.next_action_at ? ` | next action ${formatMaybeDateTime(item.next_action_at)}` : ""}</div>
                    <div class="muted small mt-2"><strong>Fault report:</strong> ${Alfred.escapeHtml(item.symptom)}</div>
                    ${item.observation ? `<div class="muted small mt-2"><strong>Observation:</strong> ${Alfred.escapeHtml(item.observation)}</div>` : ""}
                    ${item.probable_cause ? `<div class="muted small mt-2"><strong>Probable cause:</strong> ${Alfred.escapeHtml(item.probable_cause)}</div>` : ""}
                    ${item.suggested_action ? `<div class="muted small mt-2"><strong>Suggestion:</strong> ${Alfred.escapeHtml(item.suggested_action)}</div>` : ""}
                    ${item.service_center_note ? `<div class="muted small mt-2"><strong>What to say:</strong> ${Alfred.escapeHtml(item.service_center_note)}</div>` : ""}
                </div>
                <div class="text-end" style="min-width: 130px;">
                    <strong>${Alfred.formatCurrency(item.projected_cost || 0)}</strong>
                    <div class="muted small">Projected</div>
                    <div class="mt-2"><button class="btn btn-sm btn-outline-danger" type="button" onclick="deleteBikeIssue(${item.id})">Delete</button></div>
                </div>
            </div>
        </div>
    `).join("") : `<div class="empty-state">No fault reports yet.</div>`;
}

function hydrateBikeCatalog() {
    const target = document.getElementById("bikeCatalogSelect");
    target.innerHTML = [`<option value="">Choose a known model or leave blank for custom</option>`].concat(
        bikeState.catalog.map(item => `<option value="${Alfred.escapeHtml(item.catalog_key)}">${Alfred.escapeHtml(item.display_name)}</option>`)
    ).join("");
}

function hydrateBikeProfileSelectors() {
    const options = bikeState.profiles.length
        ? bikeState.profiles.map(item => `<option value="${item.id}">${Alfred.escapeHtml(item.display_name)}${item.vehicle_type_label ? ` | ${Alfred.escapeHtml(item.vehicle_type_label)}` : ""}${item.vehicle_number ? ` | ${Alfred.escapeHtml(item.vehicle_number)}` : ""}</option>`).join("")
        : `<option value="">Add a vehicle profile first</option>`;

    ["bikeServiceProfile", "bikeServiceImportProfile", "bikeDocumentProfile", "bikeConditionProfile", "bikeIssueProfile"].forEach(id => {
        const target = document.getElementById(id);
        if (!target) {
            return;
        }
        const currentValue = target.value;
        target.innerHTML = options;
        target.disabled = !bikeState.profiles.length;
        if (bikeState.profiles.length) {
            target.value = bikeState.profiles.some(item => String(item.id) === String(currentValue)) ? currentValue : String(bikeState.profiles[0].id);
        }
    });
    syncSelectedProfileIntoForms();
}

function hydrateTravelPlanOptions(plans) {
    const target = document.getElementById("bikeIssueTravelPlan");
    const options = [`<option value="">Optional trip link</option>`].concat(
        plans.map(item => `<option value="${item.id}">${Alfred.escapeHtml(item.title)} | ${Alfred.escapeHtml(item.destination)}</option>`)
    );
    target.innerHTML = options.join("");
}

function syncCatalogIntoProfileForm(event) {
    const key = event.currentTarget.value;
    const match = bikeState.catalog.find(item => item.catalog_key === key);
    if (!match) {
        return;
    }
    document.getElementById("bikeProfileVehicleType").value = match.vehicle_type || "motorcycle";
    document.getElementById("bikeProfileDisplayName").value = match.display_name || "";
    document.getElementById("bikeProfileMake").value = match.make || "";
    document.getElementById("bikeProfileModelName").value = match.model_name || "";
    document.getElementById("bikeProfileVariant").value = match.variant || "";
    document.getElementById("bikeProfileUsagePattern").value = match.vehicle_type === "car" ? "essential" : "personal";
}

function syncSelectedProfileIntoForms() {
    const activeId = document.getElementById("bikeServiceProfile").value || document.getElementById("bikeConditionProfile").value || document.getElementById("bikeIssueProfile").value;
    const profile = bikeState.profiles.find(item => String(item.id) === String(activeId)) || bikeState.profiles[0];
    if (!profile) {
        return;
    }
    document.getElementById("bikeServiceProfileId").value = profile.id;
    document.getElementById("bikeServiceBikeName").value = profile.display_name || "";
    document.getElementById("bikeServiceVehicleNumber").value = profile.vehicle_number || "";
    document.getElementById("bikeConditionProfileId").value = profile.id;
    document.getElementById("bikeConditionBikeName").value = profile.display_name || "";
    document.getElementById("bikeConditionVehicleNumber").value = profile.vehicle_number || "";
    const issueProfile = document.getElementById("bikeIssueProfile");
    if (issueProfile && !issueProfile.value) {
        issueProfile.value = String(profile.id);
    }
}

function renderBikeCharts(charts) {
    const serviceLabels = charts.service_cost_trend?.labels || [];
    const serviceValues = charts.service_cost_trend?.values || [];
    const mixLabels = charts.cost_mix?.labels || [];
    const issueValues = charts.issue_breakdown?.values || [];

    bikeServiceCostChart = drawChart(bikeServiceCostChart, "bikeServiceCostChart", "bar", {
        labels: serviceLabels,
        datasets: [{ label: "Service cost", data: serviceValues, backgroundColor: "rgba(24, 88, 214, 0.72)", borderRadius: 12 }],
    });
    setChartMeta(
        "bikeServiceCostChartMeta",
        serviceLabels.length ? "Live service spend from stored service logs only." : "No live service-log data is available yet."
    );

    bikeServiceMixChart = drawChart(bikeServiceMixChart, "bikeServiceMixChart", "line", {
        labels: mixLabels,
        datasets: [
            { label: "Service", data: charts.cost_mix?.service_values || [], borderColor: "#1858d6", backgroundColor: "rgba(24,88,214,0.12)", fill: true, tension: 0.25 },
            { label: "Trips", data: charts.cost_mix?.trip_values || [], borderColor: "#ff825c", backgroundColor: "rgba(255,130,92,0.12)", fill: true, tension: 0.25 },
        ],
    });
    setChartMeta(
        "bikeServiceMixChartMeta",
        mixLabels.length ? "Trip and service cost lines are built from saved monthly history, not demo data." : "No trip/service cost history is available yet."
    );

    bikeServiceIssueChart = drawChart(bikeServiceIssueChart, "bikeServiceIssueChart", "doughnut", {
        labels: charts.issue_breakdown?.labels || [],
        datasets: [{ data: issueValues, backgroundColor: ["#148f63", "#d97904", "#c44a3d", "#7a0f1f"] }],
    });
    setChartMeta(
        "bikeServiceIssueChartMeta",
        issueValues.some(value => Number(value || 0) > 0) ? "Open fault distribution from current issue records." : "No open fault reports are active right now."
    );
}

function drawChart(existing, elementId, type, data) {
    if (existing) {
        existing.destroy();
    }
    return new Chart(document.getElementById(elementId), {
        type,
        data,
        options: {
            plugins: { legend: { position: "bottom" } },
            scales: type === "doughnut" ? {} : { y: { beginAtZero: true } },
        },
    });
}

function setChartMeta(elementId, message) {
    const target = document.getElementById(elementId);
    if (target) {
        target.textContent = message;
    }
}

function submitBikeProfile(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    payload.is_primary = payload.is_primary === "true";
    payload.estimated_market_value = Number(payload.estimated_market_value || 0);
    payload.monthly_income_support = Number(payload.monthly_income_support || 0);
    Alfred.fetchJSON("/api/mobility/bikes/", { method: "POST", body: JSON.stringify(payload) })
        .then(() => {
            form.reset();
            document.getElementById("bikeProfileVehicleType").value = "motorcycle";
            document.getElementById("bikeProfileUsagePattern").value = "personal";
            showBikeServiceFeedback("bikeProfileFeedback", "Vehicle profile saved and verified against the internal catalog.", "success");
            loadBikeServiceDashboard();
        })
        .catch(error => showBikeServiceFeedback("bikeProfileFeedback", error.message, "danger"));
}

function submitBikeServiceImport(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = new FormData(form);
    Alfred.fetchJSON("/api/mobility/bike-services/import/", { method: "POST", body: payload })
        .then(() => {
            form.reset();
            showBikeServiceFeedback("bikeServiceImportFeedback", "Service bill parsed and service log imported.", "success");
            loadBikeServiceDashboard();
        })
        .catch(error => showBikeServiceFeedback("bikeServiceImportFeedback", error.message, "danger"));
}

function submitBikeServiceRecord(event) {
    event.preventDefault();
    syncSelectedProfileIntoForms();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    payload.bike_profile = payload.bike_profile ? Number(payload.bike_profile) : Number(document.getElementById("bikeServiceProfile").value || 0) || null;
    payload.odometer_km = Number(payload.odometer_km || 0);
    payload.cost = Number(payload.cost || 0);
    payload.next_service_km = payload.next_service_km ? Number(payload.next_service_km) : null;
    payload.next_service_date = payload.next_service_date || null;

    Alfred.fetchJSON("/api/mobility/bike-services/", { method: "POST", body: JSON.stringify(payload) })
        .then(() => {
            form.reset();
            setBikeServiceDefaults();
            hydrateBikeProfileSelectors();
            showBikeServiceFeedback("bikeServiceRecordFeedback", "Manual service log saved.", "success");
            loadBikeServiceDashboard();
        })
        .catch(error => showBikeServiceFeedback("bikeServiceRecordFeedback", error.message, "danger"));
}

function submitBikeIssue(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    payload.bike_profile = payload.bike_profile ? Number(payload.bike_profile) : null;
    payload.travel_plan = payload.travel_plan ? Number(payload.travel_plan) : null;
    payload.odometer_km = payload.odometer_km ? Number(payload.odometer_km) : null;
    payload.actual_cost = payload.actual_cost ? Number(payload.actual_cost) : null;
    payload.next_action_at = payload.next_action_at || null;

    Alfred.fetchJSON("/api/mobility/bike-issues/", { method: "POST", body: JSON.stringify(payload) })
        .then(() => {
            form.reset();
            setBikeServiceDefaults();
            showBikeServiceFeedback("bikeIssueFeedback", "Fault report created and analyzed.", "success");
            loadBikeServiceDashboard();
        })
        .catch(error => showBikeServiceFeedback("bikeIssueFeedback", error.message, "danger"));
}

function submitBikeDocumentUpload(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = new FormData(form);
    Alfred.fetchJSON("/api/mobility/bike-documents/upload/", { method: "POST", body: payload })
        .then(() => {
            form.reset();
            showBikeServiceFeedback("bikeDocumentFeedback", "Document uploaded and parsed.", "success");
            loadBikeServiceDashboard();
        })
        .catch(error => showBikeServiceFeedback("bikeDocumentFeedback", error.message, "danger"));
}

function submitBikeCondition(event) {
    event.preventDefault();
    syncSelectedProfileIntoForms();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    payload.bike_profile = payload.bike_profile ? Number(payload.bike_profile) : Number(document.getElementById("bikeConditionProfile").value || 0) || null;
    payload.odometer_km = payload.odometer_km ? Number(payload.odometer_km) : null;

    Alfred.fetchJSON("/api/mobility/bike-conditions/", { method: "POST", body: JSON.stringify(payload) })
        .then(() => {
            form.reset();
            setBikeServiceDefaults();
            hydrateBikeProfileSelectors();
            showBikeServiceFeedback("bikeConditionFeedback", "Condition snapshot saved.", "success");
            loadBikeServiceDashboard();
        })
        .catch(error => showBikeServiceFeedback("bikeConditionFeedback", error.message, "danger"));
}

function deleteBikeProfile(id) {
    deleteBikeEntity(`/api/mobility/bikes/${id}/`, "Delete this vehicle profile? Linked service logs and documents will remain but lose the saved profile defaults.");
}

function deleteBikeServiceRecord(id) {
    deleteBikeEntity(`/api/mobility/bike-services/${id}/`, "Delete this bike service record?");
}

function deleteBikeIssue(id) {
    deleteBikeEntity(`/api/mobility/bike-issues/${id}/`, "Delete this bike issue report?");
}

function deleteBikeDocument(id) {
    deleteBikeEntity(`/api/mobility/bike-documents/${id}/`, "Delete this bike document?");
}

function deleteBikeCondition(id) {
    deleteBikeEntity(`/api/mobility/bike-conditions/${id}/`, "Delete this condition snapshot?");
}

function deleteBikeEntity(url, promptText) {
    if (!window.confirm(promptText)) {
        return;
    }
    Alfred.fetchJSON(url, { method: "DELETE" })
        .then(loadBikeServiceDashboard)
        .catch(error => showBikeServiceAlert(error.message, "danger"));
}

function showBikeServiceFeedback(elementId, message, tone) {
    const target = document.getElementById(elementId);
    target.className = `alert alert-${tone} mb-0`;
    target.textContent = message;
    target.classList.remove("d-none");
}

function showBikeServiceAlert(message, tone) {
    const target = document.getElementById("bikeServicePageAlert");
    target.className = message ? `alert alert-${tone} mb-4` : "d-none mb-4";
    target.textContent = message;
}

function statusTone(priority) {
    return priority === "critical" || priority === "high" ? "status-high" : (priority === "medium" ? "status-guarded" : "status-low");
}

function documentStatusTone(status) {
    if (status === "expired" || status === "missing") {
        return "status-high";
    }
    if (status === "expiring_soon" || status === "incomplete") {
        return "status-guarded";
    }
    return "status-low";
}

function partStatusTone(status) {
    if (status === "urgent" || status === "service") {
        return "status-high";
    }
    if (status === "watch") {
        return "status-guarded";
    }
    return "status-low";
}

function formatMaybeDateTime(value) {
    return value && value.includes("T") ? Alfred.formatDateTime(value) : Alfred.formatDate(value);
}

function setBikeServiceDefaults() {
    document.getElementById("bikeServiceDate").value = todayLocal();
    document.getElementById("bikeIssueReportedAt").value = currentDateTimeLocal();
    document.getElementById("bikeConditionCapturedAt").value = currentDateTimeLocal();
}

function todayLocal() {
    const now = new Date();
    const offsetMs = now.getTimezoneOffset() * 60000;
    return new Date(now.getTime() - offsetMs).toISOString().slice(0, 10);
}

function currentDateTimeLocal() {
    const now = new Date();
    const offsetMs = now.getTimezoneOffset() * 60000;
    return new Date(now.getTime() - offsetMs).toISOString().slice(0, 16);
}

window.deleteBikeProfile = deleteBikeProfile;
window.deleteBikeServiceRecord = deleteBikeServiceRecord;
window.deleteBikeIssue = deleteBikeIssue;
window.deleteBikeDocument = deleteBikeDocument;
window.deleteBikeCondition = deleteBikeCondition;
