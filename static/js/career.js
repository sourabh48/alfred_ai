let salaryChart;

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("careerRoot")) {
        return;
    }

    document.getElementById("careerProfileForm").addEventListener("submit", submitCareerProfile);
    document.getElementById("careerResumeForm").addEventListener("submit", submitCareerResume);
    document.getElementById("careerJobMatchForm").addEventListener("submit", submitCareerJobMatch);
    loadCareerDashboard();
    Alfred.enableLiveRefresh("career-live", loadCareerDashboard, { rootId: "careerRoot" });
});

function loadCareerDashboard(options = {}) {
    return Alfred.fetchJSON("/api/career/dashboard/")
        .then(data => {
            const profile = data.profile || {};
            const projection = data.projection || {};
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
            renderCareerProjectionTable(projection.projections || []);
            renderResumePanel(data.latest_resume);
            renderJobMatchPanel(data.latest_job_analysis);
            renderStudyPlan(data.study_recommendations || {});
            renderLayoffNews(data.market?.layoff_news || []);
            renderOpenings(data.openings || []);
            if (!options.live) {
                hydrateCareerForm(profile);
            }
            Alfred.clearPageAlert("careerRoot");
        })
        .catch(error => {
            Alfred.upsertPageAlert("careerRoot", error.message, "danger");
        });
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
    const cards = [
        { title: "Experience", value: `${Alfred.formatNumber(profile.experience_years, 1)} yrs`, copy: profile.role || "Role pending" },
        { title: "Resume Parse", value: resume ? `${Alfred.formatNumber((resume.parse_confidence || 0) * 100, 0)}%` : "No resume", copy: resume ? (resume.parser_status_label || "Parsed") : "Upload a resume" },
        { title: "Job Fit", value: jobAnalysis ? `${Alfred.formatNumber(jobAnalysis.fit_score || 0, 0)}/100` : "No job link", copy: jobAnalysis ? `${Alfred.escapeHtml(jobAnalysis.company || jobAnalysis.source_name || "Latest analysis")}` : "Paste a job URL" },
        {
            title: "Career Timing",
            value: timing?.readiness_score != null ? `${Alfred.formatNumber(timing.readiness_score || 0, 0)}/100` : (market ? `${Alfred.formatNumber(market.risk_score || 0, 0)}/100` : "N/A"),
            copy: timing?.summary || (latest ? `Year-5 confidence ${latest.confidence || 0}%` : "Projection pending"),
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

function renderCareerProjectionTable(items) {
    const target = document.getElementById("careerProjectionTable");
    if (!items.length) {
        target.innerHTML = `<div class="empty-state">Projection data is not available yet.</div>`;
        return;
    }

    target.innerHTML = items.map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">Year ${item.year}</div>
                    <div class="muted small">Confidence ${item.confidence}% | Real ${Alfred.formatCurrency(item.real_income_estimate || item.projected_income)}</div>
                </div>
                <strong>${Alfred.formatCurrency(item.projected_income)}</strong>
            </div>
        </div>
    `).join("");
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
    target.innerHTML = `
        <div class="mini-card">
            <div class="fw-semibold">${Alfred.escapeHtml(resume.file_name || "Latest resume")}</div>
            <div class="muted small">${Alfred.escapeHtml(resume.parser_status_label || "Parsed")} | confidence ${Alfred.formatNumber((resume.parse_confidence || 0) * 100, 0)}%</div>
            <div class="muted small mt-2">${Alfred.escapeHtml(resume.summary || "")}</div>
            <div class="muted small mt-2">Role ${Alfred.escapeHtml(payload.role || "Unknown")} | Experience ${Alfred.formatNumber(payload.experience_years || 0, 1)} years</div>
            <div class="muted small mt-2">${(payload.skills || []).length ? Alfred.escapeHtml(payload.skills.slice(0, 12).join(", ")) : "No skill list extracted."}</div>
            <div class="muted small mt-2"><strong>Strengths:</strong> ${Alfred.escapeHtml(resume.strengths || "None detected.")}</div>
            <div class="muted small mt-2"><strong>Weaknesses:</strong> ${Alfred.escapeHtml(resume.weaknesses || "None detected.")}</div>
        </div>
    `;
}

function renderJobMatchPanel(analysis) {
    const target = document.getElementById("careerJobMatchPanel");
    if (!analysis) {
        target.innerHTML = `<div class="empty-state">No job link analyzed yet.</div>`;
        return;
    }
    const payload = analysis.extracted_payload || {};
    const fit = payload.fit || {};
    target.innerHTML = `
        <div class="mini-card">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(analysis.job_title || "Job role")} <span class="muted small">${Alfred.escapeHtml(analysis.company || analysis.source_name || "")}</span></div>
                    <div class="muted small">${Alfred.escapeHtml(analysis.location || "Location not detected")}</div>
                    <div class="muted small mt-2">${Alfred.escapeHtml(analysis.summary || "")}</div>
                    <div class="muted small mt-2"><strong>Matched:</strong> ${fit.matched_skills?.length ? Alfred.escapeHtml(fit.matched_skills.join(", ")) : "No strong overlap detected."}</div>
                    <div class="muted small mt-2"><strong>Gaps:</strong> ${fit.missing_skills?.length ? Alfred.escapeHtml(fit.missing_skills.join(", ")) : "No major gap extracted."}</div>
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

function renderOpenings(items) {
    const target = document.getElementById("careerOpenings");
    target.innerHTML = items.length ? items.map(item => `
        <div class="mini-card">
            <div class="fw-semibold">${Alfred.escapeHtml(item.title || "Opening")}</div>
            <div class="muted small">${Alfred.escapeHtml(item.company || "Unknown company")} | ${Alfred.escapeHtml(item.location || "Remote")}</div>
            <div class="muted small">${Alfred.escapeHtml(item.category || "")}${item.salary ? ` | ${Alfred.escapeHtml(item.salary)}` : ""}</div>
            <div class="muted small mt-2">${item.tags?.length ? Alfred.escapeHtml(item.tags.join(", ")) : ""}</div>
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
    const payload = new FormData(form);
    Alfred.fetchJSON("/api/career/resumes/upload/", {
        method: "POST",
        body: payload,
    })
        .then(data => {
            form.reset();
            const resume = data.resume || {};
            const confidence = resume.parse_confidence != null ? ` Confidence ${Alfred.formatNumber((Number(resume.parse_confidence) || 0) * 100, 0)}%.` : "";
            const status = resume.parser_status_label ? ` Status: ${resume.parser_status_label}.` : "";
            showCareerFeedback("careerResumeFeedback", `Resume uploaded.${status}${confidence}`.trim(), resume.parser_status === "parsed" ? "success" : "warning");
            loadCareerDashboard();
        })
        .catch(error => showCareerFeedback("careerResumeFeedback", error.message, "danger"));
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
