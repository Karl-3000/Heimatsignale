import { describe, expect, it } from 'vitest';
import { NetworkCore } from './core';
import { HALF_EXTENT, RING_RADIUS, ROOT_RADIUS, hitRadius } from './geometry';
import { countLabelOverlaps } from './labels';
import { NetworkLayout, allocateAngles, countOverlaps, type LayoutPosition } from './layout';
import { statesFromOverview, totalForScope } from './overview';
import { SCOPE_ALL } from './source';
import {
	datasetDreiWohnorte,
	datasetGross,
	datasetHerkunftAusserhalb,
	datasetKlein,
	datasetLangeNamen,
	datasetLeer,
	datasetMittel,
	datasetUngleich,
	type SyntheticDataset
} from './synthetic';
import { ownOriginFromAgs } from './types';

function coreFor(dataset: SyntheticDataset, scope: string = SCOPE_ALL): NetworkCore {
	return new NetworkCore({
		scope,
		rootName: 'Alle im Umkreis',
		rootCount: totalForScope(dataset.overview, scope),
		states: statesFromOverview(dataset.overview, scope),
		own: ownOriginFromAgs(dataset.overview.me.home.ags),
		source: dataset.source
	});
}

function positionsOf(core: NetworkCore): Map<string, LayoutPosition> {
	return core.layout.snapshot();
}

/** Klappt Ebene für Ebene alles auf und prüft nach JEDEM Schritt die Stabilitätsregel. */
async function expandAllChecked(core: NetworkCore): Promise<number> {
	let steps = 0;
	for (let depth = 1; depth <= 2; depth++) {
		const ids = core.tree.rows.filter((r) => r.depth === depth).map((r) => r.node.id);
		for (const id of ids) {
			const before = positionsOf(core);
			await core.expand(id);
			const after = positionsOf(core);
			for (const [key, pos] of before) {
				const now = after.get(key);
				expect(now).toBeDefined();
				expect(now!.x).toBe(pos.x);
				expect(now!.y).toBe(pos.y);
			}
			steps++;
		}
	}
	return steps;
}

function assertClean(core: NetworkCore): void {
	const positions = [...positionsOf(core).values()];
	expect(countOverlaps(positions, ROOT_RADIUS)).toBe(0);
	for (const p of positions) {
		expect(Number.isFinite(p.x) && Number.isFinite(p.y)).toBe(true);
		expect(Math.abs(p.x) + hitRadius(p.r)).toBeLessThanOrEqual(HALF_EXTENT);
		expect(Math.abs(p.y) + hitRadius(p.r)).toBeLessThanOrEqual(HALF_EXTENT);
	}
	expect(countLabelOverlaps(core.scene.labels.values())).toBe(0);
}

describe('allocateAngles', () => {
	it('verteilt einen vollen Kreis gleichmäßig und beginnt oben', () => {
		const angles = allocateAngles([10, 10, 10, 10], 150, -Math.PI / 2, Math.PI * 2);
		expect(angles).toHaveLength(4);
		expect(angles[0]).toBeCloseTo(-Math.PI / 2, 6);
		expect(angles[1] - angles[0]).toBeCloseTo(Math.PI / 2, 6);
		expect(angles[3] - angles[2]).toBeCloseTo(Math.PI / 2, 6);
	});

	it('zentriert einen Fächer um den Winkel des Elternknotens', () => {
		const angles = allocateAngles([14, 14, 14], 300, 1, 0.6);
		expect((angles[0] + angles[2]) / 2).toBeCloseTo(1, 6);
		expect(angles[1]).toBeCloseTo(1, 6);
	});

	it('gibt großen Knoten mehr Bogen', () => {
		const angles = allocateAngles([30, 5, 5], 150, 0, Math.PI * 2);
		expect(angles[1] - angles[0]).toBeGreaterThan(angles[2] - angles[1]);
	});
});

describe('NetworkLayout: Stabilitätsregel', () => {
	it('ist deterministisch', () => {
		const inputs = Array.from({ length: 12 }, (_, i) => ({ id: `s${i}`, parentId: null, depth: 1, r: 4 + i }));
		const a = new NetworkLayout().sync(inputs);
		const b = new NetworkLayout().sync(inputs);
		for (const [id, pos] of a.positions) {
			expect(b.positions.get(id)!.x).toBe(pos.x);
			expect(b.positions.get(id)!.y).toBe(pos.y);
		}
	});

	it('kommt zur Ruhe und meldet die Schrittzahl', () => {
		const layout = new NetworkLayout();
		const result = layout.sync([{ id: 'a', parentId: null, depth: 1, r: 10 }]);
		expect(result.ticks).toBeGreaterThan(0);
		expect(result.ticks).toBeLessThanOrEqual(800);
		// Ohne neue Knoten wird gar nicht simuliert: Das Ergebnis ist eingefroren.
		const again = layout.sync([{ id: 'a', parentId: null, depth: 1, r: 10 }]);
		expect(again.ticks).toBe(0);
		expect(again.added).toHaveLength(0);
	});

	it('legt die Stufen auf ihre Ringe', async () => {
		const core = coreFor(datasetMittel());
		await expandAllChecked(core);
		for (const p of positionsOf(core).values()) {
			const ring = [0, RING_RADIUS.state, RING_RADIUS.district, RING_RADIUS.place][p.depth];
			expect(Math.abs(Math.hypot(p.x, p.y) - ring)).toBeLessThan(120);
		}
	});

	it('platziert Kinder in der Nähe des Elternknotens', async () => {
		const core = coreFor(datasetMittel());
		const first = core.tree.rows.find((r) => r.depth === 1)!.node.id;
		await core.expand(first);
		const parent = core.layout.get(first)!;
		const parentAngle = Math.atan2(parent.y, parent.x);
		for (const row of core.tree.rows.filter((r) => r.node.parentId === first)) {
			const p = core.layout.get(row.node.id)!;
			let delta = Math.abs(Math.atan2(p.y, p.x) - parentAngle);
			if (delta > Math.PI) delta = Math.PI * 2 - delta;
			expect(delta).toBeLessThan(Math.PI / 3);
		}
	});

	it('entfernt beim Zuklappen nur den Teilbaum und lässt alles andere stehen', async () => {
		const core = coreFor(datasetMittel());
		await expandAllChecked(core);
		const target = core.tree.rows.find((r) => r.depth === 1)!.node.id;
		const before = positionsOf(core);
		const sizeBefore = before.size;
		core.collapse(target);
		const after = positionsOf(core);
		expect(after.size).toBeLessThan(sizeBefore);
		for (const [id, pos] of after) {
			expect(before.get(id)!.x).toBe(pos.x);
			expect(before.get(id)!.y).toBe(pos.y);
		}
	});
});

describe('Testdaten aus dem Projektplan', () => {
	it('5 Knoten', async () => {
		const dataset = datasetKlein();
		const core = coreFor(dataset);
		await expandAllChecked(core);
		expect(core.layout.size).toBe(5);
		expect(dataset.nodeCount).toBe(5);
		assertClean(core);
	});

	it('50 Knoten', async () => {
		const dataset = datasetMittel();
		const core = coreFor(dataset);
		await expandAllChecked(core);
		expect(core.layout.size).toBe(50);
		assertClean(core);
	});

	it('300 Knoten', async () => {
		const dataset = datasetGross();
		const core = coreFor(dataset);
		const steps = await expandAllChecked(core);
		expect(steps).toBe(60);
		expect(core.layout.size).toBe(300);
		assertClean(core);
	});

	it('lange Ortsnamen bleiben überlappungsfrei und werden bei Bedarf gekürzt', async () => {
		const core = coreFor(datasetLangeNamen());
		await expandAllChecked(core);
		assertClean(core);
		const labels = [...core.scene.labels.values()];
		const shown = labels.filter((l) => l.variant !== 'hidden');
		expect(shown.length).toBeGreaterThan(labels.length / 2);
	});

	it('sehr ungleiche Gruppen: Fläche folgt der Anzahl', async () => {
		const core = coreFor(datasetUngleich());
		assertClean(core);
		const nodes = core.scene.nodes;
		const big = nodes.find((n) => n.node.count === 80)!;
		const mid = nodes.find((n) => n.node.count === 6)!;
		expect(big).toBeDefined();
		const ratio = (big.r * big.r) / (mid.r * mid.r);
		expect(ratio).toBeCloseTo(80 / 6, 1);
		const one = nodes.find((n) => n.node.count === 1)!;
		// Auch ein Einzelner bleibt sichtbar und gut treffbar.
		expect(one.r).toBeGreaterThanOrEqual(3);
		expect(one.hit).toBeGreaterThanOrEqual(14);
		await expandAllChecked(core);
		assertClean(core);
	});

	it('drei dicht benachbarte Wohnorte: je Wohnort und zusammen', async () => {
		const dataset = datasetDreiWohnorte();
		for (const scope of [SCOPE_ALL, ...dataset.overview.residences.map((r) => r.ags)]) {
			const core = coreFor(dataset, scope);
			await expandAllChecked(core);
			assertClean(core);
			const sum = core.scene.nodes.filter((n) => n.depth === 1).reduce((a, n) => a + n.node.count, 0);
			expect(sum).toBe(totalForScope(dataset.overview, scope));
		}
	});

	it('eigene Herkunft außerhalb der fünf größten ist markiert und steht bei "Nähe" vorn', async () => {
		const core = coreFor(datasetHerkunftAusserhalb());
		const states = core.tree.rows.filter((r) => r.depth === 1);
		expect(states[0].node.key).toBe('09');
		expect(states[0].node.own).toBe(true);
		core.setSort('count');
		const byCount = core.tree.rows.filter((r) => r.depth === 1);
		expect(byCount[0].node.key).toBe('05');
		expect(byCount.findIndex((r) => r.node.own)).toBeGreaterThan(4);
		await expandAllChecked(core);
		assertClean(core);
		expect(core.scene.ownDeepestId).toBe('p09780139');
		expect(core.scene.labels.get('p09780139')!.sub).toBe('deine Herkunft');
	});

	it('leerer Umkreis: nur der Wohnort', () => {
		const core = coreFor(datasetLeer());
		expect(core.tree.rows).toHaveLength(1);
		expect(core.scene.nodes).toHaveLength(0);
		expect(core.scene.edges).toHaveLength(0);
	});
});

describe('Rechenzeit', () => {
	it('300 Knoten vollständig aufklappen bleibt im Rahmen', async () => {
		const core = coreFor(datasetGross());
		const start = Date.now();
		await expandAllChecked(core);
		const elapsed = Date.now() - start;
		// Großzügige Grenze für langsame CI-Rechner; lokal sind es deutlich unter 2 s für 60 Schritte.
		expect(elapsed).toBeLessThan(20000);
	});
});
