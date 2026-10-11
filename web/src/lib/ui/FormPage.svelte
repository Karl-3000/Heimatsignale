<script lang="ts">
	import type { Snippet } from 'svelte';

	/** Schmale Seite für Formulare und Statusmeldungen: Überschrift, Einleitung, Inhalt. */
	interface Props {
		title: string;
		lead?: string;
		wide?: boolean;
		children: Snippet;
	}

	let { title, lead, wide = false, children }: Props = $props();
</script>

<div class="page" class:wide>
	<header>
		<h1>{title}</h1>
		{#if lead}<p class="lead">{lead}</p>{/if}
	</header>
	{@render children()}
</div>

<style>
	.page {
		display: grid;
		gap: var(--hs-space-5);
		max-width: 30rem;
		margin: 0 auto;
		padding-top: var(--hs-space-4);
	}

	.page.wide {
		max-width: 38rem;
	}

	header {
		display: grid;
		gap: var(--hs-space-2);
	}

	.lead {
		color: var(--hs-ink-muted);
	}
</style>
