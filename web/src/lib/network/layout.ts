/**
 * Radiales, kräftebasiertes Layout des Herkunftsnetzes mit Stabilitätsregel.
 *
 * Die Regel aus dem Projektplan (Abschnitt 5):
 *  1. Nach jeder Änderung läuft die Simulation SYNCHRON bis zur Ruhe
 *     (alpha < alphaMin). Es gibt kein animiertes Nachschwingen.
 *  2. Danach ist das Ergebnis eingefroren: Die Positionen liegen in einer Map
 *     und werden erst bei der nächsten Nutzeraktion wieder angefasst.
 *  3. Beim Aufklappen behalten bestehende Knoten ihre Position. Sie nehmen an der
 *     Simulation nur als feste Hindernisse teil (fx/fy gesetzt). Bewegt werden
 *     ausschließlich die neu hinzugekommenen Knoten. Klickziele wandern nicht.
 *
 * Das Modul kennt weder Svelte noch das DOM.
 */

import {
	forceCollide,
	forceRadial,
	forceSimulation,
	forceX,
	forceY,
	type SimulationNodeDatum
} from 'd3-force';
import { HALF_EXTENT, NODE_GAP, RING_RADIUS, hitRadius, polar } from './geometry';

export interface LayoutNodeInput {
	id: string;
	/** null für Knoten des ersten Rings (Elternknoten ist der Wohnort in der Mitte). */
	parentId: string | null;
	/** 1 = Bundesland, 2 = Landkreis, 3 = Ort. */
	depth: number;
	/** Sichtbarer Radius des Knotens. */
	r: number;
}

export interface LayoutPosition {
	id: string;
	x: number;
	y: number;
	r: number;
	depth: number;
	parentId: string | null;
}

export interface LayoutResult {
	positions: Map<string, LayoutPosition>;
	/** In diesem Durchlauf neu platzierte Knoten. */
	added: string[];
	/** Entfernte Knoten. */
	removed: string[];
	/** Anzahl der Simulationsschritte bis zur Ruhe (0, wenn nichts zu platzieren war). */
	ticks: number;
}

interface SimNode extends SimulationNodeDatum {
	id: string;
	depth: number;
	collide: number;
	tx: number;
	ty: number;
	/** Zielradius: Ring der Stufe plus Versatz der Reihe. */
	tr: number;
	isNew: boolean;
}

const RING_BY_DEPTH = [RING_RADIUS.root, RING_RADIUS.state, RING_RADIUS.district, RING_RADIUS.place];
const ALPHA_MIN = 0.001;
/** Die Simulation kühlt in rund 120 Schritten ab; danach ist sie in Ruhe. */
const SETTLE_TICKS = 120;
const ALPHA_DECAY = 1 - Math.pow(ALPHA_MIN, 1 / SETTLE_TICKS);
const MAX_TICKS = 400;
const MAX_ROWS = 5;
/** Feste Knoten weiter weg als dieser Abstand vom Ziel eines neuen Knotens rechnen zunächst nicht mit. */
const CULL_DISTANCE = 170;
const START_ANGLE = -Math.PI / 2;

export function ringRadius(depth: number): number {
	return RING_BY_DEPTH[Math.max(0, Math.min(depth, RING_BY_DEPTH.length - 1))];
}

/**
 * Verteilt Winkel für eine Geschwistergruppe auf einem Ring.
 * Jeder Knoten bekommt so viel Bogen, wie seine Klickfläche braucht; übriger Platz
 * innerhalb von `spread` wird gleichmäßig verteilt. Die Gruppe ist um `center` zentriert.
 */
export function allocateAngles(
	collideRadii: number[],
	ring: number,
	center: number,
	spread: number
): number[] {
	const n = collideRadii.length;
	if (n === 0) return [];
	const needs = collideRadii.map((c) => (2 * c) / ring);
	const total = needs.reduce((a, b) => a + b, 0);
	const full = spread >= Math.PI * 2 - 1e-9;
	// Bei vollem Kreis teilen sich n Knoten n Lücken, sonst n - 1.
	const gaps = full ? n : n - 1;
	const slack = gaps > 0 && spread > total ? (spread - total) / gaps : 0;
	const width = total + slack * (n - 1);
	const angles: number[] = [];
	// Voller Kreis: Der erste Knoten sitzt genau auf `center`, die weiteren im Uhrzeigersinn.
	let angle = full ? center : center - width / 2 + needs[0] / 2;
	angles.push(angle);
	for (let i = 1; i < n; i++) {
		angle += needs[i - 1] / 2 + slack + needs[i] / 2;
		angles.push(angle);
	}
	return angles;
}

export class NetworkLayout {
	private positions = new Map<string, LayoutPosition>();

	/** Verwirft alle Positionen. Nur bei ausdrücklicher Neuordnung (Sortierung, neues Netz). */
	reset(): void {
		this.positions.clear();
	}

	get size(): number {
		return this.positions.size;
	}

	get(id: string): LayoutPosition | undefined {
		return this.positions.get(id);
	}

	snapshot(): Map<string, LayoutPosition> {
		return new Map(this.positions);
	}

	/**
	 * Winkelbereich, der einem Elternknoten für seine Kinder zusteht: die Hälfte des
	 * Abstands zu seinen beiden Nachbarn auf demselben Ring.
	 */
	private sectorOf(
		parentId: string,
		parentPos: { x: number; y: number },
		pending: ReadonlyMap<string, { x: number; y: number }>
	): number {
		const own = this.positions.get(parentId);
		const depth = own?.depth;
		const angle = Math.atan2(parentPos.y, parentPos.x);
		let before = Math.PI * 2;
		let after = Math.PI * 2;
		const consider = (id: string, p: { x: number; y: number }) => {
			if (id === parentId) return;
			let delta = Math.atan2(p.y, p.x) - angle;
			while (delta <= -Math.PI) delta += Math.PI * 2;
			while (delta > Math.PI) delta -= Math.PI * 2;
			if (delta >= 0) after = Math.min(after, delta);
			else before = Math.min(before, -delta);
		};
		for (const pos of this.positions.values()) {
			if (depth !== undefined && pos.depth !== depth) continue;
			consider(pos.id, pos);
		}
		if (depth === undefined) {
			for (const [id, p] of pending) consider(id, p);
		}
		if (before > Math.PI && after > Math.PI) return Math.PI * 1.5;
		return Math.min(before, Math.PI) / 2 + Math.min(after, Math.PI) / 2;
	}

	/**
	 * Gleicht das Layout mit der Liste der sichtbaren Knoten ab (ohne den Wohnort,
	 * in Baumreihenfolge, Geschwister in Sortierreihenfolge).
	 */
	sync(nodes: LayoutNodeInput[]): LayoutResult {
		const wanted = new Map(nodes.map((n) => [n.id, n]));

		const removed: string[] = [];
		for (const id of [...this.positions.keys()]) {
			if (!wanted.has(id)) {
				this.positions.delete(id);
				removed.push(id);
			}
		}

		// Bestehende Knoten: Position bleibt, nur der Radius darf sich mit den Daten ändern.
		for (const [id, pos] of this.positions) {
			const input = wanted.get(id);
			if (input) pos.r = input.r;
		}

		const fresh = nodes.filter((n) => !this.positions.has(n.id));
		if (fresh.length === 0) {
			return { positions: this.snapshot(), added: [], removed, ticks: 0 };
		}

		// Startpositionen: Geschwister fächern sich um den Winkel des Elternknotens auf.
		const groups = new Map<string, LayoutNodeInput[]>();
		for (const n of fresh) {
			const key = `${n.depth}|${n.parentId ?? ''}`;
			const g = groups.get(key);
			if (g) g.push(n);
			else groups.set(key, [n]);
		}

		const targets = new Map<string, { x: number; y: number; tr: number }>();
		// Flachere Ebenen zuerst, damit Kinder den Winkel frisch platzierter Eltern kennen.
		const ordered = [...groups.values()].sort((a, b) => a[0].depth - b[0].depth);
		for (const group of ordered) {
			const depth = group[0].depth;
			const ring = ringRadius(depth);
			const parentId = group[0].parentId;
			const parentPos = parentId ? (this.positions.get(parentId) ?? targets.get(parentId)) : null;
			const collide = group.map((n) => hitRadius(n.r) + NODE_GAP / 2);
			const need = collide.reduce((a, c) => a + (2 * c) / ring, 0);
			let center = START_ANGLE;
			let spread = Math.PI * 2;
			let sector = Math.PI * 2;
			if (parentId && parentPos && Math.hypot(parentPos.x, parentPos.y) > 1) {
				center = Math.atan2(parentPos.y, parentPos.x);
				sector = this.sectorOf(parentId, parentPos, targets);
				// Etwas Luft zwischen den Kindern, aber nie mehr als der Sektor des Elternknotens.
				spread = Math.min(need * 1.25, sector, Math.PI * 1.5);
			}
			// Reicht der Bogen nicht, werden die Geschwister in versetzten Reihen nach außen gestaffelt.
			const rows = Math.max(1, Math.min(MAX_ROWS, Math.ceil(need / Math.max(sector * 0.95, 1e-6))));
			const pitch = 2 * Math.max(...collide);
			const angles = allocateAngles(
				collide.map((c) => c / rows),
				ring,
				center,
				spread
			);
			group.forEach((n, i) => {
				const tr = ring + (i % rows) * pitch;
				const p = polar(tr, angles[i]);
				targets.set(n.id, { x: p.x, y: p.y, tr });
			});
		}

		// Erst nur mit den festen Knoten in der Nähe rechnen (schnell). Bleibt danach doch
		// eine Überlappung mit einem weiter entfernten Knoten, wird mit allen wiederholt.
		let run = this.simulate(fresh, targets, CULL_DISTANCE);
		if (run.culled && this.collidesWithFixed(run.nodes)) {
			run = this.simulate(fresh, targets, Number.POSITIVE_INFINITY);
		}
		const simNodes = run.nodes;
		const ticks = run.ticks;

		const limit = HALF_EXTENT - 8;
		const added: string[] = [];
		for (const s of simNodes) {
			if (!s.isNew) continue;
			const input = wanted.get(s.id)!;
			const x = clamp(s.x ?? s.tx, -limit, limit);
			const y = clamp(s.y ?? s.ty, -limit, limit);
			this.positions.set(s.id, {
				id: s.id,
				x: round2(x),
				y: round2(y),
				r: input.r,
				depth: input.depth,
				parentId: input.parentId
			});
			added.push(s.id);
		}

		return { positions: this.snapshot(), added, removed, ticks };
	}

	private simulate(
		fresh: readonly LayoutNodeInput[],
		targets: ReadonlyMap<string, { x: number; y: number; tr: number }>,
		cullDistance: number
	): { nodes: SimNode[]; ticks: number; culled: boolean } {
		const simNodes: SimNode[] = [];
		let culled = false;
		const freshTargets = fresh.map((n) => targets.get(n.id)!);
		for (const pos of this.positions.values()) {
			if (Number.isFinite(cullDistance)) {
				let near = false;
				for (const t of freshTargets) {
					if (Math.abs(t.x - pos.x) < cullDistance && Math.abs(t.y - pos.y) < cullDistance) {
						near = true;
						break;
					}
				}
				if (!near) {
					culled = true;
					continue;
				}
			}
			simNodes.push({
				id: pos.id,
				depth: pos.depth,
				collide: hitRadius(pos.r) + NODE_GAP / 2,
				x: pos.x,
				y: pos.y,
				fx: pos.x,
				fy: pos.y,
				tx: pos.x,
				ty: pos.y,
				tr: Math.hypot(pos.x, pos.y),
				isNew: false
			});
		}
		for (const n of fresh) {
			const t = targets.get(n.id)!;
			simNodes.push({
				id: n.id,
				depth: n.depth,
				collide: hitRadius(n.r) + NODE_GAP / 2,
				x: t.x,
				y: t.y,
				tx: t.x,
				ty: t.y,
				tr: t.tr,
				isNew: true
			});
		}

		const simulation = forceSimulation<SimNode>(simNodes)
			.alphaMin(ALPHA_MIN)
			.alphaDecay(ALPHA_DECAY)
			.velocityDecay(0.45)
			.force(
				'collide',
				forceCollide<SimNode>((d) => d.collide)
					.strength(1)
					.iterations(3)
			)
			.force(
				'radial',
				forceRadial<SimNode>((d) => d.tr, 0, 0).strength((d) => (d.isNew ? 0.5 : 0))
			)
			.force('x', forceX<SimNode>((d) => d.tx).strength((d) => (d.isNew ? 0.08 : 0)))
			.force('y', forceY<SimNode>((d) => d.ty).strength((d) => (d.isNew ? 0.08 : 0)))
			.stop();

		// Synchron bis zur Ruhe rechnen. Kein Timer, kein requestAnimationFrame.
		let ticks = 0;
		while (simulation.alpha() >= ALPHA_MIN && ticks < MAX_TICKS) {
			simulation.tick();
			ticks++;
		}

		// Restüberlappungen (sehr dichte Ringe) mit reiner Kollisionsauflösung beseitigen.
		simulation.force('radial', null).force('x', null).force('y', null);
		let guard = 0;
		while (guard < 300 && hasOverlap(simNodes)) {
			simulation.alpha(0.05);
			for (let i = 0; i < 4; i++) simulation.tick();
			guard++;
			ticks += 4;
		}
		simulation.stop();
		return { nodes: simNodes, ticks, culled };
	}

	/** Prüft neue Knoten gegen ALLE festen Knoten, auch die bei der Simulation ausgelassenen. */
	private collidesWithFixed(nodes: readonly SimNode[]): boolean {
		for (const s of nodes) {
			if (!s.isNew) continue;
			for (const pos of this.positions.values()) {
				const min = s.collide + hitRadius(pos.r) - NODE_GAP / 2;
				const dx = (s.x ?? 0) - pos.x;
				const dy = (s.y ?? 0) - pos.y;
				if (dx * dx + dy * dy < min * min - 0.01) return true;
			}
		}
		return false;
	}
}

function hasOverlap(nodes: SimNode[]): boolean {
	// Nur Paare mit mindestens einem neuen Knoten zählen; feste Knoten bleiben, wo sie sind.
	for (let i = 0; i < nodes.length; i++) {
		const a = nodes[i];
		if (!a.isNew) continue;
		for (let j = 0; j < nodes.length; j++) {
			if (j === i) continue;
			const b = nodes[j];
			if (b.isNew && j < i) continue;
			const min = a.collide + b.collide - NODE_GAP;
			const dx = (a.x ?? 0) - (b.x ?? 0);
			const dy = (a.y ?? 0) - (b.y ?? 0);
			if (dx * dx + dy * dy < min * min - 0.01) return true;
		}
	}
	return false;
}

function clamp(v: number, lo: number, hi: number): number {
	return Math.max(lo, Math.min(hi, v));
}

function round2(v: number): number {
	return Math.round(v * 100) / 100;
}

/** Prüft, ob sich zwei Klickflächen überlappen. Für Tests und Entwicklungsansicht. */
export function countOverlaps(positions: Iterable<LayoutPosition>, rootRadius: number): number {
	const list = [...positions];
	let overlaps = 0;
	for (let i = 0; i < list.length; i++) {
		const a = list[i];
		if (Math.hypot(a.x, a.y) < hitRadius(a.r) + rootRadius) overlaps++;
		for (let j = i + 1; j < list.length; j++) {
			const b = list[j];
			const min = hitRadius(a.r) + hitRadius(b.r);
			if (Math.hypot(a.x - b.x, a.y - b.y) < min - 0.5) overlaps++;
		}
	}
	return overlaps;
}
