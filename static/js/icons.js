// Font Awesome icon in front of each text button, chosen from its first words, so every page shares one look (owner, 2026-11-19).
// The icon is decorative (aria-hidden) and adds no text, so labels, screen readers and tests read the same words.
(() => {
    const RULES = [
        [/^(sign out|log out)/, "right-from-bracket"], [/^sign in/, "right-to-bracket"],
        [/^(save|keep)/, "floppy-disk"], [/^(delete|remove|forget|clear|turn off)/, "trash-can"],
        [/^download/, "download"], [/^(upload|attach)/, "upload"], [/^(load|open|show) (the )?map/, "map"], [/^(open|load)/, "folder-open"],
        [/^cancel/, "xmark"], [/^pause/, "pause"], [/^(resume|run|start|play)/, "play"], [/^stop/, "stop"],
        [/^(refresh|retry|reload|try again|check again)/, "rotate"], [/^(sync|reconcile)/, "arrows-rotate"],
        [/^(add|new|create)/, "plus"], [/^(edit|correct|rename|change)/, "pen"],
        [/^export/, "file-export"], [/^import/, "file-import"], [/^(search|find|look up)/, "magnifying-glass"],
        [/^(send|email|apply)/, "paper-plane"], [/^connect/, "link"], [/^(approve|accept|confirm|mark)/, "check"],
        [/^(reject|decline|dismiss)/, "ban"], [/^(ask|chat)/, "comment-dots"], [/^(plan|route|directions)/, "route"],
        [/^(map|show map)/, "map"], [/^copy/, "copy"], [/^print/, "print"], [/^share/, "share-nodes"],
        [/^filter/, "filter"], [/^(reset|undo|restore)/, "arrow-rotate-left"], [/^back/, "arrow-left"],
        [/^(next|continue)/, "arrow-right"], [/^(view|show|preview)/, "eye"], [/^hide/, "eye-slash"],
        [/^(check|test|verify|validate)/, "circle-check"], [/^(generate|prepare|build|draft)/, "wand-magic-sparkles"],
        [/^(analy[sz]e|compare|research)/, "chart-line"], [/^(choose|select|pick)/, "hand-pointer"], [/^(read)/, "book-open"],
        [/^dark$/, "moon"], [/^light$/, "sun"],
    ];
    const SKIP = ".btn-close, .provider-button, .navbar-toggler, [data-no-icon], .dropdown-toggle-split";
    function iconFor(button) {
        const label = (button.textContent || "").trim().toLowerCase();
        if (!label) return null;
        const rule = RULES.find(([pattern]) => pattern.test(label));
        return rule ? rule[1] : null;
    }
    function decorate(button) {
        if (!button.matches(".btn") || button.matches(SKIP) || button.querySelector("i, svg, img, .spinner-border, .spinner-grow")) return;
        const name = iconFor(button);
        if (!name) return;
        const icon = document.createElement("i");
        icon.className = `fa-solid fa-${name} alfred-btn-icon`;
        icon.setAttribute("aria-hidden", "true");
        button.prepend(icon);
    }
    function scan(root) {
        if (root.nodeType !== 1) return;
        if (root.matches?.(".btn")) decorate(root);
        root.querySelectorAll?.(".btn").forEach(decorate);
    }
    scan(document.body);
    // Pages draw buttons later and rewrite their labels; decorate those too (the icon check stops repeats).
    new MutationObserver(records => {
        for (const record of records) {
            if (record.type === "characterData") { const button = record.target.parentElement?.closest(".btn"); if (button) decorate(button); continue; }
            record.addedNodes.forEach(node => { if (node.nodeType === 1) scan(node); else if (node.parentElement?.matches(".btn")) decorate(node.parentElement); });
        }
    }).observe(document.body, {childList: true, subtree: true, characterData: true});
})();
