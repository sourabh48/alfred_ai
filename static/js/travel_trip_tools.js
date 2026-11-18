// Trip tools (owner approval 2026-11-18): bookings with confirmation reading, a recorded GPX ride, imported places.
(function () {
    const $ = id => document.getElementById(id), e = Alfred.escapeHtml, n = Alfred.formatNumber;
    if (!$("tripToolsSection")) return;
    const url = () => `/api/mobility/travel-plans/${$("tripToolsPlan").value}/tools/`;

    function say(text, kind = "success") {
        const box = $("tripToolsFeedback");
        box.className = `alert alert-${kind} mb-2`;
        box.textContent = text;
    }

    function send(body, done) {
        if (!$("tripToolsPlan").value) return say("Create a trip first.", "warning");
        const isForm = body instanceof FormData;
        return Alfred.fetchJSON(url(), { method: "POST", body: isForm ? body : JSON.stringify(body) })
            .then(data => { render(data); if (done) done(data.result); })
            .catch(error => say(error.message, "danger"));
    }

    function upload(input, operation, done) {
        const file = input.files[0];
        if (!file) return;
        const form = new FormData();
        form.append("operation", operation);
        form.append("file", file);
        send(form, done).finally(() => { input.value = ""; });
    }

    function profileChart(profile) {
        if (profile.length < 2) return "";
        const W = 600, H = 140, pad = 28, maxKm = profile[profile.length - 1].km || 1;
        const lo = Math.min(...profile.map(p => p.m)), hi = Math.max(...profile.map(p => p.m)), span = Math.max(hi - lo, 1);
        const x = km => pad + (km / maxKm) * (W - pad - 8), y = m => 8 + (1 - (m - lo) / span) * (H - pad - 8);
        const line = profile.map(p => `${x(p.km).toFixed(1)},${y(p.m).toFixed(1)}`).join(" ");
        return `<figure class="mb-2"><svg viewBox="0 0 ${W} ${H}" style="width:100%;max-width:640px;height:auto" role="img" aria-label="Elevation profile from ${n(lo)} m to ${n(hi)} m over ${n(maxKm)} km" id="tripRideChart">
            <line x1="${pad}" y1="${H - pad}" x2="${W - 8}" y2="${H - pad}" stroke="currentColor" stroke-opacity=".25"/>
            <text x="2" y="14" font-size="11" fill="currentColor" opacity=".7">${n(hi)} m</text><text x="2" y="${H - pad}" font-size="11" fill="currentColor" opacity=".7">${n(lo)} m</text>
            <text x="${W - 8}" y="${H - 8}" font-size="11" text-anchor="end" fill="currentColor" opacity=".7">${n(maxKm)} km</text>
            <polyline points="${line}" fill="none" stroke="var(--bs-primary, #2f6fde)" stroke-width="2" stroke-linejoin="round"/>
            <circle r="4" fill="var(--bs-primary, #2f6fde)" stroke="var(--bs-body-bg, #fff)" stroke-width="2" visibility="hidden"/>
            <rect x="${pad}" y="0" width="${W - pad - 8}" height="${H - pad}" fill="transparent"/></svg>
            <figcaption class="small muted" id="tripRideHover">Elevation along the ride. Point at the line for a value.</figcaption></figure>`;
    }

    function bindChart(profile) {
        const svg = $("tripRideChart");
        if (!svg) return;
        const dot = svg.querySelector("circle"), W = 600, pad = 28, maxKm = profile[profile.length - 1].km || 1;
        svg.addEventListener("mousemove", event => {
            const box = svg.getBoundingClientRect(), km = Math.max(0, ((event.clientX - box.left) / box.width * W - pad) / (W - pad - 8) * maxKm);
            const point = profile.reduce((best, p) => Math.abs(p.km - km) < Math.abs(best.km - km) ? p : best, profile[0]);
            const line = svg.querySelector("polyline").points[profile.indexOf(point)];
            dot.setAttribute("cx", line.x); dot.setAttribute("cy", line.y); dot.setAttribute("visibility", "visible");
            $("tripRideHover").textContent = `${n(point.km)} km: ${n(point.m)} m`;
        });
    }

    function render(data) {
        const b = data.bookings || [];
        $("tripBookingsList").innerHTML = b.length ? `<ul class="list-unstyled small mb-0">${b.map(x => `<li class="mb-2">
            <span class="badge text-bg-light me-1">${e(x.kind)}</span><span class="fw-semibold">${e(x.title)}</span>${x.confirmation ? ` · code ${e(x.confirmation)}` : ""}
            <br><span class="muted">${e([x.start && x.start.replace("T", " "), x.end && `to ${x.end.replace("T", " ")}`, x.place, x.provider,
                x.amount && `${x.currency} ${x.amount} paid`].filter(Boolean).join(" · ") || "No details")}</span>
            <button type="button" class="btn btn-link btn-sm p-0 ms-1" data-booking-remove="${e(x.id)}" aria-label="Remove ${e(x.title)}">Remove</button></li>`).join("")}</ul>`
            : '<p class="small mb-0">No bookings recorded for this trip.</p>';
        const r = data.ride;
        if (r) {
            const row = (label, value) => value === null || value === undefined ? "" : `<li>${label}: ${value}</li>`;
            $("tripRideBody").innerHTML = `${profileChart(r.profile || [])}<ul class="small mb-2">
                ${row("Distance", `${n(r.distance_km)} km`)}${r.compare ? row("Plan", `${n(r.compare.planned_km)} km, so the ride was ${n(Math.abs(r.compare.difference_km))} km ${r.compare.difference_km >= 0 ? "longer" : "shorter"}`) : ""}
                ${row("Climb", r.ascent_m === null ? null : `${n(r.ascent_m)} m up, ${n(r.descent_m)} m down`)}${row("Height", r.highest_m === null ? null : `${n(r.lowest_m)} to ${n(r.highest_m)} m`)}
                ${row("Steepest", r.steepest_climb_pct === null && r.steepest_descent_pct === null ? null : `${r.steepest_climb_pct ?? 0}% up, ${r.steepest_descent_pct ?? 0}% down (over 100 m stretches)`)}
                ${row("Time", r.total_hours === null ? null : `${n(r.total_hours)} h total${r.moving_hours ? `, ${n(r.moving_hours)} h moving` : ""}`)}</ul>
                <p class="small muted mb-0">From ${e(r.file)} (${n(r.points)} GPS points).${r.compare ? ` ${e(r.compare.basis)}` : " This trip has no planned distance to compare with."}</p>`;
            bindChart(r.profile || []);
        } else $("tripRideBody").innerHTML = '<p class="small mb-0">No ride loaded for this trip.</p>';
        const p = data.places || [];
        $("tripPlacesBody").innerHTML = p.length ? `<ul class="small mb-0">${p.map(x => `<li>${x.link ? `<a href="${e(x.link)}" target="_blank" rel="noopener noreferrer">${e(x.name)}</a>` : e(x.name)}
            <span class="muted">${x.lat !== null ? ` (${x.lat}, ${x.lon})` : ""}${x.note ? ` · ${e(x.note)}` : ""} · ${e(x.source)}</span>
            <button type="button" class="btn btn-link btn-sm p-0 ms-1" data-place-remove="${e(x.id)}" aria-label="Remove ${e(x.name)}">Remove</button></li>`).join("")}</ul>`
            : '<p class="small mb-0">No places imported for this trip.</p>';
    }

    function load() {
        if ($("tripToolsPlan").value) Alfred.fetchJSON(url()).then(render).catch(error => say(error.message, "danger"));
    }

    Alfred.fetchJSON("/api/mobility/travel-plans/").then(data => {
        const plans = Array.isArray(data) ? data : data.results || [];
        $("tripToolsPlan").innerHTML = plans.length ? plans.map(p => `<option value="${e(p.id)}">${e(p.title)}${p.start_date ? ` (${e(p.start_date)})` : ""}</option>`).join("")
            : '<option value="">No trips yet</option>';
        load();
    }).catch(error => say(error.message, "danger"));
    $("tripToolsPlan").addEventListener("change", load);

    function fill(draft) {
        const set = (id, value) => { if (value) $(id).value = value; };
        set("tripBookingKind", draft.kind); set("tripBookingTitle", draft.title); set("tripBookingCode", draft.confirmation);
        set("tripBookingStart", draft.start && (draft.start.includes("T") ? draft.start : `${draft.start}T00:00`));
        set("tripBookingEnd", draft.end && (draft.end.includes("T") ? draft.end : `${draft.end}T00:00`));
        set("tripBookingPlace", draft.place); set("tripBookingProvider", draft.provider); set("tripBookingAmount", draft.amount); set("tripBookingCurrency", draft.currency);
    }
    const reading = () => say("Your local AI is reading the confirmation. This can take up to a minute.", "info");
    const filled = r => { fill(r.draft); say(r.basis, "warning"); };
    $("tripBookingRead").addEventListener("click", () => { reading(); send({ operation: "booking_read", text: $("tripBookingText").value }, filled); });
    $("tripBookingPdf").addEventListener("change", event => { reading(); upload(event.target, "booking_read", filled); });
    $("tripBookingForm").addEventListener("submit", event => {
        event.preventDefault();
        const booking = Object.fromEntries(new FormData(event.target).entries());
        send({ operation: "booking_add", booking }, () => { event.target.reset(); $("tripBookingText").value = ""; say("Booking saved."); });
    });
    $("tripRideFile").addEventListener("change", event => upload(event.target, "ride", () => say("Ride loaded.")));
    $("tripPlacesFile").addEventListener("change", event => upload(event.target, "places", r => say(`Found ${n(r.found)} places; added ${n(r.added)} new.`)));
    $("tripToolsSection").addEventListener("click", event => {
        const booking = event.target.closest("[data-booking-remove]"), place = event.target.closest("[data-place-remove]");
        if (booking) send({ operation: "booking_remove", id: booking.dataset.bookingRemove }, () => say("Booking removed."));
        if (place) send({ operation: "place_remove", id: place.dataset.placeRemove }, () => say("Place removed."));
    });

    const lookup = (body, done) => Alfred.fetchJSON("/api/mobility/travel-lookup/", { method: "POST", body: JSON.stringify(body) })
        .then(done).catch(error => say(error.message, "danger"));
    const clock = iso => iso ? new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";
    $("tripHolidaysYear").value = new Date().getFullYear();
    $("tripTransitForm").addEventListener("submit", event => {
        event.preventDefault();
        lookup({ operation: "transit", origin: $("tripTransitFrom").value, destination: $("tripTransitTo").value, departure: $("tripTransitWhen").value }, r => {
            $("tripTransitBody").innerHTML = `${r.routes.map((route, i) => `<div class="mb-2"><p class="small fw-semibold mb-1">Option ${i + 1}: ${n(route.minutes)} min${route.fare ? `, fare about ${e(route.fare.currency)} ${e(route.fare.amount)}` : ""}</p>
                <ol class="small mb-0">${route.steps.map(s => s.mode === "WALK" ? `<li>Walk ${s.minutes ? `${n(s.minutes)} min` : ""}${s.note ? ` · ${e(s.note)}` : ""}</li>`
                    : `<li>${e(s.vehicle || "Transit")} ${e(s.line)}${s.headsign ? ` towards ${e(s.headsign)}` : ""}: ${e(s.from)} ${e(clock(s.depart))} to ${e(s.to)} ${e(clock(s.arrive))}
                        <span class="muted">(${n(s.stops)} stops${s.agency ? `, ${e(s.agency)}` : ""})</span></li>`).join("")}</ol></div>`).join("")}
                <p class="small muted mb-0">${e(r.note)} ${e(r.attribution)}.${r.stale ? " Saved earlier; Google could not be reached now." : ""}</p>`;
        });
    });
    $("tripHolidaysForm").addEventListener("submit", event => {
        event.preventDefault();
        lookup({ operation: "holidays", country: $("tripHolidaysCountry").value, year: $("tripHolidaysYear").value }, r => {
            const day = iso => new Date(`${iso}T00:00`).toLocaleDateString([], { weekday: "short", day: "numeric", month: "short" });
            $("tripHolidaysBody").innerHTML = `<p class="small fw-semibold mb-1">Long weekends in ${e(r.country)}, ${e(r.year)}</p>
                <ul class="small mb-2">${r.long_weekends.map(w => `<li>${e(day(w.start))} to ${e(day(w.end))}: ${n(w.days)} days off${w.leave_days.length
                    ? ` if you take ${w.leave_days.map(d => e(day(d))).join(", ")} as leave` : " with no leave needed"}</li>`).join("") || "<li>None listed.</li>"}</ul>
                <p class="small fw-semibold mb-1">Public holidays</p>
                <ul class="small mb-2">${r.holidays.map(h => `<li>${e(day(h.date))}: ${e(h.name)}${h.english && h.english !== h.name ? ` (${e(h.english)})` : ""}${h.national ? "" : `<span class="muted"> · regional: ${e(h.regions.join(", ") || "some regions")}</span>`}</li>`).join("")}</ul>
                <p class="small muted mb-0">${e(r.basis)}</p>`;
        });
    });
})();
