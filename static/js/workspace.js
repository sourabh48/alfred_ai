document.addEventListener("DOMContentLoaded", () => {
    const theme = document.getElementById("workspaceTheme");
    function setTheme(dark) {
        document.documentElement.dataset.theme = dark ? "dark" : "light";
        theme.textContent = dark ? "Light" : "Dark";
        theme.setAttribute("aria-pressed", String(dark));
        theme.setAttribute("aria-label", dark ? "Use light appearance" : "Use dark appearance");
        if (window.Chart) {
            Chart.defaults.color = dark ? "#c9dfff" : "#53647c";
            Chart.defaults.borderColor = dark ? "#37506e" : "#dce4ef";
            Object.values(Chart.instances).forEach(chart=>chart.update("none"));
        }
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
        const memory = location.pathname === "/settings/" && /^#(?:privateMemoryPanel|memoryReviewPanel|memory-[a-f0-9]{32})$/.test(location.hash);
        const banking = location.pathname === "/expenses/" && location.hash === "#bankAccountsPanel";
        document.querySelectorAll("#sidebarMenu .nav-link").forEach(link => {
            if (location.pathname === "/settings/" && link.getAttribute("href").startsWith("/settings/")) link.classList.toggle("active", memory ? link.hash === "#privateMemoryPanel" : !link.hash);
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
                    const balance = account.current_balance === null || account.current_balance === undefined ? 'Balance unavailable' : Alfred.formatCurrency(account.current_balance);
                    [account.nickname || account.bank_name || 'Bank account',reference,account.account_type,balance,account.is_active?'Active':'Inactive'].forEach(value=>{const cell=document.createElement('td');cell.textContent=value;row.append(cell)});
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
