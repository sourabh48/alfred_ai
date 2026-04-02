let salaryChart;
let careerSimulationBaseline = null;
let careerOpeningFilters = { country: "", state: "" };

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("careerRoot")) {
        return;
    }

    document.getElementById("careerProfileForm").addEventListener("submit", submitCareerProfile);
    document.getElementById("careerResumeForm").addEventListener("submit", submitCareerResume);
    document.getElementById("careerJobMatchForm").addEventListener("submit", submitCareerJobMatch);
    document.getElementById("careerRecruiterForm").addEventListener("submit", submitCareerRecruiterLead);
    document.getElementById("careerSimulationForm").addEventListener("submit", submitCareerSimulation);
    document.getElementById("careerOpeningCountryFilter")?.addEventListener("change", updateCareerOpeningFilters);
    document.getElementById("careerOpeningStateFilter")?.addEventListener("change", updateCareerOpeningFilters);
    loadCareerDashboard();
    Alfred.enableLiveRefresh("career-live", loadCareerDashboard, { rootId: "careerRoot" });
});

function loadCareerDashboard(options = {}) {
    Alfred.setPageBusy("careerRoot", true, { label: "Loading career intelligence" });
    return Alfred.fetchJSON(`/api/career/dashboard/${careerDashboardQueryString()}`)
        .then(data => {
            const profile = data.profile || {};
            const projection = data.projection || {};
            careerSimulationBaseline = projection;
            const timing = data.career_timing || {};
            renderCareerHero(profile, projection, timing);
            renderCareerSummary(profile, projection, data.latest_resume, data.latest_job_analysis, data.market, timing);
            renderCareerChart(projection.projections || []);
            renderCareerInsights(projection.insights || [projection.message || "No projections yet."], data.market?.insights || [], timing);
            renderCareerMacroContext(projection.macro_context || {}, projection.projection_basis || {});
            renderCareerEvidence([...(projection.evidence || []), ...(data.market?.evidence || []), data.openings_evidence].filter(Boolean));
            renderCareerTiming(timing);
            renderCareerDataPipeline(data.data_pipeline || {});
            renderCareerSnapshot(profile);
            renderCareerProjectionTable(projection || {});
            renderResumePanel(data.latest_resume);
            renderJobMatchPanel(data.latest_job_analysis);
            renderCompensationBenchmark(data.compensation_benchmark || {});
            renderStudyPlan(data.study_recommendations || {});
            renderLayoffNews(data.market?.layoff_news || []);
            renderOpeningFilters(data.opening_filters || {}, data.active_opening_filters || careerOpeningFilters);
            renderOpenings(data.openings || [], data.opening_counts || {});
            renderSimulationPanel();
            if (!options.live) {
                hydrateCareerForm(profile);
                hydrateSimulationForm(profile, projection);
            }
            Alfred.clearPageAlert("careerRoot");
        })
        .catch(error => {
            Alfred.upsertPageAlert("careerRoot", error.message, "danger");
        })
        .finally(() => Alfred.setPageBusy("careerRoot", false));
}

function careerDashboardQueryString() {
    const params = new URLSearchParams();
    if (careerOpeningFilters.country) {
        params.set("country", careerOpeningFilters.country);
    }
    if (careerOpeningFilters.state) {
        params.set("state", careerOpeningFilters.state);
    }
    const query = params.toString();
    return query ? `?${query}` : "";
}

function updateCareerOpeningFilters(event) {
    const target = event.currentTarget;
    if (target.id === "careerOpeningCountryFilter") {
        careerOpeningFilters.country = target.value || "";
        careerOpeningFilters.state = "";
    } else {
        careerOpeningFilters.state = target.value || "";
    }
    loadCareerDashboard({ live: true });
}

function renderOpeningFilters(filters, active) {
    careerOpeningFilters = {
        country: active?.country || careerOpeningFilters.country || "",
        state: active?.state || careerOpeningFilters.state || "",
    };
    const countrySelect = document.getElementById("careerOpeningCountryFilter");
    const stateSelect = document.getElementById("careerOpeningStateFilter");
    if (!countrySelect || !stateSelect) {
        return;
    }

    const countries = Array.isArray(filters?.countries) ? filters.countries : [];
    const statesByCountry = filters?.states_by_country || {};
    countrySelect.innerHTML = `<option value="">All countries</option>${countries.map(country => `
        <option value="${Alfred.escapeHtml(country)}"${country === careerOpeningFilters.country ? " selected" : ""}>${Alfred.escapeHtml(country)}</option>
    `).join("")}`;

    const states = careerOpeningFilters.country ? (statesByCountry[careerOpeningFilters.country] || []) : [];
    if (!states.includes(careerOpeningFilters.state)) {
        careerOpeningFilters.state = "";
    }
    stateSelect.disabled = !states.length;
    stateSelect.innerHTML = `<option value="">All states</option>${states.map(state => `
        <option value="${Alfred.escapeHtml(state)}"${state === careerOpeningFilters.state ? " selected" : ""}>${Alfred.escapeHtml(state)}</option>
    `).join("")}`;
}

function renderCareerHero(profile, projection, timing) {
    const latest = (projection.projections || []).at(-1);
    document.getElementById("careerRoleValue").textContent = profile.role || "Profile pending";
    document.getElementById("careerIncomeValue").textContent = Alfred.formatCurrency(projection.current_income || profile.last_salary || 0);
    if (timing?.window_start && timing?.window_end) {
        document.getElementById("careerGrowthCopy").textContent = `${timing.summary} Window ${Alfred.formatDate(timing.window_start)} to ${Alfred.formatDate(timing.window_end)}.`;
        return;
    }
    document.getElementById("careerGrowthCopy").textContent = latest
        ? `Year 5 projection ${Alfred.formatCurrency(latest.projected_income)}`
        : (projection.message || "Create a profile to unlock projections.");
}

function renderCareerSummary(profile, projection, resume, jobAnalysis, market, timing) {
    const latest = (projection.projections || []).at(-1);
    const projectionConfidence = projection.projection_confidence || {};
    const cards = [
        { title: "Experience", value: `${Alfred.formatNumber(profile.experience_years, 1)} yrs`, copy: profile.role || "Role pending" },
        { title: "Resume Parse", value: resume ? `${Alfred.formatNumber((resume.parse_confidence || 0) * 100, 0)}%` : "No resume", copy: resume ? (resume.parser_status_label || "Parsed") : "Upload a resume" },
        { title: "Job Fit", value: jobAnalysis ? `${Alfred.formatNumber(jobAnalysis.fit_score || 0, 0)}/100` : "No job link", copy: jobAnalysis ? `${Alfred.escapeHtml(jobAnalysis.company || jobAnalysis.source_name || "Latest analysis")}` : "Paste a job URL" },
        {
            title: "Career Timing",
            value: timing?.readiness_score != null ? `${Alfred.formatNumber(timing.readiness_score || 0, 0)}/100` : (market ? `${Alfred.formatNumber(market.risk_score || 0, 0)}/100` : "N/A"),
            copy: timing?.summary || projectionConfidence.summary || (latest ? `Year 5 projection ${Alfred.formatCurrency(latest.projected_income || 0)}` : "Projection pending"),
        },
    ];

    document.getElementById("careerSummaryCards").innerHTML = cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.title}</p>
            <h2 class="metric-value">${card.value}</h2>
            <p class="metric-caption">${card.copy}</p>
        </article>
    `).join("");
}

function renderCareerChart(items) {
    const canvas = document.getElementById("salaryChart");
    if (salaryChart) {
        salaryChart.destroy();
    }

    salaryChart = new Chart(canvas, {
        type: "line",
        data: {
            labels: items.map(item => `Year ${item.year}`),
            datasets: [{
                label: "Projected income",
                data: items.map(item => item.projected_income),
                borderColor: "#148f63",
                backgroundColor: "rgba(20, 143, 99, 0.14)",
                fill: true,
                tension: 0.3,
            }],
        },
        options: {
            plugins: { legend: { display: false } },
        },
    });
}

function renderCareerInsights(projectionInsights, marketInsights, timing) {
    const target = document.getElementById("careerInsightList");
    const items = [...projectionInsights, ...(timing?.signals || []), ...marketInsights].slice(0, 7);
    target.innerHTML = items.map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join("");
}

function renderCareerSnapshot(profile) {
    document.getElementById("careerProfileSnapshot").innerHTML = [
        ["Role", profile.role || "Profile pending"],
        ["Experience", `${Alfred.formatNumber(profile.experience_years, 1)} years`],
        ["Skills", profile.skills || "No skills listed yet."],
        ["Current income", Alfred.formatCurrency(profile.last_salary || 0)],
    ].map(([label, value]) => `
        <div class="data-row">
            <div class="data-label">${label}</div>
            <div class="data-value">${Alfred.escapeHtml(String(value))}</div>
        </div>
    `).join("");
}

function renderCareerProjectionTable(projection) {
    const target = document.getElementById("careerProjectionTable");
    const items = projection?.projections || [];
    const projectionConfidence = projection?.projection_confidence || {};
    const reasoning = Array.isArray(projection?.reasoning) ? projection.reasoning : [];
    if (!items.length) {
        target.innerHTML = `<div class="empty-state">Projection data is not available yet.</div>`;
        return;
    }

    const confidenceHeader = projectionConfidence?.label
        ? `
            <div class="mini-card">
                <div class="fw-semibold">${Alfred.escapeHtml(projectionConfidence.label)}</div>
                <div class="muted small mt-1">${Alfred.escapeHtml(
                    projectionConfidence.score != null
                        ? `${Alfred.formatNumber(projectionConfidence.score, 1)}/100`
                        : "Not attached"
                )}</div>
                <div class="muted small mt-2">${Alfred.escapeHtml(projectionConfidence.summary || "")}</div>
                <div class="muted small mt-2">${Alfred.escapeHtml(projectionConfidence.method || "")}</div>
            </div>
        `
        : "";

    const reasoningPanel = reasoning.length ? `
        <div class="mini-card">
            <div class="fw-semibold">Why the projection moves this way</div>
            <div class="muted small mt-1">${Alfred.escapeHtml(projection.explainability_note || "")}</div>
            <div class="data-stack mt-3">
                ${reasoning.map(item => `
                    <div class="data-row">
                        <div class="data-label">${Alfred.escapeHtml(item.label || "")}</div>
                        <div class="data-value">${Alfred.escapeHtml(item.detail || "")} <div class="muted small mt-1">${Alfred.escapeHtml(item.source || "")}</div></div>
                    </div>
                `).join("")}
            </div>
        </div>
    ` : "";

    target.innerHTML = `${confidenceHeader}${reasoningPanel}${items.map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">Year ${item.year}</div>
                    <div class="muted small">Real ${Alfred.formatCurrency(item.real_income_estimate || item.projected_income)}</div>
                </div>
                <strong>${Alfred.formatCurrency(item.projected_income)}</strong>
            </div>
        </div>
    `).join("")}`;
}

function renderCareerMacroContext(context, basis) {
    document.getElementById("careerMacroContext").innerHTML = [
        ["Unemployment", context.unemployment?.latest_value ?? "N/A", context.unemployment?.latest_year || "Latest available"],
        ["Inflation", context.inflation?.latest_value ?? "N/A", context.inflation?.latest_year || "Latest available"],
        ["Market 1M Return", context.market?.one_month_return_pct ?? "N/A", "India market snapshot"],
        ["Skill Count", basis.skills_count ?? 0, "Manual profile skill count"],
        ["Macro Drag", `${Alfred.formatNumber(basis.macro_drag || 0, 1)} pts`, "Pressure applied to growth rate"],
    ].map(([label, value, note]) => `
        <div class="data-row">
            <div class="data-label">${label}</div>
            <div class="data-value">${Alfred.escapeHtml(String(value))} <span class="muted small">${Alfred.escapeHtml(String(note))}</span></div>
        </div>
    `).join("");
}

function renderCareerEvidence(items) {
    const target = document.getElementById("careerEvidenceList");
    const unique = dedupeEvidence(items);
    target.innerHTML = unique.length ? unique.map(item => `
        <div class="mini-card">
            <div class="fw-semibold">${Alfred.escapeHtml(item.title || item.source_name)}</div>
            <div class="muted small">${Alfred.escapeHtml(item.source_name || "Source")} | refreshed ${Alfred.formatDateTime(item.verified_at)}</div>
            <div class="muted small mt-2">${Alfred.escapeHtml(item.summary || "")}</div>
            <div class="mt-2"><a href="${item.source_url}" target="_blank" rel="noopener">Open source</a></div>
        </div>
    `).join("") : `<div class="empty-state">No evidence records available yet.</div>`;
}

function renderCareerTiming(timing) {
    const target = document.getElementById("careerTimingPanel");
    if (!timing || (!timing.summary && !timing.window_start)) {
        target.innerHTML = `<div class="empty-state">Career timing guidance will appear once Alfred has enough profile, market, and financial data.</div>`;
        return;
    }

    target.innerHTML = `
        <div class="mini-card">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">Readiness ${Alfred.formatNumber(timing.readiness_score || 0, 0)}/100</div>
                    <div class="muted small mt-1">${Alfred.escapeHtml(timing.summary || "")}</div>
                    <div class="muted small mt-2">Window ${Alfred.formatDate(timing.window_start)} to ${Alfred.formatDate(timing.window_end)} | review again on ${Alfred.formatDate(timing.next_review_date)}</div>
                    <div class="muted small mt-2">${Alfred.escapeHtml(timing.next_step || "")}</div>
                </div>
                <span class="status-pill ${careerTone(timing.readiness_level)}">${Alfred.escapeHtml(timing.readiness_level || "guarded")}</span>
            </div>
        </div>
        <div class="mini-card">
            <div class="fw-semibold mb-2">Current signals</div>
            <ul class="insight-list mb-0">
                ${(timing.signals || []).map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join("")}
            </ul>
        </div>
        <div class="mini-card">
            <div class="fw-semibold mb-2">What blocks a bigger move</div>
            <ul class="insight-list mb-0">
                ${(timing.blockers || []).map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join("")}
            </ul>
        </div>
        <div class="mini-card">
            <div class="fw-semibold mb-2">Recommended move types</div>
            <div class="data-stack">
                ${(timing.moves || []).map(item => `
                    <div class="data-row">
                        <div class="data-label">${Alfred.escapeHtml(item.label)}</div>
                        <div class="data-value"><span class="status-pill ${careerTone(item.status)}">${Alfred.escapeHtml(item.status)}</span> <span class="muted small">${Alfred.escapeHtml(item.note || "")}</span></div>
                    </div>
                `).join("")}
            </div>
        </div>
    `;
}

function renderCareerDataPipeline(pipeline) {
    const target = document.getElementById("careerDataPipeline");
    const sections = [
        ["Collected", pipeline.collection || []],
        ["Processed", pipeline.processing || []],
        ["Verified", pipeline.verification || []],
        ["Current State", pipeline.current_state || []],
    ].filter(([, items]) => items.length);

    target.innerHTML = sections.length ? sections.map(([label, items]) => `
        <div class="mini-card">
            <div class="fw-semibold mb-2">${Alfred.escapeHtml(label)}</div>
            <ul class="insight-list mb-0">
                ${items.map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join("")}
            </ul>
        </div>
    `).join("") : `<div class="empty-state">Collection and processing details are not available yet.</div>`;
}

function renderResumePanel(resume) {
    const target = document.getElementById("careerResumePanel");
    if (!resume) {
        target.innerHTML = `<div class="empty-state">No parsed resume yet. Upload one to unlock stronger strengths, weaknesses, and job-fit analysis.</div>`;
        return;
    }
    const payload = resume.extracted_payload || {};
    const skillChips = (payload.skills || []).length
        ? `<div class="d-flex flex-wrap gap-2 mt-2">${payload.skills.slice(0, 16).map(skill => `<span class="status-pill neutral">${Alfred.escapeHtml(skill)}</span>`).join("")}</div>`
        : `<div class="muted small mt-2">No skill list extracted.</div>`;
    const linksBlock = (payload.links || []).length
        ? `<div class="mt-3">${payload.links.slice(0, 4).map(link => `<div><a href="${link}" target="_blank" rel="noopener">${Alfred.escapeHtml(link)}</a></div>`).join("")}</div>`
        : `<div class="muted small mt-3">No portfolio, LinkedIn, or project link detected.</div>`;
    const extractionMethod = payload.extraction_method
        ? payload.extraction_method.replaceAll("_", " ")
        : "unknown";
    const extractionNotes = (payload.extraction_notes || []).length
        ? `<div class="muted small mt-2">${Alfred.escapeHtml(payload.extraction_notes.join(" "))}</div>`
        : "";
    target.innerHTML = `
        <div class="mini-card">
            <div class="fw-semibold">${Alfred.escapeHtml(resume.file_name || "Latest resume")}</div>
            <div class="muted small">${Alfred.escapeHtml(resume.parser_status_label || "Parsed")} | confidence ${Alfred.formatNumber((resume.parse_confidence || 0) * 100, 0)}%</div>
            <div class="muted small mt-2">${Alfred.escapeHtml(resume.summary || "")}</div>
            <div class="muted small mt-2">Role ${Alfred.escapeHtml(payload.role || "Unknown")} | Experience ${Alfred.formatNumber(payload.experience_years || 0, 1)} years</div>
            <div class="muted small mt-2">Extraction path ${Alfred.escapeHtml(extractionMethod)}</div>
            ${skillChips}
            <div class="mt-3">
                <div class="fw-semibold small mb-2">Strengths</div>
                ${renderCareerBulletList(resume.strengths)}
            </div>
            <div class="mt-3">
                <div class="fw-semibold small mb-2">Weaknesses</div>
                ${renderCareerBulletList(resume.weaknesses)}
            </div>
            <div class="mt-3">
                <div class="fw-semibold small mb-2">Detected links</div>
                ${linksBlock}
            </div>
            ${extractionNotes}
        </div>
    `;
}

function renderCareerBulletList(value) {
    const items = String(value || "")
        .split("\n")
        .map(item => item.trim())
        .filter(Boolean);
    if (!items.length) {
        return `<div class="muted small">None detected.</div>`;
    }
    return `<ul class="insight-list mb-0">${items.map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join("")}</ul>`;
}

function renderJobMatchPanel(analysis) {
    const target = document.getElementById("careerJobMatchPanel");
    if (!analysis) {
        target.innerHTML = `<div class="empty-state">No job link analyzed yet.</div>`;
        return;
    }
    const payload = analysis.extracted_payload || {};
    const fit = payload.fit || {};
    const compensation = payload.compensation_benchmark || {};
    target.innerHTML = `
        <div class="mini-card">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(analysis.job_title || "Job role")} <span class="muted small">${Alfred.escapeHtml(analysis.company || analysis.source_name || "")}</span></div>
                    <div class="muted small">${Alfred.escapeHtml(analysis.location || "Location not detected")}</div>
                    <div class="muted small mt-1">Source ${Alfred.escapeHtml(payload.job_snapshot?.source_kind || "job_page")}</div>
                    <div class="muted small mt-2">${Alfred.escapeHtml(analysis.summary || "")}</div>
                    <div class="muted small mt-2"><strong>Matched:</strong> ${fit.matched_skills?.length ? Alfred.escapeHtml(fit.matched_skills.join(", ")) : "No strong overlap detected."}</div>
                    <div class="muted small mt-2"><strong>Gaps:</strong> ${fit.missing_skills?.length ? Alfred.escapeHtml(fit.missing_skills.join(", ")) : "No major gap extracted."}</div>
                    <div class="muted small mt-2"><strong>Compensation:</strong> ${compensation.available ? Alfred.escapeHtml(`${Alfred.formatCurrency(compensation.market_min_annual || 0)} to ${Alfred.formatCurrency(compensation.market_max_annual || compensation.market_min_annual || 0)} annual`) : "No salary-bearing evidence detected yet."}</div>
                    <div class="muted small mt-2">${Alfred.escapeHtml(analysis.strengths || "")}</div>
                    <div class="muted small mt-2">${Alfred.escapeHtml(analysis.gaps || "")}</div>
                    <div class="mt-2"><a href="${analysis.apply_url || analysis.job_url}" target="_blank" rel="noopener">Open job link</a></div>
                </div>
                <div class="text-end">
                    <div class="metric-value" style="font-size:1.6rem;">${Alfred.formatNumber(analysis.fit_score || 0, 0)}/100</div>
                    <div class="muted small">Fit score</div>
                    <div class="mt-2 muted small">Risk ${Alfred.formatNumber(analysis.market_risk_score || 0, 0)}/100</div>
                </div>
            </div>
        </div>
    `;
}

function renderCompensationBenchmark(benchmark) {
    const target = document.getElementById("careerCompensationPanel");
    if (!benchmark || !benchmark.available) {
        target.innerHTML = `<div class="mini-card"><div class="fw-semibold">Compensation Benchmark</div><div class="muted small mt-2">${Alfred.escapeHtml(benchmark?.summary || "Salary evidence will appear when Alfred finds pay-bearing job signals.")}</div></div>`;
        return;
    }
    target.innerHTML = `
        <div class="mini-card">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">Compensation Benchmark</div>
                    <div class="muted small mt-1">${Alfred.escapeHtml(benchmark.location_scope || "Global / Remote")} | ${benchmark.sample_count || 0} evidence point(s)</div>
                    <div class="muted small mt-2">${Alfred.escapeHtml(benchmark.summary || "")}</div>
                </div>
                <div class="text-end">
                    <div class="metric-value" style="font-size:1.4rem;">${Alfred.formatCurrency(benchmark.market_mid_annual || benchmark.market_min_annual || 0)}</div>
                    <div class="muted small">Mid benchmark / year</div>
                </div>
            </div>
            <div class="muted small mt-3"><strong>Band:</strong> ${Alfred.formatCurrency(benchmark.market_min_annual || 0)} to ${Alfred.formatCurrency(benchmark.market_max_annual || benchmark.market_min_annual || 0)} annual</div>
        </div>
    `;
}

function renderStudyPlan(plan) {
    const target = document.getElementById("careerStudyPlan");
    if (!plan || !(plan.tracks || []).length) {
        target.innerHTML = `<div class="empty-state">Study recommendations will appear once Alfred has enough profile, resume, or job-gap data.</div>`;
        return;
    }

    target.innerHTML = `
        <div class="mini-card">
            <div class="fw-semibold">${Alfred.escapeHtml(plan.experience_stage || "Current stage")}</div>
            <div class="muted small mt-1">${Alfred.escapeHtml(plan.stage_note || "")}</div>
            <div class="muted small mt-2">${Alfred.escapeHtml(plan.focus_window || "")}</div>
        </div>
        <div class="mini-card">
            <div class="fw-semibold mb-2">Why this list exists</div>
            <ul class="insight-list mb-0">
                ${(plan.signals || []).map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join("")}
            </ul>
        </div>
        ${(plan.tracks || []).map(item => `
            <div class="mini-card">
                <div class="d-flex justify-content-between align-items-start gap-3">
                    <div>
                        <div class="fw-semibold">${Alfred.escapeHtml(item.skill || "Skill")}</div>
                        <div class="muted small mt-1">${Alfred.escapeHtml(item.reason || "")}</div>
                        <div class="muted small mt-2">${Alfred.escapeHtml((item.grounded_in || []).join(" | "))}</div>
                    </div>
                    <span class="status-pill ${careerPriorityTone(item.priority)}">${Alfred.escapeHtml(item.priority || "medium")}</span>
                </div>
            </div>
        `).join("")}
    `;
}

function renderLayoffNews(items) {
    const target = document.getElementById("careerLayoffNews");
    target.innerHTML = items.length ? items.map(item => `
        <div class="mini-card">
            <div class="fw-semibold">${Alfred.escapeHtml(item.title || "News item")}</div>
            <div class="muted small">${Alfred.escapeHtml(item.source || "Unknown source")} | ${Alfred.escapeHtml(item.published || "No publish time")}</div>
            <div class="mt-2"><a href="${item.link}" target="_blank" rel="noopener">Open article</a></div>
        </div>
    `).join("") : `<div class="empty-state">No layoff news items were pulled from the configured feed right now.</div>`;
}

function renderOpenings(items, counts = {}) {
    const target = document.getElementById("careerOpenings");
    const meta = document.getElementById("careerOpeningsMeta");
    if (meta) {
        const filteredCount = Number(counts.filtered_candidates || items.length || 0);
        const totalCount = Number(counts.total_candidates || filteredCount);
        meta.textContent = filteredCount === totalCount
            ? `${filteredCount} verified opening${filteredCount === 1 ? "" : "s"} matched your profile right now.`
            : `${filteredCount} of ${totalCount} verified openings match the active location filter.`;
    }
    target.innerHTML = items.length ? items.map(item => `
        <div class="mini-card">
            <div class="fw-semibold">${Alfred.escapeHtml(item.title || "Opening")}</div>
            <div class="muted small">${Alfred.escapeHtml(item.company || "Unknown company")} | ${Alfred.escapeHtml(item.location || "Remote")}</div>
            <div class="muted small">${Alfred.escapeHtml(item.category || "")}${item.salary ? ` | ${Alfred.escapeHtml(item.salary)}` : ""}</div>
            <div class="muted small mt-2">${item.tags?.length ? Alfred.escapeHtml(item.tags.join(", ")) : ""}</div>
            <div class="muted small mt-2">${Alfred.escapeHtml(item.portal_name || "Verified portal")} | relevance ${Alfred.formatNumber(item.relevance_score || 0, 0)}/100${item.verified_source ? " | verified source" : ""}</div>
            <div class="muted small mt-2">${(item.match_reasons || []).length ? Alfred.escapeHtml(item.match_reasons.join(" ")) : "Matched from your role and tracked skills."}</div>
            <div class="mt-2"><a href="${item.url}" target="_blank" rel="noopener">Apply</a></div>
        </div>
    `).join("") : `<div class="empty-state">No live openings were returned from the configured job source for the current role.</div>`;
}

function hydrateCareerForm(profile) {
    const form = document.getElementById("careerProfileForm");
    form.role.value = profile.role || "";
    form.experience_years.value = profile.experience_years ?? 0;
    form.skills.value = profile.skills || "";
    form.last_salary.value = profile.last_salary ?? 0;
}

function submitCareerProfile(event) {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
    payload.experience_years = Number(payload.experience_years || 0);
    payload.last_salary = Number(payload.last_salary || 0);

    Alfred.fetchJSON("/api/career/", {
        method: "PUT",
        body: JSON.stringify(payload),
    })
        .then(() => {
            showCareerFeedback("careerFormFeedback", "Career profile updated.", "success");
            loadCareerDashboard();
        })
        .catch(error => showCareerFeedback("careerFormFeedback", error.message, "danger"));
}

function submitCareerResume(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const fileInput = form.elements.resume;
    const files = Array.from(fileInput?.files || []);
    if (!files.length) {
        showCareerFeedback("careerResumeFeedback", "Choose at least one resume or CV file first.", "warning");
        return;
    }

    const submitButton = form.querySelector("button[type='submit']");
    if (submitButton) {
        submitButton.disabled = true;
    }

    Alfred.showUploadProgress("careerResumeFeedback", {
        phase: "preparing",
        percent: 0,
        current: 1,
        total: files.length,
    });

    Alfred.uploadFilesSequentially(
        files,
        (file, uploadContext) => Alfred.uploadJSON("/api/career/resumes/upload/", {
            method: "POST",
            body: Alfred.buildSingleFileFormData(form, "resume", file),
            onUploadState: uploadContext?.reportProgress,
        }),
        {
            onProgress: state => Alfred.showUploadProgress("careerResumeFeedback", state),
        },
    )
        .then(results => {
            const summary = summarizeCareerResumeBatch(results);
            if (summary.succeeded.length) {
                form.reset();
                loadCareerDashboard();
            }
            showCareerFeedback("careerResumeFeedback", summary.message, summary.tone);
        })
        .finally(() => {
            if (submitButton) {
                submitButton.disabled = false;
            }
        });
}

function submitCareerJobMatch(event) {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
    Alfred.fetchJSON("/api/career/job-match/", {
        method: "POST",
        body: JSON.stringify(payload),
    })
        .then(() => {
            showCareerFeedback("careerJobFeedback", "Job link analyzed.", "success");
            loadCareerDashboard();
        })
        .catch(error => showCareerFeedback("careerJobFeedback", error.message, "danger"));
}

function submitCareerRecruiterLead(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const textValue = form.elements.message_text?.value?.trim() || "";
    const attachment = form.elements.attachment?.files?.[0];
    if (!textValue && !attachment) {
        showCareerFeedback("careerRecruiterFeedback", "Paste recruiter mail text or choose a JD attachment first.", "warning");
        return;
    }
    Alfred.fetchJSON("/api/career/recruiter-match/", {
        method: "POST",
        body: new FormData(form),
    })
        .then(() => {
            form.reset();
            showCareerFeedback("careerRecruiterFeedback", "Recruiter lead analyzed.", "success");
            loadCareerDashboard();
        })
        .catch(error => showCareerFeedback("careerRecruiterFeedback", error.message, "danger"));
}

function hydrateSimulationForm(profile, projection) {
    const form = document.getElementById("careerSimulationForm");
    form.monthly_income.value = projection.current_income || profile.last_salary || "";
    form.variable_income.value = "";
    form.rent_or_emi.value = "";
    form.city.value = "";
    form.experience_years.value = profile.experience_years ?? "";
    form.skills.value = profile.skills || "";
}

function submitCareerSimulation(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = {};
    const monthlyIncome = form.monthly_income.value.trim();
    const variableIncome = form.variable_income.value.trim();
    const rentOrEmi = form.rent_or_emi.value.trim();
    const city = form.city.value.trim();
    const experienceYears = form.experience_years.value.trim();
    const skills = form.skills.value
        .split(",")
        .map(item => item.trim())
        .filter(Boolean);

    if (monthlyIncome) {
        payload.monthly_income = Number(monthlyIncome);
    }
    if (variableIncome) {
        payload.variable_income = Number(variableIncome);
    }
    if (rentOrEmi) {
        payload.rent_or_emi = Number(rentOrEmi);
    }
    if (city) {
        payload.city = city;
    }
    if (experienceYears) {
        payload.experience_years = Number(experienceYears);
    }
    if (skills.length) {
        payload.skills = skills;
    }

    if (!Object.keys(payload).length) {
        showCareerFeedback("careerSimulationFeedback", "Provide at least one scenario input to simulate.", "warning");
        return;
    }

    Alfred.fetchJSON("/api/career/projection/simulate/", {
        method: "POST",
        body: JSON.stringify(payload),
    })
        .then(data => {
            renderSimulationPanel(data);
            showCareerFeedback("careerSimulationFeedback", "Simulation updated.", "success");
        })
        .catch(error => showCareerFeedback("careerSimulationFeedback", error.message, "danger"));
}

function renderSimulationPanel(simulation) {
    const target = document.getElementById("careerSimulationPanel");
    const baseline = simulation?.baseline || careerSimulationBaseline;
    const scenario = simulation?.scenario || null;
    if (!baseline) {
        target.innerHTML = `<div class="empty-state">Projection data is not available yet.</div>`;
        return;
    }

    const baselineYear1 = baseline.projections?.[0]?.projected_income || 0;
    const baselineYear5 = baseline.projections?.at(-1)?.projected_income || 0;
    const scenarioYear1 = scenario?.projections?.[0]?.projected_income || 0;
    const scenarioYear5 = scenario?.projections?.at(-1)?.projected_income || 0;
    const assumptions = simulation?.assumptions || null;
    const baselineReasoning = Array.isArray(baseline.reasoning) ? baseline.reasoning.slice(0, 3) : [];
    const scenarioReasoning = Array.isArray(scenario?.reasoning) ? scenario.reasoning.slice(0, 3) : [];

    target.innerHTML = `
        <div class="soft-grid two-up">
            <div class="mini-card">
                <div class="fw-semibold">Baseline</div>
                <div class="muted small mt-1">${Alfred.escapeHtml(baseline.projection_mode || "heuristic")}</div>
                <div class="mt-3">Year 1 <strong>${Alfred.formatCurrency(baselineYear1)}</strong></div>
                <div class="mt-2">Year 5 <strong>${Alfred.formatCurrency(baselineYear5)}</strong></div>
                <div class="muted small mt-3">${Alfred.escapeHtml(baseline.projection_method || "")}</div>
                ${baselineReasoning.length ? `<div class="muted small mt-3">${baselineReasoning.map(item => Alfred.escapeHtml(item.label || "")).join(" | ")}</div>` : ""}
            </div>
            <div class="mini-card">
                <div class="fw-semibold">Scenario</div>
                <div class="muted small mt-1">${scenario ? Alfred.escapeHtml(scenario.projection_mode || "heuristic") : "Run a scenario"}</div>
                <div class="mt-3">Year 1 <strong>${scenario ? Alfred.formatCurrency(scenarioYear1) : "Not simulated"}</strong></div>
                <div class="mt-2">Year 5 <strong>${scenario ? Alfred.formatCurrency(scenarioYear5) : "Not simulated"}</strong></div>
                <div class="muted small mt-3">${scenario ? Alfred.escapeHtml(scenario.projection_method || "") : "Scenario details appear here after a run."}</div>
                ${scenarioReasoning.length ? `<div class="muted small mt-3">${scenarioReasoning.map(item => Alfred.escapeHtml(item.label || "")).join(" | ")}</div>` : ""}
            </div>
        </div>
        <div class="mini-card">
            <div class="fw-semibold mb-2">Change Summary</div>
            <div class="data-stack">
                <div class="data-row">
                    <div class="data-label">Year 1 delta</div>
                    <div class="data-value">${scenario ? Alfred.formatCurrency(simulation.delta?.year_1_projected_income || 0) : "Run a scenario"}</div>
                </div>
                <div class="data-row">
                    <div class="data-label">Year 5 delta</div>
                    <div class="data-value">${scenario ? Alfred.formatCurrency(simulation.delta?.year_5_projected_income || 0) : "Run a scenario"}</div>
                </div>
            </div>
        </div>
        ${assumptions ? `
            <div class="mini-card">
                <div class="fw-semibold mb-2">Assumptions</div>
                <div class="muted small">Macro context locked: ${assumptions.macro_context_locked ? "Yes" : "No"}</div>
                <div class="muted small mt-2">Source: ${Alfred.escapeHtml(assumptions.macro_source || "")}</div>
                <div class="muted small mt-2">Overridden fields: ${Alfred.escapeHtml((assumptions.overridden_fields || []).join(", ") || "None")}</div>
                <div class="muted small mt-2">${Alfred.escapeHtml(assumptions.explainability_note || "")}</div>
            </div>
        ` : ""}
    `;
}

function showCareerFeedback(elementId, message, tone) {
    const box = document.getElementById(elementId);
    box.className = `alert alert-${tone} mb-0`;
    box.textContent = message;
    box.classList.remove("d-none");
}

function dedupeEvidence(items) {
    const seen = new Set();
    const result = [];
    items.forEach(item => {
        if (!item || (!item.source_url && !item.source_name && !item.title)) {
            return;
        }
        const key = `${item.source_url || ""}|${item.verified_at || ""}|${item.title || ""}`;
        if (seen.has(key)) {
            return;
        }
        seen.add(key);
        result.push(item);
    });
    return result;
}

function careerTone(value) {
    const normalized = String(value || "").toLowerCase();
    if (normalized === "favorable" || normalized === "go") {
        return "status-stable";
    }
    if (normalized === "build" || normalized === "prepare") {
        return "status-guarded";
    }
    if (normalized === "guarded" || normalized === "hold") {
        return "status-high";
    }
    return "status-low";
}

function careerPriorityTone(value) {
    const normalized = String(value || "").toLowerCase();
    if (normalized === "high") {
        return "status-high";
    }
    if (normalized === "medium") {
        return "status-guarded";
    }
    return "status-low";
}

function summarizeCareerResumeBatch(results) {
    const summary = Alfred.summarizeUploadBatch(results, { itemLabel: "resume", successVerb: "uploaded" });
    const parsedCount = summary.succeeded.filter(result => result.data?.resume?.parser_status === "parsed").length;
    const reviewCount = summary.succeeded.length - parsedCount;
    const extras = [];

    if (parsedCount) {
        extras.push(`${parsedCount} parsed cleanly`);
    }
    if (reviewCount) {
        extras.push(`${reviewCount} marked for review`);
    }

    return {
        ...summary,
        tone: reviewCount && !summary.failed.length ? "warning" : summary.tone,
        message: extras.length ? `${summary.message} ${extras.join(" | ")}.` : summary.message,
    };
}
