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
	/* Die Personen eines Orts sind ein Gegenstand: eine erhabene Karte mit großen Namen. */
	.panel {
		display: flex;
		flex-direction: column;
		gap: var(--hs-space-4);
		padding: var(--hs-space-5);
		border-radius: var(--hs-radius-lg);
		background: var(--hs-surface);
		box-shadow: var(--hs-shadow-md);
	}

	header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--hs-space-3);
	}

	h3 {
		font-size: var(--hs-text-xl);
	}

	.meta {
		margin-top: var(--hs-space-1);
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
	}

	.own {
		display: block;
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
		border-radius: 50%;
		background: var(--hs-sunken);
		color: var(--hs-ink-muted);
		cursor: pointer;
	}

	.close:hover {
		color: var(--hs-ink);
	}

	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	li {
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
		padding: var(--hs-space-3) 0;
		border-top: 1px solid var(--hs-line);
	}

	li a,
	.nick {
		font-family: var(--hs-font-display);
		font-weight: var(--hs-weight-display);
		font-size: var(--hs-text-lg);
		letter-spacing: -0.02em;
		line-height: 1.2;
		overflow-wrap: anywhere;
	}

	li a {
		color: var(--hs-ink);
		text-decoration-color: color-mix(in srgb, currentColor 28%, transparent);
	}

	li a:hover {
		color: var(--hs-accent-ink);
		text-decoration-color: currentColor;
	}

	.age {
		color: var(--hs-ink-muted);
		font-size: var(--hs-text-sm);
	}

	.empty {
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
	}

	/* Auf schmalen Bildschirmen gleitet die Liste als Blatt von unten herein. */
	@media (max-width: 719px) {
		.panel {
			position: fixed;
			left: var(--hs-space-2);
			right: var(--hs-space-2);
			bottom: calc(var(--hs-toast-offset, 0px) + env(safe-area-inset-bottom, 0px) + var(--hs-space-2));
			z-index: 45;
			max-height: 56dvh;
			overflow-y: auto;
			border-radius: var(--hs-radius-stage);
			box-shadow: var(--hs-shadow-lg);
			animation: hs-sheet-in var(--hs-duration-slow) var(--hs-ease-out);
		}
	}

	@keyframes hs-sheet-in {
		from {
			opacity: 0;
			transform: translateY(24px);
		}
	}
</style>
