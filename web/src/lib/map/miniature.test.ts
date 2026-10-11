import { describe, expect, it } from 'vitest';
import type { StateGroup } from '../api/types';
import { datasetHerkunftAusserhalb } from '../network/synthetic';
import { mergeStates, miniatureGeometry, selectMiniatureStates } from './miniature';

const s = (state_code: string, count: number): StateGroup => ({ state_code, count, distance_km: 100 });

describe('selectMiniatureStates', () => {
	it('zeigt alle, wenn es höchstens fünf sind', () => {
		const sel = selectMiniatureStates([s('09', 7), s('05', 3)], '09');
		expect(sel.shown.map((x) => x.stateCode)).toEqual(['09', '05']);
		expect(sel.restStates).toBe(0);
		expect(sel.shown[0].own).toBe(true);
	});

	it('zeigt die fünf größten und fasst den Rest als +N zusammen', () => {
		const sel = selectMiniatureStates([s('01', 1), s('02', 2), s('03', 3), s('04', 4), s('05', 5), s('06', 6), s('07', 7), s('08', 8)], null);
		expect(sel.shown.map((x) => x.stateCode)).toEqual(['08', '07', '06', '05', '04']);
		expect(sel.restStates).toBe(3);
		expect(sel.restCount).toBe(6);
		expect(sel.total).toBe(36);
	});

	it('zeigt das eigene Bundesland immer, auch außerhalb der fünf größten', () => {
		const states = datasetHerkunftAusserhalb().overview.residences[0].states;
		expect(states.findIndex((x) => x.state_code === '09')).toBeGreaterThan(4);
		const sel = selectMiniatureStates(states, '09');
		expect(sel.shown).toHaveLength(6);
		expect(sel.shown[5]).toMatchObject({ stateCode: '09', own: true });
		expect(sel.restStates).toBe(states.length - 6);
		expect(sel.shown.reduce((a, x) => a + x.count, 0) + sel.restCount).toBe(sel.total);
	});

	it('zeigt das eigene Bundesland nicht, wenn dort niemand von dort stammt', () => {
		const sel = selectMiniatureStates([s('05', 5), s('14', 2)], '09');
		expect(sel.shown.some((x) => x.own)).toBe(false);
	});

	it('kommt mit leerer Liste zurecht', () => {
		expect(selectMiniatureStates([], '09')).toEqual({ shown: [], restStates: 0, restCount: 0, total: 0 });
	});
});

describe('mergeStates', () => {
	it('summiert die Bundesländer mehrerer Wohnorte', () => {
		const merged = mergeStates([[s('09', 2), s('05', 1)], [s('09', 3), s('14', 4)]]);
		expect(merged.map((x) => [x.state_code, x.count])).toEqual([
			['09', 5],
			['14', 4],
			['05', 1]
		]);
	});
});

describe('miniatureGeometry', () => {
	it('hält alle Knoten innerhalb des Radius und macht die Fläche proportional', () => {
		const sel = selectMiniatureStates([s('09', 16), s('05', 4), s('14', 1), s('03', 1), s('06', 1), s('08', 1), s('12', 1)], '12');
		for (const radius of [34, 58, 92]) {
			const geo = miniatureGeometry(sel, radius);
			for (const n of geo.nodes) {
				expect(Math.hypot(n.x, n.y) + n.r).toBeLessThanOrEqual(radius);
			}
			const big = geo.nodes.find((n) => n.stateCode === '09')!;
			const mid = geo.nodes.find((n) => n.stateCode === '05')!;
			expect((big.r * big.r) / (mid.r * mid.r)).toBeCloseTo(4, 5);
			expect(geo.rest?.text).toBe('+1');
			expect(geo.nodes.some((n) => n.own)).toBe(true);
		}
	});

	it('zeigt Kürzel erst ab einer lesbaren Größe', () => {
		const sel = selectMiniatureStates([s('09', 3), s('05', 2)], '09');
		expect(miniatureGeometry(sel, 40).nodes[0].label).toBeNull();
		expect(miniatureGeometry(sel, 70).nodes.map((n) => n.label)).toEqual(['BY', 'NRW']);
	});
});
