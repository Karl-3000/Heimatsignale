/**
 * Sammelknoten auf der Karte (Projektplan, Abschnitt 5, "Überlagerung").
 * Liegen zwei Wohnort-Knoten in der aktuellen Zoomstufe näher als 48 px, werden sie
 * zu einem Sammelknoten mit Summe zusammengefasst. Beim Hineinzoomen wachsen die
 * Pixelabstände, und die Knoten trennen sich wieder. Die Funktion ist rein und
 * deterministisch: gleiche Eingabe, gleiche Gruppen.
 */

export const CLUSTER_THRESHOLD_PX = 48;

export interface ScreenPoint {
	id: string;
	x: number;
	y: number;
	/** Anzahl der Personen; bestimmt den Schwerpunkt des Sammelknotens. */
	weight: number;
}

export interface Cluster {
	/** Kennungen der enthaltenen Wohnorte, alphabetisch. */
	ids: string[];
	x: number;
	y: number;
	weight: number;
}

/**
 * Agglomeratives Zusammenfassen: Solange zwei Gruppen näher als die Schwelle liegen,
 * wird das engste Paar vereinigt (Schwerpunkt nach Gewicht). Am Ende haben alle
 * Gruppen paarweise mindestens den Schwellenabstand.
 */
export function clusterPoints(points: readonly ScreenPoint[], threshold: number = CLUSTER_THRESHOLD_PX): Cluster[] {
	const clusters: Cluster[] = [...points]
		.sort((a, b) => a.id.localeCompare(b.id))
		.map((p) => ({ ids: [p.id], x: p.x, y: p.y, weight: Math.max(p.weight, 0) }));

	const limit = threshold * threshold;
	for (;;) {
		let best = limit;
		let bi = -1;
		let bj = -1;
		for (let i = 0; i < clusters.length; i++) {
			for (let j = i + 1; j < clusters.length; j++) {
				const dx = clusters[i].x - clusters[j].x;
				const dy = clusters[i].y - clusters[j].y;
				const d = dx * dx + dy * dy;
				if (d < best) {
					best = d;
					bi = i;
					bj = j;
				}
			}
		}
		if (bi < 0) break;
		const a = clusters[bi];
		const b = clusters[bj];
		const wa = a.weight > 0 ? a.weight : 1;
		const wb = b.weight > 0 ? b.weight : 1;
		const merged: Cluster = {
			ids: [...a.ids, ...b.ids].sort((x, y) => x.localeCompare(y)),
			x: (a.x * wa + b.x * wb) / (wa + wb),
			y: (a.y * wa + b.y * wb) / (wa + wb),
			weight: a.weight + b.weight
		};
		clusters.splice(bj, 1);
		clusters.splice(bi, 1, merged);
	}
	return clusters;
}

export const COMPACT_RADIUS = 20;
export const MINIATURE_MIN_RADIUS = 34;
export const MINIATURE_MAX_RADIUS = 92;
const MARKER_GAP = 4;

export interface SizedCluster extends Cluster {
	/** Radius der Darstellung in px. */
	radius: number;
	/** "compact": Knoten mit Zahl. "miniature": Stufe-1-Netz als Miniatur. */
	mode: 'compact' | 'miniature';
}

/** Wunschgröße einer Miniatur: wächst mit jeder Zoomstufe über dem kleinsten Zoom. */
export function desiredMiniatureRadius(zoom: number, minZoom: number): number {
	const r = 60 + (zoom - minZoom) * 22;
	return Math.max(MINIATURE_MIN_RADIUS, Math.min(MINIATURE_MAX_RADIUS, r));
}

/**
 * Weist jedem Knoten eine Größe zu, sodass sich Darstellungen nie überdecken:
 * Jeder bekommt höchstens den halben Abstand zum nächsten Nachbarn. Reicht das nicht
 * für eine Miniatur, schrumpft der Knoten auf einen Kreis mit Zahl. Weil nach dem
 * Zusammenfassen alle Abstände mindestens 48 px betragen, passt dieser Kreis immer.
 */
export function sizeClusters(clusters: readonly Cluster[], desiredRadius: number): SizedCluster[] {
	return clusters.map((c, i) => {
		let nearest = Number.POSITIVE_INFINITY;
		for (let j = 0; j < clusters.length; j++) {
			if (j === i) continue;
			nearest = Math.min(nearest, Math.hypot(c.x - clusters[j].x, c.y - clusters[j].y));
		}
		const available = nearest / 2 - MARKER_GAP / 2;
		const radius = Math.min(desiredRadius, available);
		if (radius >= MINIATURE_MIN_RADIUS) return { ...c, radius, mode: 'miniature' as const };
		return { ...c, radius: COMPACT_RADIUS, mode: 'compact' as const };
	});
}

/** Zählt Überdeckungen zwischen Darstellungen. Für Tests. */
export function countMarkerOverlaps(clusters: readonly SizedCluster[]): number {
	let n = 0;
	for (let i = 0; i < clusters.length; i++) {
		for (let j = i + 1; j < clusters.length; j++) {
			const d = Math.hypot(clusters[i].x - clusters[j].x, clusters[i].y - clusters[j].y);
			if (d < clusters[i].radius + clusters[j].radius - 0.001) n++;
		}
	}
	return n;
}
