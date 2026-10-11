import { errorMessage, isApiError } from '../api/client';
import { formatRetryAfter } from '../util/format';
import { NetworkCore, type NetworkCoreOptions, type PeopleState } from './core';
import type { KeyRow } from './keyboard';
import type { TreeRow, TreeSnapshot } from './model';
import type { Scene } from './scene';
import { ROOT_ID, type SortMode } from './types';

export type ViewMode = 'netz' | 'liste';

const PERSON_PREFIX = 'u|';

/** Kennung einer Personenzeile der Listenansicht. Sie enthält den Ort, zu dem die Person gehört. */
export function personRowId(placeNodeId: string, userId: string): string {
	return `${PERSON_PREFIX}${placeNodeId}|${userId}`;
}

export function moreRowId(placeNodeId: string): string {
	return `${PERSON_PREFIX}${placeNodeId}|+`;
}

function placeOfRow(id: string): string | null {
	if (!id.startsWith(PERSON_PREFIX)) return null;
	const end = id.indexOf('|', PERSON_PREFIX.length);
	return end > 0 ? id.slice(PERSON_PREFIX.length, end) : null;
}

/**
 * Gemeinsamer Zustand von Netz und Listenansicht eines Herkunftsnetzes.
 *
 * Beide Ansichten lesen dieselbe Instanz. Deshalb bleiben beim Umschalten Auswahl,
 * aufgeklappte Stufen und Tastaturfokus erhalten, und beide zeigen identische Daten.
 * Die Rechenarbeit liegt im frameworkfreien NetworkCore; hier werden nur dessen
 * Ergebnisse als reaktive Werte gespiegelt. Layout-Ergebnisse sind eingefroren
 * ($state.raw) und ändern sich ausschließlich durch die Methoden dieser Klasse.
 */
export class NetworkView {
	readonly core: NetworkCore;

	tree = $state.raw<TreeSnapshot>(undefined as unknown as TreeSnapshot);
	scene = $state.raw<Scene>(undefined as unknown as Scene);
	expanded = $state.raw<ReadonlySet<string>>(new Set());
	people = $state.raw<ReadonlyMap<string, PeopleState>>(new Map());
	/** Zuletzt neu platzierte Knoten; das Netz lässt sie aus dem Elternknoten herauswachsen. */
	added = $state.raw<readonly string[]>([]);
	/** Zählt jede Layoutänderung, damit Animationen genau einmal starten. */
	revision = $state(0);

	sort = $state<SortMode>('distance');
	/** Knoten mit Tastaturfokus (wandernder Tabindex); in beiden Ansichten derselbe. */
	focusedId = $state<string>(ROOT_ID);
	/** Ausgewählter Ort, dessen Personen gezeigt werden. */
	selectedId = $state<string | null>(null);
	loading = $state.raw<ReadonlySet<string>>(new Set());
	/** Fehlermeldung je Knoten, z. B. bei zu vielen Abfragen. */
	errors = $state.raw<ReadonlyMap<string, string>>(new Map());
	/** Letzte Ansage für Screenreader. */
	announcement = $state('');
	/** Zoomfaktor der Netzansicht. */
	zoom = $state(1);
	/** Zuletzt gezeigter Ausschnitt; bleibt erhalten, wenn man von einem Profil zurückkommt. */
	scroll: { left: number; top: number } | null = null;

	constructor(options: NetworkCoreOptions) {
		this.core = new NetworkCore(options);
		this.sort = this.core.sort;
		this.mirror();
	}

	get scope(): string {
		return this.core.scope;
	}

	get rows(): TreeRow[] {
		return this.tree.rows;
	}

	/** Zeilen in der Form, die die gemeinsame Tastaturlogik erwartet. */
	get keyRows(): KeyRow[] {
		return this.tree.rows.map((row) => ({
			id: row.node.id,
			depth: row.depth,
			parentId: row.node.parentId,
			expandable: row.node.level !== 'root',
			expanded: row.node.level !== 'root' && this.expanded.has(row.node.id)
		}));
	}

	isOpen(id: string): boolean {
		return this.expanded.has(id);
	}

	isLoading(id: string): boolean {
		return this.loading.has(id);
	}

	private mirror(): void {
		this.tree = this.core.tree;
		this.scene = this.core.scene;
		this.expanded = new Set(this.core.expanded);
		this.people = new Map(this.core.people);
		this.added = [...this.core.lastAdded];
		this.revision += 1;
	}

	private setLoading(id: string, on: boolean): void {
		const next = new Set(this.loading);
		if (on) next.add(id);
		else next.delete(id);
		this.loading = next;
	}

	private setError(id: string, message: string | null): void {
		const next = new Map(this.errors);
		if (message) next.set(id, message);
		else next.delete(id);
		this.errors = next;
	}

	private describeFailure(error: unknown): string {
		if (isApiError(error) && error.isRateLimited) {
			return `Zu viele Abfragen in kurzer Zeit. Bitte versuche es ${formatRetryAfter(error.retryAfter)} noch einmal.`;
		}
		return errorMessage(error);
	}

	/**
	 * Der fokussierte Knoten des Netzes. Liegt der Fokus in der Liste auf einer Person,
	 * ist es deren Heimatort; so findet man nach dem Umschalten dieselbe Stelle wieder.
	 */
	get focusedNodeId(): string {
		const id = placeOfRow(this.focusedId) ?? this.focusedId;
		return this.tree.byId.has(id) ? id : ROOT_ID;
	}

	focus(id: string): void {
		const node = placeOfRow(id) ?? id;
		if (this.tree.byId.has(node)) this.focusedId = id;
	}

	async expand(id: string): Promise<void> {
		const node = this.core.node(id);
		if (!node || node.level === 'root' || this.loading.has(id)) return;
		if (this.core.isOpen(id)) {
			if (node.level === 'place') this.selectedId = id;
			return;
		}
		this.setError(id, null);
		this.setLoading(id, true);
		try {
			await this.core.expand(id);
			this.mirror();
			if (node.level === 'place') {
				this.selectedId = id;
				const count = this.core.people.get(id)?.items.length ?? 0;
				this.announcement = `${node.name}: ${count === 1 ? '1 Person' : `${count} Personen`} geladen.`;
			} else {
				const kids = this.core.children.get(id)?.length ?? 0;
				const what = node.level === 'state' ? (kids === 1 ? 'Landkreis' : 'Landkreise') : kids === 1 ? 'Ort' : 'Orte';
				this.announcement = `${node.name} aufgeklappt, ${kids} ${what}.`;
			}
		} catch (error) {
			const message = this.describeFailure(error);
			this.setError(id, message);
			this.announcement = message;
		} finally {
			this.setLoading(id, false);
		}
	}

	collapse(id: string): void {
		const node = this.core.node(id);
		if (!node || !this.core.isOpen(id)) return;
		this.core.collapse(id);
		this.mirror();
		if (this.selectedId && !this.core.isOpen(this.selectedId)) this.selectedId = null;
		if (this.focusedNodeId === ROOT_ID && this.focusedId !== ROOT_ID) this.focusedId = id;
		else if (placeOfRow(this.focusedId) && !this.core.isOpen(this.focusedNodeId)) this.focusedId = this.focusedNodeId;
		this.announcement = `${node.name} zugeklappt.`;
	}

	/** Klick oder Enter: eine Ebene auf- oder zuklappen. */
	async toggle(id: string): Promise<void> {
		if (id === ROOT_ID) return;
		this.focus(id);
		if (this.core.isOpen(id)) this.collapse(id);
		else await this.expand(id);
	}

	async loadMorePeople(id: string): Promise<void> {
		if (this.loading.has(id)) return;
		this.setLoading(id, true);
		try {
			await this.core.loadMorePeople(id);
			this.people = new Map(this.core.people);
		} catch (error) {
			this.setError(id, this.describeFailure(error));
		} finally {
			this.setLoading(id, false);
		}
	}

	setSort(mode: SortMode): void {
		if (mode === this.sort) return;
		this.sort = mode;
		this.core.setSort(mode);
		this.mirror();
		this.announcement = mode === 'distance' ? 'Sortiert nach Nähe zu deinem Heimatort.' : 'Sortiert nach Anzahl.';
	}

	pathToRoot(id: string): string[] {
		return this.tree.pathToRoot(id);
	}
}
