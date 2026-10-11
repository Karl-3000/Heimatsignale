<script lang="ts">
	import { onMount } from 'svelte';
	import { errorMessage } from '$lib/api/client';
	import { listConversations } from '$lib/api/endpoints';
	import { inbox } from '$lib/api/inbox.svelte';
	import { session } from '$lib/api/session.svelte';
	import type { ConversationSummary } from '$lib/api/types';
	import Badge from '$lib/ui/Badge.svelte';
	import Card from '$lib/ui/Card.svelte';
	import Notice from '$lib/ui/Notice.svelte';
	import { formatDateTime } from '$lib/util/format';

	let items = $state.raw<ConversationSummary[]>([]);
	let loading = $state(true);
	let loadError = $state<string | null>(null);

	async function load(): Promise<void> {
		try {
			items = (await listConversations()).items;
			loadError = null;
		} catch (error) {
			loadError = errorMessage(error);
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		void load();
		const timer = setInterval(
			() => {
				if (document.visibilityState !== 'hidden') void load();
			},
			Math.max(10, session.site.poll_seconds) * 1000
		);
		return () => clearInterval(timer);
	});

	function unread(c: ConversationSummary): boolean {
		return c.available && c.last_message !== null && inbox.isUnread(c.id, c.last_message.created_at, c.last_message.mine);
	}
</script>

<svelte:head>
	<title>Gespräche – {session.siteName}</title>
</svelte:head>

<div class="page" data-testid="conversations-page">
	<header class="grid gap-2">
		<h1>Gespräche</h1>
		<p class="max-w-prose text-ink-muted">Reiner Text, zu zweit. Niemand sieht, ob du online bist oder eine Nachricht gelesen hast.</p>
	</header>

	{#if loadError}<Notice tone="danger" live testid="conversations-error"><p>{loadError}</p></Notice>{/if}

	{#if loading}
		<p role="status" class="text-ink-muted">Gespräche werden geladen.</p>
	{:else if items.length === 0}
		<Card tone="sunken" padding="lg" testid="conversations-empty">
			<p class="hs-strong">Noch keine Gespräche.</p>
			<p class="text-ink-muted">
				Ein Gespräch entsteht, sobald eine Kontaktanfrage angenommen wird. Im <a href="/umkreis">Umkreis</a> findest du Menschen aus deiner Heimat.
			</p>
		</Card>
	{:else}
		<ul class="list">
			{#each items as c (c.id)}
				<li>
					<a href="/gespraeche/{c.id}" class="item" class:unread={unread(c)} class:gone={!c.available} data-testid="conversation-item">
						<span class="head">
							<span class="name">{c.partner ? c.partner.nickname : 'Gespräch nicht mehr verfügbar'}</span>
							{#if unread(c)}<Badge tone="accent">neu</Badge>{/if}
						</span>
						{#if c.available && c.partner}
							<span class="origin">aus {c.partner.home.name}, wohnt in {c.partner.residence.name}</span>
						{/if}
						{#if c.last_message}
							<span class="preview">{#if c.last_message.mine}<span class="who">Du: </span>{/if}{c.last_message.preview}</span>
							<span class="time hs-num">{formatDateTime(c.last_message.created_at)}</span>
						{:else if c.available}
							<span class="preview">Noch keine Nachricht. Schreib die erste.</span>
						{/if}
					</a>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.page {
		display: grid;
		gap: var(--hs-space-5);
		max-width: 44rem;
	}

	.list {
		display: grid;
		list-style: none;
		margin: 0;
		padding: 0;
		border: 1px solid var(--hs-line);
		border-radius: var(--hs-radius-lg);
		background: var(--hs-surface);
		overflow: hidden;
	}

	li + li {
		border-top: 1px solid var(--hs-line);
	}

	.item {
		display: grid;
		gap: 0.125rem;
		padding: var(--hs-space-4);
		color: var(--hs-ink);
		text-decoration: none;
	}

	.item:hover {
		background: var(--hs-sunken);
		color: var(--hs-ink);
	}

	.item:focus-visible {
		outline-offset: -3px;
	}

	.item.unread {
		box-shadow: inset 3px 0 0 var(--hs-accent);
	}

	.head {
		display: flex;
		align-items: center;
		gap: var(--hs-space-2);
	}

	.name {
		font-weight: var(--hs-weight-strong);
		overflow-wrap: anywhere;
	}

	.gone .name {
		font-weight: var(--hs-weight-regular);
		color: var(--hs-ink-muted);
	}

	.origin,
	.time {
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-subtle);
	}

	.preview {
		color: var(--hs-ink-muted);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.unread .preview {
		color: var(--hs-ink);
	}

	.who {
		color: var(--hs-ink-subtle);
	}
</style>
