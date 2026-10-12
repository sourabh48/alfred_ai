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
    document.querySelectorAll("#sidebarMenu .nav-link.active").forEach(link => link.setAttribute("aria-current", "page"));
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
