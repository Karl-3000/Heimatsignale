/**
 * Miniatur des Stufe-1-Netzes auf der Karte (Projektplan, Abschnitt 5, "Auf der Karte").
 * Gezeigt werden die bis zu fünf größten Bundesländer und zusätzlich immer das eigene,
 * falls dort jemand von dort stammt. Der Rest erscheint als "+N".
 */

import type { StateGroup } from '../api/types';
import { stateShort } from '../network/states';

export const MINIATURE_TOP = 5;

export interface MiniatureState {
	stateCode: string;
	count: number;
	own: boolean;
}

export interface MiniatureSelection {
	shown: MiniatureState[];
	/** Anzahl der nicht einzeln gezeigten Bundesländer ("+N"). */
	restStates: number;
	/** Personen in den nicht gezeigten Bundesländern. */
	restCount: number;
	total: number;
}

/** Fasst die Bundesländer mehrerer Wohnorte zusammen (für Sammelknoten). */
export function mergeStates(lists: ReadonlyArray<readonly StateGroup[]>): StateGroup[] {
	const acc = new Map<string, StateGroup>();
	for (const list of lists) {
		for (const s of list) {
			const e = acc.get(s.state_code);
			if (e) e.count += s.count;
			else acc.set(s.state_code, { state_code: s.state_code, count: s.count, distance_km: s.distance_km });
		}
	}
	return [...acc.values()].sort((a, b) => b.count - a.count || a.state_code.localeCompare(b.state_code));
}

export function selectMiniatureStates(
	states: readonly StateGroup[],
	ownStateCode: string | null,
	top: number = MINIATURE_TOP
): MiniatureSelection {
	const sorted = [...states]
		.filter((s) => s.count > 0)
		.sort((a, b) => b.count - a.count || a.state_code.localeCompare(b.state_code));
	const shown = sorted.slice(0, top);
	const own = ownStateCode ? sorted.find((s) => s.state_code === ownStateCode) : undefined;
	// Die eigene Herkunft ist immer dabei, auch außerhalb der fünf größten Gruppen.
	if (own && !shown.includes(own)) shown.push(own);
	const rest = sorted.filter((s) => !shown.includes(s));
	return {
		shown: shown.map((s) => ({ stateCode: s.state_code, count: s.count, own: s.state_code === ownStateCode })),
		restStates: rest.length,
		restCount: rest.reduce((a, s) => a + s.count, 0),
		total: sorted.reduce((a, s) => a + s.count, 0)
	};
}

export interface MiniatureNode {
	stateCode: string;
	x: number;
	y: number;
	r: number;
	edgeWidth: number;
	own: boolean;
	label: string | null;
	labelX: number;
	labelY: number;
	count: number;
}

export interface MiniatureGeometry {
	radius: number;
	centerRadius: number;
	nodes: MiniatureNode[];
	rest: { x: number; y: number; text: string } | null;
}

/**
 * Geometrie der Miniatur in einem Kreis mit `radius`. Die Knotenfläche ist proportional
 * zur Anzahl, bezogen auf die größte gezeigte Gruppe. Kürzel erscheinen erst, wenn die
 * Miniatur groß genug ist, um sie lesbar zu setzen.
 */
export function miniatureGeometry(selection: MiniatureSelection, radius: number): MiniatureGeometry {
	const slots = selection.shown.length + (selection.restStates > 0 ? 1 : 0);
	const centerRadius = Math.max(9, radius * 0.2);
	const withLabels = radius >= 58;
	const labelRoom = withLabels ? 11 : 0;
	const rMax = Math.max(4, Math.min(radius * 0.17, 13));
	const max = selection.shown.reduce((m, s) => Math.max(m, s.count), 1);
	const orbit = radius - rMax - labelRoom - 1;
	const nodes: MiniatureNode[] = selection.shown.map((s, i) => {
		const angle = -Math.PI / 2 + (i / Math.max(slots, 1)) * Math.PI * 2;
		const r = Math.max(2.5, rMax * Math.sqrt(s.count / max));
		const x = orbit * Math.cos(angle);
		const y = orbit * Math.sin(angle);
		const labelDistance = orbit + r + 6.5;
		return {
			stateCode: s.stateCode,
			x,
			y,
			r,
			edgeWidth: 1 + 3.5 * (s.count / max),
			own: s.own,
			label: withLabels ? stateShort(s.stateCode) : null,
			labelX: Math.min(labelDistance, radius - 5) * Math.cos(angle),
			labelY: Math.min(labelDistance, radius - 5) * Math.sin(angle),
			count: s.count
		};
	});
	let rest: MiniatureGeometry['rest'] = null;
	if (selection.restStates > 0) {
		const angle = -Math.PI / 2 + ((slots - 1) / slots) * Math.PI * 2;
		rest = { x: orbit * Math.cos(angle), y: orbit * Math.sin(angle), text: `+${selection.restStates}` };
	}
	return { radius, centerRadius, nodes, rest };
}
