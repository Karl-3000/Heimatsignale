import { describe, expect, it } from 'vitest';
import { treeKeyAction, type KeyRow } from './keyboard';
import { buildTree, descendantIds, sortNodes } from './model';
import { buildScene, layoutInputs } from './scene';
import { NetworkLayout } from './layout';
import { ROOT_ID, isOwn, nodeId, ownOriginFromAgs, toNode, type OriginNode } from './types';

const own = ownOriginFromAgs('09780139');

function n(level: 'state' | 'district' | 'place', key: string, name: string, count: number, distance: number | null, parentId: string): OriginNode {
	return toNode({ key, name, count, distance_km: distance }, level, parentId, own);
}

const root: OriginNode = { id: ROOT_ID, level: 'root', key: 'all', name: 'Marl', count: 22, distanceKm: null, parentId: null, own: false };
const children = new Map<string, OriginNode[]>([
	[ROOT_ID, [n('state', '05', 'Nordrhein-Westfalen', 7, 480, ROOT_ID), n('state', '09', 'Bayern', 12, 90, ROOT_ID), n('state', '14', 'Sachsen', 3, 420, ROOT_ID)]],
	['s09', [n('district', '09187', 'Rosenheim', 3, 150, 's09'), n('district', '09780', 'Oberallgäu', 4, 12, 's09')]],
	['d09780', [n('place', '09780124', 'Immenstadt', 1, 8, 'd09780'), n('place', '09780139', 'Sonthofen', 2, 0, 'd09780')]]
]);

describe('Kennungen und eigene Herkunft', () => {
	it('leitet Landkreis und Bundesland aus dem AGS ab', () => {
		expect(own).toEqual({ stateCode: '09', districtAgs: '09780', ags: '09780139' });
		expect(ownOriginFromAgs(null)).toBeNull();
		expect(nodeId('state', '09')).toBe('s09');
		expect(nodeId('root', 'x')).toBe(ROOT_ID);
	});

	it('markiert Ort, Landkreis und Bundesland der eigenen Herkunft', () => {
		expect(isOwn('state', '09', own)).toBe(true);
		expect(isOwn('district', '09780', own)).toBe(true);
		expect(isOwn('place', '09780139', own)).toBe(true);
		expect(isOwn('place', '09780124', own)).toBe(false);
		expect(isOwn('state', '05', own)).toBe(false);
	});
});

describe('sortNodes', () => {
	it('sortiert nach Nähe zum eigenen Heimatort', () => {
		expect(sortNodes(children.get(ROOT_ID)!, 'distance').map((x) => x.key)).toEqual(['09', '14', '05']);
	});

	it('sortiert nach Anzahl', () => {
		expect(sortNodes(children.get(ROOT_ID)!, 'count').map((x) => x.key)).toEqual(['09', '05', '14']);
	});

	it('stellt Gruppen ohne Entfernung ans Ende und verändert die Eingabe nicht', () => {
		const list = [n('state', '01', 'A', 1, null, ROOT_ID), n('state', '02', 'B', 1, 10, ROOT_ID)];
		expect(sortNodes(list, 'distance').map((x) => x.key)).toEqual(['02', '01']);
		expect(list[0].key).toBe('01');
	});
});

describe('buildTree', () => {
	it('zeigt nur aufgeklappte Ebenen, in Vorordnung', () => {
		const expanded = new Set([ROOT_ID, 's09']);
		const tree = buildTree(root, (id) => children.get(id), (id) => expanded.has(id), 'distance');
		expect(tree.rows.map((r) => r.node.id)).toEqual([ROOT_ID, 's09', 'd09780', 'd09187', 's14', 's05']);
		expect(tree.byId.get('s09')!.expanded).toBe(true);
		expect(tree.byId.get('s05')!.expanded).toBe(false);
		expect(tree.byId.get('d09187')).toMatchObject({ depth: 2, posInSet: 2, setSize: 2 });
		expect(tree.maxCount).toBe(12);
	});

	it('liefert den Pfad zur Mitte', () => {
		const expanded = new Set([ROOT_ID, 's09', 'd09780']);
		const tree = buildTree(root, (id) => children.get(id), (id) => expanded.has(id), 'count');
		expect(tree.pathToRoot('p09780139')).toEqual(['p09780139', 'd09780', 's09', ROOT_ID]);
		expect(tree.pathToRoot('gibt-es-nicht')).toEqual([]);
		expect(descendantIds(tree.rows, 's09')).toEqual(['d09780', 'p09780139', 'p09780124', 'd09187']);
	});
});

describe('buildScene', () => {
	it('erzeugt je Knoten genau eine Kante und markiert die tiefste eigene Herkunft', () => {
		const expanded = new Set([ROOT_ID, 's09', 'd09780']);
		const tree = buildTree(root, (id) => children.get(id), (id) => expanded.has(id), 'distance');
		const layout = new NetworkLayout();
		const result = layout.sync(layoutInputs(tree));
		const scene = buildScene(tree, result.positions, 'Marl');
		expect(scene.nodes).toHaveLength(7);
		expect(scene.edges).toHaveLength(7);
		expect(scene.ownDeepestId).toBe('p09780139');
		expect(scene.labels.get('p09780139')!.sub).toBe('deine Herkunft');
		expect(scene.labels.get('s09')!.sub).toBe('');
		const bayern = scene.nodes.find((x) => x.id === 's09')!;
		const sachsen = scene.nodes.find((x) => x.id === 's14')!;
		expect((bayern.r * bayern.r) / (sachsen.r * sachsen.r)).toBeCloseTo(4, 5);
		const edge = scene.edges.find((e) => e.id === 's09')!;
		expect(edge.parentId).toBe(ROOT_ID);
		expect(edge.width).toBeGreaterThan(scene.edges.find((e) => e.id === 's14')!.width);
	});
});

describe('treeKeyAction', () => {
	const rows: KeyRow[] = [
		{ id: 'root', depth: 0, parentId: null, expandable: false, expanded: true },
		{ id: 's09', depth: 1, parentId: 'root', expandable: true, expanded: true },
		{ id: 'd09780', depth: 2, parentId: 's09', expandable: true, expanded: false },
		{ id: 's05', depth: 1, parentId: 'root', expandable: true, expanded: false }
	];

	it('bewegt den Fokus mit den Pfeiltasten', () => {
		expect(treeKeyAction('ArrowDown', rows, 'root')).toEqual({ type: 'focus', id: 's09' });
		expect(treeKeyAction('ArrowUp', rows, 's05')).toEqual({ type: 'focus', id: 'd09780' });
		expect(treeKeyAction('ArrowUp', rows, 'root')).toBeNull();
		expect(treeKeyAction('End', rows, 'root')).toEqual({ type: 'focus', id: 's05' });
		expect(treeKeyAction('Home', rows, 's05')).toEqual({ type: 'focus', id: 'root' });
	});

	it('klappt mit Rechts auf und geht dann zum ersten Kind', () => {
		expect(treeKeyAction('ArrowRight', rows, 's05')).toEqual({ type: 'expand', id: 's05' });
		expect(treeKeyAction('ArrowRight', rows, 's09')).toEqual({ type: 'focus', id: 'd09780' });
	});

	it('klappt mit Links zu oder geht zum Elternknoten', () => {
		expect(treeKeyAction('ArrowLeft', rows, 's09')).toEqual({ type: 'collapse', id: 's09' });
		expect(treeKeyAction('ArrowLeft', rows, 'd09780')).toEqual({ type: 'focus', id: 's09' });
		expect(treeKeyAction('ArrowLeft', rows, 'root')).toBeNull();
	});

	it('aktiviert mit Enter und Leertaste', () => {
		expect(treeKeyAction('Enter', rows, 's05')).toEqual({ type: 'activate', id: 's05' });
		expect(treeKeyAction(' ', rows, 's05')).toEqual({ type: 'activate', id: 's05' });
		expect(treeKeyAction('a', rows, 's05')).toBeNull();
	});
});
