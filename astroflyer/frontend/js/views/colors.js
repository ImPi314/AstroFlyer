// Reads theme colors from tokens.css so canvas and WebGL views use the same palette as the page.

const cache = new Map();

export function token(name) {
    if (!cache.has(name)) {
        cache.set(name, getComputedStyle(document.documentElement).getPropertyValue(name).trim());
    }
    return cache.get(name);
}

// "#RRGGBB" to [r, g, b] in 0..1.
export function rgb(name) {
    const hex = token(name).replace('#', '');
    return [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
}

// Track color for an altitude: bright near perigee, dim near apogee.
export function altitudeColor(altitude, min, max) {
    const low = rgb('--track-low');
    const high = rgb('--track-high');
    const f = max > min ? Math.min(Math.max((altitude - min) / (max - min), 0), 1) : 0;
    return low.map((c, k) => c + Math.sqrt(f) * (high[k] - c));
}

export function css([r, g, b], alpha = 1) {
    return `rgb(${Math.round(r * 255)} ${Math.round(g * 255)} ${Math.round(b * 255)} / ${alpha})`;
}
