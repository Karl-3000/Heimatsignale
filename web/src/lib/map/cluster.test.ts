import { describe, expect, it } from 'vitest';
import { CLUSTER_THRESHOLD_PX, COMPACT_RADIUS, MINIATURE_MAX_RADIUS, MINIATURE_MIN_RADIUS, clusterPoints, countMarkerOverlaps, desiredMiniatureRadius, sizeClusters, type ScreenPoint } from './cluster';
import { fitPxPerKm, haversineKm, localProject } from './geo';
import { datasetDreiWohnorte, datasetWeit } from '../network/synthetic';

function minDistance(points: Array<{ x: number; y: number }>): number {
	let min = Number.POSITIVE_INFINITY;
	for (let i = 0; i < points.length; i++) {
		for (let j = i + 1; j < points.length; j++) {
			min = Math.min(min, Math.hypot(points[i].x - points[j].x, points[i].y - points[j].y));
		}
	}
	return min;
}

describe('clusterPoints', () => {
	it('lässt weit entfernte Knoten einzeln', () => {
		const clusters = clusterPoints([
			{ id: 'a', x: 0, y: 0, weight: 3 },
			{ id: 'b', x: 100, y: 0, weight: 5 }
		]);
		expect(clusters).toHaveLength(2);
	});

	it('fasst Knoten unter 48 px zusammen und summiert', () => {
		const clusters = clusterPoints([
			{ id: 'b', x: 40, y: 0, weight: 9 },
			{ id: 'a', x: 0, y: 0, weight: 3 }
		]);
		expect(clusters).toHaveLength(1);
		expect(clusters[0].weight).toBe(12);
		expect(clusters[0].ids).toEqual(['a', 'b']);
		// Der Schwerpunkt liegt näher am größeren Wohnort.
		expect(clusters[0].x).toBeCloseTo(30, 6);
	});

	it('trennt bei genau 48 px nicht mehr zusammen', () => {
		const clusters = clusterPoints([
			{ id: 'a', x: 0, y: 0, weight: 1 },
			{ id: 'b', x: CLUSTER_THRESHOLD_PX, y: 0, weight: 1 }
		]);
		expect(clusters).toHaveLength(2);
	});

	it('fasst Ketten so lange zusammen, bis alle Abstände mindestens 48 px betragen', () => {
		const points: ScreenPoint[] = Array.from({ length: 30 }, (_, i) => ({
			id: `p${String(i).padStart(2, '0')}`,
			x: (i * 37) % 200,
			y: (i * 53) % 160,
			weight: 1 + (i % 4)
		}));
		const clusters = clusterPoints(points);
		expect(minDistance(clusters)).toBeGreaterThanOrEqual(CLUSTER_THRESHOLD_PX);
		expect(clusters.reduce((a, c) => a + c.weight, 0)).toBe(points.reduce((a, p) => a + p.weight, 0));
		expect(clusters.reduce((a, c) => a + c.ids.length, 0)).toBe(30);
	});

	it('ist unabhängig von der Reihenfolge der Eingabe', () => {
		const points: ScreenPoint[] = [
			{ id: 'a', x: 0, y: 0, weight: 2 },
			{ id: 'b', x: 30, y: 10, weight: 5 },
			{ id: 'c', x: 200, y: 0, weight: 1 },
			{ id: 'd', x: 215, y: 20, weight: 1 }
		];
		const one = clusterPoints(points);
		const two = clusterPoints([...points].reverse());
		expect(one.map((c) => c.ids.join('+')).sort()).toEqual(two.map((c) => c.ids.join('+')).sort());
	});

	it('trennt die drei dicht benachbarten Wohnorte beim Hineinzoomen wieder', () => {
		const residences = datasetDreiWohnorte().overview.residences;
		const herten = residences.find((r) => r.name === 'Herten')!;
		const recklinghausen = residences.find((r) => r.name === 'Recklinghausen')!;
		const km = haversineKm([herten.lon, herten.lat], [recklinghausen.lon, recklinghausen.lat]);
		expect(km).toBeLessThan(6);

		// Einfache Projektion: Pixel je Kilometer verdoppeln sich mit jeder Zoomstufe.
		const project = (pxPerKm: number): ScreenPoint[] =>
			residences.map((r) => ({
				id: r.ags,
				x: (r.lon - 7.09) * 69.5 * pxPerKm,
				y: -(r.lat - 51.65) * 111.2 * pxPerKm,
				weight: r.total
			}));

		const far = clusterPoints(project(8));
		const near = clusterPoints(project(32));
		expect(far.length).toBeLessThan(residences.length);
		expect(far.some((c) => c.ids.includes(herten.ags) && c.ids.includes(recklinghausen.ags))).toBe(true);
		expect(near).toHaveLength(residences.length);
	});

	it('kommt mit leerer Eingabe zurecht', () => {
		expect(clusterPoints([])).toEqual([]);
	});
});

describe('sizeClusters', () => {
	it('zeichnet Darstellungen nie übereinander', () => {
		const points: ScreenPoint[] = Array.from({ length: 40 }, (_, i) => ({
			id: `p${String(i).padStart(2, '0')}`,
			x: (i * 71) % 420,
			y: (i * 113) % 380,
			weight: 1 + (i % 7)
		}));
		for (const desired of [MINIATURE_MIN_RADIUS, 60, MINIATURE_MAX_RADIUS]) {
			const sized = sizeClusters(clusterPoints(points), desired);
			expect(countMarkerOverlaps(sized)).toBe(0);
		}
	});

	it('schrumpft bei Enge auf einen Knoten mit Zahl', () => {
		const sized = sizeClusters(
			[
				{ ids: ['a'], x: 0, y: 0, weight: 3 },
				{ ids: ['b'], x: 50, y: 0, weight: 4 }
			],
			80
		);
		expect(sized.every((c) => c.mode === 'compact' && c.radius === COMPACT_RADIUS)).toBe(true);
	});

	it('gibt einem einzelnen Knoten die Wunschgröße', () => {
		const sized = sizeClusters([{ ids: ['a'], x: 0, y: 0, weight: 3 }], 70);
		expect(sized[0]).toMatchObject({ mode: 'miniature', radius: 70 });
	});
});

describe('desiredMiniatureRadius', () => {
	it('wächst beim Hineinzoomen und bleibt in den Grenzen', () => {
		const a = desiredMiniatureRadius(9, 9);
		const b = desiredMiniatureRadius(10, 9);
		expect(b).toBeGreaterThan(a);
		expect(desiredMiniatureRadius(20, 9)).toBe(MINIATURE_MAX_RADIUS);
		expect(desiredMiniatureRadius(0, 9)).toBe(MINIATURE_MIN_RADIUS);
	});
});

describe('100 km mit 60 Wohnorten', () => {
	const overview = datasetWeit().overview;
	const center: [number, number] = [overview.me.residence.lon, overview.me.residence.lat];

	function project(width: number, height: number, zoomFactor: number): ScreenPoint[] {
		const scale = fitPxPerKm(width, height, overview.radius_km) * zoomFactor;
		return overview.residences.map((r) => {
			const p = localProject([r.lon, r.lat], center, scale, width, height);
			return { id: r.ags, x: p.x, y: p.y, weight: r.total };
		});
	}

	it('hat 60 Wohnorte innerhalb von 100 km', () => {
		expect(overview.radius_km).toBe(100);
		expect(overview.residences).toHaveLength(60);
		for (const r of overview.residences) expect(haversineKm(center, [r.lon, r.lat])).toBeLessThanOrEqual(100);
	});

	it('hält auf Telefon und Desktop 48 px Abstand, zählt niemanden doppelt und überdeckt nichts', () => {
		const total = overview.residences.reduce((a, r) => a + r.total, 0);
		for (const [width, height] of [
			[328, 320],
			[1056, 540]
		]) {
			for (const zoomFactor of [1, 2, 4, 8, 16]) {
				const clusters = clusterPoints(project(width, height, zoomFactor));
				expect(minDistance(clusters)).toBeGreaterThanOrEqual(CLUSTER_THRESHOLD_PX);
				expect(clusters.reduce((a, c) => a + c.weight, 0)).toBe(total);
				expect(clusters.reduce((a, c) => a + c.ids.length, 0)).toBe(60);
				for (const desired of [MINIATURE_MIN_RADIUS, 60, MINIATURE_MAX_RADIUS]) {
					expect(countMarkerOverlaps(sizeClusters(clusters, desired))).toBe(0);
				}
			}
		}
	});

	it('fasst herausgezoomt zusammen und trennt beim Hineinzoomen wieder alle Wohnorte', () => {
		const far = clusterPoints(project(328, 320, 1));
		expect(far.length).toBeLessThan(30);
		expect(far.some((c) => c.ids.length > 1)).toBe(true);
		let previous = far.length;
		for (const zoomFactor of [2, 4, 8, 16, 32, 64]) {
			const count = clusterPoints(project(328, 320, zoomFactor)).length;
			expect(count).toBeGreaterThanOrEqual(previous - 1);
			previous = count;
		}
		expect(clusterPoints(project(328, 320, 64))).toHaveLength(60);
	});

	it('bleibt auch mit 400 Punkten schnell', () => {
		const points: ScreenPoint[] = Array.from({ length: 400 }, (_, i) => ({
			id: `p${String(i).padStart(3, '0')}`,
			x: (i * 7919) % 1000,
			y: (i * 104729) % 600,
			weight: 1 + (i % 5)
		}));
		const start = Date.now();
		const clusters = clusterPoints(points);
		expect(Date.now() - start).toBeLessThan(1500);
		expect(minDistance(clusters)).toBeGreaterThanOrEqual(CLUSTER_THRESHOLD_PX);
		expect(clusters.reduce((a, c) => a + c.weight, 0)).toBe(points.reduce((a, p) => a + p.weight, 0));
	});
});
