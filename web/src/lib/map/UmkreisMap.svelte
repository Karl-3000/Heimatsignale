<script lang="ts">
	import { onMount } from 'svelte';
	import type { Map as MapLibreMap, StyleSpecification } from 'maplibre-gl';
	import Plus from '@lucide/svelte/icons/plus';
	import Minus from '@lucide/svelte/icons/minus';
	import Scan from '@lucide/svelte/icons/scan';
	import 'maplibre-gl/dist/maplibre-gl.css';
	import Icon from '$lib/ui/Icon.svelte';
	import type { NearbyOverview, ResidenceOverview } from '$lib/api/types';
	import { shortenName } from '$lib/network/labels';
	import { SCOPE_ALL } from '$lib/network/source';
	import { stateName } from '$lib/network/states';
	import { personen } from '$lib/util/format';
	import { theme } from '$lib/util/theme.svelte';
	import { clusterPoints, desiredMiniatureRadius, sizeClusters, type ScreenPoint, type SizedCluster } from './cluster';
	import { circleBounds, clampToCircle, fitPxPerKm, haversineKm, localProject, type LngLat } from './geo';
	import { mergeStates, selectMiniatureStates, type MiniatureSelection } from './miniature';
	import { loadMapLibre } from './maplibre';
	import Miniature from './Miniature.svelte';
	import { DARK_MAP_COLORS, LIGHT_MAP_COLORS, buildMapStyle, readMapColors } from './style';

	/**
	 * Umkreiskarte. Der eigene Wohnort liegt in der Mitte; gezeigt wird nie mehr als der
	 * gewählte Umkreis (overview.radius_km, z. B. 20 oder 100 km). Jede Wohnort-Gemeinde ist EIN Knoten mit der Miniatur ihres
	 * Stufe-1-Netzes, nie eine einzelne Person. Die Knoten sind HTML-Elemente über der
	 * Karte: Ihre Position kommt bei jeder Kartenbewegung aus der Projektion, und aus den
	 * Pixelabständen entstehen die Sammelknoten (unter 48 px).
	 */
	interface Props {
		overview: NearbyOverview;
		/** Gewählter Wohnort (AGS) oder "all". */
		scope: string;
		tilesUrl?: string;
		glyphsUrl?: string;
		/** Merkt sich den Ausschnitt über das Verlassen der Seite hinweg. */
		camera?: { center: [number, number]; zoom: number } | null;
		onselect: (scope: string) => void;
		oncamera?: (camera: { center: [number, number]; zoom: number }) => void;
	}

	let { overview, scope, tilesUrl = '', glyphsUrl = '', camera = null, onselect, oncamera }: Props = $props();

	const PADDING = 28;
	/** Zoomstufen über dem kleinsten Zoom bei 20 km. Größere Umkreise bekommen entsprechend mehr. */
	const BASE_ZOOM_RANGE = 4;

	let container = $state<HTMLDivElement | null>(null);
	let map: MapLibreMap | null = null;
	let ready = $state(false);
	/** true, wenn MapLibre nicht starten konnte (z. B. kein WebGL). Dann gilt die Ersatzdarstellung. */
	let fallback = $state(false);
	/** Zählt Kartenbewegungen; die Knotenpositionen hängen davon ab. */
	let frame = $state(0);
	let zoom = $state(0);
	let minZoom = $state(0);
	let size = $state({ width: 0, height: 0 });

	const center = $derived<LngLat>([overview.me.residence.lon, overview.me.residence.lat]);
	const radiusKm = $derived(overview.radius_km || 20);
	// Der größte Zoom bleibt bei jedem Umkreis auf Gemeinde-Niveau: 100 km erlauben gut zwei Stufen mehr.
	const zoomRange = $derived(BASE_ZOOM_RANGE + Math.max(0, Math.log2(radiusKm / 20)));
	const ownState = $derived(overview.me.home?.state_code ?? null);
	const byAgs = $derived(new Map(overview.residences.map((r) => [r.ags, r])));

	function project(point: LngLat): { x: number; y: number } {
		if (map && ready && !fallback) return map.project(point);
		return localProject(point, center, fitPxPerKm(size.width, size.height, radiusKm, PADDING), size.width, size.height);
	}

	interface Marker {
		key: string;
		cluster: SizedCluster;
		residences: ResidenceOverview[];
		selection: MiniatureSelection;
		label: string;
		caption: string | null;
		selected: boolean;
	}

	const markers = $derived.by<Marker[]>(() => {
		// frame und size gehören zu den Abhängigkeiten: Bei jeder Kartenbewegung wird neu projiziert.
		void frame;
		if (size.width === 0 || (!ready && !fallback)) return [];
		const points: ScreenPoint[] = overview.residences.map((r) => {
			const p = project([r.lon, r.lat]);
			return { id: r.ags, x: p.x, y: p.y, weight: r.total };
		});
		const desired = desiredMiniatureRadius(zoom, minZoom);
		return sizeClusters(clusterPoints(points), desired).map((cluster) => {
			const residences = cluster.ids.map((id) => byAgs.get(id)).filter((r): r is ResidenceOverview => r !== undefined);
			const states = residences.length === 1 ? residences[0].states : mergeStates(residences.map((r) => r.states));
			const selection = selectMiniatureStates(states, ownState);
			const names = residences.map((r) => r.name);
			const single = residences.length === 1;
			const origins = selection.shown.map((s) => `${stateName(s.stateCode)} ${s.count}${s.own ? ' (deine Herkunft)' : ''}`).join(', ');
			const rest = selection.restStates > 0 ? `, ${selection.restStates} weitere Bundesländer` : '';
			const label = single
				? `${names[0]}: ${personen(cluster.weight)}. Herkunft: ${origins}${rest}. Herkunftsnetz öffnen.`
				: `${names.length} Wohnorte zusammengefasst (${names.join(', ')}): ${personen(cluster.weight)}. Hineinzoomen, um sie zu trennen.`;
			return {
				key: cluster.ids.join('+'),
				cluster,
				residences,
				selection,
				label,
				caption: single && cluster.mode === 'miniature' && cluster.radius >= 60 ? shortenName(names[0], 14) : null,
				selected: single && scope === residences[0].ags
			};
		});
	});

	const ownPoint = $derived.by(() => {
		void frame;
		if (size.width === 0 || (!ready && !fallback)) return null;
		return project(center);
	});

	/** Kreis in der Ersatzdarstellung (ohne MapLibre). */
	const fallbackCircle = $derived(fitPxPerKm(size.width, size.height, radiusKm, PADDING) * radiusKm);

	function style(): StyleSpecification {
		const colors = readMapColors(theme.effective === 'dark' ? DARK_MAP_COLORS : LIGHT_MAP_COLORS);
		const origin = typeof window !== 'undefined' ? window.location.origin : '';
		return buildMapStyle({ colors, center, radiusKm, tilesUrl, glyphsUrl }, origin) as unknown as StyleSpecification;
	}

	/** Kleinster Zoom: Der Kreis des Umkreises passt gerade vollständig in die Fläche. Weiter heraus geht es nicht. */
	function applyZoomLimits(jump: boolean): void {
		if (!map) return;
		map.setMinZoom(null);
		const fit = map.cameraForBounds(circleBounds(center, radiusKm), { padding: PADDING });
		const min = fit?.zoom ?? 9;
		minZoom = min;
		map.setMaxZoom(min + zoomRange);
		map.setMinZoom(min);
		if (jump) map.jumpTo({ center, zoom: min });
		else if (map.getZoom() < min) map.jumpTo({ zoom: min });
		zoom = map.getZoom();
	}

	function handleMove(): void {
		if (!map) return;
		zoom = map.getZoom();
		frame += 1;
	}

	function handleMoveEnd(): void {
		if (!map) return;
		const c = map.getCenter();
		const current: LngLat = [c.lng, c.lat];
		// Der Kartenmittelpunkt bleibt im Umkreis; so wandert der Ausschnitt nie aus dem Radius heraus.
		if (haversineKm(current, center) > radiusKm) {
			map.easeTo({ center: clampToCircle(current, center, radiusKm * 0.98), duration: 200 });
			return;
		}
		oncamera?.({ center: current, zoom: map.getZoom() });
	}

	function activate(marker: Marker): void {
		if (marker.residences.length === 1) {
			onselect(marker.residences[0].ags);
			return;
		}
		// Sammelknoten: so weit hineinzoomen, bis sich die Wohnorte trennen.
		if (!map) {
			onselect(SCOPE_ALL);
			return;
		}
		let west = Infinity;
		let south = Infinity;
		let east = -Infinity;
		let north = -Infinity;
		for (const r of marker.residences) {
			west = Math.min(west, r.lon);
			east = Math.max(east, r.lon);
			south = Math.min(south, r.lat);
			north = Math.max(north, r.lat);
		}
		const pad = Math.max(60, Math.min(size.width, size.height) / 4);
		map.fitBounds(
			[
				[west, south],
				[east, north]
			],
			{ padding: pad, maxZoom: minZoom + zoomRange, duration: reducedMotion() ? 0 : 300 }
		);
	}

	function reducedMotion(): boolean {
		return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
	}

	function zoomBy(delta: number): void {
		if (!map) return;
		const options = { duration: reducedMotion() ? 0 : 200 };
		if (delta > 0) map.zoomIn(options);
		else map.zoomOut(options);
	}

	function showAll(): void {
		map?.easeTo({ center, zoom: minZoom, duration: reducedMotion() ? 0 : 300 });
	}

	onMount(() => {
		const el = container;
		if (!el) return;
		let disposed = false;
		let protocolAdded = false;
		let removeProtocol: ((name: string) => void) | null = null;

		// Gemessen wird der Rahmen, nicht die Zeichenfläche: Die ist in der Ersatzdarstellung ausgeblendet.
		const frameEl = el.parentElement ?? el;
		size = { width: frameEl.clientWidth, height: frameEl.clientHeight };
		const observer = new ResizeObserver(() => {
			size = { width: frameEl.clientWidth, height: frameEl.clientHeight };
			if (map && ready) {
				map.resize();
				applyZoomLimits(false);
			}
			frame += 1;
		});
		observer.observe(frameEl);

		void (async () => {
			try {
				const maplibre = await loadMapLibre();
				if (disposed) return;
				if (tilesUrl) {
					const { Protocol } = await import('pmtiles');
					if (disposed) return;
					const protocol = new Protocol();
					maplibre.addProtocol('pmtiles', protocol.tile);
					protocolAdded = true;
					removeProtocol = maplibre.removeProtocol;
				}
				const instance = new maplibre.Map({
					container: el,
					style: style(),
					center,
					zoom: 9,
					attributionControl: false,
					dragRotate: false,
					pitchWithRotate: false,
					touchPitch: false,
					renderWorldCopies: false,
					fadeDuration: 0
				});
				map = instance;
				instance.touchZoomRotate.disableRotation();
				instance.keyboard.disableRotation();
				instance.getCanvas().setAttribute('aria-label', 'Karte deines Umkreises. Mit den Pfeiltasten verschieben, mit Plus und Minus zoomen.');
				instance.on('load', () => {
					if (disposed) return;
					applyZoomLimits(true);
					if (camera && camera.zoom >= minZoom) instance.jumpTo({ center: camera.center, zoom: camera.zoom });
					zoom = instance.getZoom();
					ready = true;
					frame += 1;
				});
				instance.on('move', handleMove);
				instance.on('moveend', handleMoveEnd);
			} catch {
				// Kein WebGL oder Bibliothek nicht ladbar: schematische Ersatzdarstellung zeigen.
				fallback = true;
			}
		})();

		return () => {
			disposed = true;
			observer.disconnect();
			map?.remove();
			map = null;
			if (protocolAdded) removeProtocol?.('pmtiles');
		};
	});

	// Wechsel des Umkreises: Kreis und Maske neu zeichnen, Zoomgrenzen neu setzen, ganz herauszoomen.
	let appliedRadius = 0;
	$effect(() => {
		const current = radiusKm;
		if (!ready || !map) return;
		if (appliedRadius === 0) {
			appliedRadius = current;
			return;
		}
		if (current === appliedRadius) return;
		appliedRadius = current;
		map.setStyle(style());
		applyZoomLimits(true);
		frame += 1;
	});

	// Themenwechsel: Stil mit den Farben des neuen Themas neu setzen.
	let appliedTheme = '';
	$effect(() => {
		const current = `${theme.choice}|${theme.effective}`;
		if (!ready || !map) return;
		if (appliedTheme === '') {
			appliedTheme = current;
			return;
		}
		if (current === appliedTheme) return;
		appliedTheme = current;
		// Kurz warten, bis das Attribut am Dokument gesetzt ist und die Tokens neu gelten.
		const target = map;
		const timer = setTimeout(() => target.setStyle(style()), 0);
		return () => clearTimeout(timer);
	});
</script>

<div class="hs-stage map" data-testid="umkreis-map" data-ready={ready || fallback ? 'true' : 'false'}>
	<div class="canvas" bind:this={container} class:fallback></div>

	{#if fallback && size.width > 0}
		<div class="fallback-circle" style:width="{fallbackCircle * 2}px" style:height="{fallbackCircle * 2}px" aria-hidden="true"></div>
	{/if}

	<div class="overlay">
		{#if ownPoint}
			<div class="own" style:transform="translate({ownPoint.x}px, {ownPoint.y}px)" aria-hidden="true">
				<span class="own-dot"></span>
			</div>
		{/if}
		{#each markers as marker (marker.key)}
			<button
				type="button"
				class="marker marker-{marker.cluster.mode}"
				class:selected={marker.selected}
				class:multi={marker.residences.length > 1}
				style:transform="translate({marker.cluster.x}px, {marker.cluster.y}px) translate(-50%, -50%)"
				style:width="{marker.cluster.radius * 2}px"
				style:height="{marker.cluster.radius * 2}px"
				aria-label={marker.label}
				aria-pressed={marker.residences.length === 1 ? (marker.selected ? 'true' : 'false') : undefined}
				title={marker.residences.map((r) => r.name).join(', ')}
				data-testid={marker.residences.length > 1 ? 'map-cluster' : 'map-node'}
				data-ags={marker.cluster.ids.join(' ')}
				data-mode={marker.cluster.mode}
				onclick={() => activate(marker)}
			>
				{#if marker.cluster.mode === 'miniature'}
					<Miniature selection={marker.selection} radius={marker.cluster.radius} caption={marker.caption} />
				{:else}
					<span class="number hs-num">{marker.cluster.weight}</span>
				{/if}
			</button>
		{/each}
	</div>

	{#if !fallback}
		<div class="controls">
			<button type="button" onclick={() => zoomBy(-1)} disabled={!ready || zoom <= minZoom + 0.01} aria-label="Karte verkleinern" data-testid="map-zoom-out">
				<Icon icon={Minus} size={18} />
			</button>
			<button type="button" onclick={() => zoomBy(1)} disabled={!ready || zoom >= minZoom + zoomRange - 0.01} aria-label="Karte vergrößern" data-testid="map-zoom-in">
				<Icon icon={Plus} size={18} />
			</button>
			<button type="button" onclick={showAll} disabled={!ready} aria-label="Ganzen Umkreis zeigen" data-testid="map-reset">
				<Icon icon={Scan} size={18} />
			</button>
		</div>
	{/if}

	{#if tilesUrl && !fallback}
		<p class="attribution">
			Kartendaten © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap-Mitwirkende</a>
		</p>
	{/if}
</div>

<style>
	.map {
		height: clamp(21rem, 58dvh, 36rem);
	}

	.canvas {
		position: absolute;
		inset: 0;
	}

	.canvas.fallback {
		display: none;
	}

	.canvas :global(.maplibregl-canvas:focus-visible) {
		outline: 2px solid var(--hs-stage-accent);
		outline-offset: -4px;
		border-radius: var(--hs-radius-stage);
	}

	/* Ersatzdarstellung ohne WebGL: derselbe Lichtring, außen dunkler. */
	.fallback-circle {
		position: absolute;
		left: 50%;
		top: 50%;
		transform: translate(-50%, -50%);
		border: 1.25px dashed color-mix(in srgb, var(--hs-stage-ink) 75%, transparent);
		border-radius: 50%;
		box-shadow:
			0 0 0 100vmax color-mix(in srgb, var(--hs-stage-deep) 60%, transparent),
			0 0 18px 2px color-mix(in srgb, var(--hs-stage-ink) 22%, transparent);
	}

	.overlay {
		position: absolute;
		inset: 0;
		pointer-events: none;
		overflow: hidden;
	}

	.own {
		position: absolute;
		left: 0;
		top: 0;
		width: 0;
		height: 0;
	}

	.own-dot {
		position: absolute;
		left: -5px;
		top: -5px;
		width: 10px;
		height: 10px;
		border: 1.5px solid var(--hs-stage-ink);
		border-radius: 50%;
	}

	.marker {
		position: absolute;
		left: 0;
		top: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 0;
		border: 0;
		border-radius: 50%;
		background: transparent;
		color: var(--hs-stage-ink);
		cursor: pointer;
		pointer-events: auto;
		/* Größenwechsel beim Zoomen weich, die Position selbst folgt der Karte ohne Verzögerung. */
		transition:
			width var(--hs-duration-fast) var(--hs-ease-standard),
			height var(--hs-duration-fast) var(--hs-ease-standard),
			box-shadow var(--hs-duration-fast) var(--hs-ease-standard);
	}

	/* Ein Licht mit Zahl, wie die Knoten im Netz. */
	.marker-compact {
		background: var(--hs-stage-ink);
		color: var(--hs-stage-on-light);
		box-shadow: 0 0 0 5px color-mix(in srgb, var(--hs-stage-ink) 14%, transparent);
	}

	/* Sammelknoten: ein zweiter Ring zeigt, dass hier mehrere Gemeinden zusammengefasst sind. */
	.marker-compact.multi {
		box-shadow:
			0 0 0 3px var(--hs-stage-bg),
			0 0 0 4.5px var(--hs-stage-ink),
			0 0 0 10px color-mix(in srgb, var(--hs-stage-ink) 12%, transparent);
	}

	.marker:hover {
		box-shadow: 0 0 0 7px color-mix(in srgb, var(--hs-stage-ink) 22%, transparent);
	}

	.marker.selected {
		box-shadow:
			0 0 0 2px var(--hs-stage-bg),
			0 0 0 4.5px var(--hs-stage-accent);
	}

	.marker:focus-visible {
		outline: 2.5px solid var(--hs-stage-accent);
		outline-offset: 4px;
		border-radius: 50%;
	}

	.number {
		font-size: var(--hs-text-sm);
		font-weight: var(--hs-weight-strong);
		line-height: 1;
	}

	.controls {
		position: absolute;
		right: var(--hs-space-4);
		bottom: var(--hs-space-4);
		display: flex;
		padding: 3px;
		border-radius: var(--hs-radius-full);
		background: var(--hs-stage-glass);
		box-shadow: inset 0 0 0 1px var(--hs-stage-line);
		backdrop-filter: blur(12px);
		-webkit-backdrop-filter: blur(12px);
	}

	.controls button {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 2.5rem;
		height: 2.5rem;
		border: 0;
		border-radius: 50%;
		background: transparent;
		color: var(--hs-stage-ink);
		cursor: pointer;
	}

	.controls button:hover:not(:disabled) {
		background: var(--hs-stage-glass-strong);
	}

	.controls button:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.controls button:focus-visible {
		outline: 2px solid var(--hs-stage-accent);
		outline-offset: 1px;
		border-radius: 50%;
	}

	.attribution {
		position: absolute;
		left: var(--hs-space-4);
		bottom: var(--hs-space-4);
		font-size: var(--hs-text-xs);
		color: var(--hs-stage-muted);
	}

	.attribution a {
		color: var(--hs-stage-muted);
	}
</style>
