<script lang="ts">
	import X from '@lucide/svelte/icons/x';
	import Icon from '$lib/ui/Icon.svelte';
	import Button from '$lib/ui/Button.svelte';
	import { formatAge, personen } from '$lib/util/format';
	import type { NetworkView } from './view.svelte';

	/**
	 * Die Personen eines Heimatorts, als Liste am ausgewählten Ortsknoten.
	 * Jeder Eintrag führt zum Profil. Gezeigt werden nur Nickname und ungefähres Alter.
	 */
	interface Props {
		view: NetworkView;
		linkPeople?: boolean;
	}

	let { view, linkPeople = true }: Props = $props();

	const node = $derived(view.selectedId ? (view.tree.byId.get(view.selectedId)?.node ?? null) : null);
	const people = $derived(view.selectedId ? (view.people.get(view.selectedId) ?? null) : null);
	const parent = $derived(node?.parentId ? (view.tree.byId.get(node.parentId)?.node ?? null) : null);
</script>

{#if node && people}
	<section class="panel" aria-label="Personen aus {node.name}" data-testid="people-panel">
		<header>
			<div>
				<h3>Aus {node.name}</h3>
				<p class="meta">
					<span class="hs-num">{parent ? `${parent.name}, ${personen(node.count)}` : personen(node.count)}</span>
					{#if node.own}<span class="own">deine Herkunft</span>{/if}
				</p>
			</div>
			<button type="button" class="close" onclick={() => view.collapse(node.id)} aria-label="Personenliste schließen" data-testid="people-close">
				<Icon icon={X} size={18} />
			</button>
		</header>
		{#if people.items.length === 0}
			<p class="empty">Gerade ist hier niemand sichtbar.</p>
		{:else}
			<ul>
				{#each people.items as user (user.id)}
					<li data-testid="people-item">
						{#if linkPeople}
							<a href="/profil/{user.id}" data-testid="people-link">{user.nickname}</a>
						{:else}
							<span class="nick">{user.nickname}</span>
						{/if}
						<span class="age hs-num">{formatAge(user.age_range)}</span>
					</li>
				{/each}
			</ul>
		{/if}
		{#if people.hasMore}
			<Button size="sm" loading={view.isLoading(node.id)} onclick={() => void view.loadMorePeople(node.id)} testid="people-more">Weitere laden</Button>
		{/if}
	</section>
{/if}

<style>
	.panel {
		display: flex;
		flex-direction: column;
		gap: var(--hs-space-3);
		padding: var(--hs-space-4);
		border: 1px solid var(--hs-line);
		border-left: 3px solid var(--hs-accent);
		border-radius: var(--hs-radius-lg);
		background: var(--hs-surface);
	}

	header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--hs-space-3);
	}

	h3 {
		font-size: var(--hs-text-lg);
	}

	.meta {
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
	}

	.own {
		margin-left: var(--hs-space-2);
		color: var(--hs-origin);
		font-weight: var(--hs-weight-strong);
	}

	.close {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 2.5rem;
		height: 2.5rem;
		flex: none;
		border: 0;
		border-radius: var(--hs-radius-md);
		background: transparent;
		color: var(--hs-ink-muted);
		cursor: pointer;
	}

	.close:hover {
		background: var(--hs-sunken);
		color: var(--hs-ink);
	}

	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	li {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--hs-space-3);
		min-height: 2.75rem;
		padding: var(--hs-space-2) 0;
		border-top: 1px solid var(--hs-line);
	}

	li a,
	.nick {
		font-weight: var(--hs-weight-strong);
		overflow-wrap: anywhere;
	}

	.age {
		color: var(--hs-ink-muted);
		font-size: var(--hs-text-sm);
		white-space: nowrap;
	}

	.empty {
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
	}
</style>
