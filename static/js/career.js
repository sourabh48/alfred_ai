let salaryChart;
let careerSimulationBaseline = null;
let careerOpeningFilters = { country: "", state: "" };
let careerOpportunities = [];
let careerOpportunityPage = "/api/career/job-analyses/";

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("careerRoot")) {
        return;
    }

    document.getElementById("careerProfileForm").addEventListener("submit", submitCareerProfile);
    document.getElementById("careerResumeForm").addEventListener("submit", submitCareerResume);
    document.getElementById("careerJobMatchForm").addEventListener("submit", submitCareerJobMatch);
    document.getElementById("careerRecruiterForm").addEventListener("submit", submitCareerRecruiterLead);
    document.getElementById("careerRecruiterResumeReload").addEventListener("click", loadCareerResumeChoices);
    loadCareerResumeChoices();
    document.getElementById("careerSimulationForm").addEventListener("submit", submitCareerSimulation);
    document.getElementById("careerOpeningCountryFilter")?.addEventListener("change", updateCareerOpeningFilters);
    document.getElementById("careerOpeningStateFilter")?.addEventListener("change", updateCareerOpeningFilters);
    document.getElementById("careerOutcomesReload").addEventListener("click", () => loadCareerOpportunities(careerOpportunityPage));
    document.getElementById("careerPatternsLoad").addEventListener("click", loadCareerPatterns);
    document.getElementById("careerOutcomeAnalysis").addEventListener("change", event => {
        renderCareerOutcomeForm(careerOpportunities.find(item => String(item.id) === event.target.value));
    });
    loadCareerOpportunities();
    loadCareerDashboard();
    Alfred.enableLiveRefresh("career-live", loadCareerDashboard, { rootId: "careerRoot" });
});

function loadCareerDashboard(options = {}) {
    Alfred.setPageBusy("careerRoot", true, { label: "Loading career intelligence" });
    const query = careerDashboardQueryString();
    return Alfred.fetchJSON(`/api/career/dashboard/${query}`)
        .then(data => {
            if (query !== careerDashboardQueryString()) {
                return;
            }
            // A response can arrive after the owner opens sources or starts editing.
            if (options.live && Alfred.shouldPauseLiveRefresh(document.getElementById("careerRoot"))) {
                return false;
            }
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
            if (!options.live && !options.preserveEdits) {
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
    loadCareerDashboard({ preserveEdits: true });
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
    Alfred.setHTML(countrySelect, `<option value="">All countries</option>${countries.map(country => `
        <option value="${Alfred.escapeHtml(country)}"${country === careerOpeningFilters.country ? " selected" : ""}>${Alfred.escapeHtml(country)}</option>
    `).join("")}`);

    const states = careerOpeningFilters.country ? (statesByCountry[careerOpeningFilters.country] || []) : [];
    if (!states.includes(careerOpeningFilters.state)) {
        careerOpeningFilters.state = "";
    }
    stateSelect.disabled = !states.length;
    Alfred.setHTML(stateSelect, `<option value="">All states</option>${states.map(state => `
        <option value="${Alfred.escapeHtml(state)}"${state === careerOpeningFilters.state ? " selected" : ""}>${Alfred.escapeHtml(state)}</option>
    `).join("")}`);
}

function renderCareerHero(profile, projection, timing) {
    const latest = (projection.projections || []).at(-1);
    document.getElementById("careerRoleValue").textContent = profile.role || "Profile pending";
    document.getElementById("careerIncomeValue").textContent = Number(projection.current_income) > 0 ? Alfred.formatCurrency(projection.current_income) : "Unavailable";
    const incomeConflict = document.getElementById("careerIncomeConflict");
    incomeConflict.textContent = projection.income_signals?.income_conflict?.message || "";
    incomeConflict.classList.toggle("d-none", !incomeConflict.textContent);
    if (!(projection.projections || []).length && projection.message) {
        document.getElementById("careerGrowthCopy").textContent = projection.message;
        return;
    }
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
        { title: "Rule-based Job Fit", value: jobAnalysis ? (jobAnalysis.fit_score == null ? "Unavailable" : `${Alfred.formatNumber(jobAnalysis.fit_score, 0)}/100`) : "No comparison", copy: jobAnalysis ? `${Alfred.escapeHtml(jobAnalysis.company || jobAnalysis.source_name || "Latest analysis")} · Not a hiring probability` : "Provide a job description" },
        {
            title: "Career Timing",
            value: timing?.readiness_score != null ? `${Alfred.formatNumber(timing.readiness_score || 0, 0)}/100` : (market ? `${Alfred.formatNumber(market.risk_score || 0, 0)}/100` : "N/A"),
            copy: timing?.summary || projectionConfidence.summary || (latest ? `Year 5 projection ${Alfred.formatCurrency(latest.projected_income || 0)}` : "Projection pending"),
        },
    ];

    Alfred.setHTML(document.getElementById("careerSummaryCards"), cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.title}</p>
            <h2 class="metric-value">${card.value}</h2>
            <p class="metric-caption">${card.copy}</p>
        </article>
    `).join(""));
}

function renderCareerChart(items) {
    const canvas = document.getElementById("salaryChart");
    salaryChart = Alfred.renderChart(salaryChart, canvas, {
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
    Alfred.setHTML(target, items.map(item => `<li class="insight-item surface-card">${Alfred.escapeHtml(item)}</li>`).join(""));
}

function renderCareerSnapshot(profile) {
    Alfred.setHTML(document.getElementById("careerProfileSnapshot"), [
        ["Role", profile.role || "Profile pending"],
        ["Experience", `${Alfred.formatNumber(profile.experience_years, 1)} years`],
        ["Skills", profile.skills || "No skills listed yet."],
        ["Current income", Number(profile.last_salary) > 0 ? Alfred.formatCurrency(profile.last_salary, profile.salary_currency || "INR") : "Not recorded"],
    ].map(([label, value]) => `
        <div class="data-row">
            <div class="data-label">${label}</div>
            <div class="data-value">${Alfred.escapeHtml(String(value))}</div>
        </div>
    `).join(""));
}

function renderCareerProjectionTable(projection) {
    const target = document.getElementById("careerProjectionTable");
    const items = projection?.projections || [];
    const projectionConfidence = projection?.projection_confidence || {};
    const reasoning = Array.isArray(projection?.reasoning) ? projection.reasoning : [];
    if (!items.length) {
        Alfred.setHTML(target, `<div class="empty-state">Projection data is not available yet.</div>`);
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

    Alfred.setHTML(target, `${confidenceHeader}${reasoningPanel}${items.map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">Year ${item.year}</div>
                    <div class="muted small">Real ${Alfred.formatCurrency(item.real_income_estimate || item.projected_income)}</div>
                </div>
                <strong>${Alfred.formatCurrency(item.projected_income)}</strong>
            </div>
        </div>
    `).join("")}`);
}

function renderCareerMacroContext(context, basis) {
    Alfred.setHTML(document.getElementById("careerMacroContext"), [
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
    `).join(""));
}

function renderCareerEvidence(items) {
    const target = document.getElementById("careerEvidenceList");
    const unique = dedupeEvidence(items);
    Alfred.setHTML(target, unique.length ? unique.map(item => `
        <div class="mini-card">
            <div class="fw-semibold">${Alfred.escapeHtml(item.title || item.source_name)}</div>
            <div class="muted small">${Alfred.escapeHtml(item.source_name || "Source")} | refreshed ${Alfred.formatDateTime(item.verified_at)}</div>
            <div class="muted small mt-2">${Alfred.escapeHtml(item.summary || "")}</div>
            <div class="mt-2"><a href="${Alfred.safeHref(item.source_url)}" target="_blank" rel="noopener">Open source</a></div>
        </div>
    `).join("") : `<div class="empty-state">No evidence records available yet.</div>`);
}

function renderCareerTiming(timing) {
    const target = document.getElementById("careerTimingPanel");
    if (!timing || (!timing.summary && !timing.window_start)) {
        Alfred.setHTML(target, `<div class="empty-state">Career timing guidance will appear once Alfred has enough profile, market, and financial data.</div>`);
        return;
    }

    Alfred.setHTML(target, `
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
        <div class="mini-card surface-card">
            <div class="fw-semibold mb-2">Current signals</div>
            <ul class="insight-list mb-0">
                ${(timing.signals || []).map(item => `<li class="insight-item surface-card">${Alfred.escapeHtml(item)}</li>`).join("")}
            </ul>
        </div>
        <div class="mini-card surface-card">
            <div class="fw-semibold mb-2">What blocks a bigger move</div>
            <ul class="insight-list mb-0">
                ${(timing.blockers || []).map(item => `<li class="insight-item surface-card">${Alfred.escapeHtml(item)}</li>`).join("")}
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
    `);
}

function renderCareerDataPipeline(pipeline) {
    const target = document.getElementById("careerDataPipeline");
    const sections = [
        ["Collected", pipeline.collection || []],
        ["Processed", pipeline.processing || []],
        ["Verified", pipeline.verification || []],
        ["Current State", pipeline.current_state || []],
    ].filter(([, items]) => items.length);

    Alfred.setHTML(target, sections.length ? sections.map(([label, items]) => `
        <div class="mini-card">
            <div class="fw-semibold mb-2">${Alfred.escapeHtml(label)}</div>
            <ul class="insight-list mb-0">
                ${items.map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join("")}
            </ul>
        </div>
    `).join("") : `<div class="empty-state">Collection and processing details are not available yet.</div>`);
}

function renderResumePanel(resume) {
    const target = document.getElementById("careerResumePanel");
    if (!resume) {
        Alfred.setHTML(target, `<div class="empty-state">No parsed resume yet. Upload one to unlock stronger strengths, weaknesses, and job-fit analysis.</div>`);
        return;
    }
    const payload = resume.extracted_payload || {};
    const skillChips = (payload.skills || []).length
        ? `<div class="d-flex flex-wrap gap-2 mt-2">${payload.skills.map(skill => `<span class="status-pill neutral">${Alfred.escapeHtml(skill)}</span>`).join("")}</div>`
        : `<div class="muted small mt-2">No skill list extracted.</div>`;
    const linksBlock = (payload.links || []).length
        ? `<div class="mt-3">${payload.links.slice(0, 4).map(link => `<div><a href="${Alfred.safeHref(link)}" target="_blank" rel="noopener">${Alfred.escapeHtml(link)}</a></div>`).join("")}</div>`
        : `<div class="muted small mt-3">No portfolio, LinkedIn, or project link detected.</div>`;
    const extractionMethod = payload.extraction_method
        ? payload.extraction_method.replaceAll("_", " ")
        : "unknown";
    const extractionNotes = (payload.extraction_notes || []).length
        ? `<div class="muted small mt-2">${Alfred.escapeHtml(payload.extraction_notes.join(" "))}</div>`
        : "";
    Alfred.setHTML(target, `
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
            ${resume.parser_status !== "parsed" && (payload.role || payload.experience_years || (payload.skills || []).length) ? `
            <div class="mt-3">
                ${payload.profile_confirmed_at ? `<div class="muted small">You confirmed these details for your profile.</div>` : `
                <div class="muted small mb-2">This read was weak, so your profile was not changed. If the details above are right, you can use them; empty profile fields are filled and skills are added.</div>
                <button type="button" class="btn btn-outline-primary btn-sm" id="careerResumeUseDetails">Use these details in my profile</button>`}
                <div id="careerResumeUseFeedback" class="d-none alert mt-2 mb-0" role="status" aria-live="polite"></div>
            </div>` : ""}
        </div>
    `);
    const useButton = document.getElementById("careerResumeUseDetails");
    if (useButton) useButton.addEventListener("click", () => {
        useButton.disabled = true;
        Alfred.fetchJSON(`/api/career/resumes/${resume.id}/use-details/`, {method: "POST", body: "{}"})
            .then(data => {
                showCareerFeedback("careerResumeUseFeedback", data.detail, "success");
                loadCareerDashboard();
            })
            .catch(error => {
                useButton.disabled = false;
                showCareerFeedback("careerResumeUseFeedback", error.message, "danger");
            });
    });
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
        Alfred.setHTML(target, `<div class="empty-state">No job link analyzed yet.</div>`);
        return;
    }
    const payload = analysis.extracted_payload || {};
    const fit = payload.fit || {};
    const sourcesOpen = target.querySelector('[data-fit-sources]')?.open || false;
    const compensation = payload.compensation_benchmark || {};
    let jobHref = "";
    try {
        const url = new URL(analysis.apply_url || analysis.job_url);
        if (["http:", "https:"].includes(url.protocol) && !url.username && !url.password) jobHref = url.href;
    } catch (_) { /* A missing or malformed source is displayed without an active link. */ }
    Alfred.setHTML(target, `
        <div class="mini-card surface-card">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(analysis.job_title || "Job role")} <span class="muted small">${Alfred.escapeHtml(analysis.company || analysis.source_name || "")}</span></div>
                    <div class="muted small">${Alfred.escapeHtml(analysis.location || "Location not detected")}</div>
                    <div class="muted small mt-1">Source ${Alfred.escapeHtml(payload.job_snapshot?.source_kind || "job_page")} | ${Alfred.escapeHtml(analysis.source_document_name || "Saved job source")}</div>
                    <div class="muted small mt-2">${Alfred.escapeHtml(analysis.summary || "")}</div>
                    <div class="muted small mt-2"><strong>Matched listed terms${fit.sources?.length ? " [1, 2]" : ""}:</strong> ${fit.matched_skills?.length ? Alfred.escapeHtml(fit.matched_skills.join(", ")) : "No overlap established."}</div>
                    <div class="muted small mt-2"><strong>Not listed in saved skills${fit.sources?.length ? " [1, 2]" : ""}:</strong> ${fit.missing_skills?.length ? Alfred.escapeHtml(fit.missing_skills.join(", ")) : "No additional term extracted; this does not confirm full coverage."}</div>
                    <div class="small mt-2" data-fit-uncertainty>${(fit.uncertainty || ["Legacy comparison has no saved uncertainty or source references; analyze it again before relying on the score."]).map(item => `<p class="mb-1">${Alfred.escapeHtml(item)}</p>`).join("")}</div>
                    <details class="mt-3 text-break" data-fit-sources ${sourcesOpen ? "open" : ""}>
                        <summary>Saved comparison sources</summary>
                        <div class="small mt-2">Captured with this analysis; not live or independently verified source claims.</div>
                        ${(fit.sources || []).map((source, index) => `<div class="mt-2 small"><strong>[${index + 1}] ${Alfred.escapeHtml(source.label || source.kind)}</strong>
                            <div>${Alfred.escapeHtml(source.kind || "")} ${source.record_id ? `record ${Alfred.escapeHtml(source.record_id)}` : ""} · Saved skills: ${Alfred.escapeHtml((source.skills || []).join(", ") || "Unavailable")}</div>
                            <div>Experience field: ${source.experience_years == null ? "Unavailable" : Alfred.escapeHtml(source.experience_years)} years</div>
                            ${source.excerpt ? `<blockquote class="mt-2 mb-0">${Alfred.escapeHtml(source.excerpt)}</blockquote>` : ""}</div>`).join("") || "No saved source references."}
                    </details>
                    <div class="muted small mt-2"><strong>Compensation:</strong> ${compensation.available ? Alfred.escapeHtml(`${formatCompensationAmount(compensation.market_min_annual, compensation.currency)} to ${formatCompensationAmount(compensation.market_max_annual || compensation.market_min_annual, compensation.currency)} annual`) : "No salary-bearing evidence detected yet."}</div>
                    <div class="muted small mt-2">${Alfred.escapeHtml(analysis.strengths || "")}</div>
                    <div class="muted small mt-2">${Alfred.escapeHtml(analysis.gaps || "")}</div>
                    <div class="mt-2">${jobHref ? `<a href="${Alfred.escapeHtml(jobHref)}" target="_blank" rel="noopener">Open job link</a>` : "Job link unavailable"}</div>
                </div>
                <div class="text-end">
                    <div class="metric-value" style="font-size:1.6rem;">${analysis.fit_score == null ? "Unavailable" : `${Alfred.formatNumber(analysis.fit_score, 0)}/100`}</div>
                    <div class="muted small">Rule-based fit</div>
                    <div class="mt-2 muted small">Risk ${Alfred.formatNumber(analysis.market_risk_score || 0, 0)}/100</div>
                </div>
            </div>
        </div>
    `);
}

function careerOpportunityLabel(item) {
    return `${item.job_title || "Role"} · ${item.company || "Company not recorded"}${item.outcome?.outcome ? ` · ${item.outcome.outcome}` : ""}`;
}

function loadCareerOpportunities(url = "/api/career/job-analyses/") {
    return Alfred.fetchJSON(url).then(data => {
        careerOpportunityPage = url;
        careerOpportunities = data.results || [];
        const select = document.getElementById("careerOutcomeAnalysis");
        select.replaceChildren(new Option(careerOpportunities.length ? "Choose an opportunity" : "No recorded opportunities", ""));
        careerOpportunities.forEach(item => select.add(new Option(careerOpportunityLabel(item), item.id)));
        document.getElementById("careerOutcomeListFeedback").classList.add("d-none");
        for (const [id, target] of [["careerOutcomesPrevious", data.previous], ["careerOutcomesNext", data.next]]) {
            const button = document.getElementById(id);
            button.disabled = !target;
            button.onclick = target ? () => loadCareerOpportunities(target) : null;
        }
        renderCareerOutcomeForm(null);
        loadCareerFollowUps();
    }).catch(error => showCareerFeedback("careerOutcomeListFeedback", error.message, "danger"));
}

const CAREER_STAGES = ["evaluated", "applied", "responded", "assessment", "interview", "offer", "rejected", "discarded", "hired"];
const careerStageLabel = stage => stage ? stage.charAt(0).toUpperCase() + stage.slice(1) : "No stage set";

function loadCareerFollowUps() {
    const target = document.getElementById("careerFollowUps");
    return Alfred.fetchJSON("/api/career/follow-ups/").then(data => {
        const row = item => `<li>${Alfred.escapeHtml(item.job_title || "Role")} · ${Alfred.escapeHtml(item.company || "Company not recorded")} · ${Alfred.escapeHtml(careerStageLabel(item.stage))} · ${Alfred.escapeHtml(item.due_on)}</li>`;
        target.innerHTML = data.due.length
            ? `<div class="alert alert-warning small mb-0" id="careerFollowUpsDue"><strong>Follow-ups due (${data.due.length})</strong><ul class="mb-0">${data.due.map(row).join("")}</ul>
               <div class="mt-1">ALFRED does not send anything. Mark a follow-up as sent only after you send it yourself.</div></div>`
            : (data.upcoming.length ? `<p class="small muted mb-0" id="careerFollowUpsNone">No follow-ups due today. Next: ${Alfred.escapeHtml(data.upcoming[0].due_on)}.</p>` : "");
        const unavailable = data.unavailable || [];
        if (unavailable.length) {
            target.insertAdjacentHTML('beforeend', `<div class="alert alert-warning small mt-2 mb-0" id="careerFollowUpsUnavailable" role="status">
                <strong>Follow-up dates need review (${Alfred.escapeHtml(String(data.unavailable_count))})</strong>
                <p class="mb-1">These opportunities have missing, malformed or conflicting histories. No dates were guessed and saved records were not changed.
                Use the Opportunity selector to inspect retained history and review a recovery. Normal editing is paused to preserve that history.</p>
                <ul>${unavailable.map(item => `<li>${Alfred.escapeHtml(item.job_title || 'Role')} · ${Alfred.escapeHtml(item.company || 'Company not recorded')}</li>`).join('')}</ul>
                <p class="mb-0">Checked up to the 300 most recently updated opportunities; showing ${unavailable.length} needing review.</p></div>`);
        }
    }).catch(() => { target.innerHTML = '<p class="small" role="status">Follow-ups could not load. Refresh this page to retry; saved records have not been changed.</p>'; });
}

function renderCareerApplication(item) {
    const target = document.getElementById("careerApplicationPanel");
    if (!item) { target.replaceChildren(); return; }
    const app = item.application || {}, follow = app.follow_up || {}, fresh = item.match_freshness || {};
    const history = (app.history || []).map(step => `<li>${Alfred.escapeHtml(careerStageLabel(step.stage))} on ${Alfred.escapeHtml(step.on)}</li>`).join("");
    const sent = (app.follow_ups || []).map(step => `<li>Follow-up sent on ${Alfred.escapeHtml(step.on)} (${Alfred.escapeHtml(careerStageLabel(step.stage))})</li>`).join("");
    const skills = (label, list) => list?.length ? `<div>${label}: ${Alfred.escapeHtml(list.join(", "))}</div>` : "";
    const freshness = fresh.status === "stale"
        ? `<div class="alert alert-warning small" id="careerMatchStale"><strong>This match used an older resume.</strong> ${Alfred.escapeHtml((fresh.reasons || []).join(" "))}
             ${skills("Skills added since", fresh.added_skills)}${skills("Skills removed since", fresh.removed_skills)}Run the job match again before relying on its fit.</div>`
        : (fresh.status === "current" ? `<p class="small muted" id="careerMatchCurrent">This match uses your current resume.</p>` : "");
    target.innerHTML = `
        <div class="surface-card p-3 mb-3" id="careerApplication">
            <h4 class="h6">Application progress</h4>
            ${freshness}
            <div class="row g-2 align-items-end">
                <div class="col-md-5"><label class="form-label small" for="careerApplicationStage">Stage</label>
                    <select class="form-select form-select-sm" id="careerApplicationStage">${CAREER_STAGES.map(stage => `<option value="${stage}">${careerStageLabel(stage)}</option>`).join("")}</select></div>
                <div class="col-md-4"><label class="form-label small" for="careerApplicationDate">Date</label>
                    <input class="form-control form-control-sm" id="careerApplicationDate" type="date"></div>
                <div class="col-md-3"><button class="btn btn-outline-primary btn-sm w-100" type="button" id="careerApplicationSave" ${follow.status === 'unavailable' ? 'disabled aria-describedby="careerApplicationFollowUp"' : ''}>Save stage</button></div>
            </div>
            <p class="small mt-2 mb-1" id="careerApplicationFollowUp">Current stage: <strong>${Alfred.escapeHtml(careerStageLabel(app.stage))}</strong>. ${Alfred.escapeHtml(follow.detail || "")}</p>
            ${["due", "upcoming"].includes(follow.status) ? `<button class="btn btn-outline-secondary btn-sm" type="button" id="careerFollowUpSent">I sent a follow-up today</button>` : ""}
            ${history || sent ? `<details class="small mt-2"><summary>History</summary><ul class="mb-0">${history}${sent}</ul></details>` : ""}
            <button class="btn btn-outline-secondary btn-sm mt-2" type="button" id="careerHistoryReviewOpen">Review retained history${follow.status === 'unavailable' ? ' and recovery' : ''}</button>
            <div id="careerHistoryReviewHost"></div>
            <div id="careerApplicationFeedback" class="d-none alert mt-2 mb-0" role="status" aria-live="polite"></div>
        </div>`;
    if (app.stage) document.getElementById("careerApplicationStage").value = app.stage;
    const send = change => Alfred.fetchJSON(`/api/career/job-analyses/${item.id}/application/`, {method: "POST", body: JSON.stringify({...change, revision: item.updated_at})})
        .then(data => {
            const index = careerOpportunities.findIndex(row => row.id === item.id);
            if (index >= 0) careerOpportunities[index] = data.opportunity;
            renderCareerOutcomeForm(data.opportunity);
            showCareerFeedback("careerApplicationFeedback", "Saved.", "success");
            loadCareerFollowUps();
        })
        .catch(error => showCareerFeedback("careerApplicationFeedback", error.message, "danger"));
    document.getElementById("careerApplicationSave").addEventListener("click", () => {
        const on = document.getElementById("careerApplicationDate").value;
        send({stage: document.getElementById("careerApplicationStage").value, ...(on ? {on} : {})});
    });
    document.getElementById("careerFollowUpSent")?.addEventListener("click", () => send({follow_up_sent: true}));
    document.getElementById('careerHistoryReviewOpen').addEventListener('click', () => {
        const host = document.getElementById('careerHistoryReviewHost');
        if (host.childElementCount) { host.hidden = !host.hidden; return; }
        renderCareerHistoryReview(item, host);
    });
}

function renderCareerHistoryReview(item, host) {
    const panel = document.createElement('section'); panel.className='border rounded p-3 mt-3';
    panel.setAttribute('aria-label','Retained timeline review'); host.append(panel);
    panel.innerHTML=`<h5 class="h6">Retained application history</h5>
        <button type="button" class="btn btn-outline-secondary btn-sm mb-2" data-reload>Reload retained history</button>
        <p role="status" class="small" data-feedback>Loading private history…</p>
        <details><summary>Current recorded source</summary><pre class="text-wrap" style="overflow-wrap:anywhere" data-source></pre></details>
        <details><summary>Prior retained timelines</summary><pre class="text-wrap" style="overflow-wrap:anywhere" data-archives></pre></details>
        <form data-recovery hidden class="mt-3">
            <p class="small">Review a new timeline using a stage and date you confirm. The exact prior history stays retained.
            Earlier follow-ups remain in that archive and do not count in the new timeline. Nothing is sent to employers.</p>
            <label class="form-label" for="careerRecoveryStage">Reviewed stage</label>
            <select class="form-select mb-2" id="careerRecoveryStage" required><option value="">Choose a stage</option>${CAREER_STAGES.map(stage=>`<option value="${stage}">${careerStageLabel(stage)}</option>`).join('')}</select>
            <label class="form-label" for="careerRecoveryDate">Reviewed stage date</label>
            <input class="form-control mb-2" id="careerRecoveryDate" type="date" required>
            <button class="btn btn-outline-primary" type="submit">Preview recovery</button>
        </form>
        <section data-proposal hidden class="mt-3" aria-label="Recovery awaiting confirmation">
            <p class="small" data-summary></p>
            <button type="button" class="btn btn-primary" data-confirm>Confirm recovery and retain original</button>
            <button type="button" class="btn btn-outline-secondary" data-cancel>Cancel review</button>
        </section>`;
    const url=`/api/career/job-analyses/${item.id}/history-review/`, form=panel.querySelector('form');
    const feedback=panel.querySelector('[data-feedback]'), card=panel.querySelector('[data-proposal]');
    let source=null, proposal=null, pending=false, focusAfter=null;
    const post=body=>Alfred.fetchJSON(url,{method:'POST',body:JSON.stringify(body)});
    function controls() {
        panel.setAttribute('aria-busy',String(pending));
        panel.querySelectorAll('button').forEach(button=>button.disabled=pending);
        form.querySelectorAll('input,select,button').forEach(control=>control.disabled=pending||Boolean(proposal));
    }
    async function run(work) {
        if(pending) return;
        pending=true; controls();
        try { await work(); }
        catch(error) {
            if(!panel.isConnected) return;
            if([401,403].includes(error.status)) { panel.replaceChildren(document.createTextNode('Sign in again before viewing private history.')); return; }
            feedback.textContent=`${error.message} Your reviewed values are kept on this page; retry the same card or reload retained history.`;
        } finally {
            pending=false;
            if(panel.isConnected) { controls(); if(focusAfter?.isConnected) focusAfter.focus(); }
            focusAfter=null;
        }
    }
    async function load() {
        if(proposal) { await post({mode:'cancel',proposal_id:proposal.proposal_id}); proposal=null; }
        const data=await Alfred.fetchJSON(url);
        if(!panel.isConnected) return;
        source=data; card.hidden=true; form.hidden=!data.can_recover;
        panel.querySelector('[data-source]').textContent=JSON.stringify(data.application,null,2);
        panel.querySelector('[data-archives]').textContent=JSON.stringify(data.recoveries,null,2);
        feedback.textContent=data.can_recover ? 'Review an explicit stage and date. Preview does not change the current timeline.'
            : 'Retained history is available above. Recovery is unavailable for a valid timeline or when review bounds are reached.';
    }
    panel.querySelector('[data-reload]').addEventListener('click',()=>run(load));
    form.addEventListener('submit',event=>{
        event.preventDefault();
        const fields={stage:panel.querySelector('#careerRecoveryStage').value,on:panel.querySelector('#careerRecoveryDate').value};
        run(async()=>{
            const data=await post({mode:'preview',revision:source.revision,fields});
            if(!panel.isConnected) return;
            proposal=data; card.hidden=false;
            panel.querySelector('[data-summary]').textContent=`${careerStageLabel(data.fields.stage)} from ${data.fields.on}. ${data.detail} Review expires ${new Date(data.expires_at).toLocaleString()}.`;
            feedback.textContent='Preview ready. No timeline change until you confirm.';
            focusAfter=panel.querySelector('[data-confirm]');
        });
    });
    panel.querySelector('[data-cancel]').addEventListener('click',()=>run(async()=>{
        await post({mode:'cancel',proposal_id:proposal.proposal_id});
        if(!panel.isConnected) return;
        proposal=null; card.hidden=true; feedback.textContent='Review cancelled. The original timeline was not changed.';
        focusAfter=form.querySelector('button[type=submit]');
    }));
    panel.querySelector('[data-confirm]').addEventListener('click',()=>run(async()=>{
        await post({mode:'confirm',proposal_id:proposal.proposal_id,fields:proposal.fields,confirmed:true});
        if(!panel.isConnected) return;
        await loadCareerOpportunities(careerOpportunityPage);
        const select=document.getElementById('careerOutcomeAnalysis');
        if([...select.options].some(option=>option.value===String(item.id))) {
            select.value=String(item.id); select.dispatchEvent(new Event('change'));
            showCareerFeedback('careerApplicationFeedback','Recovery saved. The original history is retained.','success');
        }
    }));
    run(load);
}

function renderCareerInterviewPrep(item) {
    const target = document.getElementById("careerInterviewPrepPanel");
    const prep = item?.interview_prep;
    if (!prep) { target.replaceChildren(); return; }
    if (!prep.available) { target.innerHTML = `<p class="small muted" id="careerInterviewPrepUnavailable">${Alfred.escapeHtml(prep.reason)}</p>`; return; }
    const list = (items, render) => items.length ? `<ul class="small mb-3">${items.map(render).join("")}</ul>` : `<p class="small muted">None from this match.</p>`;
    const skill = entry => `<li><strong>${Alfred.escapeHtml(entry.skill)}</strong>: ${Alfred.escapeHtml(entry.prompt)}</li>`;
    target.innerHTML = `
        <details class="surface-card p-3 mb-3" id="careerInterviewPrep" open>
            <summary class="fw-semibold">Interview preparation</summary>
            <p class="small muted mt-2">${Alfred.escapeHtml(prep.basis)}</p>
            <h4 class="h6">Show your matched skills</h4>${list(prep.prove, skill)}
            <h4 class="h6">Prepare for gaps</h4>${list(prep.gaps, skill)}
            <h4 class="h6">General practice</h4>${list(prep.general, text => `<li>${Alfred.escapeHtml(text)}</li>`)}
        </details>`;
}

// Career Ops workflows (career-ops 775861b, MIT): triage, evaluation, CV-grounded drafts and offer reading. Email goes only after the owner reviews it and presses Send.
let careerTriageBrief;
const careerList = value => (value || []).join(", ");
const careerSplit = value => value.split(",").map(part => part.trim()).filter(Boolean);

function renderCareerApplicationKit(item) {
    const target = document.getElementById("careerApplicationKitPanel");
    if (!item) { target.replaceChildren(); return; }
    const triage = item.triage;
    const dims = triage ? triage.dimensions.map(dim => `<li>${Alfred.escapeHtml(dim.key.replace("_", " "))}: ${dim.score === null ? "left out" : `${dim.score}/5`} (weight ${Math.round(dim.weight * 100)}%). ${Alfred.escapeHtml(dim.reason)}</li>`).join("") : "";
    const field = (id, label, help = "") => `<div class="col-md-6"><label class="form-label small" for="${id}">${label}</label><input class="form-control form-control-sm" id="${id}" ${help ? `aria-describedby="${id}Help"` : ""}>${help ? `<div class="form-text" id="${id}Help">${help}</div>` : ""}</div>`;
    target.innerHTML = `
        <details class="surface-card p-3 mb-3" id="careerKit">
            <summary class="fw-semibold">Application kit</summary>
            <p class="small muted mt-2">Built only from your CV and this saved job match. ALFRED sends an email only after you review that exact email and press Send; it never submits job-board forms.</p>
            <h4 class="h6">Triage</h4>
            <div id="careerTriageResult" role="status">${triage ? `<p class="small mb-1"><strong>${triage.score === null ? "Not scored" : `${triage.score}/5`} · ${Alfred.escapeHtml(triage.verdict)}</strong> on ${Alfred.escapeHtml(triage.scored_on)}. ${Alfred.escapeHtml(triage.reason || "")}</p><ul class="small">${dims}</ul><p class="small muted">${Alfred.escapeHtml(triage.basis)}</p>` : `<p class="small muted">Not triaged yet.</p>`}</div>
            <form id="careerTriageForm" class="row g-2 mb-3">
                ${field("careerTriageRoles", "Target roles", "Comma separated. Empty uses your profile role.")}
                ${field("careerTriageLocations", "Locations you accept", "Comma separated.")}
                ${field("careerTriageFloor", "Yearly pay floor")}
                ${field("careerTriageCurrency", "Pay floor currency", "Three letters, such as INR. Pay in another currency is left out, never converted.")}
                ${field("careerTriageDq", "Hard disqualifiers", "Phrases in a job description that rule it out, comma separated.")}
                ${field("careerTriageFlags", "Red flags", "Phrases that lower the score by 0.5 each.")}
                ${field("careerTriagePriority", "Priority companies", "Always pass, comma separated.")}
                <div class="col-md-6 d-flex align-items-end"><div class="form-check"><input class="form-check-input" type="checkbox" id="careerTriageRemote"><label class="form-check-label small" for="careerTriageRemote">Remote roles are fine for me</label></div></div>
                <div class="col-12 d-flex flex-wrap gap-2"><button class="btn btn-outline-primary btn-sm" type="submit" id="careerTriageScore">Score this opportunity</button>
                    <button class="btn btn-outline-secondary btn-sm" type="button" id="careerTriageBatch">Score all saved opportunities</button></div>
            </form>
            <div id="careerBatchResult" aria-live="polite"></div>
            <h4 class="h6">Drafts</h4>
            <div class="d-flex flex-wrap gap-2 align-items-end mb-2">
                <button class="btn btn-outline-secondary btn-sm" type="button" id="careerKitEvaluation">Full evaluation (A-G)</button>
                <button class="btn btn-outline-secondary btn-sm" type="button" id="careerKitCv">Tailored CV</button>
                <button class="btn btn-outline-secondary btn-sm" type="button" id="careerKitBullets">Improve CV bullets (local AI)</button>
                <button class="btn btn-outline-secondary btn-sm" type="button" id="careerKitCover">Cover letter</button>
                <div><label class="form-label small mb-0" for="careerKitEmailKind">Email type</label>
                    <select class="form-select form-select-sm" id="careerKitEmailKind">
                        <option value="hr_application">Application to HR or a recruiter</option><option value="referral_request">Referral request</option>
                        <option value="cold_application">Speculative application</option><option value="follow_up">Follow-up on an application</option>
                        <option value="process_stuck">Application process broke</option><option value="confirmed_time_noshow">Missed confirmed call</option></select></div>
                <button class="btn btn-outline-secondary btn-sm" type="button" id="careerKitEmail">Email draft</button>
            </div>
            <div id="careerKitDraft" aria-live="polite"></div>
            <h4 class="h6 mt-3">Offer reading</h4>
            <form id="careerOfferForm" class="row g-2">
                <div class="col-12"><label class="form-label small" for="careerOfferText">Offer letter or contract text</label>
                    <textarea class="form-control form-control-sm" id="careerOfferText" rows="4" aria-describedby="careerOfferTextHelp"></textarea>
                    <div class="form-text" id="careerOfferTextHelp">Read on this computer only. It is not stored or sent anywhere.</div></div>
                ${field("careerOfferAmount", "Offered pay (optional)")}
                <div class="col-md-3"><label class="form-label small" for="careerOfferCurrency">Currency</label><input class="form-control form-control-sm" id="careerOfferCurrency" value="INR"></div>
                <div class="col-md-3"><label class="form-label small" for="careerOfferPeriod">Per</label><select class="form-select form-select-sm" id="careerOfferPeriod"><option>year</option><option>month</option><option>week</option><option>day</option><option>hour</option></select></div>
                <div class="col-12"><button class="btn btn-outline-secondary btn-sm" type="submit" id="careerOfferRead">Read offer</button></div>
            </form>
            <div id="careerOfferResult" class="mt-2" aria-live="polite"></div>
            <div id="careerKitFeedback" class="d-none alert mt-2 mb-0" role="status" aria-live="polite"></div>
        </details>`;
    const setBrief = brief => {
        if (!brief) return;
        for (const [id, key] of [["careerTriageRoles", "target_roles"], ["careerTriageLocations", "locations"], ["careerTriageDq", "hard_dq"], ["careerTriageFlags", "red_flags"], ["careerTriagePriority", "priority_companies"]])
            document.getElementById(id).value = careerList(brief[key]);
        document.getElementById("careerTriageFloor").value = brief.pay_floor || "";
        document.getElementById("careerTriageCurrency").value = brief.pay_currency || "";
        document.getElementById("careerTriageRemote").checked = !!brief.remote_ok;
    };
    if (triage?.brief) setBrief(triage.brief);
    else if (careerTriageBrief !== undefined) setBrief(careerTriageBrief);
    else Alfred.fetchJSON("/api/career/triage-brief/").then(data => { careerTriageBrief = data.brief; if (document.getElementById("careerTriageForm")) setBrief(data.brief); }).catch(() => {});
    const fail = error => showCareerFeedback("careerKitFeedback", error.message, "danger");
    const brief = () => {
        const value = id => document.getElementById(id).value;
        return {target_roles: careerSplit(value("careerTriageRoles")), locations: careerSplit(value("careerTriageLocations")),
            hard_dq: careerSplit(value("careerTriageDq")), red_flags: careerSplit(value("careerTriageFlags")),
            priority_companies: careerSplit(value("careerTriagePriority")), pay_floor: value("careerTriageFloor").trim(),
            pay_currency: value("careerTriageCurrency").trim(), remote_ok: document.getElementById("careerTriageRemote").checked};
    };
    document.getElementById("careerTriageBatch").addEventListener("click", () => {
        Alfred.fetchJSON("/api/career/triage/batch/", {method: "POST", body: JSON.stringify({brief: brief()})}).then(data => {
            careerTriageBrief = brief();
            const rows = data.results.map(row => `<li>${Alfred.escapeHtml(row.title || "Untitled")}${row.company ? ` at ${Alfred.escapeHtml(row.company)}` : ""}: <strong>${row.score === null ? "not scored" : `${row.score}/5`} · ${Alfred.escapeHtml(row.verdict)}</strong>${row.saved ? "" : " (changed meanwhile; not saved)"}</li>`).join("");
            document.getElementById("careerBatchResult").innerHTML = `<div id="careerBatchList" class="small mb-3"><p class="mb-1">${data.results.length} scored, best first${data.skipped ? `; ${data.skipped} without a job match skipped` : ""}.</p><ol>${rows}</ol><p class="muted mb-0">${Alfred.escapeHtml(data.basis)}</p></div>`;
        }).catch(fail);
    });
    document.getElementById("careerTriageForm").addEventListener("submit", event => {
        event.preventDefault();
        const current = brief();
        Alfred.fetchJSON(`/api/career/job-analyses/${item.id}/triage/`, {method: "POST", body: JSON.stringify({brief: current})}).then(data => {
            careerTriageBrief = current;
            const index = careerOpportunities.findIndex(row => row.id === item.id);
            if (index >= 0) careerOpportunities[index] = data.opportunity;
            renderCareerOutcomeForm(data.opportunity);
            document.getElementById("careerKit").open = true;
        }).catch(fail);
    });
    const showDraft = (data, extra = "") => {
        const host = document.getElementById("careerKitDraft");
        if (!data.available) { host.innerHTML = `<p class="small" role="status">${Alfred.escapeHtml(data.reason)}</p>`; return; }
        host.innerHTML = `${data.subject ? `<p class="small mb-1"><strong>Subject:</strong> <span id="careerKitSubject">${Alfred.escapeHtml(data.subject)}</span></p>` : ""}
            <label class="form-label small" for="careerKitText">Draft (select all and copy)</label>
            <textarea class="form-control form-control-sm font-monospace" id="careerKitText" rows="14" readonly></textarea>
            <ul class="small mt-2 mb-1">${data.notes.map(note => `<li>${Alfred.escapeHtml(note)}</li>`).join("")}</ul>${extra}`;
        document.getElementById("careerKitText").value = data.text;
    };
    const draft = (query, extra, then) => Alfred.fetchJSON(`/api/career/job-analyses/${item.id}/kit/?${query}`).then(data => { showDraft(data, extra); if (then && data.available) then(data); }).catch(fail);
    const cvLinks = `<p class="small mb-0">Printable CV: <a id="careerKitPrint" href="/career/job-analyses/${item.id}/tailored-cv/" target="_blank" rel="noopener">plain</a> ·
        <a id="careerKitPrintStyled" href="/career/job-analyses/${item.id}/tailored-cv/?style=styled" target="_blank" rel="noopener">styled</a> ·
        <a id="careerKitTex" href="/career/job-analyses/${item.id}/tailored-cv/?format=tex">LaTeX (.tex)</a></p>`;
    document.getElementById("careerKitCv").addEventListener("click", () => draft("type=cv", cvLinks));
    document.getElementById("careerKitCover").addEventListener("click", () => draft("type=cover"));
    document.getElementById("careerKitEmail").addEventListener("click", () => {
        const kind = document.getElementById("careerKitEmailKind").value;
        draft(`type=email&kind=${encodeURIComponent(kind)}`, `<div id="careerSendPanel"></div>`, data => renderCareerSendPanel(item, data, kind));
    });
    document.getElementById("careerKitEvaluation").addEventListener("click", () => {
        Alfred.fetchJSON(`/api/career/job-analyses/${item.id}/kit/?type=evaluation`).then(renderCareerEvaluation).catch(fail);
    });
    document.getElementById("careerKitBullets").addEventListener("click", event => {
        const button = event.currentTarget, host = document.getElementById("careerKitDraft");
        button.disabled = true;
        host.innerHTML = '<p class="small" role="status">Asking your local model. This can take a minute.</p>';
        Alfred.fetchJSON(`/api/career/job-analyses/${item.id}/rewrite-bullets/`, {method: "POST", body: "{}"}).then(data => {
            host.innerHTML = `<div id="careerBullets"><p class="small muted">${Alfred.escapeHtml(data.basis)}</p><ol class="small">${data.results.map(row => `<li class="mb-2">
                <div><span class="muted">Your bullet:</span> ${Alfred.escapeHtml(row.original)}</div>
                ${row.accepted ? `<div><strong>Suggestion:</strong> ${Alfred.escapeHtml(row.suggestion)}</div>`
                    : `<div><strong>Kept your bullet.</strong> ${Alfred.escapeHtml(row.issues.join(" "))}</div>`}</li>`).join("")}</ol></div>`;
        }).catch(error => { host.replaceChildren(); fail(error); }).finally(() => { button.disabled = false; });
    });
    document.getElementById("careerOfferForm").addEventListener("submit", event => {
        event.preventDefault();
        const amount = document.getElementById("careerOfferAmount").value.trim();
        const body = {offer_text: document.getElementById("careerOfferText").value,
            offered: amount ? {amount, currency: document.getElementById("careerOfferCurrency").value.trim(), period: document.getElementById("careerOfferPeriod").value} : null};
        Alfred.fetchJSON(`/api/career/job-analyses/${item.id}/offer-prep/`, {method: "POST", body: JSON.stringify(body)}).then(data => {
            const list = (items, render) => items.length ? `<ul class="small">${items.map(render).join("")}</ul>` : `<p class="small muted">None.</p>`;
            const clause = entry => `<li><strong>${Alfred.escapeHtml(entry.label)}</strong>${entry.quotes.length ? `<ul>${entry.quotes.map(quote => `<li>"${Alfred.escapeHtml(quote)}"</li>`).join("")}</ul>` : ": not mentioned."}</li>`;
            const pay = row => `<li>${Alfred.escapeHtml(row.label)}: ${Alfred.escapeHtml(row.amount ? `${row.currency} ${row.amount}` : row.detail)}${row.gap ? ` · ${Alfred.escapeHtml(row.gap_label)}: ${Alfred.escapeHtml(row.currency)} ${Alfred.escapeHtml(row.gap)}` : ""}</li>`;
            document.getElementById("careerOfferResult").innerHTML = `<div id="careerOfferReport">
                <p class="small"><strong>${Alfred.escapeHtml(data.disclaimer)}</strong></p>
                <h5 class="h6">What the offer says</h5>${list(data.clause_walk, clause)}
                ${data.pay.length ? `<h5 class="h6">Pay</h5>${list(data.pay, pay)}` : ""}
                <h5 class="h6">Questions for your lawyer</h5>${list(data.lawyer_questions, text => `<li>${Alfred.escapeHtml(text)}</li>`)}
                <h5 class="h6">Items to raise with the employer</h5>${list(data.raise_with_employer, text => `<li>${Alfred.escapeHtml(text)}</li>`)}</div>`;
        }).catch(fail);
    });
}

const CAREER_MATCH_LABEL = {strong: "Strong", partial: "Partial", missing: "Missing"};

function renderCareerEvaluation(report) {
    const host = document.getElementById("careerKitDraft");
    if (!report.available) { host.innerHTML = `<p class="small" role="status">${Alfred.escapeHtml(report.reason)}</p>`; return; }
    const e = Alfred.escapeHtml, list = items => items.length ? `<ul class="small">${items.map(text => `<li>${e(text)}</li>`).join("")}</ul>` : "";
    const verdict = report.verdict;
    host.innerHTML = `<article id="careerEvaluation" class="small" aria-label="Evaluation report">
        <p class="muted">${e(report.basis)}</p>
        <p><strong>Triage:</strong> ${e(verdict.verdict)}${verdict.score === null ? "" : ` (${verdict.score}/5)`}. ${e(verdict.reason || "")}</p>
        <h5 class="h6">A) ${e(report.A.title)}</h5>
        <dl class="row mb-2">${Object.entries(report.A.rows).map(([key, value]) => `<dt class="col-5 col-md-3">${e(key)}</dt><dd class="col-7 col-md-9 mb-1">${e(String(value))}</dd>`).join("")}</dl>
        <h5 class="h6">B) ${e(report.B.title)}</h5>
        <ol id="careerEvaluationRows">${report.B.rows.map(row => `<li class="mb-2"><strong>${e(row.requirement)}</strong> · ${e(row.band)} (${e(row.tier)}) · ${CAREER_MATCH_LABEL[row.match]}
            <div class="muted">Posting: ${e(row.jd_signal)}</div><div>${e(row.evidence)}</div></li>`).join("")}</ol>
        ${report.B.dropped ? `<p>+${report.B.dropped} lower-importance requirements not listed.</p>` : ""}
        ${report.B.gaps.length ? `<h6>Gaps to prepare</h6><ul>${report.B.gaps.map(gap => `<li><strong>${e(gap.requirement)}</strong>${gap.blocker ? " (blocker)" : ""}: ${e(gap.risk)} ${e(gap.mitigation)}</li>`).join("")}</ul>` : ""}
        <h5 class="h6">C) ${e(report.C.title)}</h5><p>${e(report.C.assessment)}</p>${list(report.C.plan)}
        <h5 class="h6">D) ${e(report.D.title)}</h5>${list(report.D.lines)}
        <h5 class="h6">E) ${e(report.E.title)}</h5>${list(report.E.steps)}
        ${report.E.lead_with.length ? `<p>Lead with: ${e(report.E.lead_with.join(", "))}</p>` : ""}${list(report.E.achievements.map(line => `Put first: ${line}`))}
        ${report.E.add_only_if_true.length ? `<p>Asked for but not on your CV (add only if true): ${e(report.E.add_only_if_true.join(", "))}</p>` : ""}
        <h5 class="h6">F) ${e(report.F.title)}</h5>${report.F.stories.length ? list(report.F.stories.map(story => `${story.prompt} Start from: ${story.seed}`)) : "<p>No critical or high requirement to prepare for.</p>"}
        <h5 class="h6">G) ${e(report.G.title)}</h5><p>Assessment: ${e(report.G.assessment)}.</p>${list([...report.G.signals, ...report.G.concerns.map(line => `Concern: ${line}`)])}
        <button class="btn btn-outline-secondary btn-sm" type="button" id="careerEvaluationDownload">Download report (.md)</button>
    </article>`;
    document.getElementById("careerEvaluationDownload").addEventListener("click", () => {
        const link = document.createElement("a");
        link.href = URL.createObjectURL(new Blob([report.markdown], {type: "text/markdown"}));
        link.download = "job-evaluation.md";
        link.click();
        setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    });
}

function renderCareerSendPanel(item, data, kind) {
    const host = document.getElementById("careerSendPanel");
    const attachDefault = ["hr_application", "cold_application", "process_stuck"].includes(kind);
    host.innerHTML = `<form id="careerSendForm" class="border-top pt-2 mt-2">
        <h5 class="h6">Send this email</h5>
        <p class="small muted">Edit it here, review it, then press Send. Nothing goes until you do; any change needs a new review.</p>
        <div class="row g-2">
            <div class="col-md-6"><label class="form-label small" for="careerSendTo">To</label><input class="form-control form-control-sm" id="careerSendTo" type="email" autocomplete="off"></div>
            <div class="col-md-6"><label class="form-label small" for="careerSendSubject">Subject</label><input class="form-control form-control-sm" id="careerSendSubject"></div>
            <div class="col-12"><label class="form-label small" for="careerSendBody">Email</label><textarea class="form-control form-control-sm" id="careerSendBody" rows="10"></textarea></div>
            <div class="col-12"><div class="form-check"><input class="form-check-input" type="checkbox" id="careerSendAttach" ${attachDefault ? "checked" : ""}><label class="form-check-label small" for="careerSendAttach">Attach my uploaded CV</label></div></div>
            <div class="col-12"><button class="btn btn-outline-primary btn-sm" type="submit" id="careerSendReview">Review before sending</button></div>
        </div>
        <div id="careerSendReviewResult" class="mt-2" aria-live="polite"></div>
    </form>`;
    document.getElementById("careerSendSubject").value = data.subject || "";
    document.getElementById("careerSendBody").value = data.text || "";
    const fields = () => ({to: document.getElementById("careerSendTo").value, subject: document.getElementById("careerSendSubject").value,
        body: document.getElementById("careerSendBody").value, attach_cv: document.getElementById("careerSendAttach").checked});
    const result = document.getElementById("careerSendReviewResult");
    const form = document.getElementById("careerSendForm");
    form.addEventListener("input", () => result.replaceChildren());
    form.addEventListener("change", () => result.replaceChildren());
    form.addEventListener("submit", event => {
        event.preventDefault();
        const reviewed = fields();
        Alfred.fetchJSON(`/api/career/job-analyses/${item.id}/email/review/`, {method: "POST", body: JSON.stringify(reviewed)}).then(review => {
            const e = Alfred.escapeHtml;
            const files = review.attachments.length ? review.attachments.map(file => `${e(file.name)} (${Math.ceil(file.bytes / 1024)} KB)`).join(", ") : "none";
            result.innerHTML = `<div id="careerSendManifest" class="small surface-card p-2">
                <p class="mb-1"><strong>From:</strong> ${e(review.from || "not set")} · <strong>To:</strong> ${e(review.to || "not set")}</p>
                <p class="mb-1"><strong>Subject:</strong> ${e(review.subject)}</p><p class="mb-1"><strong>Attachments:</strong> ${files}</p>
                ${review.blockers.length ? `<p class="mb-1 text-danger"><strong>Fix before sending:</strong></p><ul>${review.blockers.map(text => `<li>${e(text)}</li>`).join("")}</ul>` : ""}
                ${review.warnings.length ? `<p class="mb-1"><strong>Check:</strong></p><ul>${review.warnings.map(text => `<li>${e(text)}</li>`).join("")}</ul>` : ""}
                ${review.ready ? `<button class="btn btn-primary btn-sm" type="button" id="careerSendNow">Send to ${e(review.to)}</button>` : ""}
                <p class="muted mb-0 mt-1">${e(review.note)}</p></div>`;
            if (!review.ready) return;
            document.getElementById("careerSendNow").addEventListener("click", event => {
                event.currentTarget.disabled = true;
                Alfred.fetchJSON(`/api/career/job-analyses/${item.id}/email/send/`, {method: "POST",
                    body: JSON.stringify({...reviewed, confirmation: review.confirmation, confirm: true})}).then(sent => {
                    result.innerHTML = `<p class="small alert alert-success mb-0" id="careerSendDone" role="status">${sent.already_sent ? "Already sent earlier; not sent again." : "Sent"} to ${e(sent.sent.to)}.</p>`;
                }).catch(error => { result.innerHTML = `<p class="small alert alert-danger mb-0" role="alert">${e(error.message)}</p>`; });
            });
        }).catch(error => { result.innerHTML = `<p class="small alert alert-danger mb-0" role="alert">${Alfred.escapeHtml(error.message)}</p>`; });
    });
}

function loadCareerPatterns() {
    const target = document.getElementById("careerPatternsPanel");
    return Alfred.fetchJSON("/api/career/patterns/").then(data => {
        if (!data.available) { target.innerHTML = `<p class="small" id="careerPatternsUnavailable" role="status">${Alfred.escapeHtml(data.reason)}</p>`; return; }
        const rows = (items, render) => items.map(render).join("");
        target.innerHTML = `<div class="surface-card p-3" id="careerPatterns">
            <p class="small muted">${Alfred.escapeHtml(data.basis)}</p>
            <p class="small">Sent: ${data.sent}. Moved forward: ${data.conversion_rate}% of sent. Of decided (${data.decided}): ${data.decided_rate === null ? "no decisions yet" : `${data.decided_rate}% positive`}.</p>
            <table class="table table-sm small"><caption>Stages you recorded</caption><thead><tr><th scope="col">Stage</th><th scope="col">Count</th><th scope="col">Share</th></tr></thead>
            <tbody>${rows(data.funnel, row => `<tr><td>${Alfred.escapeHtml(careerStageLabel(row.stage))}</td><td>${row.count}</td><td>${row.percent}%</td></tr>`)}</tbody></table>
            ${data.score_vs_outcome.length ? `<table class="table table-sm small"><caption>Triage score by outcome</caption><thead><tr><th scope="col">Outcome</th><th scope="col">Average</th><th scope="col">Range</th><th scope="col">Count</th></tr></thead>
            <tbody>${rows(data.score_vs_outcome, row => `<tr><td>${Alfred.escapeHtml(row.group)}</td><td>${row.average}/5</td><td>${row.min}-${row.max}</td><td>${row.count}</td></tr>`)}</tbody></table>` : ""}
            ${data.top_gaps.length ? `<p class="small mb-0">Skills most often missing where you were rejected or withdrew: ${Alfred.escapeHtml(data.top_gaps.map(gap => `${gap.skill} (${gap.count})`).join(", "))}.</p>` : ""}
        </div>`;
    }).catch(() => { target.innerHTML = '<p class="small" role="status">Patterns could not load. Try again.</p>'; });
}

function renderCareerOutcomeForm(item) {
    renderCareerApplication(item);
    renderCareerInterviewPrep(item);
    renderCareerApplicationKit(item);
    const target = document.getElementById("careerOutcomeFormPanel");
    if (!item) { target.replaceChildren(); return; }
    const saved = item.outcome || {}, evidence = item.salary_evidence || {};
    const value = key => Alfred.escapeHtml(String(saved[key] ?? evidence[key] ?? ""));
    target.innerHTML = `
        <form id="careerOutcomeForm" data-live-refresh-hold="true">
            <p class="small muted">Annual comparisons assume 12 months, 52 weeks, 260 days or 2,080 hours. They are estimates, not predicted pay.</p>
            <div class="row g-3">
                <div class="col-md-6"><label class="form-label" for="careerOutcomeDecision">Your decision</label>
                    <select class="form-select" id="careerOutcomeDecision" name="outcome" required>
                        <option value="">Choose a decision</option><option value="accepted">Accepted</option><option value="rejected">Rejected</option>
                    </select></div>
                <div class="col-md-6"><label class="form-label" for="careerOutcomeDate">Decision date</label>
                    <input class="form-control" id="careerOutcomeDate" name="decided_at" type="date" value="${value("decided_at")}" required></div>
                <div class="col-md-6"><label class="form-label" for="careerOutcomeSalaryMin">Salary evidence minimum</label>
                    <input class="form-control" id="careerOutcomeSalaryMin" name="salary_min" type="number" min="0.01" step="0.01" value="${value("salary_min")}" required></div>
                <div class="col-md-6"><label class="form-label" for="careerOutcomeSalaryMax">Salary evidence maximum</label>
                    <input class="form-control" id="careerOutcomeSalaryMax" name="salary_max" type="number" min="0.01" step="0.01" value="${value("salary_max")}" required></div>
                <div class="col-md-6"><label class="form-label" for="careerOutcomeCurrency">Recorded currency code</label>
                    <input class="form-control" id="careerOutcomeCurrency" name="salary_currency" maxlength="3" pattern="[A-Za-z]{3}" value="${value("salary_currency")}" required></div>
                <div class="col-md-6"><label class="form-label" for="careerOutcomePeriod">Salary period</label>
                    <select class="form-select" id="careerOutcomePeriod" name="salary_period" required>
                        <option value="year">Per year</option><option value="month">Per month</option><option value="week">Per week</option><option value="day">Per day</option><option value="hour">Per hour</option>
                    </select></div>
                <div class="col-12"><label class="form-label" for="careerOutcomeSource">Reviewed source URL</label>
                    <input class="form-control" id="careerOutcomeSource" name="source_url" type="url" value="${Alfred.escapeHtml(saved.source_url || item.job_url || "")}" required></div>
                <div class="col-12"><label class="form-label" for="careerOutcomeLocation">Location</label>
                    <input class="form-control" id="careerOutcomeLocation" name="location" value="${Alfred.escapeHtml(saved.location || item.location || "")}" required></div>
                <div class="col-12"><label class="form-label" for="careerOutcomeNotes">Your notes</label>
                    <textarea class="form-control" id="careerOutcomeNotes" name="notes" maxlength="1200">${value("notes")}</textarea></div>
                <div class="col-12"><label class="form-label" for="careerOutcomeReason">Reason for rejection, if applicable</label>
                    <textarea class="form-control" id="careerOutcomeReason" name="rejection_reason" maxlength="600">${value("rejection_reason")}</textarea></div>
            </div>
            <button class="btn btn-primary mt-3" type="submit">Save your outcome</button>
            <div id="careerOutcomeFeedback" class="d-none alert mt-3 mb-0" role="status" aria-live="polite"></div>
        </form>`;
    const form = document.getElementById("careerOutcomeForm");
    form.elements.outcome.value = saved.outcome || "";
    form.elements.salary_period.value = saved.salary_period || evidence.salary_period || "year";
    form.addEventListener("submit", event => {
        event.preventDefault();
        const button = form.querySelector("button[type=submit]"); button.disabled = true;
        const payload = Object.fromEntries(new FormData(form).entries()); payload.revision = item.updated_at;
        Alfred.fetchJSON(`/api/career/job-analyses/${item.id}/outcome/`, {method:"PATCH", body:JSON.stringify(payload)})
            .then(data => {
                const index = careerOpportunities.findIndex(row => row.id === item.id);
                if (index >= 0) careerOpportunities[index] = data.opportunity;
                document.getElementById("careerOutcomeAnalysis").selectedOptions[0].textContent = careerOpportunityLabel(data.opportunity);
                renderCareerOutcomeForm(data.opportunity);
                showCareerFeedback("careerOutcomeFeedback", "Your outcome was saved as an owner report.", "success");
            })
            .catch(error => showCareerFeedback("careerOutcomeFeedback", error.message, "danger"))
            .finally(() => { button.disabled = false; });
    });
}

function formatCompensationAmount(value, currency) {
    const amount = Number(value || 0);
    if (/^[A-Z]{3}$/.test(currency || "")) {
        try {
            return new Intl.NumberFormat("en-IN", { style: "currency", currency, maximumFractionDigits: 2 }).format(amount);
        } catch (_) { /* Unsupported code: show the amount without implying a currency. */ }
    }
    return `${amount.toLocaleString("en-IN", { maximumFractionDigits: 2 })} (currency not stated)`;
}

function renderCompensationBenchmark(benchmark) {
    const target = document.getElementById("careerCompensationPanel");
    if (!benchmark || !benchmark.available) {
        Alfred.setHTML(target, `<div class="mini-card"><div class="fw-semibold">Compensation Benchmark</div><div class="muted small mt-2">${Alfred.escapeHtml(benchmark?.summary || "Salary evidence will appear when Alfred finds pay-bearing job signals.")}</div></div>`);
        return;
    }
    const observations = (benchmark.salary_observations || []).map(item => {
        const link = openingSourceLink(item.url);
        const band = `${formatCompensationAmount(item.salary_min_annual, item.currency)} to ${formatCompensationAmount(item.salary_max_annual || item.salary_min_annual, item.currency)} annual`;
        return `<li class="insight-item surface-card">${Alfred.escapeHtml(item.source || "Source")} | ${Alfred.escapeHtml(item.location || "Location not specified")} | ${Alfred.escapeHtml(band)} | ${item.observed_at ? `Checked ${Alfred.escapeHtml(Alfred.formatDate(item.observed_at))}` : "Check date unavailable"}${link ? ` · <a href="${Alfred.escapeHtml(link)}" target="_blank" rel="noopener">Source</a>` : ""}</li>`;
    }).join("");
    Alfred.setHTML(target, `
        <div class="mini-card">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">Compensation Benchmark</div>
                    <div class="muted small mt-1">${Alfred.escapeHtml(benchmark.location_scope || "Global / Remote")} | ${benchmark.sample_count || 0} evidence point(s)</div>
                    <div class="muted small mt-2">${Alfred.escapeHtml(benchmark.summary || "")}</div>
                </div>
                <div class="text-end">
                    <div class="metric-value" style="font-size:1.4rem;">${Alfred.escapeHtml(formatCompensationAmount(benchmark.market_mid_annual || benchmark.market_min_annual, benchmark.currency))}</div>
                    <div class="muted small">Mid benchmark / year</div>
                </div>
            </div>
            <div class="muted small mt-3"><strong>Band:</strong> ${Alfred.escapeHtml(formatCompensationAmount(benchmark.market_min_annual, benchmark.currency))} to ${Alfred.escapeHtml(formatCompensationAmount(benchmark.market_max_annual || benchmark.market_min_annual, benchmark.currency))} annual</div>
            ${observations ? `<ul class="insight-list mb-0 mt-3">${observations}</ul>` : ""}
        </div>
    `);
}

function renderStudyPlan(plan) {
    const target = document.getElementById("careerStudyPlan");
    if (!plan || !(plan.tracks || []).length) {
        Alfred.setHTML(target, `<div class="empty-state">Study recommendations will appear once Alfred has enough profile, resume, or job-gap data.</div>`);
        return;
    }

    Alfred.setHTML(target, `
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
    `);
}

function renderLayoffNews(items) {
    const target = document.getElementById("careerLayoffNews");
    Alfred.setHTML(target, items.length ? items.map(item => `
        <div class="mini-card">
            <div class="fw-semibold">${Alfred.escapeHtml(item.title || "News item")}</div>
            <div class="muted small">${Alfred.escapeHtml(item.source || "Unknown source")} | ${Alfred.escapeHtml(item.published || "No publish time")}</div>
            <div class="mt-2"><a href="${Alfred.safeHref(item.link)}" target="_blank" rel="noopener">Open article</a></div>
        </div>
    `).join("") : `<div class="empty-state">No layoff news items were pulled from the configured feed right now.</div>`);
}

function openingSourceLink(value) {
    try {
        const url = new URL(value);
        if (url.protocol === "https:" && !url.username && !url.password) return url.href;
    } catch (_) { /* Untrusted feed links remain inactive. */ }
    return "";
}

function renderOpenings(items, counts = {}) {
    const target = document.getElementById("careerOpenings");
    const meta = document.getElementById("careerOpeningsMeta");
    if (meta) {
        const filteredCount = Number(counts.filtered_candidates ?? items.length);
        const totalCount = Number(counts.total_candidates ?? filteredCount);
        meta.textContent = filteredCount === totalCount
            ? `${filteredCount} job lead${filteredCount === 1 ? "" : "s"} matched your search. Availability is unverified.`
            : `${filteredCount} of ${totalCount} job leads match the active location filter. Availability is unverified.`;
    }
    Alfred.setHTML(target, items.length ? items.map(item => {
        const link = openingSourceLink(item.url), proof = openingSourceLink(item.source_evidence?.source_url);
        const labels = {fresh:"Fresh feed evidence; opening availability is unverified.", stale:"Stale cached lead; recheck the source.", unknown:"Unverified lead; freshness evidence is missing.", unavailable:"Source unavailable; cached lead only."};
        return `
        <div class="mini-card surface-card">
            <div class="fw-semibold">${Alfred.escapeHtml(item.title || "Opening")}</div>
            <div class="muted small">${Alfred.escapeHtml(item.company || "Unknown company")} | ${Alfred.escapeHtml(item.location || "Location not specified")}</div>
            <div class="muted small">${Alfred.escapeHtml(item.category || "")}${item.salary ? ` | ${Alfred.escapeHtml(item.salary)}` : ""}</div>
            <div class="muted small mt-2">${item.tags?.length ? Alfred.escapeHtml(item.tags.join(", ")) : ""}</div>
            <div class="muted small mt-2">${Alfred.escapeHtml(item.portal_name || "Source")} | rule-based relevance ${Alfred.formatNumber(item.relevance_score || 0, 0)}/100; not a hiring probability</div>
            <div class="muted small mt-2" data-opening-source-status="${Alfred.escapeHtml(item.source_status || "unknown")}">${Alfred.escapeHtml(labels[item.source_status] || labels.unknown)} ${item.source_evidence?.verified_at ? `Checked ${Alfred.escapeHtml(item.source_evidence.verified_at)}.` : ""} ${item.source_evidence?.stale_after ? `Evidence expires ${Alfred.escapeHtml(item.source_evidence.stale_after)}.` : ""}</div>
            <div class="muted small mt-2">${item.publication_date ? `Posted ${Alfred.escapeHtml(item.publication_date)}.` : "Posting date not stated."}</div>
            <div class="muted small mt-2">${(item.match_reasons || []).length ? Alfred.escapeHtml(item.match_reasons.join(" ")) : "No direct title or skill overlap with your role and tracked skills."}</div>
            <div class="mt-2">${link ? `<a href="${Alfred.escapeHtml(link)}" target="_blank" rel="noopener">View posting</a>` : "Posting link unavailable"}${proof ? ` · <a href="${Alfred.escapeHtml(proof)}" target="_blank" rel="noopener">Source feed</a>` : ""}</div>
        </div>
    `; }).join("") : `<div class="empty-state">No source-backed job leads are available for this search.</div>`);
}

function hydrateCareerForm(profile) {
    const form = document.getElementById("careerProfileForm");
    form.role.value = profile.role || "";
    form.experience_years.value = profile.experience_years ?? 0;
    form.skills.value = profile.skills || "";
    form.last_salary.value = profile.last_salary ?? 0;
    form.salary_currency.value = profile.salary_currency || "";
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
                loadCareerResumeChoices();
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
    const form = event.currentTarget;
    const select = document.getElementById("careerRecruiterResume");
    if (form.dataset.submitting === "true" || select.disabled) return;
    const payload = Object.fromEntries(new FormData(form).entries());
    payload.resume_id = select.value;
    const button = form.querySelector("button[type='submit']");
    button.disabled = true;
    form.dataset.submitting = "true";
    showCareerFeedback("careerJobFeedback", "Analyzing the job link against the selected resume…", "info");
    Alfred.fetchJSON("/api/career/job-match/", {
        method: "POST",
        body: JSON.stringify(payload),
    })
        .then(() => {
            showCareerFeedback("careerJobFeedback", "Job link analyzed.", "success");
            loadCareerDashboard();
            loadCareerOpportunities();
        })
        .catch(error => showCareerFeedback("careerJobFeedback", error.message, "danger"))
        .finally(() => {
            delete form.dataset.submitting;
            button.disabled = select.disabled;
        });
}

function loadCareerResumeChoices() {
    const form = document.getElementById("careerRecruiterForm");
    const select = form.elements.resume_id;
    const reload = document.getElementById("careerRecruiterResumeReload");
    const status = document.getElementById("careerRecruiterResumeStatus");
    const jobForm = document.getElementById("careerJobMatchForm");
    const previous = select.value;
    select.disabled = reload.disabled = true;
    form.querySelector("button[type='submit']").disabled = true;
    jobForm.querySelector("button[type='submit']").disabled = true;
    status.textContent = "Loading your saved resumes…";
    return Alfred.fetchJSON("/api/career/resumes/").then(data => {
        const resumes = Array.isArray(data) ? data : data.results;
        select.replaceChildren(new Option("Latest saved resume (manual profile if none)", ""));
        resumes.forEach(resume => select.add(new Option(`${resume.file_name} — ${resume.parser_status_label}`, resume.id)));
        if (previous && !resumes.some(resume => String(resume.id) === previous)) {
            select.add(new Option("Previously selected resume unavailable; choose another", previous));
        }
        select.value = previous;
        select.disabled = false;
        status.textContent = "Used for recruiter and job-link matching. Only your saved resumes are listed. Matching captures these fields; later edits do not rewrite earlier analyses.";
    }).catch(() => {
        select.replaceChildren(new Option("Resume list unavailable", previous));
        status.textContent = "Resume list unavailable. Reload to retry; your recruiter text and attachment are preserved.";
    }).finally(() => {
        reload.disabled = false;
        form.querySelector("button[type='submit']").disabled = select.disabled || form.dataset.submitting === "true";
        jobForm.querySelector("button[type='submit']").disabled = select.disabled || jobForm.dataset.submitting === "true";
    });
}

function submitCareerRecruiterLead(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (form.dataset.submitting === "true" || form.elements.resume_id.disabled) return;
    const textValue = form.elements.message_text?.value?.trim() || "";
    const attachment = form.elements.attachment?.files?.[0];
    if (!textValue && !attachment) {
        showCareerFeedback("careerRecruiterFeedback", "Paste recruiter mail text or choose a JD attachment first.", "warning");
        return;
    }
    const selected = form.elements.resume_id.value;
    const body = new FormData(form);
    const button = form.querySelector("button[type='submit']");
    button.disabled = true;
    form.dataset.submitting = "true";
    showCareerFeedback("careerRecruiterFeedback", "Analyzing the selected resume and recruiter evidence…", "info");
    Alfred.fetchJSON("/api/career/recruiter-match/", {
        method: "POST",
        body,
    })
        .then(() => {
            form.reset();
            form.elements.resume_id.value = selected;
            showCareerFeedback("careerRecruiterFeedback", "Recruiter lead analyzed.", "success");
            loadCareerDashboard();
            loadCareerOpportunities();
        })
        .catch(error => showCareerFeedback("careerRecruiterFeedback", error.message, "danger"))
        .finally(() => {
            delete form.dataset.submitting;
            button.disabled = form.elements.resume_id.disabled;
        });
}

function hydrateSimulationForm(profile, projection) {
    const form = document.getElementById("careerSimulationForm");
    form.monthly_income.value = projection.current_income || "";
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
        Alfred.setHTML(target, `<div class="empty-state">Projection data is not available yet.</div>`);
        return;
    }

    const baselineYear1 = baseline.projections?.[0]?.projected_income || 0;
    const baselineYear5 = baseline.projections?.at(-1)?.projected_income || 0;
    const scenarioYear1 = scenario?.projections?.[0]?.projected_income || 0;
    const scenarioYear5 = scenario?.projections?.at(-1)?.projected_income || 0;
    const assumptions = simulation?.assumptions || null;
    const baselineReasoning = Array.isArray(baseline.reasoning) ? baseline.reasoning.slice(0, 3) : [];
    const scenarioReasoning = Array.isArray(scenario?.reasoning) ? scenario.reasoning.slice(0, 3) : [];

    Alfred.setHTML(target, `
        <div class="soft-grid two-up">
            <div class="mini-card">
                <div class="fw-semibold">Baseline</div>
                <div class="muted small mt-1">${Alfred.escapeHtml(baseline.projection_mode || "heuristic")}</div>
                <div class="mt-3">Year 1 <strong>${baselineYear1 > 0 ? Alfred.formatCurrency(baselineYear1) : "Unavailable"}</strong></div>
                <div class="mt-2">Year 5 <strong>${baselineYear5 > 0 ? Alfred.formatCurrency(baselineYear5) : "Unavailable"}</strong></div>
                <div class="muted small mt-3">${Alfred.escapeHtml(baseline.projection_method || "")}</div>
                ${baselineReasoning.length ? `<div class="muted small mt-3">${baselineReasoning.map(item => Alfred.escapeHtml(item.label || "")).join(" | ")}</div>` : ""}
            </div>
            <div class="mini-card">
                <div class="fw-semibold">Scenario</div>
                <div class="muted small mt-1">${scenario ? Alfred.escapeHtml(scenario.projection_mode || "heuristic") : "Run a scenario"}</div>
                <div class="mt-3">Year 1 <strong>${scenario ? (scenarioYear1 > 0 ? Alfred.formatCurrency(scenarioYear1) : "Unavailable") : "Not simulated"}</strong></div>
                <div class="mt-2">Year 5 <strong>${scenario ? (scenarioYear5 > 0 ? Alfred.formatCurrency(scenarioYear5) : "Unavailable") : "Not simulated"}</strong></div>
                <div class="muted small mt-3">${scenario ? Alfred.escapeHtml(scenario.projection_method || "") : "Scenario details appear here after a run."}</div>
                ${scenarioReasoning.length ? `<div class="muted small mt-3">${scenarioReasoning.map(item => Alfred.escapeHtml(item.label || "")).join(" | ")}</div>` : ""}
            </div>
        </div>
        <div class="mini-card">
            <div class="fw-semibold mb-2">Change Summary</div>
            <div class="data-stack">
                <div class="data-row">
                    <div class="data-label">Year 1 delta</div>
                    <div class="data-value">${scenario ? (simulation.delta?.year_1_projected_income == null ? "Unavailable" : Alfred.formatCurrency(simulation.delta.year_1_projected_income)) : "Run a scenario"}</div>
                </div>
                <div class="data-row">
                    <div class="data-label">Year 5 delta</div>
                    <div class="data-value">${scenario ? (simulation.delta?.year_5_projected_income == null ? "Unavailable" : Alfred.formatCurrency(simulation.delta.year_5_projected_income)) : "Run a scenario"}</div>
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
    `);
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
