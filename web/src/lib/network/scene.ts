/**
 * Baut aus Baum und eingefrorenen Positionen die Zeichenanweisung des Netzes:
 * Knoten, Kanten und Beschriftungen. Rein und ohne DOM, damit sich die Regeln
 * (Fläche, Linienstärke, überlappungsfreie Beschriftung) prüfen lassen.
 */

import { ROOT_RADIUS, HALF_EXTENT, edgePath, edgeWidth, hitRadius, nodeRadius } from './geometry';
import { LABEL_LINE_HEIGHT, estimateTextWidth, placeLabels, shortLabel, type Box, type LabelInput, type LabelPlacement } from './labels';
import type { LayoutNodeInput, LayoutPosition } from './layout';
import type { TreeSnapshot } from './model';
import { ROOT_ID, type OriginNode } from './types';

/** Ab diesem Radius steht die Anzahl im Knoten, darunter hinter dem Namen. */
export const COUNT_INSIDE_RADIUS = 10;

export const OWN_ORIGIN_TEXT = 'deine Herkunft';

/** Eingabe für das Layout: alle sichtbaren Knoten außer dem Wohnort, in Baumreihenfolge. */
export function layoutInputs(tree: TreeSnapshot): LayoutNodeInput[] {
	const out: LayoutNodeInput[] = [];
	for (const row of tree.rows) {
		if (row.depth === 0) continue;
		out.push({
			id: row.node.id,
			parentId: row.node.parentId === ROOT_ID ? null : row.node.parentId,
			depth: row.depth,
			r: nodeRadius(row.node.count, tree.maxCount)
		});
	}
	return out;
}

export interface SceneNode {
	id: string;
	node: OriginNode;
	x: number;
	y: number;
	r: number;
	hit: number;
	depth: number;
	expanded: boolean;
	countInside: boolean;
}

export interface SceneEdge {
	/** Kennung des Kindknotens; jede Kante gehört zu genau einem Kind. */
	id: string;
	parentId: string;
	d: string;
	width: number;
	count: number;
}

export interface Scene {
	nodes: SceneNode[];
	edges: SceneEdge[];
	labels: Map<string, LabelPlacement>;
	rootLabel: { x: number; y: number; box: Box };
	/** Tiefster sichtbarer Knoten der eigenen Herkunft, falls vorhanden. */
	ownDeepestId: string | null;
}

export function buildScene(tree: TreeSnapshot, positions: ReadonlyMap<string, LayoutPosition>, rootName: string): Scene {
	const nodes: SceneNode[] = [];
	const edges: SceneEdge[] = [];
	const inputs: LabelInput[] = [];

	let ownDeepestId: string | null = null;
	let ownDepth = 0;
	for (const row of tree.rows) {
		if (row.node.own && row.depth > ownDepth && positions.has(row.node.id)) {
			ownDepth = row.depth;
			ownDeepestId = row.node.id;
		}
	}

	for (const row of tree.rows) {
		if (row.depth === 0) continue;
		const pos = positions.get(row.node.id);
		if (!pos) continue;
		const r = nodeRadius(row.node.count, tree.maxCount);
		const countInside = r >= COUNT_INSIDE_RADIUS;
		nodes.push({
			id: row.node.id,
			node: row.node,
			x: pos.x,
			y: pos.y,
			r,
			hit: hitRadius(r),
			depth: row.depth,
			expanded: row.expanded,
			countInside
		});

		const parentId = row.node.parentId ?? ROOT_ID;
		const parent = parentId === ROOT_ID ? { x: 0, y: 0 } : positions.get(parentId);
		if (parent) {
			edges.push({
				id: row.node.id,
				parentId,
				d: edgePath({ x: parent.x, y: parent.y }, { x: pos.x, y: pos.y }),
				width: edgeWidth(row.node.count, tree.maxCount),
				count: row.node.count
			});
		}

		inputs.push({
			id: row.node.id,
			x: pos.x,
			y: pos.y,
			r,
			full: row.node.name,
			short: shortLabel(row.node.level, row.node.key, row.node.name),
			suffix: countInside ? undefined : String(row.node.count),
			sub: row.node.id === ownDeepestId ? OWN_ORIGIN_TEXT : undefined,
			priority: (row.node.own ? 1_000_000 : 0) + (4 - row.depth) * 10_000 + Math.min(row.node.count, 9_999)
		});
	}

	// Der Wohnort in der Mitte und sein Name sind feste Hindernisse.
	const rootWidth = estimateTextWidth(rootName, 13) + 8;
	const rootLabelY = ROOT_RADIUS + 6 + LABEL_LINE_HEIGHT / 2;
	const rootLabelBox: Box = {
		x0: -rootWidth / 2,
		y0: ROOT_RADIUS + 5,
		x1: rootWidth / 2,
		y1: ROOT_RADIUS + 7 + LABEL_LINE_HEIGHT
	};
	const rootBox: Box = { x0: -ROOT_RADIUS - 2, y0: -ROOT_RADIUS - 2, x1: ROOT_RADIUS + 2, y1: ROOT_RADIUS + 2 };

	const labels = placeLabels(inputs, { obstacles: [rootBox, rootLabelBox], halfExtent: HALF_EXTENT });

	return { nodes, edges, labels, rootLabel: { x: 0, y: rootLabelY, box: rootLabelBox }, ownDeepestId };
}
