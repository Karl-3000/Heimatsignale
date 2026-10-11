/**
 * Eigener Kartenstil für MapLibre: eine Nachtkarte in Tinte-Tönen, in beiden Themen.
 * Die Karte ist Teil der Bühne; die Lichter (Wohnort-Knoten) bleiben der Vordergrund.
 * Land ist etwas heller als Wasser, Straßen sind dünn und blass, es gibt keine POI-Symbole.
 * Grundlage ist das Protomaps-Basemap-Schema v4 (Ebenen earth, water, landuse,
 * roads, boundaries, places). Ohne Kachel-URL besteht der Stil nur aus dem leuchtenden
 * Umkreis-Kreis und der Abdunklung außerhalb; der Grund bleibt durchsichtig, sodass die
 * Bühne darunter zu sehen ist. Die Karte funktioniert dann ohne jede Netzanfrage.
 * Ortsnamen auf der Grundkarte gibt es nur, wenn eine Glyphen-URL gesetzt ist.
 */

import { circleRing, maskPolygon, type LngLat } from './geo';

export interface MapColors {
	background: string;
	land: string;
	water: string;
	green: string;
	road: string;
	boundary: string;
	label: string;
	halo: string;
	circle: string;
	mask: string;
}

/** Feste Farben für Umgebungen ohne DOM und als Rückfall. Entsprechen tokens.css. */
export const LIGHT_MAP_COLORS: MapColors = {
	background: '#0a1030',
	land: '#101842',
	water: '#070b24',
	green: '#121d48',
	road: '#2b3568',
	boundary: '#4b5688',
	label: '#a9b3dc',
	halo: '#0a1030',
	circle: '#e9edff',
	mask: '#060a20'
};

/** Im dunklen Thema ist die Bühne eine Spur heller als die Seite. */
export const DARK_MAP_COLORS: MapColors = {
	...LIGHT_MAP_COLORS,
	background: '#0c1233',
	halo: '#0c1233'
};

/** Liest die Kartenfarben aus den Design-Tokens des gerade wirksamen Themas. */
export function readMapColors(fallback: MapColors = LIGHT_MAP_COLORS): MapColors {
	if (typeof document === 'undefined') return fallback;
	const style = getComputedStyle(document.documentElement);
	const token = (name: string, otherwise: string): string => style.getPropertyValue(name).trim() || otherwise;
	return {
		background: token('--hs-stage-bg', fallback.background),
		land: token('--hs-map-land', fallback.land),
		water: token('--hs-map-water', fallback.water),
		green: token('--hs-map-green', fallback.green),
		road: token('--hs-map-road', fallback.road),
		boundary: token('--hs-map-boundary', fallback.boundary),
		label: token('--hs-map-label', fallback.label),
		halo: token('--hs-stage-bg', fallback.halo),
		circle: token('--hs-mondweiss', fallback.circle),
		mask: token('--hs-stage-deep', fallback.mask)
	};
}

export interface StyleOptions {
	colors: MapColors;
	center: LngLat;
	radiusKm: number;
	/** Absolute oder relative URL der PMTiles-Datei; leer für eine Karte ohne Kacheln. */
	tilesUrl?: string;
	/** Glyphen-URL mit {fontstack} und {range}; leer für eine Karte ohne Ortsnamen. */
	glyphsUrl?: string;
}

export const BASEMAP_SOURCE = 'grundkarte';
export const CIRCLE_SOURCE = 'umkreis';
export const MASK_SOURCE = 'maske';

type Json = Record<string, unknown>;

/** Macht aus einer relativen URL eine absolute, wie sie das pmtiles-Protokoll erwartet. */
export function pmtilesUrl(tilesUrl: string, origin: string): string {
	const absolute = /^https?:\/\//i.test(tilesUrl) ? tilesUrl : origin.replace(/\/$/, '') + (tilesUrl.startsWith('/') ? tilesUrl : `/${tilesUrl}`);
	return `pmtiles://${absolute}`;
}

/**
 * Baut den vollständigen Stil. Das Ergebnis entspricht der MapLibre-Style-Spezifikation
 * (Version 8) und wird beim Aufrufer als StyleSpecification übergeben.
 */
export function buildMapStyle(options: StyleOptions, origin: string = ''): Json {
	const c = options.colors;
	const hasTiles = Boolean(options.tilesUrl);
	const hasGlyphs = hasTiles && Boolean(options.glyphsUrl);

	const sources: Record<string, Json> = {
		[CIRCLE_SOURCE]: {
			type: 'geojson',
			data: {
				type: 'Feature',
				properties: {},
				geometry: { type: 'LineString', coordinates: circleRing(options.center, options.radiusKm) }
			}
		},
		[MASK_SOURCE]: {
			type: 'geojson',
			data: {
				type: 'Feature',
				properties: {},
				geometry: { type: 'Polygon', coordinates: maskPolygon(options.center, options.radiusKm) }
			}
		}
	};

	// Ohne Kacheln gibt es keinen Hintergrund: Die Zeichenfläche bleibt durchsichtig und zeigt die Bühne.
	const layers: Json[] = hasTiles ? [{ id: 'hintergrund', type: 'background', paint: { 'background-color': c.water } }] : [];

	if (hasTiles) {
		sources[BASEMAP_SOURCE] = {
			type: 'vector',
			url: pmtilesUrl(options.tilesUrl as string, origin),
			attribution: '© OpenStreetMap-Mitwirkende'
		};
		layers.push(
			{ id: 'land', type: 'fill', source: BASEMAP_SOURCE, 'source-layer': 'earth', paint: { 'fill-color': c.land } },
			{
				id: 'gruen',
				type: 'fill',
				source: BASEMAP_SOURCE,
				'source-layer': 'landuse',
				filter: ['in', ['get', 'kind'], ['literal', ['park', 'forest', 'wood', 'nature_reserve', 'national_park', 'protected_area', 'grassland', 'meadow', 'cemetery']]],
				paint: { 'fill-color': c.green, 'fill-opacity': 0.9 }
			},
			{ id: 'wasser', type: 'fill', source: BASEMAP_SOURCE, 'source-layer': 'water', filter: ['==', ['geometry-type'], 'Polygon'], paint: { 'fill-color': c.water } },
			{
				id: 'strassen-klein',
				type: 'line',
				source: BASEMAP_SOURCE,
				'source-layer': 'roads',
				minzoom: 11,
				filter: ['==', ['get', 'kind'], 'minor_road'],
				layout: { 'line-cap': 'round', 'line-join': 'round' },
				paint: { 'line-color': c.road, 'line-width': ['interpolate', ['linear'], ['zoom'], 11, 0.4, 14, 1.6] }
			},
			{
				id: 'strassen-gross',
				type: 'line',
				source: BASEMAP_SOURCE,
				'source-layer': 'roads',
				filter: ['in', ['get', 'kind'], ['literal', ['highway', 'major_road']]],
				layout: { 'line-cap': 'round', 'line-join': 'round' },
				paint: { 'line-color': c.road, 'line-width': ['interpolate', ['linear'], ['zoom'], 7, 0.6, 10, 1.4, 14, 3.2] }
			},
			{
				id: 'grenzen',
				type: 'line',
				source: BASEMAP_SOURCE,
				'source-layer': 'boundaries',
				paint: { 'line-color': c.boundary, 'line-width': 0.7, 'line-dasharray': [3, 2], 'line-opacity': 0.6 }
			}
		);
		if (hasGlyphs) {
			layers.push({
				id: 'ortsnamen',
				type: 'symbol',
				source: BASEMAP_SOURCE,
				'source-layer': 'places',
				filter: ['==', ['get', 'kind'], 'locality'],
				layout: {
					'text-field': ['coalesce', ['get', 'name:de'], ['get', 'name']],
					'text-font': ['Noto Sans Regular'],
					'text-size': ['interpolate', ['linear'], ['zoom'], 8, 10, 13, 13],
					'text-max-width': 7
				},
				paint: { 'text-color': c.label, 'text-halo-color': c.halo, 'text-halo-width': 1.2 }
			});
		}
	}

	// Außerhalb des Umkreises wird es dunkler: Gezeigt wird nie mehr als der gewählte Umkreis.
	// Der Kreis selbst ist ein weicher Lichtring mit einer feinen gestrichelten Linie darin.
	layers.push(
		{ id: 'maske', type: 'fill', source: MASK_SOURCE, paint: { 'fill-color': c.mask, 'fill-opacity': hasTiles ? 0.82 : 0.6 } },
		{
			id: 'umkreis-schein',
			type: 'line',
			source: CIRCLE_SOURCE,
			paint: { 'line-color': c.circle, 'line-width': 9, 'line-blur': 9, 'line-opacity': 0.22 }
		},
		{
			id: 'umkreis-linie',
			type: 'line',
			source: CIRCLE_SOURCE,
			paint: { 'line-color': c.circle, 'line-width': 1.25, 'line-dasharray': [2, 3], 'line-opacity': 0.75 }
		}
	);

	const style: Json = { version: 8, name: 'Heimatsignale', sources, layers };
	if (hasGlyphs) style.glyphs = options.glyphsUrl;
	return style;
}
