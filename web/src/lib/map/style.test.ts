import { describe, expect, it } from 'vitest';
import { BASEMAP_SOURCE, CIRCLE_SOURCE, DARK_MAP_COLORS, LIGHT_MAP_COLORS, MASK_SOURCE, buildMapStyle, pmtilesUrl } from './style';

const base = { colors: LIGHT_MAP_COLORS, center: [7.09, 51.65] as [number, number], radiusKm: 20 };

type Layer = { id: string; type: string; source?: string; layout?: Record<string, unknown> };
type Style = { version: number; sources: Record<string, { url?: string }>; layers: Layer[]; glyphs?: string };

describe('buildMapStyle', () => {
	it('funktioniert ohne Kacheln: nur Hintergrund, Maske und Kreis, keine fremden Adressen', () => {
		const style = buildMapStyle(base) as unknown as Style;
		expect(style.version).toBe(8);
		expect(Object.keys(style.sources).sort()).toEqual([MASK_SOURCE, CIRCLE_SOURCE].sort());
		expect(style.layers.map((l) => l.id)).toEqual(['maske', 'umkreis-schein', 'umkreis-linie']);
		expect(style.glyphs).toBeUndefined();
		expect(JSON.stringify(style).includes('http')).toBe(false);
	});

	it('bindet PMTiles über das eigene Protokoll ein und zeichnet keine POI-Symbole', () => {
		const style = buildMapStyle({ ...base, tilesUrl: '/tiles/de.pmtiles' }, 'https://beispiel.example') as unknown as Style;
		expect(style.sources[BASEMAP_SOURCE].url).toBe('pmtiles://https://beispiel.example/tiles/de.pmtiles');
		expect(style.layers.some((l) => l.type === 'symbol')).toBe(false);
		expect(style.glyphs).toBeUndefined();
		// Maske und Kreis liegen immer über der Grundkarte.
		expect(style.layers.slice(-3).map((l) => l.id)).toEqual(['maske', 'umkreis-schein', 'umkreis-linie']);
		expect(style.layers[0].id).toBe('hintergrund');
	});

	it('zeigt Ortsnamen nur mit Glyphen-URL', () => {
		const style = buildMapStyle({ ...base, tilesUrl: '/tiles/de.pmtiles', glyphsUrl: '/fonts/{fontstack}/{range}.pbf' }, 'https://beispiel.example') as unknown as Style;
		expect(style.glyphs).toBe('/fonts/{fontstack}/{range}.pbf');
		expect(style.layers.filter((l) => l.type === 'symbol').map((l) => l.id)).toEqual(['ortsnamen']);
		const ohneKacheln = buildMapStyle({ ...base, glyphsUrl: '/fonts/{fontstack}/{range}.pbf' }) as unknown as Style;
		expect(ohneKacheln.glyphs).toBeUndefined();
	});

	it('ist in beiden Themen eine Nachtkarte: gleiche Schlüssel, nur der Bühnengrund weicht ab', () => {
		expect(Object.keys(DARK_MAP_COLORS).sort()).toEqual(Object.keys(LIGHT_MAP_COLORS).sort());
		expect(DARK_MAP_COLORS.background).not.toBe(LIGHT_MAP_COLORS.background);
	});
});

describe('pmtilesUrl', () => {
	it('lässt absolute Adressen unverändert und ergänzt relative um die Origin', () => {
		expect(pmtilesUrl('https://a.example/x.pmtiles', 'https://b.example')).toBe('pmtiles://https://a.example/x.pmtiles');
		expect(pmtilesUrl('tiles/x.pmtiles', 'https://b.example/')).toBe('pmtiles://https://b.example/tiles/x.pmtiles');
	});
});
