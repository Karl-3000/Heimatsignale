import { describe, expect, it } from 'vitest';
import { EDGE_WIDTH_MAX, EDGE_WIDTH_MIN, HIT_RADIUS_MIN, NODE_RADIUS_MAX, NODE_RADIUS_MIN, edgePath, edgeWidth, hitRadius, nodeRadius } from './geometry';

describe('nodeRadius', () => {
	it('macht die Fläche proportional zur Anzahl, nicht den Radius', () => {
		const a = nodeRadius(20, 80);
		const b = nodeRadius(80, 80);
		expect(b).toBe(NODE_RADIUS_MAX);
		expect((b * b) / (a * a)).toBeCloseTo(4, 6);
		expect(b / a).toBeCloseTo(2, 6);
	});

	it('hält einen Mindestradius für sehr kleine Gruppen', () => {
		expect(nodeRadius(1, 10000)).toBe(NODE_RADIUS_MIN);
		expect(nodeRadius(0, 10)).toBe(NODE_RADIUS_MIN);
		expect(nodeRadius(5, 0)).toBe(NODE_RADIUS_MIN);
	});

	it('wächst nie über den Höchstradius', () => {
		expect(nodeRadius(500, 80)).toBe(NODE_RADIUS_MAX);
	});
});

describe('hitRadius', () => {
	it('ist nie kleiner als die Mindestklickfläche', () => {
		expect(hitRadius(3)).toBe(HIT_RADIUS_MIN);
		expect(hitRadius(28)).toBe(32);
	});
});

describe('edgeWidth', () => {
	it('wächst linear mit der Anzahl', () => {
		expect(edgeWidth(80, 80)).toBe(EDGE_WIDTH_MAX);
		const half = edgeWidth(40, 80);
		expect(half).toBeCloseTo((EDGE_WIDTH_MIN + EDGE_WIDTH_MAX) / 2, 6);
		expect(edgeWidth(1, 80)).toBeGreaterThan(EDGE_WIDTH_MIN);
	});
});

describe('edgePath', () => {
	it('zeichnet von der Mitte eine gebogene quadratische Kurve', () => {
		const d = edgePath({ x: 0, y: 0 }, { x: 150, y: 0 });
		expect(d.startsWith('M0,0Q')).toBe(true);
		// Der Kontrollpunkt liegt neben der Geraden, sonst wäre die Kante nicht gekrümmt.
		const control = d.slice(d.indexOf('Q') + 1).split(' ')[0].split(',').map(Number);
		expect(Math.abs(control[1])).toBeGreaterThan(5);
	});

	it('zeichnet zwischen den Ringen eine kubische Kurve bis zum Kind', () => {
		const d = edgePath({ x: 150, y: 0 }, { x: 0, y: 310 });
		expect(d.includes('C')).toBe(true);
		expect(d.endsWith('0,310')).toBe(true);
	});
});
