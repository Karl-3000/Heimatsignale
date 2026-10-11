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
	/** Eingaben der Beschriftung, damit die Ansicht sie für ihren Ausschnitt neu platzieren kann. */
	labelInputs: LabelInput[];
}

export interface SceneLabelOptions {
	/** Bildschirm-Pixel je Netzeinheit. */
	scale?: number;
	/** Sichtbarer Ausschnitt in Netzkoordinaten. */
	bounds?: Box;
	/** Weitere Hindernisse, z. B. die Fläche unter den Bedienelementen. */
	obstacles?: Box[];
}

export interface SceneLabels {
	labels: Map<string, LabelPlacement>;
	rootLabel: { x: number; y: number; box: Box; fontSize: number };
}

/**
 * Platziert die Beschriftungen einer Szene für einen Ausschnitt und Maßstab. Der Wohnort
 * in der Mitte und sein Name sind feste Hindernisse.
 */
export function placeSceneLabels(inputs: LabelInput[], rootName: string, options: SceneLabelOptions = {}): SceneLabels {
	const k = options.scale && options.scale > 0 ? 1 / options.scale : 1;
	const rootFont = 13 * k;
	const rootWidth = (estimateTextWidth(rootName, 13) + 8) * k;
	const rootLabelY = ROOT_RADIUS + (6 + LABEL_LINE_HEIGHT / 2) * k;
	const rootLabelBox: Box = {
		x0: -rootWidth / 2,
		y0: ROOT_RADIUS + 5 * k,
		x1: rootWidth / 2,
		y1: ROOT_RADIUS + (7 + LABEL_LINE_HEIGHT) * k
	};
	const rootBox: Box = { x0: -ROOT_RADIUS - 2, y0: -ROOT_RADIUS - 2, x1: ROOT_RADIUS + 2, y1: ROOT_RADIUS + 2 };
	const labels = placeLabels(inputs, {
		obstacles: [rootBox, rootLabelBox, ...(options.obstacles ?? [])],
		halfExtent: HALF_EXTENT,
		bounds: options.bounds,
		scale: options.scale
	});
	return { labels, rootLabel: { x: 0, y: rootLabelY, box: rootLabelBox, fontSize: rootFont } };
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
			// Ringe um die eigene Herkunft gehören zum Knoten; die Beschriftung hält Abstand davon.
			r: row.node.own ? r + 6 : r + 1,
			full: row.node.name,
			short: shortLabel(row.node.level, row.node.key, row.node.name),
			suffix: countInside ? undefined : String(row.node.count),
			sub: row.node.id === ownDeepestId ? OWN_ORIGIN_TEXT : undefined,
			priority: (row.node.own ? 1_000_000 : 0) + (4 - row.depth) * 10_000 + Math.min(row.node.count, 9_999)
		});
	}

	const placed = placeSceneLabels(inputs, rootName);

	return { nodes, edges, labels: placed.labels, rootLabel: placed.rootLabel, ownDeepestId, labelInputs: inputs };
}
