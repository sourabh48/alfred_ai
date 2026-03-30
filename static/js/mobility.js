const mobilityState = { plans: [], logs: [], photos: [], profiles: [] };

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("mobilityRoot")) {
        return;
    }

    document.getElementById("travelPlanForm").addEventListener("submit", submitTravelPlan);
    document.getElementById("travelAdviceButton").addEventListener("click", previewTravelAdvice);
    document.getElementById("tripLogForm").addEventListener("submit", submitTripLog);
    document.getElementById("tripPhotoForm").addEventListener("submit", submitTripPhoto);
    document.getElementById("photoPlan").addEventListener("change", syncPhotoLogOptions);

    setMobilityDefaults();
    loadMobilityDashboard();
    Alfred.enableLiveRefresh("mobility-live", loadMobilityDashboard, { rootId: "mobilityRoot" });
});

function loadMobilityDashboard() {
    const selectedPhotoPlan = document.getElementById("photoPlan")?.value || "";
    const selectedPhotoLog = document.getElementById("photoLog")?.value || "";

    return Alfred.fetchJSON("/api/mobility/dashboard/")
        .then(data => {
            mobilityState.plans = data.travel_plans || [];
            mobilityState.logs = data.trip_logs || [];
            mobilityState.photos = data.trip_photos || [];
            mobilityState.profiles = data.bike_profiles || [];

            showRootAlert("", "secondary");
            renderHero(data.summary || {}, data.condition_snapshot);
            renderSummaryCards(data.summary || {});
            renderTravelPlans(mobilityState.plans);
            renderTripLogs(mobilityState.logs);
            renderPhotoGallery(mobilityState.photos);
            renderHeatmap(data.heatmap_points || []);
            hydrateVehicleProfiles();
            hydratePlanSelects(selectedPhotoPlan, selectedPhotoLog);
        })
        .catch(error => showRootAlert(error.message, "danger"));
}

function renderHero(summary, conditionSnapshot) {
    document.getElementById("mobilityTripHero").textContent = `Upcoming trips: ${Alfred.formatNumber(summary.upcoming_trips || 0, 0)} | mapped points: ${Alfred.formatNumber(summary.mapped_points || 0, 0)}`;
    document.getElementById("mobilityConditionMeta").textContent = conditionSnapshot
        ? `Latest bike condition ${Alfred.escapeHtml(conditionSnapshot.overall_status_label)} | score ${Alfred.formatNumber(conditionSnapshot.overall_score || 0, 0)}`
        : "No bike condition snapshot logged yet.";
    document.getElementById("mobilityDocumentMeta").textContent = `Expiring documents: ${Alfred.formatNumber(summary.expiring_documents || 0, 0)}`;
}

function renderSummaryCards(summary) {
    const cards = [
        ["Upcoming Trips", Alfred.formatNumber(summary.upcoming_trips || 0, 0), `${Alfred.formatNumber(summary.completed_trips || 0, 0)} completed`],
        ["Distance Logged", `${Alfred.formatNumber(summary.total_trip_distance_km || 0, 1)} km`, `${Alfred.formatNumber(summary.trip_logs || 0, 0)} journal entries`],
        ["Photo Trail", Alfred.formatNumber(summary.photo_count || 0, 0), `${Alfred.formatNumber(summary.mapped_points || 0, 0)} mapped points`],
        ["Bike Service Link", summary.condition_score ? `${Alfred.formatNumber(summary.condition_score, 0)}/100` : "No data", `${Alfred.escapeHtml(summary.condition_status || "No status")} | ${Alfred.formatNumber(summary.expiring_documents || 0, 0)} documents due`],
    ];
    document.getElementById("mobilitySummaryCards").innerHTML = cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card[0]}</p>
            <h2 class="metric-value">${card[1]}</h2>
            <p class="metric-caption">${card[2]}</p>
        </article>
    `).join("");
}

function renderTravelAdvice(data) {
    const target = document.getElementById("travelAdvisorPanel");
    const offbeat = data.offbeat_suggestions || [];
    const itinerary = data.itinerary_outline || [];
    const reasons = data.feasibility?.reasons || [];
    const evidence = data.evidence || [];
    target.innerHTML = `
        <div class="detail-item">
            <div class="fw-semibold mb-2">Destination match</div>
            <div class="muted">${Alfred.escapeHtml(data.destination_match?.display_name || "Not resolved")}</div>
        </div>
        <div class="detail-item">
            <div class="fw-semibold mb-2">Weather and feasibility</div>
            <div class="muted">${Alfred.escapeHtml(data.weather?.summary || "Weather unavailable")}</div>
            <div class="muted small mt-2">${reasons.length ? reasons.map(item => Alfred.escapeHtml(item)).join(" | ") : "No feasibility note yet."}</div>
        </div>
        <div class="detail-item">
            <div class="fw-semibold mb-2">Stay budget</div>
            <div class="muted">${Alfred.escapeHtml(data.stay_advice?.tier || "Unknown")} | cap ${Alfred.formatCurrency(data.stay_advice?.recommended_room_cap || 0)} per night</div>
            <div class="muted small mt-2">${Alfred.escapeHtml(data.stay_advice?.notes || "")}</div>
        </div>
        <div class="detail-item">
            <div class="fw-semibold mb-2">Vehicle readiness</div>
            <div class="muted">${Alfred.escapeHtml(data.bike_readiness?.recommendation || "No vehicle recommendation yet.")}</div>
            <div class="muted small mt-2">${data.bike_readiness?.bike_name ? Alfred.escapeHtml(data.bike_readiness.bike_name) : "No linked vehicle"}${data.bike_readiness?.vehicle_type ? ` | ${Alfred.escapeHtml(data.bike_readiness.vehicle_type)}` : ""}</div>
            <div class="muted small mt-2">${data.bike_readiness?.estimated_mileage_kmpl ? `${Alfred.formatNumber(data.bike_readiness.estimated_mileage_kmpl, 1)} kmpl` : "No mileage estimate"}${data.bike_readiness?.estimated_range_km ? ` | ${Alfred.formatNumber(data.bike_readiness.estimated_range_km, 0)} km range` : ""}</div>
        </div>
        <div class="detail-item">
            <div class="fw-semibold mb-2">Offbeat stops</div>
            ${offbeat.length ? offbeat.map(item => `<div class="muted small mb-2">${Alfred.escapeHtml(item.title)} | ${Alfred.escapeHtml(item.detail)}</div>`).join("") : `<div class="muted">No offbeat suggestion could be resolved right now.</div>`}
        </div>
        <div class="detail-item">
            <div class="fw-semibold mb-2">Suggested itinerary</div>
            ${itinerary.length ? itinerary.map(item => `<div class="muted small mb-2">${Alfred.escapeHtml(item)}</div>`).join("") : `<div class="muted">No itinerary yet.</div>`}
        </div>
        <div class="detail-item">
            <div class="fw-semibold mb-2">Evidence</div>
            ${evidence.length ? evidence.map(item => `<div class="muted small mb-2">${Alfred.escapeHtml(item.source_name || "Source")} | refreshed ${Alfred.formatDateTime(item.verified_at)} | <a href="${item.source_url}" target="_blank" rel="noopener">open</a></div>`).join("") : `<div class="muted">No external evidence captured yet.</div>`}
        </div>
    `;
}

function renderTravelPlans(items) {
    const target = document.getElementById("travelPlanList");
    target.innerHTML = items.length ? items.map(item => {
        const planLogs = mobilityState.logs.filter(log => log.travel_plan === item.id);
        const spend = planLogs.reduce((sum, log) => sum + Number(log.spend_amount || 0), 0);
        const distance = planLogs.reduce((sum, log) => sum + Number(log.distance_km || 0), 0);
        return `
            <div class="mini-card">
                <div class="d-flex justify-content-between align-items-start gap-3">
                    <div>
                        <div class="fw-semibold">${Alfred.escapeHtml(item.title)} <span class="muted small">${Alfred.escapeHtml(item.status_label)}</span></div>
                        <div class="muted small">${Alfred.escapeHtml(item.destination)} | ${Alfred.formatDate(item.start_date)} to ${Alfred.formatDate(item.end_date)} | ${Alfred.escapeHtml(item.transport_mode_label)}</div>
                        ${item.vehicle_profile_name ? `<div class="muted small">Vehicle: ${Alfred.escapeHtml(item.vehicle_profile_name)}</div>` : ""}
                        <div class="muted small">${Alfred.formatNumber(item.duration_days, 0)} days | ${Alfred.formatNumber(item.log_count || 0, 0)} logs | ${Alfred.formatNumber(item.photo_count || 0, 0)} photos</div>
                        <div class="muted small">Logged spend ${Alfred.formatCurrency(spend)} | distance ${Alfred.formatNumber(distance, 1)} km</div>
                    </div>
                    <div class="text-end">
                        <strong>${Alfred.formatCurrency(item.budget)}</strong>
                        <div class="mt-2"><button class="btn btn-sm btn-outline-danger" type="button" onclick="deleteTravelPlan(${item.id})">Delete</button></div>
                    </div>
                </div>
            </div>
        `;
    }).join("") : `<div class="empty-state">No travel plans saved yet.</div>`;
}

function renderTripLogs(items) {
    const target = document.getElementById("tripLogList");
    target.innerHTML = items.length ? items.map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.title)}</div>
                    <div class="muted small">${Alfred.escapeHtml(item.travel_plan_title)} | ${Alfred.formatDate(item.log_date)} | ${Alfred.escapeHtml(item.location_name || "Unknown location")}</div>
                    <div class="muted small">${Alfred.formatNumber(item.distance_km || 0, 1)} km | ${Alfred.formatCurrency(item.spend_amount || 0)} | ${Alfred.escapeHtml(item.mood || "No mood set")}</div>
                    ${item.latitude !== null && item.longitude !== null ? `<div class="muted small">Coordinates ${Alfred.formatNumber(item.latitude, 4)}, ${Alfred.formatNumber(item.longitude, 4)}</div>` : ""}
                </div>
                <button class="btn btn-sm btn-outline-danger" type="button" onclick="deleteTripLog(${item.id})">Delete</button>
            </div>
        </div>
    `).join("") : `<div class="empty-state">No trip logs captured yet.</div>`;
}

function renderPhotoGallery(items) {
    const target = document.getElementById("tripPhotoGallery");
    target.innerHTML = items.length ? items.map(item => `
        <article class="photo-card">
            <img src="${item.photo_url}" alt="${Alfred.escapeHtml(item.caption || item.travel_plan_title)}" loading="lazy">
            <div class="photo-card-body">
                <div class="fw-semibold">${Alfred.escapeHtml(item.caption || item.travel_plan_title)}</div>
                <div class="muted small">${Alfred.escapeHtml(item.location_name || item.travel_plan_title)}</div>
                <div class="muted small">${item.trip_log_title ? `Linked log: ${Alfred.escapeHtml(item.trip_log_title)}` : `Plan: ${Alfred.escapeHtml(item.travel_plan_title)}`}</div>
                <div class="muted small">${item.taken_at ? Alfred.formatDateTime(item.taken_at) : "Time not set"}</div>
                <button class="btn btn-sm btn-outline-danger mt-3" type="button" onclick="deleteTripPhoto(${item.id})">Delete</button>
            </div>
        </article>
    `).join("") : `<div class="empty-state w-100">No trip photos uploaded yet.</div>`;
}

function renderHeatmap(points) {
    const target = document.getElementById("tripHeatmap");
    const validPoints = points.filter(point => point.latitude !== null && point.longitude !== null);
    if (!validPoints.length) {
        target.innerHTML = `<div class="empty-state">Add log or photo coordinates to generate the travel heat map.</div>`;
        return;
    }
    const latitudes = validPoints.map(point => Number(point.latitude));
    const longitudes = validPoints.map(point => Number(point.longitude));
    const minLat = Math.min(...latitudes);
    const maxLat = Math.max(...latitudes);
    const minLng = Math.min(...longitudes);
    const maxLng = Math.max(...longitudes);
    const latSpan = Math.max(maxLat - minLat, 0.0001);
    const lngSpan = Math.max(maxLng - minLng, 0.0001);
    const maxIntensity = Math.max(...validPoints.map(point => Number(point.intensity || 1)), 1);

    target.innerHTML = validPoints.map(point => {
        const x = ((Number(point.longitude) - minLng) / lngSpan) * 100;
        const y = 100 - (((Number(point.latitude) - minLat) / latSpan) * 100);
        const size = 18 + ((Number(point.intensity || 1) / maxIntensity) * 26);
        const title = [point.title || "Trip point", point.location_name || "Location not set", point.date || "No date"].join(" | ");
        return `<div class="heatmap-spot ${point.type === "photo" ? "photo" : "log"}" style="left:${x}%; top:${y}%; width:${size}px; height:${size}px;" title="${Alfred.escapeHtml(title)}"></div>`;
    }).join("");
}

function hydratePlanSelects(selectedPhotoPlan, selectedPhotoLog) {
    const tripLogPlan = document.getElementById("tripLogPlan");
    const photoPlan = document.getElementById("photoPlan");
    const hasPlans = mobilityState.plans.length > 0;
    const defaultPlanId = hasPlans ? String(mobilityState.plans[0].id) : "";
    const activePhotoPlan = keepValue(selectedPhotoPlan, mobilityState.plans) || defaultPlanId;

    const options = hasPlans ? mobilityState.plans.map(item => `<option value="${item.id}">${Alfred.escapeHtml(item.title)} | ${Alfred.escapeHtml(item.destination)}</option>`).join("") : `<option value="">Create a travel plan first</option>`;
    tripLogPlan.innerHTML = options;
    photoPlan.innerHTML = options;
    tripLogPlan.disabled = !hasPlans;
    photoPlan.disabled = !hasPlans;
    if (hasPlans) {
        tripLogPlan.value = defaultPlanId;
        photoPlan.value = activePhotoPlan;
    }

    syncPhotoLogOptions(selectedPhotoLog);
    document.querySelector("#tripLogForm button[type='submit']").disabled = !hasPlans;
    document.querySelector("#tripPhotoForm button[type='submit']").disabled = !hasPlans;
    if (!hasPlans) {
        showFeedback("tripLogFeedback", "Create a travel plan before logging trip activity.", "warning");
        showFeedback("tripPhotoFeedback", "Create a travel plan before uploading trip photos.", "warning");
    } else {
        hideFeedback("tripLogFeedback");
        hideFeedback("tripPhotoFeedback");
    }
}

function hydrateVehicleProfiles() {
    const target = document.getElementById("travelVehicleProfile");
    if (!target) {
        return;
    }
    const currentValue = target.value;
    const options = [`<option value="">Optional vehicle link</option>`].concat(
        mobilityState.profiles.map(item => `<option value="${item.id}">${Alfred.escapeHtml(item.display_name)}${item.vehicle_type_label ? ` | ${Alfred.escapeHtml(item.vehicle_type_label)}` : ""}</option>`)
    );
    target.innerHTML = options.join("");
    if (mobilityState.profiles.some(item => item.is_primary)) {
        const primary = mobilityState.profiles.find(item => item.is_primary);
        target.value = mobilityState.profiles.some(item => String(item.id) === String(currentValue)) ? currentValue : String(primary.id);
    }
}

function syncPhotoLogOptions(selectedPhotoLog = "") {
    const photoLog = document.getElementById("photoLog");
    const planId = Number(document.getElementById("photoPlan").value || 0);
    const eligibleLogs = mobilityState.logs.filter(item => item.travel_plan === planId);
    const selected = keepValue(selectedPhotoLog, eligibleLogs);
    const options = [`<option value="">Optional log link</option>`].concat(
        eligibleLogs.map(item => `<option value="${item.id}" ${String(item.id) === selected ? "selected" : ""}>${Alfred.escapeHtml(item.title)} | ${Alfred.escapeHtml(item.travel_plan_title)}</option>`)
    );
    photoLog.innerHTML = options.join("");
    photoLog.disabled = !eligibleLogs.length;
}

function submitTravelPlan(event) {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
    payload.budget = Number(payload.budget || 0);
    payload.vehicle_profile = payload.vehicle_profile ? Number(payload.vehicle_profile) : null;
    Alfred.fetchJSON("/api/mobility/travel-plans/", { method: "POST", body: JSON.stringify(payload) })
        .then(() => {
            showFeedback("travelPlanFeedback", "Travel plan saved.", "success");
            renderTravelAdvicePlaceholder("Travel plan saved. Generate AI Travel Advice to pull live weather and itinerary guidance for the destination.");
            loadMobilityDashboard();
        })
        .catch(error => showFeedback("travelPlanFeedback", error.message, "danger"));
}

function previewTravelAdvice() {
    const form = document.getElementById("travelPlanForm");
    const payload = Object.fromEntries(new FormData(form).entries());
    payload.budget = Number(payload.budget || 0);
    payload.vehicle_profile_id = payload.vehicle_profile ? Number(payload.vehicle_profile) : null;
    if (!payload.destination || !payload.start_date || !payload.end_date) {
        showFeedback("travelPlanFeedback", "Destination, start date, and end date are required for AI travel advice.", "warning");
        return;
    }
    renderTravelAdvicePlaceholder("Pulling live location and weather context...");
    Alfred.fetchJSON("/api/mobility/travel-advisor/preview/", { method: "POST", body: JSON.stringify(payload) })
        .then(renderTravelAdvice)
        .catch(error => renderTravelAdvicePlaceholder(error.message));
}

function submitTripLog(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    if (!payload.travel_plan) {
        showFeedback("tripLogFeedback", "Select a travel plan first.", "warning");
        return;
    }
    payload.travel_plan = Number(payload.travel_plan);
    payload.latitude = optionalNumber(payload.latitude);
    payload.longitude = optionalNumber(payload.longitude);
    payload.distance_km = Number(payload.distance_km || 0);
    payload.spend_amount = Number(payload.spend_amount || 0);
    Alfred.fetchJSON("/api/mobility/trip-logs/", { method: "POST", body: JSON.stringify(payload) })
        .then(() => { form.reset(); setMobilityDefaults(); showFeedback("tripLogFeedback", "Trip log saved.", "success"); loadMobilityDashboard(); })
        .catch(error => showFeedback("tripLogFeedback", error.message, "danger"));
}

function submitTripPhoto(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    if (!formData.get("travel_plan")) {
        showFeedback("tripPhotoFeedback", "Select a travel plan before uploading a photo.", "warning");
        return;
    }
    const payload = new FormData();
    formData.forEach((value, key) => {
        if (value !== "" && value !== null) {
            payload.append(key, value);
        }
    });
    Alfred.fetchJSON("/api/mobility/trip-photos/", { method: "POST", body: payload })
        .then(() => { form.reset(); setMobilityDefaults(); showFeedback("tripPhotoFeedback", "Trip photo uploaded.", "success"); loadMobilityDashboard(); })
        .catch(error => showFeedback("tripPhotoFeedback", error.message, "danger"));
}

function deleteTravelPlan(id) { deleteRecord(`/api/mobility/travel-plans/${id}/`, "Delete this travel plan and its logs/photos?"); }
function deleteTripLog(id) { deleteRecord(`/api/mobility/trip-logs/${id}/`, "Delete this trip log?"); }
function deleteTripPhoto(id) { deleteRecord(`/api/mobility/trip-photos/${id}/`, "Delete this trip photo?"); }

function deleteRecord(url, promptText) {
    if (!window.confirm(promptText)) {
        return;
    }
    Alfred.fetchJSON(url, { method: "DELETE" }).then(loadMobilityDashboard).catch(error => showRootAlert(error.message, "danger"));
}

function showFeedback(id, message, tone) {
    const target = document.getElementById(id);
    target.className = `alert alert-${tone} mb-0`;
    target.textContent = message;
    target.classList.remove("d-none");
}

function hideFeedback(id) {
    const target = document.getElementById(id);
    target.className = "d-none alert mb-0";
    target.textContent = "";
}

function showRootAlert(message, tone) {
    const target = document.getElementById("mobilityPageAlert");
    target.className = message ? `alert alert-${tone} mb-4` : "d-none mb-4";
    target.textContent = message;
}

function renderTravelAdvicePlaceholder(message) {
    document.getElementById("travelAdvisorPanel").innerHTML = `<div class="detail-item">${Alfred.escapeHtml(message)}</div>`;
}

function keepValue(value, items) { return items.some(item => String(item.id) === String(value || "")) ? String(value) : ""; }
function optionalNumber(value) { return value === "" || value === null || value === undefined ? null : Number(value); }
function setMobilityDefaults() {
    document.getElementById("tripStartDate").value = todayLocal();
    document.getElementById("tripEndDate").value = todayLocal();
    document.getElementById("logDate").value = todayLocal();
    document.getElementById("photoTakenAt").value = currentDateTimeLocal();
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

window.deleteTravelPlan = deleteTravelPlan;
window.deleteTripLog = deleteTripLog;
window.deleteTripPhoto = deleteTripPhoto;
