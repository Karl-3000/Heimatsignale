/** Wahl des Umkreises (z. B. 20 oder 100 km). Frei von Framework-Code. */

export const RADIUS_STORAGE_KEY = 'hs:umkreis';

/** Bereinigte, aufsteigend sortierte Auswahl. Der Standardwert gehört immer dazu. */
export function radiusOptions(options: readonly number[] | null | undefined, fallback: number): number[] {
	const set = new Set<number>();
	for (const value of options ?? []) {
		if (typeof value === 'number' && Number.isFinite(value) && value > 0) set.add(value);
	}
	if (Number.isFinite(fallback) && fallback > 0) set.add(fallback);
	return [...set].sort((a, b) => a - b);
}

/**
 * Der zu verwendende Umkreis: die gespeicherte Wahl, wenn der Server sie (noch) anbietet,
 * sonst der Standardwert. So führt ein veralteter Speicherwert nie zu einer ungültigen Anfrage.
 */
export function resolveRadius(stored: string | number | null | undefined, options: readonly number[], fallback: number): number {
	const value = typeof stored === 'number' ? stored : stored ? Number(stored) : Number.NaN;
	if (Number.isFinite(value) && options.includes(value)) return value;
	return fallback;
}

/** Der größte angebotene Umkreis: So weit reichen Profile, Anfragen, Blockieren und Melden. */
export function largestRadius(options: readonly number[], fallback: number): number {
	return options.length > 0 ? Math.max(...options) : fallback;
}
