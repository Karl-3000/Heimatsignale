/**
 * Geometrie des Herkunftsnetzes: Ringradien, Knotengrößen, Kantenformen.
 * Das Netz liegt in einem festen Koordinatensystem mit dem Wohnort im Ursprung;
 * eine Einheit entspricht bei Zoomfaktor 1 einem CSS-Pixel.
 */

import type { Level } from './types';

/** Ringradien: Bundesländer, Landkreise, Orte. */
export const RING_RADIUS: Record<Level, number> = {
	root: 0,
	state: 150,
	district: 310,
	place: 480
};

/** Halbe Kantenlänge der festen Zeichenfläche. Sie ändert sich nie, damit nichts springt. */
export const HALF_EXTENT = 720;

export const ROOT_RADIUS = 24;
export const NODE_RADIUS_MAX = 28;
export const NODE_RADIUS_MIN = 3;
/** Kleinster Radius der unsichtbaren Klickfläche (ergibt 28 px Durchmesser). */
export const HIT_RADIUS_MIN = 14;
export const HIT_PADDING = 4;
/** Mindestabstand zwischen zwei Klickflächen. */
export const NODE_GAP = 4;

export const EDGE_WIDTH_MIN = 1;
export const EDGE_WIDTH_MAX = 10;

/**
 * Radius eines Knotens. Die FLÄCHE ist proportional zur Anzahl, nicht der Radius:
 * r = rMax * sqrt(count / maxCount). Nur ganz unten greift ein Mindestradius,
 * damit ein Einzelner neben einer Gruppe von 80 sichtbar bleibt.
 */
export function nodeRadius(count: number, maxCount: number, rMax: number = NODE_RADIUS_MAX): number {
	if (!(count > 0) || !(maxCount > 0)) return NODE_RADIUS_MIN;
	const r = rMax * Math.sqrt(Math.min(count, maxCount) / maxCount);
	return Math.max(NODE_RADIUS_MIN, r);
}

/** Radius der Klickfläche: nie kleiner als HIT_RADIUS_MIN. */
export function hitRadius(r: number): number {
	return Math.max(r + HIT_PADDING, HIT_RADIUS_MIN);
}

/** Linienstärke einer Kante, linear zur Anzahl. */
export function edgeWidth(count: number, maxCount: number): number {
	if (!(count > 0) || !(maxCount > 0)) return EDGE_WIDTH_MIN;
	const t = Math.min(count, maxCount) / maxCount;
	return EDGE_WIDTH_MIN + (EDGE_WIDTH_MAX - EDGE_WIDTH_MIN) * t;
}

export interface Point {
	x: number;
	y: number;
}

export function polar(radius: number, angle: number): Point {
	return { x: radius * Math.cos(angle), y: radius * Math.sin(angle) };
}

export function angleOf(p: Point): number {
	return Math.atan2(p.y, p.x);
}

export function distance(a: Point, b: Point): number {
	return Math.hypot(a.x - b.x, a.y - b.y);
}

function fmt(n: number): string {
	return (Math.round(n * 10) / 10).toString();
}

/**
 * Gekrümmte Kante vom Elternknoten zum Kind.
 * Von der Mitte aus: leichte Bogenlinie (quadratische Kurve mit seitlich versetztem
 * Kontrollpunkt). Zwischen den Ringen: radiale S-Kurve, deren Kontrollpunkte auf dem
 * mittleren Radius liegen, sodass Kanten gebündelt aus dem Elternknoten wachsen.
 */
export function edgePath(parent: Point, child: Point): string {
	const pr = Math.hypot(parent.x, parent.y);
	const cr = Math.hypot(child.x, child.y);
	if (pr < 1) {
		const mx = (parent.x + child.x) / 2;
		const my = (parent.y + child.y) / 2;
		const dx = child.x - parent.x;
		const dy = child.y - parent.y;
		const bend = 0.12;
		const qx = mx - dy * bend;
		const qy = my + dx * bend;
		return `M${fmt(parent.x)},${fmt(parent.y)}Q${fmt(qx)},${fmt(qy)} ${fmt(child.x)},${fmt(child.y)}`;
	}
	const mid = (pr + cr) / 2;
	const pa = Math.atan2(parent.y, parent.x);
	const ca = Math.atan2(child.y, child.x);
	const c1 = polar(mid, pa);
	const c2 = polar(mid, ca);
	return (
		`M${fmt(parent.x)},${fmt(parent.y)}` +
		`C${fmt(c1.x)},${fmt(c1.y)} ${fmt(c2.x)},${fmt(c2.y)} ${fmt(child.x)},${fmt(child.y)}`
	);
}
