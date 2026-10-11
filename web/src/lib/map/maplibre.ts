/**
 * Lädt MapLibre GL erst, wenn die Karte gebraucht wird (eigener Chunk).
 * Je nach Version und Bündelung liegt die Bibliothek im Standardexport oder direkt
 * im Modulobjekt; beide Fälle werden abgedeckt.
 */

export type MapLibre = typeof import('maplibre-gl');

export async function loadMapLibre(): Promise<MapLibre> {
	const mod: MapLibre = await import('maplibre-gl');
	const candidate = (mod as unknown as { default?: MapLibre }).default;
	return candidate && typeof candidate.Map === 'function' ? candidate : mod;
}
