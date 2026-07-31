let bikeServiceCostChart;
let bikeServiceMixChart;
let bikeServiceIssueChart;
let bikeMileageChart;
let bikeCatalogMakeTimer;
let bikeCatalogFetchToken = 0;
const BIKE_CATALOG_INTERACTION_HOLD_MS = 7000;

const bikeState = {
    profiles: [],
    catalog: [],
    catalogManufacturers: [],
    catalogRequestKey: "",
    editingProfileId: null,
    catalogInteractionUntil: 0,
};

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("bikeServiceRoot")) {
        return;
    }

    document.getElementById("bikeProfileForm").addEventListener("submit", submitBikeProfile);
    installBikeProfileFormGuards();
    document.getElementById("bikeProfileCancel").addEventListener("click", resetBikeProfileForm);
    document.getElementById("bikeCatalogMakeSelect").addEventListener("input", event => {
        lockBikeCatalogInteraction();
        scheduleBikeCatalogHydration(event);
    });
    document.getElementById("bikeCatalogMakeSelect").addEventListener("change", () => {
        lockBikeCatalogInteraction();
        hydrateBikeCatalog();
    });
    document.getElementById("bikeCatalogSelect").addEventListener("change", syncCatalogIntoProfileForm);
    document.getElementById("bikeProfileVehicleType").addEventListener("change", () => {
        lockBikeCatalogInteraction();
        hydrateBikeCatalogManufacturers();
    });
    document.getElementById("bikeServiceImportForm").addEventListener("submit", submitBikeServiceImport);
    document.getElementById("bikeServiceRecordForm").addEventListener("submit", submitBikeServiceRecord);
    document.getElementById("bikeRefillForm").addEventListener("submit", submitBikeRefill);
    document.getElementById("bikeIssueForm").addEventListener("submit", submitBikeIssue);
    document.getElementById("bikeDocumentForm").addEventListener("submit", submitBikeDocumentUpload);
    document.getElementById("bikeConditionForm").addEventListener("submit", submitBikeCondition);
    ["bikeServiceProfile", "bikeConditionProfile", "bikeIssueProfile", "bikeRefillProfile"].forEach(id => {
        document.getElementById(id).addEventListener("change", syncSelectedProfileIntoForms);
    });

    setBikeServiceDefaults();
    loadBikeServiceDashboard();
    Alfred.enableLiveRefresh("bike-service-live", loadBikeServiceDashboard, { rootId: "bikeServiceRoot", interactionHoldMs: 4500 });
});

function loadBikeServiceDashboard() {
    return Alfred.fetchJSON("/api/mobility/bike-service-dashboard/")
        .then(data => {
            const selectedMake = document.getElementById("bikeCatalogMakeSelect")?.value || "";
            const selectedCatalogKey = document.getElementById("bikeCatalogSelect")?.value || "";
            const catalogLocked = isBikeCatalogInteractionActive();
            const profileEditorLocked = isBikeProfileEditorDirty();
            const summary = data.summary || {};
            const profile = data.bike_profile || {};
            bikeState.profiles = data.bike_profiles || [];
            if (!catalogLocked) {
                bikeState.catalog = data.bike_catalog || [];
                bikeState.catalogRequestKey = "";
            }
            bikeState.catalogManufacturers = data.bike_catalog_manufacturers || buildCatalogManufacturersFromModels(bikeState.catalog);
            showBikeServiceAlert("", "secondary");
            renderBikeServiceHero(summary);
            renderBikeHeroSignals(summary, profile, data.pending_tasks || []);
            renderBikeServiceSummary(summary);
            renderBikeProfileList(bikeState.profiles);
            renderBikeProfile(profile);
            renderBikeMileageInsights(summary, profile, data.charts?.mileage_trend || {});
            renderBikeCompliance(data.document_compliance || []);
            renderServiceHistorySummary(data.service_history_summary || {});
            renderRouteWearPanel(data.route_wear || {});
            renderPartInsights(data.part_insights || []);
            renderBikeServiceTasks(data.pending_tasks || []);
            renderBikeServiceObservations(data.observations || [], data.suggestions || []);
            renderBikeServiceBrief(data.service_center_brief || {});
            renderBikeServiceLogs(data.bike_services || []);
            renderBikeRefills(data.bike_refills || []);
            renderBikeIssues(data.bike_issues || []);
            renderBikeDocuments(data.bike_documents || []);
            renderBikeConditions(data.bike_conditions || []);
            if (!catalogLocked) {
                hydrateBikeCatalogManufacturers(selectedMake, selectedCatalogKey);
            }
            hydrateBikeProfileSelectors();
            hydrateTravelPlanOptions(data.travel_plans || []);
            if (!profileEditorLocked) {
                syncBikeProfileEditor();
            }
            renderBikeCharts(data.charts || {});
        })
        .catch(error => showBikeServiceAlert(error.message, "danger"));
}

function renderBikeServiceHero(summary) {
    const nextValue = document.getElementById("bikeServiceNextValue");
    const nextMeta = document.getElementById("bikeServiceNextMeta");
    Alfred.setTextIfChanged(nextValue, summary.next_service_date ? Alfred.formatDate(summary.next_service_date) : "No due date");
    Alfred.setTextIfChanged(nextMeta, summary.next_service_km
        ? `Next checkpoint at ${Alfred.formatNumber(summary.next_service_km, 0)} km`
        : "Upload a service bill or log a manual service to activate due-date tracking.");
    const projectedCost = summary.projected_next_service_cost || 0;
    const adjustedCost = summary.route_adjusted_service_cost || projectedCost;
    const routeBuffer = summary.route_service_buffer || 0;
    Alfred.setTextIfChanged(
        "bikeServiceProjectionMeta",
        `Projected service cost: ${Alfred.formatCurrency(projectedCost)} | route-adjusted ${Alfred.formatCurrency(adjustedCost)} | buffer ${Alfred.formatCurrency(routeBuffer)}`
    );
}

function renderBikeHeroSignals(summary, profile, tasks) {
    const target = document.getElementById("bikeHeroSignalStrip");
    if (!target) {
        return;
    }

    const actualMileage = Number(summary.average_actual_mileage_kmpl || 0);
    const optimalMileage = Number(summary.expected_mileage_kmpl || 0);
    const openFaults = Number(summary.open_faults || 0);
    const criticalFaults = Number(summary.critical_faults || 0);
    const activeVehicleLabel = profile.bike_name || "No active vehicle";
    const activeVehicleMeta = [
        profile.vehicle_type_label || humanizeToken(profile.vehicle_type),
        profile.make,
        profile.model_name,
    ].filter(Boolean).join(" | ") || "Select or create a vehicle profile to activate service intelligence.";

    const signals = [
        {
            label: "Active Vehicle",
            value: activeVehicleLabel,
            meta: activeVehicleMeta,
        },
        {
            label: "Mileage Status",
            value: actualMileage ? `${Alfred.formatNumber(actualMileage, 1)} kmpl` : (optimalMileage ? `${Alfred.formatNumber(optimalMileage, 1)} kmpl` : "No benchmark"),
            meta: actualMileage && optimalMileage
                ? `${summary.mileage_gap_kmpl >= 0 ? "+" : ""}${Alfred.formatNumber(summary.mileage_gap_kmpl || 0, 1)} kmpl vs benchmark`
                : (optimalMileage ? "Real-world comparison starts after refill logs." : "Save a vehicle benchmark to compare mileage."),
        },
        {
            label: "Compliance",
            value: `${Alfred.formatNumber(summary.document_compliance_score || 0, 0)}/100`,
            meta: `${Alfred.formatNumber(summary.expiring_documents || 0, 0)} expiring | ${Alfred.formatNumber(summary.missing_required_documents || 0, 0)} missing required`,
        },
        {
            label: "Risk Watch",
            value: `${openFaults} open`,
            meta: `${criticalFaults} critical/high | ${Alfred.formatNumber(tasks.length || 0, 0)} pending task${Number(tasks.length || 0) === 1 ? "" : "s"}`,
        },
    ];

    Alfred.setHTMLIfChanged(target, signals.map(item => `
        <article class="hero-signal">
            <p class="hero-signal-label">${Alfred.escapeHtml(item.label)}</p>
            <p class="hero-signal-value">${Alfred.escapeHtml(String(item.value))}</p>
            <p class="hero-signal-meta">${Alfred.escapeHtml(item.meta)}</p>
        </article>
    `).join(""));
}

function renderBikeServiceSummary(summary) {
    const actualMileage = Number(summary.average_actual_mileage_kmpl || 0);
    const optimalMileage = Number(summary.expected_mileage_kmpl || 0);
    const mileageGap = Number(summary.mileage_gap_kmpl || 0);
    const mileageValue = actualMileage
        ? `${Alfred.formatNumber(actualMileage, 1)} kmpl`
        : (optimalMileage ? `${Alfred.formatNumber(optimalMileage, 1)} kmpl optimal` : "No estimate");
    const mileageCaption = actualMileage && optimalMileage
        ? `Optimal ${Alfred.formatNumber(optimalMileage, 1)} kmpl | gap ${mileageGap >= 0 ? "+" : ""}${Alfred.formatNumber(mileageGap, 1)}`
        : (optimalMileage
            ? `${Alfred.formatNumber(summary.refill_count || 0, 0)} refill logs | add refill history to compare`
            : "Add a model and refill logs to compare mileage");
    const cards = [
        ["Lifetime Service Spend", Alfred.formatCurrency(summary.total_service_cost || 0), `${Alfred.formatNumber(summary.service_count || 0, 0)} service logs | ${Alfred.formatCurrency(summary.annual_service_cost || 0)} this year`],
        ["Trip Costing", Alfred.formatCurrency(summary.trip_cost_total || 0), `${Alfred.formatNumber(summary.trip_distance_total || 0, 1)} km | ${summary.trip_cost_per_km ? `${Alfred.formatCurrency(summary.trip_cost_per_km)} / km` : "No cost/km yet"}`],
        ["Compliance", `${Alfred.formatNumber(summary.document_compliance_score || 0, 0)}/100`, `${Alfred.formatNumber(summary.expiring_documents || 0, 0)} expiring | ${Alfred.formatNumber(summary.missing_required_documents || 0, 0)} missing required`],
        ["Mileage vs Optimal", mileageValue, mileageCaption],
        [
            "Route Wear",
            summary.route_wear_index ? `${Alfred.formatNumber(summary.route_wear_index, 1)}/100` : "No route signal",
            `${Alfred.formatNumber(summary.route_distance_90d || 0, 1)} km in 90 days | buffer ${Alfred.formatCurrency(summary.route_service_buffer || 0)}`,
        ],
    ];

    Alfred.setHTMLIfChanged("bikeServiceSummaryCards", cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card[0]}</p>
            <h2 class="metric-value">${card[1]}</h2>
            <p class="metric-caption">${card[2]}</p>
        </article>
    `).join(""));
}

function renderBikeProfileList(items) {
    const target = document.getElementById("bikeProfileList");
    Alfred.setHTMLIfChanged(target, items.length ? items.map(item => `
        <div class="mini-card vehicle-mini-card ${bikeState.editingProfileId === item.id ? "is-editing" : ""}">
            <div class="d-flex justify-content-between gap-3 align-items-start">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.display_name)} ${item.is_primary ? `<span class="muted small">primary</span>` : ""}${bikeState.editingProfileId === item.id ? ` <span class="muted small">editing</span>` : ""}</div>
                    <div class="muted small">${Alfred.escapeHtml(item.vehicle_type_label || "Vehicle")} | ${Alfred.escapeHtml(item.make || "Unknown make")} | ${Alfred.escapeHtml(item.bike_class || "Unknown class")} | ${Alfred.escapeHtml(item.verification_status_label || "Custom")}</div>
                    <div class="muted small">${item.vehicle_number ? Alfred.escapeHtml(item.vehicle_number) : "Vehicle number not saved"}${item.expected_mileage_kmpl ? ` | ${Alfred.formatNumber(item.expected_mileage_kmpl, 1)} kmpl` : ""}</div>
                    <div class="muted small">${Alfred.escapeHtml(item.usage_pattern_label || "Personal / Lifestyle")}${item.estimated_market_value ? ` | ${Alfred.formatCurrency(item.estimated_market_value)}` : ""}</div>
                </div>
                <div class="list-actions">
                    <button class="btn btn-sm btn-outline-primary" type="button" onclick="editBikeProfile(${item.id})">Edit</button>
                    <button class="btn btn-sm btn-outline-danger" type="button" onclick="deleteBikeProfile(${item.id})">Delete</button>
                </div>
            </div>
        </div>
    `).join("") : `<div class="empty-state">No vehicle profiles saved yet. Add one to activate document parsing and vehicle-specific intelligence.</div>`);
}

function renderBikeProfile(profile) {
    const target = document.getElementById("bikeProfilePanel");
    const mods = profile.performance_modifications || [];
    const maintenanceGuidance = profile.maintenance_guidance || [];
    const stats = [
        {
            label: "Vehicle",
            value: profile.bike_name || "Not set",
            meta: [profile.vehicle_type_label || humanizeToken(profile.vehicle_type), profile.verification_status_label || "Custom profile"].filter(Boolean).join(" | "),
        },
        {
            label: "Make / Model",
            value: [profile.make, profile.model_name].filter(Boolean).join(" ") || "Not set",
            meta: profile.variant || "Variant not saved",
        },
        {
            label: "Vehicle Number",
            value: profile.vehicle_number || "Not set",
            meta: profile.registration_number || "Registration number not parsed",
        },
        {
            label: "Usage",
            value: profile.usage_pattern_label || humanizeToken(profile.usage_pattern) || "Not set",
            meta: profile.monthly_income_support ? `Utility support ${Alfred.formatCurrency(profile.monthly_income_support)}/month` : "No utility-income value linked",
        },
        {
            label: "Fuel / Tank",
            value: profile.fuel_type ? humanizeToken(profile.fuel_type) : "Not set",
            meta: profile.fuel_tank_capacity_l ? `${Alfred.formatNumber(profile.fuel_tank_capacity_l, 1)} L tank` : "Tank capacity not saved",
        },
        {
            label: "Engine / Class",
            value: profile.engine_cc ? `${Alfred.formatNumber(profile.engine_cc, 0)} cc` : "Not saved",
            meta: profile.bike_class ? humanizeToken(profile.bike_class) : "Class not saved",
        },
        {
            label: "Mileage Benchmark",
            value: profile.expected_mileage_kmpl ? `${Alfred.formatNumber(profile.expected_mileage_kmpl, 1)} kmpl` : "No benchmark",
            meta: profile.optimal_cruising_speed_kmph ? `Cruising ${Alfred.formatNumber(profile.optimal_cruising_speed_kmph, 0)} km/h` : "Cruising-speed target not saved",
        },
        {
            label: "Estimated Range",
            value: profile.estimated_range_km ? `${Alfred.formatNumber(profile.estimated_range_km, 0)} km` : "No range estimate",
            meta: profile.service_interval_km ? `Service every ${Alfred.formatNumber(profile.service_interval_km, 0)} km` : "Service interval not saved",
        },
        {
            label: "Insurance",
            value: profile.insurance_status || "Missing",
            meta: profile.insurance_expiry ? `Expires ${Alfred.formatDate(profile.insurance_expiry)}` : "Insurance expiry not saved",
        },
        {
            label: "PUC",
            value: profile.puc_status || "Missing",
            meta: profile.puc_expiry ? `Expires ${Alfred.formatDate(profile.puc_expiry)}` : "PUC expiry not saved",
        },
        {
            label: "Condition",
            value: profile.condition_score ? `${Alfred.formatNumber(profile.condition_score, 0)}/100` : "No score",
            meta: profile.condition_status || "No condition status yet",
        },
        {
            label: "Market Value",
            value: profile.estimated_market_value ? Alfred.formatCurrency(profile.estimated_market_value) : "Not set",
            meta: profile.is_primary ? "Primary tracked vehicle" : "Secondary tracked vehicle",
        },
    ];

    Alfred.setHTMLIfChanged(target, `
        <div class="surface-inset surface-inset-strong">
            <div class="panel-eyebrow">Live Vehicle Snapshot</div>
            ${renderInsightStatGrid(stats)}
        </div>
            <div class="detail-item">${Alfred.escapeHtml(profile.condition_assessment || "Log a condition snapshot to generate a condition assessment.")}</div>
        <div class="detail-item">${Alfred.escapeHtml(profile.modification_impact_note || "No performance modification signal yet.")}</div>
        <div class="detail-item">${mods.length ? `Detected modification signals: ${Alfred.escapeHtml(mods.join(", "))}` : "No performance-oriented modification keywords detected in your current service history."}</div>
        ${maintenanceGuidance.length ? `<div class="surface-inset mt-3"><div class="panel-eyebrow">Manufacturer Guidance</div>${maintenanceGuidance.map(item => `<div class="detail-item"><strong>${Alfred.escapeHtml(item.label || "")}:</strong> ${Alfred.escapeHtml(item.interval || "")}. ${Alfred.escapeHtml(item.note || "")}${item.source_url ? ` <a class="proof-link" href="${item.source_url}" target="_blank" rel="noopener">${Alfred.escapeHtml(item.source_name || "official proof")}</a>` : ""}</div>`).join("")}</div>` : ""}
        ${profile.official_source_url ? `<div class="detail-item">Official proof: <a class="proof-link" href="${profile.official_source_url}" target="_blank" rel="noopener">${Alfred.escapeHtml(profile.official_source_name || "official source")}</a></div>` : `<div class="detail-item">Official proof: no catalog proof linked yet for this vehicle.</div>`}
    `);
}

function renderBikeMileageInsights(summary, profile, mileageChart) {
    const target = document.getElementById("bikeMileageInsightPanel");
    const stats = [
        {
            label: "Latest Actual",
            value: summary.latest_actual_mileage_kmpl ? `${Alfred.formatNumber(summary.latest_actual_mileage_kmpl, 1)} kmpl` : "No refill data",
            meta: "Most recent full or partial refill checkpoint",
        },
        {
            label: "Average Actual",
            value: summary.average_actual_mileage_kmpl ? `${Alfred.formatNumber(summary.average_actual_mileage_kmpl, 1)} kmpl` : "Need refill history",
            meta: `${Alfred.formatNumber(summary.refill_count || 0, 0)} refill log${Number(summary.refill_count || 0) === 1 ? "" : "s"}`,
        },
        {
            label: "Saved Optimal",
            value: summary.expected_mileage_kmpl ? `${Alfred.formatNumber(summary.expected_mileage_kmpl, 1)} kmpl` : "No benchmark saved",
            meta: profile.official_source_name || "Custom profile benchmark",
        },
        {
            label: "Mileage Gap",
            value: summary.average_actual_mileage_kmpl && summary.expected_mileage_kmpl ? `${summary.mileage_gap_kmpl >= 0 ? "+" : ""}${Alfred.formatNumber(summary.mileage_gap_kmpl, 1)} kmpl` : "Not enough data",
            meta: summary.average_actual_mileage_kmpl && summary.expected_mileage_kmpl ? "Average actual vs saved benchmark" : "Gap starts after refill logging",
        },
        {
            label: "Fuel Spend",
            value: Alfred.formatCurrency(summary.fuel_cost_total || 0),
            meta: "Tracked only from your saved refill records",
        },
        {
            label: "Estimated Range",
            value: summary.estimated_range_km ? `${Alfred.formatNumber(summary.estimated_range_km, 0)} km / tank` : "No range estimate",
            meta: profile.fuel_tank_capacity_l ? `${Alfred.formatNumber(profile.fuel_tank_capacity_l, 1)} L tank` : "Tank capacity not saved",
        },
    ];
    const proofLine = profile.official_source_url
        ? `<div class="detail-item">Benchmark proof: <a class="proof-link" href="${profile.official_source_url}" target="_blank" rel="noopener">${Alfred.escapeHtml(profile.official_source_name || "official source")}</a></div>`
        : `<div class="detail-item">Benchmark source: custom or heuristic profile value.</div>`;
    const comparisonNote = summary.average_actual_mileage_kmpl && summary.expected_mileage_kmpl
        ? `<div class="detail-item">${Alfred.escapeHtml(mileageComparisonNarrative(summary.average_actual_mileage_kmpl, summary.expected_mileage_kmpl))}</div>`
        : `<div class="detail-item">Add refill logs after each fill-up to generate a real-world mileage comparison.</div>`;
    const evidenceNote = mileageChart?.labels?.length
        ? `<div class="detail-item">Comparison uses ${Alfred.escapeHtml(String(mileageChart.labels.length))} refill checkpoint(s) stored in your own account.</div>`
        : "";

    Alfred.setHTMLIfChanged(target, `
        <div class="surface-inset surface-inset-strong">
            <div class="panel-eyebrow">Mileage Comparison Summary</div>
            ${renderInsightStatGrid(stats)}
        </div>
        ${comparisonNote}
        ${proofLine}
        ${evidenceNote}
    `);
}

function mileageComparisonNarrative(actualMileage, optimalMileage) {
    const delta = Number(actualMileage || 0) - Number(optimalMileage || 0);
    if (delta <= -5) {
        return `Actual mileage is materially below the saved benchmark by ${Alfred.formatNumber(Math.abs(delta), 1)} kmpl. Check riding conditions, tyre pressure, load, chain condition, and recent service quality.`;
    }
    if (delta < 0) {
        return `Actual mileage is slightly below the saved benchmark by ${Alfred.formatNumber(Math.abs(delta), 1)} kmpl. A few more refill logs will confirm whether the drop is persistent.`;
    }
    if (delta >= 3) {
        return `Actual mileage is currently above the saved benchmark by ${Alfred.formatNumber(delta, 1)} kmpl. Keep tracking in similar riding conditions to confirm the gain is stable.`;
    }
    return "Actual mileage is broadly aligned with the saved benchmark.";
}

function renderBikeCompliance(items) {
    const target = document.getElementById("bikeComplianceList");
    Alfred.setHTMLIfChanged(target, items.length ? items.map(item => `
        <div class="mini-card timeline-card">
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
    `).join("") : `<div class="empty-state">No document compliance records yet.</div>`);
}

function renderServiceHistorySummary(summary) {
    const target = document.getElementById("bikeServiceHistorySummary");
    const stats = [
        { label: "Service Logs", value: Alfred.formatNumber(summary.total_service_logs || 0, 0), meta: "Complete maintenance record count" },
        { label: "Imported Bills", value: Alfred.formatNumber(summary.imported_service_bills || 0, 0), meta: "Auto-created from uploaded service files" },
        { label: "Manual Logs", value: Alfred.formatNumber(summary.manual_service_logs || 0, 0), meta: "User-created maintenance entries" },
        { label: "Fuel Refills", value: Alfred.formatNumber(summary.fuel_refill_count || 0, 0), meta: "Used for actual mileage tracking" },
        { label: "Avg Service Cost", value: Alfred.formatCurrency(summary.average_service_cost || 0), meta: "Average spend per service record" },
        { label: "Vehicle Docs", value: Alfred.formatNumber(summary.document_count || 0, 0), meta: "Uploaded and parsed vehicle proofs" },
        { label: "Condition Checks", value: Alfred.formatNumber(summary.condition_snapshot_count || 0, 0), meta: "Saved health snapshots" },
        { label: "Recurring Centers", value: (summary.recurring_centers || []).join(", ") || "No pattern yet", meta: "Most repeated workshop/service center names" },
    ];
    Alfred.setHTMLIfChanged(target, `
        <div class="surface-inset surface-inset-strong">
            <div class="panel-eyebrow">Maintenance Memory</div>
            ${renderInsightStatGrid(stats)}
        </div>
        <div class="detail-item">${Alfred.escapeHtml(summary.history_note || "Service-history intelligence will appear once a bill or manual log is stored.")}</div>
    `);
}

function renderRouteWearPanel(routeWear) {
    const target = document.getElementById("bikeRouteWearPanel");
    if (!target) {
        return;
    }

    const signals = routeWear.signals || {};
    const componentPressure = routeWear.component_pressure || [];
    const routeGuidance = routeWear.maintenance_guidance || {};
    const routeActions = routeGuidance.actions || [];
    const costFactors = routeWear.service_cost_guidance?.cost_factors || routeGuidance.cost_factors || [];
    const evidence = routeWear.evidence || [];
    const hasRouteLogs = Number(routeWear.recent_distance_km || 0) > 0 || Number(signals.recent_trip_count || 0) > 0;
    const stats = [
        {
            label: "Wear Status",
            value: routeWear.wear_status ? humanizeToken(routeWear.wear_status) : "No route signal",
            meta: routeWear.wear_index != null ? `${Alfred.formatNumber(routeWear.wear_index, 1)}/100 wear index` : "Trip logs activate this score",
        },
        {
            label: "90-Day Distance",
            value: `${Alfred.formatNumber(routeWear.recent_distance_km || 0, 1)} km`,
            meta: `${Alfred.formatNumber(signals.recent_trip_count || 0, 0)} recent trip log${Number(signals.recent_trip_count || 0) === 1 ? "" : "s"}`,
        },
        {
            label: "Route-Adjusted Cost",
            value: Alfred.formatCurrency(routeWear.route_adjusted_service_cost || 0),
            meta: `Pressure ${Alfred.formatCurrency(routeWear.route_cost_pressure || 0)}`,
        },
        {
            label: "Service Buffer",
            value: Alfred.formatCurrency(routeWear.suggested_service_buffer || 0),
            meta: routeWear.interval_consumed_pct != null
                ? `${Alfred.formatNumber(routeWear.interval_consumed_pct, 1)}% of ${Alfred.formatNumber(routeWear.service_interval_km || 0, 0)} km interval`
                : "No service interval saved",
        },
        {
            label: "Tightened Interval",
            value: routeGuidance.recommended_interval_km ? `${Alfred.formatNumber(routeGuidance.recommended_interval_km, 0)} km` : "Model interval",
            meta: routeGuidance.service_interval_tightening_pct
                ? `${Alfred.formatNumber(routeGuidance.service_interval_tightening_pct, 1)}% tighter than saved interval`
                : "No route tightening needed yet",
        },
    ];
    const signalChips = [
        ["Rough", signals.rough_route_logs],
        ["Hill", signals.hill_route_logs],
        ["Rain", signals.rain_route_logs],
        ["Dust", signals.dust_route_logs],
        ["Highway", signals.highway_route_logs],
        ["City", signals.city_stop_go_logs],
        ["Load", signals.loaded_route_logs],
    ].map(([label, value]) => `<span class="chip-neutral">${label} ${Alfred.formatNumber(value || 0, 0)}</span>`).join("");
    const componentCards = componentPressure.length
        ? componentPressure.map(item => `
            <div class="mini-card timeline-card">
                <div class="d-flex justify-content-between gap-3 align-items-start">
                    <div>
                        <div class="fw-semibold">${Alfred.escapeHtml(item.component || "")}</div>
                        <div class="muted small mt-2">${Alfred.escapeHtml(item.reason || "")}</div>
                    </div>
                    <span class="status-pill ${routeWearTone(item.pressure)}">${Alfred.escapeHtml(humanizeToken(item.pressure || "watch"))}</span>
                </div>
            </div>
        `).join("")
        : `<div class="empty-state">Component pressure appears after trip or fault history is available.</div>`;
    const actionCards = routeActions.length
        ? routeActions.map(action => `
            <div class="mini-card timeline-card">
                <div class="d-flex justify-content-between gap-3 align-items-start">
                    <div>
                        <div class="fw-semibold">${Alfred.escapeHtml(action.label || "")}</div>
                        <div class="muted small mt-2">${Alfred.escapeHtml(action.note || "")}</div>
                        <div class="muted small mt-2">${Alfred.escapeHtml((action.components || []).join(" | "))}</div>
                        ${action.evidence ? `<div class="muted small mt-2">${Alfred.escapeHtml(action.evidence)}</div>` : ""}
                    </div>
                    <div class="text-end" style="min-width: 120px;">
                        <span class="status-pill ${routeWearTone(action.priority)}">${Alfred.escapeHtml(humanizeToken(action.priority || "watch"))}</span>
                        <div class="muted small mt-2">${action.next_check_km ? `${Alfred.formatNumber(action.next_check_km, 0)} km check` : "No interval"}</div>
                        <div class="muted small">${action.estimated_cost_range ? `${Alfred.formatCurrency(action.estimated_cost_range.min || 0)}-${Alfred.formatCurrency(action.estimated_cost_range.max || 0)}` : ""}</div>
                    </div>
                </div>
            </div>
        `).join("")
        : `<div class="empty-state">Route-specific actions appear after trip evidence is stored.</div>`;
    const costFactorLine = costFactors.length
        ? `<div class="detail-item">Cost factors: ${costFactors.map(item => `${Alfred.escapeHtml(item.label || item.key || "Route")} ${Alfred.formatCurrency(item.estimated_pressure_cost || 0)}`).join(" | ")}</div>`
        : "";
    const evidenceList = evidence.length
        ? evidence.map(item => `<div class="muted small">${Alfred.escapeHtml(item)}</div>`).join("")
        : `<div class="muted small">No route evidence has been stored yet.</div>`;

    Alfred.setHTMLIfChanged(target, `
        <div class="surface-inset surface-inset-strong">
            <div class="panel-eyebrow">Route-Wear Contract</div>
            ${renderInsightStatGrid(stats)}
        </div>
        <div class="chip-row">${signalChips}</div>
        <div class="detail-item">${Alfred.escapeHtml(routeWear.recommendation || (hasRouteLogs ? "Route wear is being tracked from saved trip logs." : "Add trip logs with route notes to activate route-aware service costs."))}</div>
        ${costFactorLine}
        <div class="data-stack">${actionCards}</div>
        <div class="data-stack">${componentCards}</div>
        <div class="detail-item">
            <div class="fw-semibold mb-2">Evidence</div>
            ${evidenceList}
        </div>
    `);
}

function renderPartInsights(items) {
    const target = document.getElementById("bikePartImpactBoard");
    if (!items.length) {
        Alfred.setHTMLIfChanged(target, `<div class="empty-state">No part-impact intelligence is available yet. Import a service bill or create a fault report first.</div>`);
        return;
    }

    Alfred.setHTMLIfChanged(target, items.map(item => `
        <div class="mini-card timeline-card">
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
    `).join(""));
}

function renderBikeDocuments(items) {
    const target = document.getElementById("bikeDocumentList");
    Alfred.setHTMLIfChanged(target, items.length ? items.map(item => `
        <div class="mini-card timeline-card">
            <div class="d-flex justify-content-between gap-3 align-items-start">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.document_type_label)} <span class="muted small">${Alfred.escapeHtml(item.bike_name)}</span></div>
                    <div class="muted small">${Alfred.escapeHtml(item.issuer || "Issuer not detected")}${item.document_number ? ` | ${Alfred.escapeHtml(item.document_number)}` : ""}</div>
                    <div class="muted small">${item.issue_date ? `Issued ${Alfred.formatDate(item.issue_date)}` : "Issue date not detected"}${item.expiry_date ? ` | Expires ${Alfred.formatDate(item.expiry_date)}` : ""}</div>
                    <div class="muted small">${Alfred.escapeHtml(item.verification_status_label)} | ${Alfred.escapeHtml(item.parser_status_label || "Parsed")}${item.parse_confidence ? ` | confidence ${Alfred.formatNumber(item.parse_confidence * 100, 0)}%` : ""}</div>
                    ${item.parser_notes ? `<div class="muted small mt-2">${Alfred.escapeHtml(item.parser_notes)}</div>` : ""}
                    ${item.document_url ? `<div class="mt-2"><a class="proof-link" href="${item.document_url}" target="_blank" rel="noopener">Open document</a></div>` : ""}
                </div>
                <div class="text-end">
                    ${item.premium_amount ? `<strong>${Alfred.formatCurrency(item.premium_amount)}</strong><div class="muted small">premium/cost</div>` : ""}
                    <div class="mt-2"><button class="btn btn-sm btn-outline-danger" type="button" onclick="deleteBikeDocument(${item.id})">Delete</button></div>
                </div>
            </div>
        </div>
    `).join("") : `<div class="empty-state">No bike documents saved yet.</div>`);
}

function renderBikeRefills(items) {
    const target = document.getElementById("bikeRefillList");
    Alfred.setHTMLIfChanged(target, items.length ? items.map(item => `
        <div class="mini-card timeline-card">
            <div class="d-flex justify-content-between gap-3 align-items-start">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.bike_name)} <span class="muted small">${Alfred.formatDate(item.refill_date)}</span></div>
                    <div class="muted small">${item.trip_meter_km ? `${Alfred.formatNumber(item.trip_meter_km, 1)} km` : "Trip value not saved"} | ${Alfred.formatNumber(item.fuel_liters || 0, 2)} L${item.odometer_km ? ` | ${Alfred.formatNumber(item.odometer_km, 0)} km odo` : ""}</div>
                    <div class="muted small">${item.actual_mileage_kmpl ? `${Alfred.formatNumber(item.actual_mileage_kmpl, 1)} kmpl` : "Mileage not derivable yet"}${item.fuel_price_per_liter ? ` | ${Alfred.formatCurrency(item.fuel_price_per_liter)} / L` : ""}</div>
                    <div class="muted small">${item.station_name ? Alfred.escapeHtml(item.station_name) : "Pump not saved"}${item.is_full_tank ? " | full tank" : " | partial refill"}</div>
                    ${item.notes ? `<div class="muted small mt-2">${Alfred.escapeHtml(item.notes)}</div>` : ""}
                </div>
                <div class="text-end">
                    <strong>${Alfred.formatCurrency(item.total_cost || 0)}</strong>
                    <div class="mt-2"><button class="btn btn-sm btn-outline-danger" type="button" onclick="deleteBikeRefill(${item.id})">Delete</button></div>
                </div>
            </div>
        </div>
    `).join("") : `<div class="empty-state">No refill logs yet. Add a refill after each fill-up to compare actual mileage with the saved benchmark.</div>`);
}

function renderBikeConditions(items) {
    const target = document.getElementById("bikeConditionList");
    Alfred.setHTMLIfChanged(target, items.length ? items.map(item => `
        <div class="mini-card timeline-card">
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
    `).join("") : `<div class="empty-state">No bike condition snapshots yet.</div>`);
}

function renderBikeServiceTasks(tasks) {
    const target = document.getElementById("bikeServiceTasks");
    Alfred.setHTMLIfChanged(target, tasks.length ? tasks.map(task => `
        <div class="mini-card timeline-card">
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
    `).join("") : `<div class="empty-state">No pending tasks. Upload a bill, document, or fault report to activate the planner.</div>`);
}

function renderBikeServiceObservations(observations, suggestions) {
    const target = document.getElementById("bikeServiceObservations");
    const items = observations.concat(suggestions).slice(0, 6);
    Alfred.setHTMLIfChanged(target, items.length ? items.map(item => `<div class="detail-item">${Alfred.escapeHtml(item)}</div>`).join("") : `<div class="empty-state">No observations yet.</div>`);
}

function renderBikeServiceBrief(brief) {
    const target = document.getElementById("bikeServiceBrief");
    const points = brief.talking_points || [];
    Alfred.setHTMLIfChanged(target, `
        <div class="surface-inset surface-inset-strong">
            <div class="panel-eyebrow">Service Center Briefing</div>
            ${renderInsightStatGrid([
                {
                    label: "Opening Line",
                    value: brief.opening || "No briefing available yet.",
                    meta: "Use this as the first short summary with the workshop.",
                },
                {
                    label: "Projected Linked Cost",
                    value: Alfred.formatCurrency(brief.projected_total || 0),
                    meta: `${Alfred.formatNumber(points.length || 0, 0)} talking point${points.length === 1 ? "" : "s"} generated`,
                },
            ])}
        </div>
        <div class="detail-item">
            <div class="fw-semibold mb-2">What to tell the service center</div>
            ${points.length ? points.map(point => `<div class="muted small mb-2">${Alfred.escapeHtml(point)}</div>`).join("") : `<div class="muted">No active fault reports to brief yet.</div>`}
        </div>
    `);
}

function renderBikeServiceLogs(items) {
    const target = document.getElementById("bikeServiceLogList");
    Alfred.setHTMLIfChanged(target, items.length ? items.map(item => `
        <div class="mini-card timeline-card">
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
    `).join("") : `<div class="empty-state">No bike service logs yet.</div>`);
}

function renderBikeIssues(items) {
    const target = document.getElementById("bikeIssueBoard");
    Alfred.setHTMLIfChanged(target, items.length ? items.map(item => `
        <div class="mini-card timeline-card">
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
    `).join("") : `<div class="empty-state">No fault reports yet.</div>`);
}

function installBikeProfileFormGuards() {
    const form = document.getElementById("bikeProfileForm");
    if (!form) {
        return;
    }
    const markDirty = event => {
        if (event.target?.closest?.("#bikeProfileForm")) {
            markBikeProfileEditorDirty();
        }
    };
    form.addEventListener("input", markDirty, true);
    form.addEventListener("change", markDirty, true);
    form.addEventListener("focusin", event => {
        if (event.target?.closest?.("#bikeCatalogMakeSelect, #bikeCatalogSelect")) {
            lockBikeCatalogInteraction();
        }
    }, true);
    form.addEventListener("pointerdown", event => {
        if (event.target?.closest?.("#bikeCatalogMakeSelect, #bikeCatalogSelect")) {
            lockBikeCatalogInteraction();
        }
    }, true);
    form.addEventListener("keydown", event => {
        if (event.target?.closest?.("#bikeCatalogMakeSelect, #bikeCatalogSelect")) {
            lockBikeCatalogInteraction();
        }
    }, true);
}

function lockBikeCatalogInteraction(durationMs = BIKE_CATALOG_INTERACTION_HOLD_MS) {
    const nextUntil = Date.now() + Number(durationMs || 0);
    bikeState.catalogInteractionUntil = Math.max(Number(bikeState.catalogInteractionUntil || 0), nextUntil);
    const root = document.getElementById("bikeServiceRoot");
    if (root && Alfred.lockLiveRefresh) {
        Alfred.lockLiveRefresh(root, durationMs);
    }
}

function isBikeCatalogInteractionActive() {
    const makeInput = document.getElementById("bikeCatalogMakeSelect");
    const modelSelect = document.getElementById("bikeCatalogSelect");
    const active = document.activeElement;
    return Boolean(
        Number(bikeState.catalogInteractionUntil || 0) > Date.now()
        || active === makeInput
        || active === modelSelect
    );
}

function markBikeProfileEditorDirty() {
    const form = document.getElementById("bikeProfileForm");
    if (form) {
        form.dataset.userEditing = "true";
    }
}

function clearBikeProfileEditorDirty() {
    const form = document.getElementById("bikeProfileForm");
    if (form) {
        form.dataset.userEditing = "false";
    }
    bikeState.catalogInteractionUntil = 0;
}

function isBikeProfileEditorDirty() {
    const form = document.getElementById("bikeProfileForm");
    if (!form) {
        return false;
    }
    return form.dataset.userEditing === "true" || form.contains(document.activeElement);
}

function hydrateBikeCatalogManufacturers(preferredMake = "", preferredCatalogKey = "") {
    const makeInput = document.getElementById("bikeCatalogMakeSelect");
    if (!makeInput) {
        return Promise.resolve([]);
    }
    const vehicleType = document.getElementById("bikeProfileVehicleType")?.value || "";
    const manufacturers = catalogManufacturersForVehicleType(vehicleType);
    const nextMake = preferredMake || makeInput.value || "";
    renderCatalogMakeOptions(manufacturers, nextMake);
    if (makeInput.value !== nextMake) {
        makeInput.value = nextMake;
    }
    return hydrateBikeCatalog({ preferredCatalogKey });
}

function renderCatalogMakeOptions(manufacturers, selectedMake = "") {
    const datalist = document.getElementById("bikeCatalogMakeOptions");
    if (!datalist) {
        return;
    }
    const entries = [...(manufacturers || [])];
    const normalizedSelected = normalizeCatalogMake(selectedMake);
    if (normalizedSelected && !entries.some(item => normalizeCatalogMake(item.make) === normalizedSelected)) {
        entries.push({ make: selectedMake, model_count: 0, vehicle_types: [] });
    }
    entries.sort((left, right) => left.make.localeCompare(right.make));
    Alfred.setHTMLIfChanged(datalist, entries.map(item => {
        const label = item.model_count ? `${item.make} (${Alfred.formatNumber(item.model_count, 0)})` : item.make;
        return `<option value="${Alfred.escapeHtml(item.make)}" label="${Alfred.escapeHtml(label)}"></option>`;
    }).join(""));
}

function scheduleBikeCatalogHydration() {
    clearTimeout(bikeCatalogMakeTimer);
    bikeCatalogMakeTimer = setTimeout(() => {
        hydrateBikeCatalog();
    }, 250);
}

function hydrateBikeCatalog(options = {}) {
    const modelSelect = document.getElementById("bikeCatalogSelect");
    if (!modelSelect) {
        return Promise.resolve([]);
    }
    const vehicleType = document.getElementById("bikeProfileVehicleType")?.value || "";
    const make = document.getElementById("bikeCatalogMakeSelect")?.value || "";
    const preferredCatalogKey = options.preferredCatalogKey || "";
    const requestToken = ++bikeCatalogFetchToken;

    if (!make) {
        bikeState.catalog = [];
        bikeState.catalogRequestKey = "";
        Alfred.syncSelectOptions(modelSelect, [], {
            includeBlank: true,
            blankLabel: "Choose a make first",
            fallbackValue: "",
            disableWhenEmpty: true,
        });
        return Promise.resolve([]);
    }

    const requestKey = `${vehicleType || "all"}|${make}`;
    const renderCatalog = models => {
        Alfred.syncSelectOptions(modelSelect, models, {
            includeBlank: true,
            blankLabel: "Choose a known model or leave blank for custom",
            currentValue: preferredCatalogKey || modelSelect.value,
            preferredValue: preferredCatalogKey,
            fallbackValue: "",
            getValue: item => item.catalog_key,
            getLabel: item => item.display_name,
            disableWhenEmpty: true,
        });
        return models;
    };

    if (bikeState.catalogRequestKey === requestKey) {
        return Promise.resolve(renderCatalog(bikeState.catalog));
    }

    if (!isBikeCatalogInteractionActive()) {
        Alfred.syncSelectOptions(modelSelect, [], {
            includeBlank: true,
            blankLabel: "Loading models...",
            fallbackValue: "",
            disableWhenEmpty: true,
        });
    }

    const params = new URLSearchParams();
    if (vehicleType) {
        params.set("vehicle_type", vehicleType);
    }
    params.set("make", make);

    return Alfred.fetchJSON(`/api/mobility/bike-models/catalog/?${params.toString()}`)
        .then(data => {
            const currentMake = document.getElementById("bikeCatalogMakeSelect")?.value || "";
            const currentVehicleType = document.getElementById("bikeProfileVehicleType")?.value || "";
            const currentRequestKey = `${currentVehicleType || "all"}|${currentMake}`;
            if (requestToken !== bikeCatalogFetchToken || currentRequestKey !== requestKey) {
                return bikeState.catalog;
            }
            bikeState.catalog = data.results || [];
            bikeState.catalogRequestKey = requestKey;
            if (isBikeCatalogInteractionActive() && document.activeElement === modelSelect) {
                return bikeState.catalog;
            }
            return renderCatalog(bikeState.catalog);
        })
        .catch(error => {
            if (requestToken !== bikeCatalogFetchToken) {
                return [];
            }
            bikeState.catalog = [];
            bikeState.catalogRequestKey = requestKey;
            Alfred.syncSelectOptions(modelSelect, [], {
                includeBlank: true,
                blankLabel: "Unable to load models for this make",
                fallbackValue: "",
                disableWhenEmpty: true,
            });
            showBikeServiceFeedback("bikeProfileFeedback", error.message || "Unable to load catalog models for the selected make.", "warning");
            return [];
        });
}

function catalogManufacturersForVehicleType(vehicleType) {
    const normalizedType = String(vehicleType || "").trim();
    return (bikeState.catalogManufacturers || []).filter(item => {
        const vehicleTypes = Array.isArray(item.vehicle_types) ? item.vehicle_types : [];
        return !normalizedType || !vehicleTypes.length || vehicleTypes.includes(normalizedType);
    });
}

function normalizeCatalogMake(value) {
    return String(value || "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, " ")
        .trim();
}

function buildCatalogManufacturersFromModels(models) {
    const grouped = new Map();
    (models || []).forEach(item => {
        const make = item.make || "";
        if (!make) {
            return;
        }
        if (!grouped.has(make)) {
            grouped.set(make, { make, model_count: 0, vehicle_types: new Set() });
        }
        const entry = grouped.get(make);
        entry.model_count += 1;
        if (item.vehicle_type) {
            entry.vehicle_types.add(item.vehicle_type);
        }
    });
    return Array.from(grouped.values())
        .map(item => ({ ...item, vehicle_types: Array.from(item.vehicle_types).sort() }))
        .sort((left, right) => left.make.localeCompare(right.make));
}

function hydrateBikeProfileSelectors() {
    ["bikeServiceProfile", "bikeServiceImportProfile", "bikeDocumentProfile", "bikeConditionProfile", "bikeIssueProfile", "bikeRefillProfile"].forEach(id => {
        const target = document.getElementById(id);
        if (!target) {
            return;
        }
        Alfred.syncSelectOptions(target, bikeState.profiles, {
            includeBlank: !bikeState.profiles.length,
            blankLabel: "Add a vehicle profile first",
            getValue: item => item.id,
            getLabel: item => `${item.display_name}${item.vehicle_type_label ? ` | ${item.vehicle_type_label}` : ""}${item.vehicle_number ? ` | ${item.vehicle_number}` : ""}`,
            disableWhenEmpty: true,
        });
    });
    syncSelectedProfileIntoForms();
}

function hydrateTravelPlanOptions(plans) {
    Alfred.syncSelectOptions("bikeIssueTravelPlan", plans, {
        includeBlank: true,
        blankLabel: "Optional trip link",
        getValue: item => item.id,
        getLabel: item => `${item.title} | ${item.destination}`,
    });
}

function syncCatalogIntoProfileForm(event) {
    lockBikeCatalogInteraction();
    markBikeProfileEditorDirty();
    const key = event.currentTarget.value;
    const match = bikeState.catalog.find(item => item.catalog_key === key);
    if (!match) {
        return;
    }
    document.getElementById("bikeProfileVehicleType").value = match.vehicle_type || "motorcycle";
    document.getElementById("bikeCatalogMakeSelect").value = match.make || "";
    document.getElementById("bikeProfileDisplayName").value = match.display_name || "";
    document.getElementById("bikeProfileModelName").value = match.model_name || "";
    document.getElementById("bikeProfileVariant").value = match.variant || "";
    document.getElementById("bikeProfileClass").value = match.bike_class || "roadster";
    document.getElementById("bikeProfileUsagePattern").value = match.vehicle_type === "car" ? "essential" : "personal";
    document.getElementById("bikeProfileEngineCc").value = valueOrEmpty(match.engine_cc);
    document.getElementById("bikeProfileFuelTank").value = valueOrEmpty(match.fuel_tank_capacity_l);
    document.getElementById("bikeProfileMileage").value = valueOrEmpty(match.expected_mileage_kmpl);
    document.getElementById("bikeProfileFuelType").value = match.fuel_type || "petrol";
    document.getElementById("bikeProfileServiceIntervalKm").value = valueOrEmpty(match.service_interval_km);
    document.getElementById("bikeProfileServiceIntervalDays").value = valueOrEmpty(match.service_interval_days);
    document.getElementById("bikeProfileCruisingSpeed").value = valueOrEmpty(match.optimal_cruising_speed_kmph);
}

function valueOrEmpty(value) {
    return value == null ? "" : value;
}

function populateBikeProfileForm(profile) {
    document.getElementById("bikeProfileId").value = profile.id || "";
    document.getElementById("bikeProfileVehicleType").value = profile.vehicle_type || "motorcycle";
    hydrateBikeCatalogManufacturers(profile.make || "", profile.catalog_key || "");
    document.getElementById("bikeProfileDisplayName").value = profile.display_name || "";
    document.getElementById("bikeProfileModelName").value = profile.model_name || "";
    document.getElementById("bikeProfileVariant").value = profile.variant || "";
    document.getElementById("bikeProfileVehicleNumber").value = profile.vehicle_number || "";
    document.getElementById("bikeProfileClass").value = profile.bike_class || "roadster";
    document.getElementById("bikeProfileUsagePattern").value = profile.usage_pattern || "personal";
    document.getElementById("bikeProfileMarketValue").value = valueOrEmpty(profile.estimated_market_value);
    document.getElementById("bikeProfileIncomeSupport").value = valueOrEmpty(profile.monthly_income_support);
    document.getElementById("bikeProfileEngineCc").value = valueOrEmpty(profile.engine_cc);
    document.getElementById("bikeProfileFuelTank").value = valueOrEmpty(profile.fuel_tank_capacity_l);
    document.getElementById("bikeProfileMileage").value = valueOrEmpty(profile.expected_mileage_kmpl);
    document.getElementById("bikeProfileFuelType").value = profile.fuel_type || "petrol";
    document.getElementById("bikeProfileServiceIntervalKm").value = valueOrEmpty(profile.service_interval_km);
    document.getElementById("bikeProfileServiceIntervalDays").value = valueOrEmpty(profile.service_interval_days);
    document.getElementById("bikeProfileCruisingSpeed").value = valueOrEmpty(profile.optimal_cruising_speed_kmph);
    document.getElementById("bikeProfilePrimary").value = profile.is_primary ? "true" : "false";
    clearBikeProfileEditorDirty();
}

function syncBikeProfileEditor() {
    if (!bikeState.editingProfileId) {
        return;
    }
    const profile = bikeState.profiles.find(item => item.id === bikeState.editingProfileId);
    if (!profile) {
        resetBikeProfileForm();
        return;
    }
    populateBikeProfileForm(profile);
    setBikeProfileFormMode(profile);
}

function setBikeProfileFormMode(profile) {
    const submitButton = document.getElementById("bikeProfileSubmit");
    const cancelButton = document.getElementById("bikeProfileCancel");
    if (profile) {
        submitButton.textContent = `Update ${profile.display_name || "Vehicle"}`;
        cancelButton.classList.remove("d-none");
        return;
    }
    submitButton.textContent = "Save Vehicle Profile";
    cancelButton.classList.add("d-none");
}

function resetBikeProfileForm() {
    const form = document.getElementById("bikeProfileForm");
    bikeState.editingProfileId = null;
    form.reset();
    clearBikeProfileEditorDirty();
    document.getElementById("bikeProfileId").value = "";
    document.getElementById("bikeProfileVehicleType").value = "motorcycle";
    hydrateBikeCatalogManufacturers();
    document.getElementById("bikeProfileClass").value = "roadster";
    document.getElementById("bikeProfileUsagePattern").value = "personal";
    document.getElementById("bikeProfileFuelType").value = "petrol";
    document.getElementById("bikeProfilePrimary").value = "true";
    setBikeProfileFormMode(null);
}

function editBikeProfile(id) {
    const profile = bikeState.profiles.find(item => item.id === id);
    if (!profile) {
        showBikeServiceAlert("The selected vehicle profile could not be found.", "warning");
        return;
    }
    bikeState.editingProfileId = id;
    populateBikeProfileForm(profile);
    setBikeProfileFormMode(profile);
    showBikeServiceFeedback("bikeProfileFeedback", `Editing ${profile.display_name}. Update the fields and save to apply changes.`, "info");
}

function syncSelectedProfileIntoForms() {
    const activeId = document.getElementById("bikeServiceProfile").value || document.getElementById("bikeConditionProfile").value || document.getElementById("bikeIssueProfile").value || document.getElementById("bikeRefillProfile").value;
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
    document.getElementById("bikeRefillProfileId").value = profile.id;
    document.getElementById("bikeRefillBikeName").value = profile.display_name || "";
    document.getElementById("bikeRefillVehicleNumber").value = profile.vehicle_number || "";
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
    const mileageLabels = charts.mileage_trend?.labels || [];
    const actualMileageValues = charts.mileage_trend?.actual_values || [];
    const optimalMileageValues = charts.mileage_trend?.optimal_values || [];

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

    bikeMileageChart = drawChart(bikeMileageChart, "bikeMileageChart", "line", {
        labels: mileageLabels,
        datasets: [
            {
                label: "Actual mileage",
                data: actualMileageValues,
                borderColor: "#148f63",
                backgroundColor: "rgba(20,143,99,0.16)",
                fill: true,
                tension: 0.25,
                pointRadius: 4,
                pointHoverRadius: 5,
            },
            {
                label: "Optimal benchmark",
                data: optimalMileageValues,
                borderColor: "#1858d6",
                backgroundColor: "rgba(24,88,214,0.08)",
                borderDash: [6, 6],
                fill: false,
                tension: 0,
                pointRadius: 2,
            },
        ],
    }, {
        scales: { y: { beginAtZero: false } },
    });
    setChartMeta(
        "bikeMileageChartMeta",
        actualMileageValues.length
            ? `${actualMileageValues.length} refill checkpoint${actualMileageValues.length === 1 ? "" : "s"} compared against ${charts.mileage_trend?.source_name || "the saved benchmark"}.`
            : "No refill-based mileage checkpoints are stored yet. Add a refill after each fill-up to activate the comparison."
    );
}

function drawChart(existing, elementId, type, data, extraOptions = {}) {
    if (existing) {
        existing.destroy();
    }
    return new Chart(document.getElementById(elementId), {
        type,
        data,
        options: {
            plugins: { legend: { position: "bottom" } },
            scales: type === "doughnut" ? {} : { y: { beginAtZero: true } },
            ...extraOptions,
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
    const isEditing = Boolean(bikeState.editingProfileId);
    const payload = buildBikeProfilePayload(form);
    const url = isEditing ? `/api/mobility/bikes/${bikeState.editingProfileId}/` : "/api/mobility/bikes/";
    const method = isEditing ? "PATCH" : "POST";
    Alfred.fetchJSON(url, { method, body: JSON.stringify(payload) })
        .then(() => {
            resetBikeProfileForm();
            showBikeServiceFeedback(
                "bikeProfileFeedback",
                isEditing
                    ? "Vehicle profile updated and re-verified against the active catalog rules."
                    : "Vehicle profile saved and verified against the internal catalog.",
                "success"
            );
            loadBikeServiceDashboard();
        })
        .catch(error => showBikeServiceFeedback("bikeProfileFeedback", error.message, "danger"));
}

function buildBikeProfilePayload(form) {
    const payload = Object.fromEntries(new FormData(form).entries());
    payload.make = String(payload.make || "").trim();
    payload.is_primary = payload.is_primary === "true";
    payload.estimated_market_value = Number(payload.estimated_market_value || 0);
    payload.monthly_income_support = Number(payload.monthly_income_support || 0);
    payload.engine_cc = payload.engine_cc === "" ? null : Number(payload.engine_cc);
    payload.fuel_tank_capacity_l = payload.fuel_tank_capacity_l === "" ? null : Number(payload.fuel_tank_capacity_l);
    payload.expected_mileage_kmpl = payload.expected_mileage_kmpl === "" ? null : Number(payload.expected_mileage_kmpl);
    payload.service_interval_km = payload.service_interval_km === "" ? null : Number(payload.service_interval_km);
    payload.service_interval_days = payload.service_interval_days === "" ? null : Number(payload.service_interval_days);
    payload.optimal_cruising_speed_kmph = payload.optimal_cruising_speed_kmph === "" ? null : Number(payload.optimal_cruising_speed_kmph);
    return payload;
}

function submitBikeServiceImport(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const fileInput = form.elements.service_file;
    const files = Array.from(fileInput?.files || []);
    if (!files.length) {
        showBikeServiceFeedback("bikeServiceImportFeedback", "Choose at least one service bill or work note first.", "warning");
        return;
    }

    const submitButton = form.querySelector("button[type='submit']");
    if (submitButton) {
        submitButton.disabled = true;
    }

    Alfred.showUploadProgress("bikeServiceImportFeedback", {
        phase: "preparing",
        percent: 0,
        current: 1,
        total: files.length,
    });

    Alfred.uploadFilesSequentially(
        files,
        (file, uploadContext) => Alfred.uploadJSON("/api/mobility/bike-services/import/", {
            method: "POST",
            body: Alfred.buildSingleFileFormData(form, "service_file", file),
            onUploadState: uploadContext?.reportProgress,
        }),
        {
            onProgress: state => Alfred.showUploadProgress("bikeServiceImportFeedback", state),
        },
    )
        .then(results => {
            const summary = summarizeBikeServiceImportBatch(results);
            if (summary.succeeded.length) {
                form.reset();
                loadBikeServiceDashboard();
            }
            showBikeServiceFeedback("bikeServiceImportFeedback", summary.message, summary.tone);
        })
        .finally(() => {
            if (submitButton) {
                submitButton.disabled = false;
            }
        });
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

function submitBikeRefill(event) {
    event.preventDefault();
    syncSelectedProfileIntoForms();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    payload.bike_profile = payload.bike_profile ? Number(payload.bike_profile) : Number(document.getElementById("bikeRefillProfile").value || 0) || null;
    payload.odometer_km = payload.odometer_km ? Number(payload.odometer_km) : null;
    payload.trip_meter_km = Number(payload.trip_meter_km || 0);
    payload.fuel_liters = Number(payload.fuel_liters || 0);
    payload.total_cost = Number(payload.total_cost || 0);
    payload.is_full_tank = payload.is_full_tank === "true";

    Alfred.fetchJSON("/api/mobility/bike-refills/", { method: "POST", body: JSON.stringify(payload) })
        .then(() => {
            form.reset();
            setBikeServiceDefaults();
            hydrateBikeProfileSelectors();
            showBikeServiceFeedback("bikeRefillFeedback", "Fuel refill log saved. Mileage comparison updated.", "success");
            loadBikeServiceDashboard();
        })
        .catch(error => showBikeServiceFeedback("bikeRefillFeedback", error.message, "danger"));
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
    const fileInput = form.elements.document_file;
    const files = Array.from(fileInput?.files || []);
    if (!files.length) {
        showBikeServiceFeedback("bikeDocumentFeedback", "Choose at least one vehicle document first.", "warning");
        return;
    }

    const submitButton = form.querySelector("button[type='submit']");
    if (submitButton) {
        submitButton.disabled = true;
    }

    Alfred.showUploadProgress("bikeDocumentFeedback", {
        phase: "preparing",
        percent: 0,
        current: 1,
        total: files.length,
    });

    Alfred.uploadFilesSequentially(
        files,
        (file, uploadContext) => Alfred.uploadJSON("/api/mobility/bike-documents/upload/", {
            method: "POST",
            body: Alfred.buildSingleFileFormData(form, "document_file", file),
            onUploadState: uploadContext?.reportProgress,
        }),
        {
            onProgress: state => Alfred.showUploadProgress("bikeDocumentFeedback", state),
        },
    )
        .then(results => {
            const summary = Alfred.summarizeUploadBatch(results, { itemLabel: "vehicle document", successVerb: "uploaded" });
            if (summary.succeeded.length) {
                form.reset();
                loadBikeServiceDashboard();
            }
            showBikeServiceFeedback("bikeDocumentFeedback", summary.message, summary.tone);
        })
        .finally(() => {
            if (submitButton) {
                submitButton.disabled = false;
            }
        });
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

function deleteBikeRefill(id) {
    deleteBikeEntity(`/api/mobility/bike-refills/${id}/`, "Delete this refill log?");
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

function routeWearTone(status) {
    if (status === "high" || status === "urgent") {
        return "status-high";
    }
    if (status === "watch" || status === "medium") {
        return "status-guarded";
    }
    return "status-low";
}

function humanizeToken(value) {
    return String(value || "")
        .replace(/[_-]+/g, " ")
        .replace(/\b\w/g, char => char.toUpperCase())
        .trim();
}

function renderInsightStatGrid(items) {
    return `<div class="insight-stat-grid">${items.map(item => `
        <article class="insight-stat">
            <p class="insight-stat-label">${Alfred.escapeHtml(item.label || "")}</p>
            <p class="insight-stat-value">${Alfred.escapeHtml(String(item.value == null || item.value === "" ? "Not set" : item.value))}</p>
            ${item.meta ? `<p class="insight-stat-meta">${Alfred.escapeHtml(item.meta)}</p>` : ""}
        </article>
    `).join("")}</div>`;
}

function formatMaybeDateTime(value) {
    return value && value.includes("T") ? Alfred.formatDateTime(value) : Alfred.formatDate(value);
}

function setBikeServiceDefaults() {
    document.getElementById("bikeServiceDate").value = todayLocal();
    document.getElementById("bikeRefillDate").value = todayLocal();
    document.getElementById("bikeIssueReportedAt").value = currentDateTimeLocal();
    document.getElementById("bikeConditionCapturedAt").value = currentDateTimeLocal();
    document.getElementById("bikeRefillFullTank").value = "true";
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

function summarizeBikeServiceImportBatch(results) {
    const summary = Alfred.summarizeUploadBatch(results, { itemLabel: "service file", successVerb: "imported" });
    const createdLogs = summary.succeeded.filter(result => result.data?.service_record).length;
    return {
        ...summary,
        message: createdLogs ? `${summary.message} ${createdLogs} service log${createdLogs === 1 ? "" : "s"} created.` : summary.message,
    };
}

window.deleteBikeProfile = deleteBikeProfile;
window.editBikeProfile = editBikeProfile;
window.deleteBikeServiceRecord = deleteBikeServiceRecord;
window.deleteBikeRefill = deleteBikeRefill;
window.deleteBikeIssue = deleteBikeIssue;
window.deleteBikeDocument = deleteBikeDocument;
window.deleteBikeCondition = deleteBikeCondition;
