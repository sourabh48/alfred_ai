// One chart look for every page: a colour-blind-safe palette chosen per theme, quiet axes, readable tooltips.
// The palette lives in workspace.css (--series-1..8 per theme) so charts and legend dots share one source.
// Charts whose values are rupees: their tooltips and axes carry ₹ in Indian digit grouping.
const MONEY_CHARTS = new Set(["dashboardMonthlyChart", "dashboardCategoryChart", "expenseTrend", "budgetForecastChart", "loanTrendChart",
    "allocationChart", "growthChart", "familyNetChart", "taxComparisonChart", "bikeServiceCostChart", "bikeServiceMixChart", "salaryChart"]);
const chartTheme = {series: [], other: "", surface: ""};
function styleCharts(dark) {
    if (!window.Chart) return;
    const ink = dark ? "#c9dfff" : "#53647c", grid = dark ? "#2b4462" : "#e8eef6";
    const css = getComputedStyle(document.documentElement);
    Object.assign(chartTheme, {series: [1,2,3,4,5,6,7,8].map(n=>css.getPropertyValue(`--series-${n}`).trim()),
        other: css.getPropertyValue("--series-other").trim(), surface: dark ? "#182b44" : "#ffffff"});
    const d = Chart.defaults;
    Object.assign(d, { color: ink, borderColor: grid, maintainAspectRatio: false, locale: "en-IN" });
    const isMoney = chart => MONEY_CHARTS.has(chart.canvas.id);
    d.font.family = getComputedStyle(document.body).fontFamily; d.font.size = 12;
    d.animation.duration = matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 650;
    d.animation.easing = "easeOutQuart";
    Object.assign(d.plugins.legend.labels, { usePointStyle: true, pointStyle: "circle", boxWidth: 8, boxHeight: 8, padding: 14,
        // A series with nothing recorded is left out of the legend rather than shown as an empty promise.
        filter: (item, data) => item.datasetIndex === undefined || (data.datasets[item.datasetIndex]?.data || []).some(v => Number(v)) });
    Object.assign(d.plugins.tooltip, { backgroundColor: dark ? "#0b1626" : "#10253f", padding: 10, cornerRadius: 8, boxPadding: 4,
        usePointStyle: true, titleFont: { weight: "600" } });
    d.plugins.tooltip.callbacks.label = ctx => {
        const name = ctx.dataset.label || ctx.label || "";
        const value = isMoney(ctx.chart) && typeof ctx.raw === "number" ? Alfred.formatCurrency(ctx.raw) : ctx.formattedValue;
        return name ? `${name}: ${value}` : value;
    };
    d.scale.grid.color = grid; d.scale.border.display = false; d.scale.ticks.padding = 6;
    // Per-type scale defaults hold only what they override, so whole objects are assigned.
    d.scales.category.grid = { display: false };
    const compact = new Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 1 });
    d.scales.linear.ticks = { maxTicksLimit: 6, callback(value) { return (isMoney(this.chart) ? "₹" : "") + compact.format(value); } };
    Object.assign(d.scales.radialLinear, { grid: { color: grid }, angleLines: { color: grid },
        pointLabels: { color: ink, font: { size: 12 } }, ticks: { display: false, maxTicksLimit: 5 } });
    if (!Chart.registry.plugins.get("alfredLook")) Chart.register({
        id: "alfredLook",
        afterInit(chart) {  // a chart is an image to a screen reader: name it after its card heading
            const canvas = chart.canvas;
            if (!canvas.getAttribute("aria-label")) {
                const heading = canvas.closest(".surface-card, .card, section")?.querySelector("h2, h3, h5, .card-title");
                canvas.setAttribute("role", "img");
                canvas.setAttribute("aria-label", `${heading ? heading.textContent.trim() : "Chart"} (chart; figures are also listed on this page)`);
            }
        },
        beforeUpdate(chart) {
            const surface=chartTheme.surface, color=i=>chartTheme.series[i] || chartTheme.other;
            if(matchMedia("(prefers-reduced-motion: reduce)").matches) chart.options.animation=false;
            // Colour follows the thing, not its position: Income is the same green on every chart.
            const entity = { Expenses: 0, Spending: 0, Loans: 1, "Loan payments": 1, Investments: 3, Other: 4, Income: 5, "Card payments": 6 };
            chart.data.datasets.forEach((ds, index) => {
                const i = entity[ds.label] ?? index;
                if (ds.alfredKeepColors) return;  // e.g. severity, which keeps its status colours
                const type = ds.type || chart.config.type;
                if (["doughnut", "pie", "polarArea"].includes(type) || ds.alfredByPoint) {
                    ds.backgroundColor = (ds.data || []).map((_, j) => color(j));
                    Object.assign(ds, { borderColor: surface, borderWidth: 2, hoverOffset: 4, borderRadius: type === "bar" ? 4 : 0 });
                } else if (type === "bar") {
                    Object.assign(ds, { backgroundColor: color(i), borderColor: surface, borderWidth: 0, borderRadius: 4, maxBarThickness: 44 });
                } else {
                    const c = color(i);
                    Object.assign(ds, { borderColor: c, backgroundColor: c + "26", pointBackgroundColor: c, pointBorderColor: surface,
                        pointBorderWidth: 2, pointRadius: ds.pointRadius ?? 4, pointHoverRadius: 7, borderWidth: 2, tension: ds.tension ?? 0.3 });
                }
            });
        },
    });
    // Charts already drawn keep their resolved axis colours, so repaint them for the new theme.
    Object.values(Chart.instances).forEach(chart => {
        Object.values(chart.options.scales || {}).forEach(scale => {
            scale.ticks.color = ink; scale.grid.color = grid;
            if (scale.pointLabels) scale.pointLabels.color = ink;
            if (scale.angleLines) scale.angleLines.color = grid;
        });
        chart.update("none");
    });
}

document.addEventListener("DOMContentLoaded", () => {
    matchMedia("(prefers-reduced-motion: reduce)").addEventListener("change",()=>{
        if(!window.Chart)return;
        Object.values(Chart.instances).forEach(chart=>{chart.stop();chart.options.animation={duration:matchMedia("(prefers-reduced-motion: reduce)").matches?0:650,easing:"easeOutQuart"};});
        styleCharts(document.documentElement.dataset.theme==="dark");
    });
    const theme = document.getElementById("workspaceTheme");
    function setTheme(dark) {
        document.documentElement.dataset.theme = dark ? "dark" : "light";
        theme.textContent = dark ? "Light" : "Dark";
        theme.setAttribute("aria-pressed", String(dark));
        theme.setAttribute("aria-label", dark ? "Use light appearance" : "Use dark appearance");
        styleCharts(dark);
    }
    let preference;
    try { preference = localStorage.getItem("alfred.appearance"); } catch (_) { /* Locked-down browser. */ }
    setTheme(preference ? preference === "dark" : matchMedia("(prefers-color-scheme: dark)").matches);
    theme.addEventListener("click", () => {
        const dark = document.documentElement.dataset.theme !== "dark";
        setTheme(dark);
        try { localStorage.setItem("alfred.appearance", dark ? "dark" : "light"); } catch (_) { /* Theme still applies. */ }
    });
    function markNavigation() {
        const banking = location.pathname === "/expenses/" && location.hash === "#bankAccountsPanel";
        document.querySelectorAll("#sidebarMenu .nav-link").forEach(link => {
            if (location.pathname === "/settings/" && link.getAttribute("href").startsWith("/settings/")) link.classList.toggle("active", link.getAttribute("href") === "/settings/");
            if (location.pathname === "/expenses/" && link.getAttribute("href").startsWith("/expenses/")) link.classList.toggle("active", banking ? link.hash === "#bankAccountsPanel" : !link.hash);
            if (link.classList.contains("active")) link.setAttribute("aria-current", "page"); else link.removeAttribute("aria-current");
        });
    }
    markNavigation(); window.addEventListener("hashchange", markNavigation);
    const menu = document.getElementById("sidebarMenu");
    document.addEventListener("keydown", event => {
        if (event.key === "Escape" && menu) {
            const toggle = document.querySelector('[aria-controls="sidebarMenu"]');
            const close = () => { bootstrap.Collapse.getOrCreateInstance(menu).hide(); toggle.focus(); };
            if (menu.classList.contains("show")) close();
            else if (menu.classList.contains("collapsing") && toggle.getAttribute("aria-expanded") === "true") menu.addEventListener("shown.bs.collapse", close, {once: true});
        }
    });
    document.querySelectorAll('[data-table-controls]').forEach(controls => {
        const body = document.getElementById(controls.dataset.tableControls);
        const search = controls.querySelector('input'), order = controls.querySelector('select');
        const observer = new MutationObserver(apply);
        function apply() {
            observer.disconnect();
            const focused = body.contains(document.activeElement) ? document.activeElement : null;
            const rows = [...body.rows].filter(row=>row.cells.length>1);
            rows.forEach((row,index)=>{row.dataset.originalOrder ??= String(index)});
            rows.sort((a,b)=>order.value ? a.cells[controls.dataset.tableControls==='loanTableBody'?1:0].textContent.localeCompare(b.cells[controls.dataset.tableControls==='loanTableBody'?1:0].textContent)*(order.value==='asc'?1:-1) : Number(a.dataset.originalOrder)-Number(b.dataset.originalOrder)).forEach(row=>body.append(row));
            let matches = 0, retained = 0;
            rows.forEach(row => {
                const match = row.textContent.toLowerCase().includes(search.value.toLowerCase());
                const selected = Boolean(row.querySelector('input[type=checkbox]:checked'));
                row.hidden = !match && !selected; matches += match; retained += !match && selected;
            });
            controls.querySelector('[data-table-count]').textContent = `${matches} matching displayed records${retained ? ` · ${retained} selected records retained for review` : ''}`;
            focused?.focus({preventScroll:true});
            observer.observe(body,{childList:true});
        }
        search.addEventListener('input',apply); order.addEventListener('change',apply); body.addEventListener('change',apply); apply();
    });
    const bankBody = document.getElementById('bankAccountsBody');
    if (bankBody) {
        const status = document.getElementById('bankAccountsStatus'), refresh = document.getElementById('bankAccountsRefresh');
        const previous = document.getElementById('bankAccountsPrevious'), next = document.getElementById('bankAccountsNext');
        let page = 1, generation = 0, active = true;
        function currencyPicker(account) {
            // FIN-15: confirm a not-recorded account currency once; the server refuses a change after postings.
            const select = document.createElement('select'); select.className = 'form-select form-select-sm';
            select.setAttribute('aria-label', `Currency of ${account.nickname || account.bank_name || 'this account'}`);
            [['','Not recorded'],['INR','INR'],['USD','USD'],['EUR','EUR'],['GBP','GBP']].forEach(([value,label])=>select.append(new Option(label,value)));
            select.addEventListener('change', async () => {
                if (!select.value) return;
                select.disabled = true;
                try { await Alfred.fetchJSON(`/api/expenses/accounts/${account.id}/`,{method:'PATCH',body:JSON.stringify({currency:select.value})}); await loadAccounts(); status.textContent = `Account currency recorded. ${status.textContent}`; }
                catch (error) { status.textContent = error.message; select.value = ''; select.disabled = false; }
            });
            return select;
        }
        async function loadAccounts() {
            const ticket = ++generation; refresh.disabled = true; previous.disabled = true; next.disabled = true;
            bankBody.setAttribute('aria-busy','true'); status.textContent = 'Loading your recorded accounts.';
            try {
                let pagination;
                const result = await Alfred.fetchJSON(`/api/expenses/accounts/?page=${page}&page_size=25`,{onResponse:response=>{pagination={count:response.headers.get('X-Total-Count'),previous:response.headers.get('X-Has-Previous')==='true',next:response.headers.get('X-Has-Next')==='true'}}});
                if (!active || ticket !== generation) return;
                const accounts = result.results || result; bankBody.replaceChildren();
                accounts.forEach(account => {
                    const row = document.createElement('tr');
                    const reference = /^\*{4}\d{4}$/.test(account.masked_account_number) ? account.masked_account_number : 'Reference hidden';
                    const balance = account.current_balance === null || account.current_balance === undefined ? 'Balance unavailable' : Alfred.formatCurrency(account.current_balance, account.currency || 'INR') + (account.currency && account.currency !== 'INR' ? ' · kept out of rupee totals' : '');
                    const since = account.balance_since_statement || {};
                    const rolled = since.status === 'estimated' ? ` · about ${Alfred.formatCurrency(since.estimated_balance, account.currency || 'INR')} now, from the ${since.anchor_date} statement plus ${since.entries} later ${since.entries === 1 ? 'entry' : 'entries'} (estimate, not a bank quote${since.same_day_not_counted ? `; ${since.same_day_not_counted} same-day ${since.same_day_not_counted === 1 ? 'entry' : 'entries'} not counted` : ''})` : '';
                    [account.nickname || account.bank_name || 'Bank account',reference,account.account_type,balance + rolled,account.currency || currencyPicker(account),account.is_active?'Active':'Inactive'].forEach(value=>{const cell=document.createElement('td');cell.append(value);row.append(cell)});
                    bankBody.append(row);
                });
                status.textContent = accounts.length ? `${pagination.count ?? accounts.length} owned accounts · page ${page} · latest recorded balances, not live bank quotes` : 'No bank accounts recorded. Imported statements can create owned accounts.';
                previous.disabled = !pagination.previous; next.disabled = !pagination.next;
            } catch (error) { if (active && ticket === generation) status.textContent = error.message; }
            finally { refresh.disabled = false; bankBody.setAttribute('aria-busy','false'); }
        }
        refresh.addEventListener('click',loadAccounts);
        previous.addEventListener('click',()=>{page--;loadAccounts()}); next.addEventListener('click',()=>{page++;loadAccounts()});
        window.addEventListener('pagehide',()=>{active=false;generation++;bankBody.replaceChildren();status.textContent=''});
        window.addEventListener('pageshow',event=>{active=true;if(event.persisted)loadAccounts()});
        loadAccounts();
    }
});

// Long pages get an "On this page" bar so a section is one click away instead of a long scroll.
document.addEventListener("DOMContentLoaded", () => {
    const main = document.getElementById("alfredMainScroll");
    if (!main || main.querySelector("nav.page-index, [data-no-page-index]")) return;  // a hand-made index, or a page that opts out (Home is short)
    const headings = [...main.querySelectorAll("h2")].filter(h => !h.closest(".alfred-hero, [hidden], .modal")
        && h.offsetParent !== null && /^[A-Za-z]/.test(h.textContent.trim())).slice(0, 14);
    if (headings.length < 4) return;
    const used = new Set();
    const nav = document.createElement("nav");
    nav.className = "page-index page-index-auto"; nav.setAttribute("aria-label", "On this page");
    headings.forEach(h => {
        if (!h.id) {
            let id = "section-" + h.textContent.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
            while (document.getElementById(id) || used.has(id)) id += "-2";
            h.id = id;
        }
        used.add(h.id);
        const link = document.createElement("a");
        const label = h.textContent.trim().replace(/\s+/g, " ").replace(/[.!]$/, "");
        link.href = "#" + h.id; link.textContent = label.length > 34 ? label.slice(0, 34).replace(/\s+\S*$/, "") + "…" : label;
        nav.append(link);
    });
    const hero = main.querySelector(".alfred-hero");
    (hero?.querySelector("h1")?.parentElement || main).append(nav);
});
