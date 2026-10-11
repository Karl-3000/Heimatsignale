/** Geografische Hilfsfunktionen für die Umkreiskarte. Ohne Kartenbibliothek, mit Tests. */

const EARTH_RADIUS_KM = 6371.0088;
const RAD = Math.PI / 180;

export type LngLat = [number, number];

export function haversineKm(a: LngLat, b: LngLat): number {
	const dLat = (b[1] - a[1]) * RAD;
	const dLon = (b[0] - a[0]) * RAD;
	const s =
		Math.sin(dLat / 2) ** 2 + Math.cos(a[1] * RAD) * Math.cos(b[1] * RAD) * Math.sin(dLon / 2) ** 2;
	return 2 * EARTH_RADIUS_KM * Math.asin(Math.min(1, Math.sqrt(s)));
}

/** Zielpunkt nach `distanceKm` in Richtung `bearing` (Radiant, 0 = Norden, im Uhrzeigersinn). */
export function destination(center: LngLat, distanceKm: number, bearing: number): LngLat {
	const d = distanceKm / EARTH_RADIUS_KM;
	const lat1 = center[1] * RAD;
	const lon1 = center[0] * RAD;
	const lat2 = Math.asin(Math.sin(lat1) * Math.cos(d) + Math.cos(lat1) * Math.sin(d) * Math.cos(bearing));
	const lon2 =
		lon1 + Math.atan2(Math.sin(bearing) * Math.sin(d) * Math.cos(lat1), Math.cos(d) - Math.sin(lat1) * Math.sin(lat2));
	return [lon2 / RAD, lat2 / RAD];
}

/** Geschlossener Ring eines Kreises um `center`, gegen den Uhrzeigersinn. */
export function circleRing(center: LngLat, radiusKm: number, steps: number = 96): LngLat[] {
	const ring: LngLat[] = [];
	for (let i = 0; i < steps; i++) {
		ring.push(destination(center, radiusKm, (-i / steps) * Math.PI * 2));
	}
	ring.push(ring[0]);
	return ring;
}

/** Umschließendes Rechteck des Kreises: [[west, süd], [ost, nord]]. */
export function circleBounds(center: LngLat, radiusKm: number): [LngLat, LngLat] {
	const north = destination(center, radiusKm, 0);
	const east = destination(center, radiusKm, Math.PI / 2);
	const south = destination(center, radiusKm, Math.PI);
	const west = destination(center, radiusKm, (3 * Math.PI) / 2);
	return [
		[west[0], south[1]],
		[east[0], north[1]]
	];
}

/**
 * Hält einen Kartenmittelpunkt innerhalb des Kreises. Liegt er außerhalb, wird er
 * auf der Verbindungslinie zum Zentrum bis an den Rand zurückgeholt.
 */
export function clampToCircle(point: LngLat, center: LngLat, radiusKm: number): LngLat {
	const d = haversineKm(point, center);
	if (d <= radiusKm) return point;
	const t = radiusKm / d;
	return [center[0] + (point[0] - center[0]) * t, center[1] + (point[1] - center[1]) * t];
}

/** Fläche mit kreisförmigem Loch: deckt alles außerhalb des Umkreises ab. */
export function maskPolygon(center: LngLat, radiusKm: number): LngLat[][] {
	const outer: LngLat[] = [
		[-180, -85],
		[180, -85],
		[180, 85],
		[-180, 85],
		[-180, -85]
	];
	const hole = circleRing(center, radiusKm).slice().reverse();
	return [outer, hole];
}

/**
 * Einfache ebene Projektion um einen Mittelpunkt. Für Umkreise bis etwa 100 km genau genug;
 * dient als Ersatzdarstellung, wenn die Kartenbibliothek nicht starten kann (kein WebGL).
 */
export function localProject(
	point: LngLat,
	center: LngLat,
	pxPerKm: number,
	width: number,
	height: number
): { x: number; y: number } {
	const dxKm = (point[0] - center[0]) * 111.32 * Math.cos(center[1] * RAD);
	const dyKm = (point[1] - center[1]) * 110.57;
	return { x: width / 2 + dxKm * pxPerKm, y: height / 2 - dyKm * pxPerKm };
}

/** Pixel je Kilometer, bei denen der Kreis mit Rand genau in die Fläche passt. */
export function fitPxPerKm(width: number, height: number, radiusKm: number, padding: number = 28): number {
	const usable = Math.max(40, Math.min(width, height) - 2 * padding);
	return usable / (2 * radiusKm);
}
