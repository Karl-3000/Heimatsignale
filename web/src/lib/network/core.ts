/**
 * Zustand und Abläufe eines Herkunftsnetzes, frei von Framework-Code.
 * Die Svelte-Schicht (view.svelte.ts) spiegelt nur, was hier berechnet wird.
 * Jede Änderung endet in `recompute()`: Baum bauen, Layout bis zur Ruhe rechnen
 * und einfrieren, Zeichenanweisung erzeugen.
 */

import type { PublicUser } from '../api/types';
import { NetworkLayout } from './layout';
import { buildTree, descendantIds, type TreeSnapshot } from './model';
import { buildScene, layoutInputs, type Scene } from './scene';
import type { OriginSource } from './source';
import { ROOT_ID, toNode, type OriginItem, type OriginNode, type OwnOrigin, type SortMode } from './types';

export interface PeopleState {
	items: PublicUser[];
	page: number;
	hasMore: boolean;
}

export interface NetworkCoreOptions {
	scope: string;
	rootName: string;
	rootCount: number;
	states: readonly OriginItem[];
	own: OwnOrigin | null;
	source: OriginSource;
	sort?: SortMode;
}

export class NetworkCore {
	readonly scope: string;
	readonly root: OriginNode;
	readonly own: OwnOrigin | null;
	readonly source: OriginSource;
	readonly children = new Map<string, OriginNode[]>();
	readonly people = new Map<string, PeopleState>();
	readonly expanded = new Set<string>([ROOT_ID]);
	readonly layout = new NetworkLayout();
	sort: SortMode;
	tree!: TreeSnapshot;
	scene!: Scene;
	/** Kennungen der beim letzten Durchlauf neu platzierten Knoten (für die Aufklapp-Animation). */
	lastAdded: string[] = [];

	constructor(options: NetworkCoreOptions) {
		this.scope = options.scope;
		this.own = options.own;
		this.source = options.source;
		this.sort = options.sort ?? 'distance';
		this.root = {
			id: ROOT_ID,
			level: 'root',
			key: options.scope,
			name: options.rootName,
			count: options.rootCount,
			distanceKm: null,
			parentId: null,
			own: false
		};
		this.children.set(
			ROOT_ID,
			options.states.map((item) => toNode(item, 'state', ROOT_ID, this.own))
		);
		this.recompute();
	}

	node(id: string): OriginNode | undefined {
		return this.tree.byId.get(id)?.node;
	}

	/** Bundesländer und Landkreise klappen Kinder auf, Orte ihre Personenliste. */
	isExpandable(id: string): boolean {
		return id !== ROOT_ID && this.tree.byId.has(id);
	}

	isOpen(id: string): boolean {
		return this.expanded.has(id);
	}

	/** Lädt bei Bedarf die nächste Stufe und klappt genau eine Ebene auf. */
	async expand(id: string): Promise<void> {
		const node = this.node(id);
		if (!node || node.level === 'root' || this.expanded.has(id)) return;

		if (node.level === 'state' && !this.children.has(id)) {
			const items = await this.source.districts(this.scope, node.key);
			this.children.set(
				id,
				items.map((item) => toNode(item, 'district', id, this.own))
			);
		} else if (node.level === 'district' && !this.children.has(id)) {
			const items = await this.source.places(this.scope, node.key);
			this.children.set(
				id,
				items.map((item) => toNode(item, 'place', id, this.own))
			);
		} else if (node.level === 'place' && !this.people.has(id)) {
			const page = await this.source.people(this.scope, node.key, 1);
			this.people.set(id, { items: page.items, page: 1, hasMore: page.has_more });
		}

		// Der Knoten kann während des Ladens zugeklappt worden sein (Elternknoten geschlossen).
		if (!this.tree.byId.has(id)) return;
		this.expanded.add(id);
		this.recompute();
	}

	/** Klappt den Knoten samt allem darunter zu. */
	collapse(id: string): void {
		if (id === ROOT_ID || !this.expanded.has(id)) return;
		for (const child of descendantIds(this.tree.rows, id)) this.expanded.delete(child);
		this.expanded.delete(id);
		this.recompute();
	}

	async toggle(id: string): Promise<void> {
		if (this.expanded.has(id)) this.collapse(id);
		else await this.expand(id);
	}

	async loadMorePeople(id: string): Promise<void> {
		const node = this.node(id);
		const state = this.people.get(id);
		if (!node || !state || !state.hasMore) return;
		const next = await this.source.people(this.scope, node.key, state.page + 1);
		this.people.set(id, { items: [...state.items, ...next.items], page: state.page + 1, hasMore: next.has_more });
	}

	/** Neue Sortierung ordnet das ganze Netz neu. Das ist eine ausdrückliche Nutzeraktion. */
	setSort(mode: SortMode): void {
		if (mode === this.sort) return;
		this.sort = mode;
		this.layout.reset();
		this.recompute();
	}

	recompute(): void {
		this.tree = buildTree(
			this.root,
			(id) => this.children.get(id),
			(id) => this.expanded.has(id),
			this.sort
		);
		const result = this.layout.sync(layoutInputs(this.tree));
		this.lastAdded = result.added;
		this.scene = buildScene(this.tree, result.positions, this.root.name);
	}

	/** Pfad vom Knoten bis zur Mitte, der Knoten selbst zuerst. */
	pathToRoot(id: string): string[] {
		return this.tree.pathToRoot(id);
	}
}
