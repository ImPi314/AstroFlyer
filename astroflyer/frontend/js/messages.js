// Message log under the timeline: run progress, warnings and errors in plain words.

import { escapeHtml, icon } from './format.js';

const MAX_ENTRIES = 200;
const entries = [];
let root;
let open = false;

export function mountMessages(element) {
    root = element;
    root.innerHTML = `
        <button class="messages-toggle" type="button" aria-expanded="false" aria-controls="messages-list">
            ${icon('chevron-right')}
            <span class="messages-latest" aria-live="polite"></span>
        </button>
        <ol class="messages-list" id="messages-list" hidden></ol>`;
    root.querySelector('.messages-toggle').addEventListener('click', () => {
        open = !open;
        root.classList.toggle('is-open', open);
        root.querySelector('.messages-toggle').setAttribute('aria-expanded', String(open));
        root.querySelector('.messages-list').hidden = !open;
        if (open) scrollToEnd();
    });
}

export function log(level, text) {
    entries.push({ level, text, at: new Date() });
    if (entries.length > MAX_ENTRIES) entries.shift();
    render();
}

function render() {
    const latest = entries.at(-1);
    const latestEl = root.querySelector('.messages-latest');
    latestEl.textContent = latest.text;
    latestEl.dataset.level = latest.level;
    root.querySelector('.messages-list').innerHTML = entries.map((entry) => `
        <li class="message" data-level="${entry.level}">
            <time>${entry.at.toLocaleTimeString('en-GB')}</time>
            ${entry.level === 'error' ? icon('triangle-alert', 'Error') : ''}
            <span>${escapeHtml(entry.text)}</span>
        </li>`).join('');
    if (open) scrollToEnd();
}

function scrollToEnd() {
    const list = root.querySelector('.messages-list');
    list.scrollTop = list.scrollHeight;
}
