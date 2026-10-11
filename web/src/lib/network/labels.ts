/**
 * Beschriftung des Herkunftsnetzes: Kurzformen und überlappungsfreie Platzierung.
 *
 * Regel: Beschriftungen sind immer lesbar und überlappen nie. Reicht der Platz nicht
 * für den vollen Namen, wird die Kurzform versucht ("NRW", "Garmisch-P."). Reicht auch
 * das nicht, wird die Beschriftung ausgeblendet; der volle Name bleibt per Tipp,
 * Tastaturfokus und in der Listenansicht erreichbar.
 */

import { stateShort } from './states';
import type { Level } from './types';

export const LABEL_FONT_SIZE = 12.5;
export const LABEL_SUB_FONT_SIZE = 11;
export const LABEL_LINE_HEIGHT = 15;
const LABEL_GAP = 5;

const NARROW = new Set([...'iljI.,:;|!\'’ '].map((c) => c));
const SEMI = new Set([...'ftr-()/1'].map((c) => c));
const WIDE = new Set([...'mwMW@'].map((c) => c));

/**
 * Schätzt die Breite eines Textes in Inter ohne DOM-Messung. Bewusst leicht
 * großzügig, damit echte Texte nie breiter ausfallen als ihr reservierter Kasten.
 */
export function estimateTextWidth(text: string, fontSize: number = LABEL_FONT_SIZE): number {
	let em = 0;
	for (const ch of text) {
		if (NARROW.has(ch)) em += 0.3;
		else if (SEMI.has(ch)) em += 0.4;
		else if (WIDE.has(ch)) em += 0.9;
		else if (ch >= '0' && ch <= '9') em += 0.64;
		else if (ch === '…') em += 0.8;
		else if (ch !== ch.toLowerCase()) em += 0.7;
		else em += 0.58;
	}
	return em * fontSize * 1.04;
}

const LEADING = /^(Landkreis|Kreis|Städteregion|Regionalverband|Region)\s+/;
const TRAILING = /,\s*(Stadt|Landeshauptstadt|Hansestadt|Universitätsstadt|Kreisfreie Stadt|Markt|St\.)$/i;

/**
 * Kürzt einen Orts- oder Kreisnamen auf etwa `max` Zeichen.
 * "Garmisch-Partenkirchen" wird zu "Garmisch-P.", "Hohenstein-Ernstthal" zu "Hohenstein-E.".
 */
export function shortenName(name: string, max: number = 12): string {
	let s = name.trim().replace(/\s*\([^)]*\)\s*/g, ' ').trim();
	s = s.replace(TRAILING, '').replace(LEADING, '').trim();
	s = s.replace(/^Sankt\s+/, 'St. ');
	if (s.length <= max) return s;

	// Doppelnamen: den Teil nach dem letzten Bindestrich auf den Anfangsbuchstaben kürzen.
	const hyphen = s.lastIndexOf('-');
	if (hyphen > 2 && hyphen < s.length - 2) {
		const candidate = `${s.slice(0, hyphen + 1)}${s.charAt(hyphen + 1)}.`;
		if (candidate.length <= max + 2) return candidate;
		s = candidate;
	}

	// Mehrere Wörter: hintere Wörter weglassen, solange vorn genug übrig bleibt.
	const words = s.split(' ');
	if (words.length > 1) {
		let out = words[0];
		for (let i = 1; i < words.length; i++) {
			if ((out + ' ' + words[i]).length > max) break;
			out += ' ' + words[i];
		}
		if (out.length >= 5 && out.length <= max && out.length < s.length) return `${out}…`;
	}

	return `${s.slice(0, Math.max(3, max - 1)).replace(/[-\s.]+$/, '')}…`;
}

/** Kurzform eines Knotens: amtliches Kürzel beim Bundesland, sonst gekürzter Name. */
export function shortLabel(level: Level, key: string, name: string): string {
	if (level === 'state') return stateShort(key);
	return shortenName(name);
}

export interface LabelInput {
	id: string;
	x: number;
	y: number;
	/** Sichtbarer Radius des Knotens. */
	r: number;
	full: string;
	short: string;
	/** Angehängte Zahl, wenn sie nicht im Knoten selbst steht. */
	suffix?: string;
	/** Zweite Zeile, z. B. "deine Herkunft". */
	sub?: string;
	/** Höhere Werte werden zuerst platziert. */
	priority: number;
}

export interface Box {
	x0: number;
	y0: number;
	x1: number;
	y1: number;
}

export type LabelVariant = 'full' | 'short' | 'hidden';
export type LabelAnchor = 'start' | 'middle' | 'end';

export interface LabelPlacement {
	id: string;
	variant: LabelVariant;
	text: string;
	suffix: string;
	sub: string;
	/** Ankerpunkt der ersten Textzeile (Grundlinie mittig, dominant-baseline: central). */
	x: number;
	y: number;
	anchor: LabelAnchor;
	box: Box | null;
	/** Schriftgrößen und Zeilenhöhe in Netzeinheiten (auf dem Bildschirm konstant). */
	fontSize: number;
	subFontSize: number;
	lineHeight: number;
}

export interface PlaceLabelsOptions {
	/** Zusätzliche Hindernisse, z. B. der Wohnort in der Mitte samt seiner Beschriftung. */
	obstacles?: Box[];
	halfExtent?: number;
	/**
	 * Sichtbarer Ausschnitt in Netzkoordinaten. Beschriftungen, die darüber hinausragen würden,
	 * wechseln die Seite, werden gekürzt oder ausgeblendet, statt abgeschnitten zu werden.
	 */
	bounds?: Box;
	/**
	 * Bildschirm-Pixel je Netzeinheit. Die Schrift bleibt auf dem Bildschirm gleich groß;
	 * in Netzeinheiten braucht sie beim Herauszoomen deshalb mehr Platz.
	 */
	scale?: number;
}

function intersects(a: Box, b: Box): boolean {
	return a.x0 < b.x1 && a.x1 > b.x0 && a.y0 < b.y1 && a.y1 > b.y0;
}

function circleHitsBox(cx: number, cy: number, r: number, b: Box): boolean {
	const nx = Math.max(b.x0, Math.min(cx, b.x1));
	const ny = Math.max(b.y0, Math.min(cy, b.y1));
	const dx = cx - nx;
	const dy = cy - ny;
	return dx * dx + dy * dy < r * r;
}

interface Candidate {
	x: number;
	y: number;
	anchor: LabelAnchor;
	box: Box;
}

function candidates(n: LabelInput, width: number, lines: number, k: number): Candidate[] {
	const LABEL_PADDING = 2 * k;
	const h = lines * LABEL_LINE_HEIGHT * k;
	const off = n.r + LABEL_GAP * k;
	const half = (LABEL_LINE_HEIGHT * k) / 2;
	const right: Candidate = {
		x: n.x + off,
		y: n.y,
		anchor: 'start',
		box: { x0: n.x + off - LABEL_PADDING, y0: n.y - half, x1: n.x + off + width + LABEL_PADDING, y1: n.y - half + h }
	};
	const left: Candidate = {
		x: n.x - off,
		y: n.y,
		anchor: 'end',
		box: { x0: n.x - off - width - LABEL_PADDING, y0: n.y - half, x1: n.x - off + LABEL_PADDING, y1: n.y - half + h }
	};
	const below: Candidate = {
		x: n.x,
		y: n.y + off + half,
		anchor: 'middle',
		box: { x0: n.x - width / 2 - LABEL_PADDING, y0: n.y + off, x1: n.x + width / 2 + LABEL_PADDING, y1: n.y + off + h }
	};
	const above: Candidate = {
		x: n.x,
		y: n.y - off - h + half,
		anchor: 'middle',
		box: { x0: n.x - width / 2 - LABEL_PADDING, y0: n.y - off - h, x1: n.x + width / 2 + LABEL_PADDING, y1: n.y - off }
	};
	// Bevorzugt nach außen, vom Wohnort weg; danach die übrigen Seiten.
	const horizontal = Math.abs(n.x) >= Math.abs(n.y) * 0.6;
	const outwardH = n.x >= 0 ? right : left;
	const inwardH = n.x >= 0 ? left : right;
	const outwardV = n.y >= 0 ? below : above;
	const inwardV = n.y >= 0 ? above : below;
	return horizontal
		? [outwardH, outwardV, inwardV, inwardH]
		: [outwardV, outwardH, inwardH, inwardV];
}

/**
 * Platziert Beschriftungen gierig nach Priorität. Jede Beschriftung probiert den vollen
 * Namen an vier Seiten, dann die Kurzform an vier Seiten, und wird sonst ausgeblendet.
 * Hindernisse sind alle Knotenkreise, bereits platzierte Beschriftungen und der Rand.
 */
export function placeLabels(
	inputs: LabelInput[],
	options: PlaceLabelsOptions = {}
): Map<string, LabelPlacement> {
	const half = options.halfExtent ?? Number.POSITIVE_INFINITY;
	const bounds = options.bounds ?? null;
	// k: Netzeinheiten je Bildschirm-Pixel.
	const k = options.scale && options.scale > 0 ? 1 / options.scale : 1;
	const sizes = { fontSize: LABEL_FONT_SIZE * k, subFontSize: LABEL_SUB_FONT_SIZE * k, lineHeight: LABEL_LINE_HEIGHT * k };
	const placed: Box[] = [...(options.obstacles ?? [])];
	const result = new Map<string, LabelPlacement>();
	const order = [...inputs].sort((a, b) => b.priority - a.priority || a.id.localeCompare(b.id));

	for (const n of order) {
		const suffix = n.suffix ?? '';
		const sub = n.sub ?? '';
		const lines = sub ? 2 : 1;
		const subWidth = sub ? estimateTextWidth(sub, LABEL_SUB_FONT_SIZE) * k : 0;
		const variants: Array<{ variant: LabelVariant; text: string }> = [{ variant: 'full', text: n.full }];
		if (n.short && n.short !== n.full) variants.push({ variant: 'short', text: n.short });

		let chosen: LabelPlacement | null = null;
		for (const v of variants) {
			const main = estimateTextWidth(suffix ? `${v.text} ${suffix}` : v.text) * k;
			const width = Math.max(main, subWidth);
			for (const c of candidates(n, width, lines, k)) {
				const b = c.box;
				if (b.x0 < -half || b.x1 > half || b.y0 < -half || b.y1 > half) continue;
				if (bounds && (b.x0 < bounds.x0 || b.x1 > bounds.x1 || b.y0 < bounds.y0 || b.y1 > bounds.y1)) continue;
				let free = true;
				for (const p of placed) {
					if (intersects(b, p)) {
						free = false;
						break;
					}
				}
				if (!free) continue;
				for (const o of inputs) {
					if (o.id === n.id) continue;
					if (circleHitsBox(o.x, o.y, o.r + 1, b)) {
						free = false;
						break;
					}
				}
				if (!free) continue;
				chosen = { id: n.id, variant: v.variant, text: v.text, suffix, sub, x: c.x, y: c.y, anchor: c.anchor, box: b, ...sizes };
				break;
			}
			if (chosen) break;
		}

		if (chosen && chosen.box) {
			placed.push(chosen.box);
			result.set(n.id, chosen);
		} else {
			result.set(n.id, { id: n.id, variant: 'hidden', text: n.full, suffix, sub, x: n.x, y: n.y, anchor: 'middle', box: null, ...sizes });
		}
	}
	return result;
}

/** Zählt Überlappungen zwischen platzierten Beschriftungen. Für Tests. */
export function countLabelOverlaps(placements: Iterable<LabelPlacement>): number {
	const boxes = [...placements].filter((p) => p.box).map((p) => p.box as Box);
	let n = 0;
	for (let i = 0; i < boxes.length; i++) {
		for (let j = i + 1; j < boxes.length; j++) {
			if (intersects(boxes[i], boxes[j])) n++;
		}
	}
	return n;
}
