import { describe, expect, it } from 'vitest';
import { circleBounds, circleRing, clampToCircle, destination, fitPxPerKm, haversineKm, localProject, maskPolygon, type LngLat } from './geo';

const MARL: LngLat = [7.0904, 51.6567];

describe('geo', () => {
	it('misst Entfernungen', () => {
		expect(haversineKm(MARL, MARL)).toBe(0);
		// Marl nach Recklinghausen: gut 8 km.
		const d = haversineKm(MARL, [7.1979, 51.6141]);
		expect(d).toBeGreaterThan(8);
		expect(d).toBeLessThan(10);
	});

	it('findet Zielpunkte in 20 km Entfernung', () => {
		for (const bearing of [0, 1, 2, 3, 4, 5, 6]) {
			expect(haversineKm(MARL, destination(MARL, 20, bearing))).toBeCloseTo(20, 3);
		}
	});

	it('zeichnet einen geschlossenen Kreis mit 20 km Radius', () => {
		const ring = circleRing(MARL, 20, 64);
		expect(ring).toHaveLength(65);
		expect(ring[0]).toEqual(ring[64]);
		for (const p of ring) expect(haversineKm(MARL, p)).toBeCloseTo(20, 3);
	});

	it('liefert ein Rechteck, das den Kreis umschließt', () => {
		const [[west, south], [east, north]] = circleBounds(MARL, 20);
		expect(west).toBeLessThan(MARL[0]);
		expect(east).toBeGreaterThan(MARL[0]);
		expect(south).toBeLessThan(MARL[1]);
		expect(north).toBeGreaterThan(MARL[1]);
		for (const p of circleRing(MARL, 20)) {
			expect(p[0]).toBeGreaterThanOrEqual(west - 1e-6);
			expect(p[0]).toBeLessThanOrEqual(east + 1e-6);
			expect(p[1]).toBeGreaterThanOrEqual(south - 1e-9);
			expect(p[1]).toBeLessThanOrEqual(north + 1e-9);
		}
	});

	it('holt einen Mittelpunkt außerhalb des Kreises an den Rand zurück', () => {
		const inside: LngLat = [7.2, 51.6];
		expect(clampToCircle(inside, MARL, 20)).toEqual(inside);
		const clamped = clampToCircle([8.5, 52.5], MARL, 20);
		expect(haversineKm(MARL, clamped)).toBeLessThan(21);
		expect(haversineKm(MARL, clamped)).toBeGreaterThan(18);
	});

	it('baut eine Maske mit Loch', () => {
		const mask = maskPolygon(MARL, 20);
		expect(mask).toHaveLength(2);
		expect(mask[0][0]).toEqual(mask[0][mask[0].length - 1]);
		expect(mask[1][0]).toEqual(mask[1][mask[1].length - 1]);
	});

	it('projiziert in der Ersatzdarstellung den Mittelpunkt in die Mitte und 20 km an den Rand', () => {
		const scale = fitPxPerKm(400, 300, 20, 30);
		expect(scale).toBeCloseTo(6, 6);
		expect(localProject(MARL, MARL, scale, 400, 300)).toEqual({ x: 200, y: 150 });
		const north = localProject(destination(MARL, 20, 0), MARL, scale, 400, 300);
		expect(north.x).toBeCloseTo(200, 0);
		expect(150 - north.y).toBeGreaterThan(118);
		expect(150 - north.y).toBeLessThan(122);
		const east = localProject(destination(MARL, 20, Math.PI / 2), MARL, scale, 400, 300);
		expect(east.x - 200).toBeGreaterThan(118);
		expect(east.x - 200).toBeLessThan(122);
	});
});
