/* Bounded answer formatting: create only text nodes and fixed, inert elements. */
(() => {
    function inline(parent, text) {
        const tokens = /(!?\[[^\]\n]*\]\([^\n)]*\)|[a-z][a-z0-9+.-]*:\/\/[^\s<]+|<[^>\n]*>)|`([^`\n]+)`|\*\*([^*\n]+)\*\*|(?<![\p{L}\p{N}_])__([^_\n]+)__(?![\p{L}\p{N}_])|\*([^*\n]+)\*|(?<![\p{L}\p{N}_])_([^_\n]+)_(?![\p{L}\p{N}_])/giu;
        let offset = 0;
        for (const match of text.matchAll(tokens)) {
            parent.append(document.createTextNode(text.slice(offset,match.index)));
            const node = match[1] !== undefined ? document.createTextNode(match[1])
                : document.createElement(match[2] !== undefined ? 'code' : match[3] !== undefined || match[4] !== undefined ? 'strong' : 'em');
            if (match[1] === undefined) node.textContent = match.slice(2).find(value => value !== undefined);
            parent.append(node); offset = match.index+match[0].length;
        }
        parent.append(document.createTextNode(text.slice(offset)));
    }
    const fence = line => /^ {0,3}(`{3,}|~{3,})([a-zA-Z0-9_+-]{0,24})\s*$/.exec(line);
    const heading = line => /^ {0,3}(#{1,6})\s+(.+?)(?:\s+#+)?\s*$/.exec(line);
    const listItem = line => /^ {0,3}([-+*]|\d{1,9}[.)])\s+(.+)$/.exec(line);
    const quote = line => /^ {0,3}>\s?(.*)$/.exec(line);
    function cells(line) {
        return line.trim().replace(/^\|/,'').replace(/\|$/,'').split('|').map(cell => cell.trim());
    }
    function tableAt(lines, start) {
        if (!lines[start].includes('|') || !lines[start+1]?.includes('|')) return null;
        const header = cells(lines[start]), rule = cells(lines[start+1]);
        if (header.length < 2 || header.length > 12 || rule.length !== header.length || !rule.every(cell => /^:?-{3,}:?$/.test(cell))) return null;
        let end = start+2;
        while (end < lines.length && lines[end].trim() && lines[end].includes('|')) end++;
        const rows = lines.slice(start+2,end).map(cells);
        if (rows.length > 100 || rows.some(row => row.length !== header.length) || lines.slice(start,end).some(line => /\\\||`/.test(line))) return null;
        return {header,rows,end};
    }
    Alfred.renderAnswerMarkdown = text => {
        const root = document.createElement('div'); root.className = 'assistant-answer';
        const lines = text.replace(/\r\n?/g,'\n').split('\n');
        if (new TextEncoder().encode(text).length > 8192 || lines.length > 512) {
            const plain = document.createElement('p'); plain.textContent = text; root.append(plain); return root;
        }
        const startsBlock = index => fence(lines[index]) || heading(lines[index]) || listItem(lines[index]) || quote(lines[index]) || tableAt(lines,index);
        for (let index = 0; index < lines.length;) {
            const line = lines[index];
            if (!line.trim()) { index++; continue; }
            const code = fence(line), title = heading(line), item = listItem(line), quoted = quote(line), table = tableAt(lines,index);
            if (code) {
                const content = []; index++;
                while (index < lines.length) {
                    const closing = /^ {0,3}(`{3,}|~{3,})\s*$/.exec(lines[index]);
                    if (closing && closing[1][0] === code[1][0] && closing[1].length >= code[1].length) { index++; break; }
                    content.push(lines[index++]);
                }
                const figure = document.createElement('figure'), caption = document.createElement('figcaption');
                caption.textContent = code[2] ? `Code: ${code[2]}` : 'Code';
                const pre = document.createElement('pre'), literal = document.createElement('code');
                pre.tabIndex = 0; pre.setAttribute('role','region'); pre.setAttribute('aria-label','Code snippet');
                literal.textContent = content.join('\n'); pre.append(literal); figure.append(caption,pre); root.append(figure);
            } else if (title) {
                const node = document.createElement(`h${Math.min(6,title[1].length+2)}`);
                inline(node,title[2]); root.append(node); index++;
            } else if (table) {
                const region = document.createElement('div'); region.className = 'assistant-table';
                region.tabIndex = 0; region.setAttribute('role','region'); region.setAttribute('aria-label','Answer table');
                const node = document.createElement('table'), caption = document.createElement('caption');
                caption.className = 'visually-hidden'; caption.textContent = 'Answer table';
                const head = document.createElement('thead'), headRow = document.createElement('tr'), body = document.createElement('tbody');
                table.header.forEach(value => { const cell = document.createElement('th'); cell.scope = 'col'; inline(cell,value); headRow.append(cell); });
                head.append(headRow);
                table.rows.forEach(row => {
                    const tr = document.createElement('tr'); row.forEach(value => { const cell = document.createElement('td'); inline(cell,value); tr.append(cell); }); body.append(tr);
                });
                node.append(caption,head,body); region.append(node); root.append(region); index = table.end;
            } else if (item) {
                const ordered = /^\d/.test(item[1]), node = document.createElement(ordered ? 'ol' : 'ul');
                if (ordered) node.start = Number(item[1].slice(0,-1));
                while (index < lines.length) {
                    const next = listItem(lines[index]);
                    if (!next || /^\d/.test(next[1]) !== ordered) break;
                    const li = document.createElement('li'); inline(li,next[2]); node.append(li); index++;
                }
                root.append(node);
            } else if (quoted) {
                const node = document.createElement('blockquote'), content = [];
                while (index < lines.length && quote(lines[index])) content.push(quote(lines[index++])[1]);
                inline(node,content.join('\n')); root.append(node);
            } else {
                const content = [line]; index++;
                while (index < lines.length && lines[index].trim() && !startsBlock(index)) content.push(lines[index++]);
                const node = document.createElement('p'); inline(node,content.join('\n')); root.append(node);
            }
        }
        return root;
    };
})();
