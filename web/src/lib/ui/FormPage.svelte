<script lang="ts">
	import type { Snippet } from 'svelte';

	/** Schmale Seite für Formulare und Statusmeldungen: Überschrift, Einleitung, Inhalt. */
	interface Props {
		title: string;
		lead?: string;
		wide?: boolean;
		/** Seitentitel klein setzen, wenn der Inhalt selbst eine große Überschrift trägt (Schritte der Registrierung). */
		quietTitle?: boolean;
		children: Snippet;
	}

	let { title, lead, wide = false, quietTitle = false, children }: Props = $props();
</script>

<div class="page" class:wide>
	<header>
		<h1 class:quiet={quietTitle}>{title}</h1>
		{#if lead}<p class="lead">{lead}</p>{/if}
	</header>
	{@render children()}
</div>

<style>
	.page {
		display: grid;
		gap: var(--hs-space-6);
		max-width: 31rem;
		margin: 0 auto;
		padding-top: var(--hs-space-6);
	}

	.page.wide {
		max-width: 36rem;
	}

	header {
		display: grid;
		gap: var(--hs-space-3);
	}

	h1.quiet {
		font-family: var(--hs-font-sans);
		font-size: var(--hs-text-sm);
		font-weight: var(--hs-weight-strong);
		letter-spacing: 0;
		line-height: 1.4;
		color: var(--hs-ink-muted);
	}

	.lead {
		font-size: var(--hs-text-lg);
		line-height: 1.5;
		color: var(--hs-ink-muted);
	}

	@media (min-width: 720px) {
		.page {
			padding-top: var(--hs-space-8);
		}
	}
</style>
