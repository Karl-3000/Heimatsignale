import { errorMessage, isApiError } from '../api/client';
import { getOverview } from '../api/endpoints';
import type { NearbyOverview } from '../api/types';
import { formatRetryAfter } from '../util/format';
import { apiSource } from './api-source';
import { scopeName, statesFromOverview, totalForScope } from './overview';
import { SCOPE_ALL, type OriginSource } from './source';
import { ownOriginFromAgs, type SortMode } from './types';
import { NetworkView, type ViewMode } from './view.svelte';

function initialMode(): ViewMode {
	// Unter 640 px Breite ist die Listenansicht der Standard (Projektplan, Abschnitt 5).
	if (typeof window !== 'undefined' && window.matchMedia('(max-width: 639px)').matches) return 'liste';
	return 'netz';
}

/**
 * Gemeinsamer Zustand der Umkreis-Ansicht: Karte, Netz und Liste lesen dieselbe Instanz.
 *
 * Der Zustand lebt außerhalb der Seite. Wer ein Profil öffnet und zurückgeht, findet
 * deshalb dieselbe Auswahl, dieselben aufgeklappten Stufen, denselben Ausschnitt und
 * denselben Fokus wieder. Je Wohnort (und für "Alle im Umkreis") gibt es eine eigene
 * NetworkView; schon geladene Stufen werden nicht erneut abgefragt.
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
	/** Zuletzt gezeigter Kartenausschnitt. */
	camera: { center: [number, number]; zoom: number } | null = null;

	private views = new Map<string, NetworkView>();
	private readonly source: OriginSource;

	constructor(source: OriginSource = apiSource) {
		this.source = source;
	}

	get isEmpty(): boolean {
		return this.overview !== null && this.overview.total === 0;
	}

	/** Übernimmt eine fertige Übersicht (Entwicklungsansicht, Tests). */
	setOverview(overview: NearbyOverview): void {
		this.overview = overview;
		this.views.clear();
		if (this.scope !== SCOPE_ALL && !overview.residences.some((r) => r.ags === this.scope)) this.scope = SCOPE_ALL;
		this.view = this.ensureView(this.scope);
	}

	/** Lädt die Übersicht einmal. Mit `force` werden alle Netze verworfen und neu aufgebaut. */
	async load(force: boolean = false): Promise<void> {
		if (this.loading) return;
		if (this.overview && !force) return;
		this.loading = true;
		this.error = null;
		try {
			this.setOverview(await getOverview());
		} catch (e) {
			this.error =
				isApiError(e) && e.isRateLimited
					? `Zu viele Abfragen in kurzer Zeit. Bitte versuche es ${formatRetryAfter(e.retryAfter)} noch einmal.`
					: errorMessage(e);
		} finally {
			this.loading = false;
		}
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

	/** Verwirft alles, z. B. nach der Abmeldung. */
	reset(): void {
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
