import { errorMessage, isApiError } from '../api/client';
import { getOverview } from '../api/endpoints';
import type { NearbyOverview, SiteInfo } from '../api/types';
import { formatRetryAfter } from '../util/format';
import { RADIUS_STORAGE_KEY, radiusOptions, resolveRadius } from '../util/radius';
import { readStorage, writeStorage } from '../util/storage';
import { createApiSource } from './api-source';
import { scopeName, statesFromOverview, totalForScope } from './overview';
import { SCOPE_ALL, type OriginSource } from './source';
import { ownOriginFromAgs, type SortMode } from './types';
import { NetworkView, type ViewMode } from './view.svelte';

function initialMode(): ViewMode {
	// Unter 640 px Breite ist die Listenansicht der Standard (Projektplan, Abschnitt 5).
	if (typeof window !== 'undefined' && window.matchMedia('(max-width: 639px)').matches) return 'liste';
	return 'netz';
}

/** Liefert die Datenquelle für einen Umkreis; null bedeutet den Standard des Servers. */
export type SourceFactory = (radiusKm: number | null) => OriginSource;

/**
 * Gemeinsamer Zustand der Umkreis-Ansicht: Karte, Netz und Liste lesen dieselbe Instanz.
 *
 * Der Zustand lebt außerhalb der Seite. Wer ein Profil öffnet und zurückgeht, findet
 * deshalb dieselbe Auswahl, dieselben aufgeklappten Stufen, denselben Ausschnitt und
 * denselben Fokus wieder. Je Wohnort (und für "Alle im Umkreis") gibt es eine eigene
 * NetworkView; schon geladene Stufen werden nicht erneut abgefragt.
 *
 * Hier liegt auch der gewählte Umkreis (z. B. 20 oder 100 km). Übersicht, Herkunft und
 * Personen werden immer mit demselben Wert abgefragt. Ein Wechsel verwirft alle Netze,
 * weil sich die Zahlen ändern; Darstellung (Netz oder Liste) und Sortierung bleiben.
 */
export class UmkreisState {
	overview = $state.raw<NearbyOverview | null>(null);
	loading = $state(false);
	error = $state<string | null>(null);
	/** AGS des gewählten Wohnorts oder "all". */
	scope = $state<string>(SCOPE_ALL);
	mode = $state<ViewMode>(initialMode());
	sort = $state<SortMode>('distance');
	view = $state.raw<NetworkView | null>(null);
	/** Gewählter Umkreis in km; null, solange die Auswahl des Servers noch nicht bekannt ist. */
	radius = $state<number | null>(null);
	/** Wählbare Umkreise in km, aufsteigend. */
	options = $state.raw<number[]>([]);
	/** Zuletzt gezeigter Kartenausschnitt. */
	camera: { center: [number, number]; zoom: number } | null = null;

	private views = new Map<string, NetworkView>();
	private readonly sourceFor: SourceFactory;
	private source: OriginSource;
	private requestId = 0;

	constructor(sourceFor: SourceFactory = (radiusKm) => createApiSource(radiusKm ?? undefined)) {
		this.sourceFor = sourceFor;
		this.source = sourceFor(null);
	}

	get isEmpty(): boolean {
		return this.overview !== null && this.overview.total === 0;
	}

	/**
	 * Übernimmt Auswahl und Standardwert aus der Sitzung. Die im Browser gespeicherte Wahl
	 * gilt nur, wenn der Server sie anbietet.
	 */
	configure(site: Pick<SiteInfo, 'radius_km' | 'radius_options'>): void {
		const options = radiusOptions(site.radius_options, site.radius_km);
		this.options = options;
		if (this.radius === null || !options.includes(this.radius)) {
			this.radius = resolveRadius(readStorage(RADIUS_STORAGE_KEY), options, site.radius_km);
		}
	}

	/** Übernimmt eine fertige Übersicht (Entwicklungsansicht, Tests). */
	setOverview(overview: NearbyOverview): void {
		this.overview = overview;
		this.views.clear();
		this.source = this.sourceFor(this.radius);
		if (this.scope !== SCOPE_ALL && !overview.residences.some((r) => r.ags === this.scope)) this.scope = SCOPE_ALL;
		this.view = this.ensureView(this.scope);
	}

	/** Lädt die Übersicht einmal. Mit `force` werden alle Netze verworfen und neu aufgebaut. */
	async load(force: boolean = false): Promise<void> {
		if (this.loading && !force) return;
		if (this.overview && !force) return;
		const id = ++this.requestId;
		this.loading = true;
		this.error = null;
		try {
			const overview = await this.fetchOverview();
			// Eine inzwischen gestartete neuere Abfrage (anderer Umkreis) hat Vorrang.
			if (id !== this.requestId) return;
			this.setOverview(overview);
		} catch (e) {
			if (id !== this.requestId) return;
			this.error =
				isApiError(e) && e.isRateLimited
					? `Zu viele Abfragen in kurzer Zeit. Bitte versuche es ${formatRetryAfter(e.retryAfter)} noch einmal.`
					: errorMessage(e);
		} finally {
			if (id === this.requestId) this.loading = false;
		}
	}

	private async fetchOverview(): Promise<NearbyOverview> {
		try {
			return await getOverview(this.radius ?? undefined);
		} catch (e) {
			// Der Server bietet den gespeicherten Umkreis nicht mehr an: einmal mit seinem Standard laden.
			if (isApiError(e) && e.status === 422 && this.radius !== null) {
				const overview = await getOverview();
				this.radius = overview.radius_km;
				writeStorage(RADIUS_STORAGE_KEY, null);
				return overview;
			}
			throw e;
		}
	}

	/**
	 * Wechselt den Umkreis. Die Übersicht wird neu geladen und alle Netze beginnen von vorn
	 * (aufgeklappte Stufen, Auswahl, Personenliste), weil sich die Zahlen ändern.
	 */
	async setRadius(radiusKm: number): Promise<void> {
		if (radiusKm === this.radius) return;
		if (this.options.length > 0 && !this.options.includes(radiusKm)) return;
		this.radius = radiusKm;
		writeStorage(RADIUS_STORAGE_KEY, String(radiusKm));
		this.camera = null;
		await this.load(true);
	}

	private ensureView(scope: string): NetworkView | null {
		const overview = this.overview;
		if (!overview) return null;
		let view = this.views.get(scope);
		if (!view) {
			view = new NetworkView({
				scope,
				rootName: scopeName(overview, scope),
				rootCount: totalForScope(overview, scope),
				states: statesFromOverview(overview, scope),
				own: ownOriginFromAgs(overview.me.home?.ags),
				source: this.source,
				sort: this.sort
			});
			this.views.set(scope, view);
		} else if (view.sort !== this.sort) {
			view.setSort(this.sort);
		}
		return view;
	}

	/** Wählt einen Wohnort oder "all". */
	select(scope: string): void {
		this.scope = scope;
		this.view = this.ensureView(scope);
	}

	setSort(mode: SortMode): void {
		this.sort = mode;
		this.view?.setSort(mode);
	}

	/** Verwirft die geladenen Daten, z. B. nach der Abmeldung. Der gewählte Umkreis bleibt. */
	reset(): void {
		this.requestId += 1;
		this.loading = false;
		this.overview = null;
		this.view = null;
		this.views.clear();
		this.scope = SCOPE_ALL;
		this.error = null;
		this.camera = null;
	}
}

/** Die eine Instanz der echten Umkreis-Ansicht. */
export const umkreis = new UmkreisState();
