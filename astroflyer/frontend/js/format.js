// Display formatting and small DOM helpers shared by every region.

const formatters = new Map();

export function num(value, digits = 0) {
    if (value == null || !Number.isFinite(value)) return '–';
    if (!formatters.has(digits)) {
        formatters.set(digits, new Intl.NumberFormat('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits }));
    }
    return formatters.get(digits).format(value);
}

export function sci(value, digits = 2) {
    if (value == null || !Number.isFinite(value)) return '–';
    return value.toExponential(digits);
}

// Elapsed time as "T+ 1 d 05:14:07".
export function elapsed(seconds) {
    const s = Math.max(0, Math.floor(seconds));
    const days = Math.floor(s / 86400);
    const hms = [Math.floor(s / 3600) % 24, Math.floor(s / 60) % 60, s % 60]
        .map((n) => String(n).padStart(2, '0'))
        .join(':');
    return days ? `T+ ${days} d ${hms}` : `T+ ${hms}`;
}

export function icon(name, label) {
    const a11y = label ? `role="img" aria-label="${label}"` : 'aria-hidden="true"';
    return `<svg class="icon" ${a11y}><use href="icons/icons.svg#${name}"></use></svg>`;
}

// Hands a text file to the browser's (or desktop window's) save dialog.
export function saveFile(name, text, type = 'text/plain') {
    const url = URL.createObjectURL(new Blob([text], { type }));
    const link = document.createElement('a');
    link.href = url;
    link.download = name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function escapeHtml(text) {
    return String(text).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}
