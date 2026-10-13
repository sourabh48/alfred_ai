document.addEventListener("DOMContentLoaded", () => {
    const theme = document.getElementById("workspaceTheme");
    function setTheme(dark) {
        document.documentElement.dataset.theme = dark ? "dark" : "light";
        theme.textContent = dark ? "Light" : "Dark";
        theme.setAttribute("aria-pressed", String(dark));
        theme.setAttribute("aria-label", dark ? "Use light appearance" : "Use dark appearance");
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
        document.querySelectorAll("#sidebarMenu .nav-link").forEach(link => {
            if (location.pathname === "/settings/" && link.getAttribute("href").startsWith("/settings/")) link.classList.toggle("active", memory ? link.hash === "#privateMemoryPanel" : !link.hash);
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
});
