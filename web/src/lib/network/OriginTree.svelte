<script lang="ts">
	import { tick } from 'svelte';
	import { goto } from '$app/navigation';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Icon from '$lib/ui/Icon.svelte';
	import Badge from '$lib/ui/Badge.svelte';
	import type { PublicUser } from '$lib/api/types';
	import { formatAge, personen } from '$lib/util/format';
	import { treeKeyAction, type KeyRow } from './keyboard';
	import { LEVEL_LABEL, ROOT_ID, type OriginNode } from './types';
	import { moreRowId, personRowId, type NetworkView } from './view.svelte';

	/**
	 * Listenansicht des Herkunftsnetzes: ein Baum nach dem ARIA-Muster "Tree View"
	 * mit denselben Daten, derselben Reihenfolge und demselben Zustand wie das Netz.
	 * Unter einem aufgeklappten Ort stehen die Personen als weitere Baumebene.
	 */
	interface Props {
		view: NetworkView;
		/** false in der Vorschau ohne Anmeldung: Personen sind dann keine Links. */
		linkPeople?: boolean;
		testid?: string;
	}

	let { view, linkPeople = true, testid = 'origin-tree' }: Props = $props();

	type Row =
		| { kind: 'node'; id: string; depth: number; parentId: string | null; node: OriginNode; open: boolean; posInSet: number; setSize: number }
		| { kind: 'person'; id: string; depth: number; parentId: string; user: PublicUser; posInSet: number; setSize: number }
		| { kind: 'more'; id: string; depth: number; parentId: string; posInSet: number; setSize: number };

	let container = $state<HTMLDivElement | null>(null);

	const rows = $derived.by(() => {
		const out: Row[] = [];
		for (const row of view.rows) {
			const id = row.node.id;
			const open = id === ROOT_ID ? true : view.isOpen(id);
			out.push({ kind: 'node', id, depth: row.depth, parentId: row.node.parentId, node: row.node, open, posInSet: row.posInSet, setSize: row.setSize });
			if (row.node.level === 'place' && open) {
				const people = view.people.get(id);
				if (!people) continue;
				const size = people.items.length + (people.hasMore ? 1 : 0);
				people.items.forEach((user, index) => {
					out.push({ kind: 'person', id: personRowId(id, user.id), depth: row.depth + 1, parentId: id, user, posInSet: index + 1, setSize: size });
				});
				if (people.hasMore) out.push({ kind: 'more', id: moreRowId(id), depth: row.depth + 1, parentId: id, posInSet: size, setSize: size });
			}
		}
		return out;
	});

	const keyRows = $derived<KeyRow[]>(
		rows.map((row) => ({
			id: row.id,
			depth: row.depth,
			parentId: row.parentId,
			expandable: row.kind === 'node' && row.node.level !== 'root',
			expanded: row.kind === 'node' && row.node.level !== 'root' && row.open
		}))
	);

	/** Genau eine Zeile ist per Tab erreichbar: die zuletzt fokussierte. */
	const tabStop = $derived(rows.some((r) => r.id === view.focusedId) ? view.focusedId : view.focusedNodeId);

	function focusRow(id: string): void {
		const el = container?.querySelector<HTMLElement>(`[data-row-id="${CSS.escape(id)}"]`);
		el?.focus();
	}

	async function activate(row: Row): Promise<void> {
		view.focus(row.id);
		if (row.kind === 'node') {
			if (row.node.level !== 'root') await view.toggle(row.id);
		} else if (row.kind === 'person') {
			if (linkPeople) await goto(`/profil/${row.user.id}`);
		} else {
			await view.loadMorePeople(row.parentId);
		}
	}

	async function handleKey(event: KeyboardEvent, row: Row): Promise<void> {
		const action = treeKeyAction(event.key, keyRows, row.id);
		if (!action) return;
		event.preventDefault();
		if (action.type === 'focus') {
			view.focus(action.id);
			await tick();
			focusRow(action.id);
		} else if (action.type === 'expand') {
			await view.expand(action.id);
		} else if (action.type === 'collapse') {
			view.collapse(action.id);
		} else {
			await activate(row);
		}
	}

	function handleClick(event: MouseEvent, row: Row): void {
		// Der Nickname ist ein echter Link (neuer Tab, Kontextmenü); er navigiert selbst.
		if (event.target instanceof Element && event.target.closest('a')) {
			view.focus(row.id);
			return;
		}
		void activate(row);
	}
</script>

<div class="tree" role="tree" aria-label="Herkunft der Zugezogenen, {view.core.root.name}" bind:this={container} data-testid={testid}>
	{#each rows as row (row.id)}
		{#if row.kind === 'node'}
			{@const node = row.node}
			{@const isRoot = node.level === 'root'}
			{@const error = view.errors.get(row.id)}
			<div
				class="row level-{node.level}"
				class:own={node.own}
				class:selected={view.selectedId === row.id}
				role="treeitem"
				aria-level={row.depth + 1}
				aria-posinset={row.posInSet}
				aria-setsize={row.setSize}
				aria-expanded={isRoot ? 'true' : row.open ? 'true' : 'false'}
				aria-selected={view.selectedId === row.id ? 'true' : 'false'}
				aria-busy={view.isLoading(row.id) ? 'true' : undefined}
				tabindex={tabStop === row.id ? 0 : -1}
				style:--depth={row.depth}
				data-row-id={row.id}
				data-level={node.level}
				data-own={node.own ? 'true' : undefined}
				data-testid="tree-item"
				onclick={(event) => handleClick(event, row)}
				onkeydown={(event) => void handleKey(event, row)}
				onfocus={() => view.focus(row.id)}
			>
				<span class="chevron" aria-hidden="true">
					{#if !isRoot}<Icon icon={row.open ? ChevronDown : ChevronRight} size={16} />{/if}
				</span>
				<span class="main">
					<span class="name">{node.name}</span>
					<span class="hs-sr-only">, {LEVEL_LABEL[node.level]}</span>
					{#if node.own}<Badge tone="origin">deine Herkunft</Badge>{/if}
					{#if view.isLoading(row.id)}<span class="state">lädt</span>{/if}
				</span>
				<span class="count hs-num">{personen(node.count)}</span>
				{#if error}<span class="error">{error}</span>{/if}
			</div>
		{:else if row.kind === 'person'}
			<div
				class="row person"
				role="treeitem"
				aria-level={row.depth + 1}
				aria-posinset={row.posInSet}
				aria-setsize={row.setSize}
				aria-selected="false"
				tabindex={tabStop === row.id ? 0 : -1}
				style:--depth={row.depth}
				data-row-id={row.id}
				data-testid="tree-person"
				onclick={(event) => handleClick(event, row)}
				onkeydown={(event) => void handleKey(event, row)}
				onfocus={() => view.focus(row.id)}
			>
				<span class="chevron" aria-hidden="true"></span>
				<span class="main">
					{#if linkPeople}
						<a href="/profil/{row.user.id}" tabindex="-1" class="name">{row.user.nickname}</a>
					{:else}
						<span class="name">{row.user.nickname}</span>
					{/if}
				</span>
				<span class="count hs-num">{formatAge(row.user.age_range)}</span>
			</div>
		{:else}
			<div
				class="row more"
				role="treeitem"
				aria-level={row.depth + 1}
				aria-posinset={row.posInSet}
				aria-setsize={row.setSize}
				aria-selected="false"
				tabindex={tabStop === row.id ? 0 : -1}
				style:--depth={row.depth}
				data-row-id={row.id}
				data-testid="tree-more"
				onclick={(event) => handleClick(event, row)}
				onkeydown={(event) => void handleKey(event, row)}
				onfocus={() => view.focus(row.id)}
			>
				<span class="chevron" aria-hidden="true"></span>
				<span class="main"><span class="name link">Weitere Personen laden</span></span>
			</div>
		{/if}
	{/each}
</div>

<style>
	.tree {
		border: 1px solid var(--hs-line);
		border-radius: var(--hs-radius-lg);
		background: var(--hs-surface);
		padding: var(--hs-space-2);
	}

	.row {
		display: grid;
		grid-template-columns: 1.25rem minmax(0, 1fr) auto;
		align-items: center;
		column-gap: var(--hs-space-2);
		min-height: 2.75rem;
		padding: var(--hs-space-2) var(--hs-space-3);
		padding-left: calc(var(--hs-space-3) + var(--depth, 0) * 1.25rem);
		border-radius: var(--hs-radius-md);
		cursor: pointer;
	}

	.row:hover {
		background: var(--hs-sunken);
	}

	.row:focus-visible {
		outline: 2px solid var(--hs-focus);
		outline-offset: -2px;
	}

	.row.selected {
		background: var(--hs-accent-soft);
		box-shadow: inset 3px 0 0 var(--hs-accent);
	}

	.row.level-root {
		cursor: default;
		font-weight: var(--hs-weight-strong);
	}

	.row.level-root:hover {
		background: transparent;
	}

	.chevron {
		display: inline-flex;
		color: var(--hs-ink-muted);
	}

	.main {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--hs-space-1) var(--hs-space-2);
		min-width: 0;
	}

	.name {
		overflow-wrap: anywhere;
	}

	.row.own .name {
		font-weight: var(--hs-weight-strong);
	}

	.row.level-state .name {
		font-weight: var(--hs-weight-strong);
	}

	.count {
		color: var(--hs-ink-muted);
		font-size: var(--hs-text-sm);
		white-space: nowrap;
	}

	.state {
		font-size: var(--hs-text-xs);
		color: var(--hs-ink-subtle);
	}

	.error {
		grid-column: 2 / -1;
		font-size: var(--hs-text-sm);
		color: var(--hs-danger);
		font-weight: var(--hs-weight-strong);
	}

	.person .name,
	.link {
		color: var(--hs-accent);
		text-decoration: underline;
		text-decoration-thickness: 1px;
		text-underline-offset: 0.18em;
	}
</style>
