/**
 * Baumlogik des Herkunftsnetzes: Sortierung, sichtbare Zeilen, Pfad zur Mitte.
 * Netz und Listenansicht lesen beide dieselbe Zeilenliste, deshalb zeigen sie
 * immer identische Daten in identischer Reihenfolge.
 */

import { hierarchy, type HierarchyNode } from 'd3-hierarchy';
import type { OriginNode, SortMode } from './types';

const collator = new Intl.Collator('de');

export function compareNodes(a: OriginNode, b: OriginNode, mode: SortMode): number {
	if (mode === 'distance') {
		const da = a.distanceKm ?? Number.POSITIVE_INFINITY;
		const db = b.distanceKm ?? Number.POSITIVE_INFINITY;
		// Die eigene Herkunft steht bei "Nähe" immer vorn.
		if (a.own !== b.own) return a.own ? -1 : 1;
		if (da !== db) return da - db;
		if (a.count !== b.count) return b.count - a.count;
	} else {
		if (a.count !== b.count) return b.count - a.count;
		const da = a.distanceKm ?? Number.POSITIVE_INFINITY;
		const db = b.distanceKm ?? Number.POSITIVE_INFINITY;
		if (da !== db) return da - db;
	}
	return collator.compare(a.name, b.name) || a.id.localeCompare(b.id);
}

export function sortNodes(nodes: readonly OriginNode[], mode: SortMode): OriginNode[] {
	return [...nodes].sort((a, b) => compareNodes(a, b, mode));
}

/** Eine sichtbare Zeile des Baums, in Vorordnung (Eltern vor Kindern). */
export interface TreeRow {
	node: OriginNode;
	/** 0 = Wohnort, 1 = Bundesland, 2 = Landkreis, 3 = Ort. */
	depth: number;
	expanded: boolean;
	/** Position unter den Geschwistern, ab 1 (für aria-posinset). */
	posInSet: number;
	setSize: number;
}

export interface TreeSnapshot {
	rows: TreeRow[];
	byId: Map<string, TreeRow>;
	/** Größte Gruppe der ersten Stufe; Bezugsgröße für Flächen und Linienstärken. */
	maxCount: number;
	/** Kennungen vom Knoten bis zur Mitte, der Knoten selbst zuerst. */
	pathToRoot(id: string): string[];
}

export function buildTree(
	root: OriginNode,
	childrenOf: (id: string) => readonly OriginNode[] | undefined,
	isExpanded: (id: string) => boolean,
	mode: SortMode
): TreeSnapshot {
	const h = hierarchy<OriginNode>(root, (d) => {
		if (!isExpanded(d.id)) return null;
		const kids = childrenOf(d.id);
		return kids && kids.length > 0 ? sortNodes(kids, mode) : null;
	});

	const rows: TreeRow[] = [];
	const byId = new Map<string, TreeRow>();
	const hierById = new Map<string, HierarchyNode<OriginNode>>();

	h.eachBefore((n) => {
		const siblings = n.parent?.children ?? [n];
		const row: TreeRow = {
			node: n.data,
			depth: n.depth,
			expanded: isExpanded(n.data.id) && (n.children?.length ?? 0) > 0,
			posInSet: siblings.indexOf(n) + 1,
			setSize: siblings.length
		};
		rows.push(row);
		byId.set(n.data.id, row);
		hierById.set(n.data.id, n);
	});

	let maxCount = 0;
	for (const child of h.children ?? []) maxCount = Math.max(maxCount, child.data.count);
	if (maxCount === 0) maxCount = Math.max(1, root.count);

	return {
		rows,
		byId,
		maxCount,
		pathToRoot(id: string): string[] {
			const n = hierById.get(id);
			return n ? n.ancestors().map((a) => a.data.id) : [];
		}
	};
}

/** Alle Nachfahren eines Knotens in der aktuellen Zeilenliste. */
export function descendantIds(rows: readonly TreeRow[], id: string): string[] {
	const start = rows.findIndex((r) => r.node.id === id);
	if (start < 0) return [];
	const depth = rows[start].depth;
	const out: string[] = [];
	for (let i = start + 1; i < rows.length && rows[i].depth > depth; i++) out.push(rows[i].node.id);
	return out;
}
