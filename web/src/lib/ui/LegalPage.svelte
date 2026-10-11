<script lang="ts">
	import type { Snippet } from 'svelte';
	import Notice from './Notice.svelte';

	/**
	 * Rahmen der Rechtstexte. Alle drei Seiten sind Entwürfe mit sichtbar markierten
	 * Platzhaltern (class="todo") für Angaben, die nur der Betreiber machen kann.
	 */
	interface Props {
		title: string;
		children: Snippet;
	}

	let { title, children }: Props = $props();
</script>

<article class="legal hs-prose" data-testid="legal-page">
	<h1>{title}</h1>
	<Notice tone="warning" title="Entwurf, vor Inbetriebnahme rechtlich prüfen" testid="legal-draft">
		<p>
			Dieser Text ist eine Vorlage und keine Rechtsberatung. Markierte Stellen mit „TODO“ muss der Betreiber ausfüllen. Vor dem ersten fremden
			Nutzer muss eine fachkundige Person den Text prüfen.
		</p>
	</Notice>
	{@render children()}
</article>

<style>
	.legal {
		padding-top: var(--hs-space-5);
		line-height: 1.7;
	}

	.legal :global(h1) {
		margin-bottom: var(--hs-space-5);
	}

	.legal :global(h2) {
		font-size: var(--hs-text-xl);
	}

	.legal :global(.todo) {
		padding: 0.1em 0.4em;
		border-radius: var(--hs-radius-sm);
		background: var(--hs-sunken);
		box-shadow: inset 0 0 0 1px var(--hs-line-strong);
		color: var(--hs-ink);
		font-weight: var(--hs-weight-strong);
	}

	.legal :global(table) {
		width: 100%;
		border-collapse: collapse;
		font-size: var(--hs-text-sm);
		line-height: 1.5;
	}

	.legal :global(.table-wrap) {
		max-width: 100%;
		overflow-x: auto;
		border-radius: var(--hs-radius-lg);
		background: var(--hs-surface);
		box-shadow: var(--hs-shadow-sm);
	}

	.legal :global(th),
	.legal :global(td) {
		padding: var(--hs-space-3) var(--hs-space-4);
		border-bottom: 1px solid var(--hs-line);
		text-align: left;
		vertical-align: top;
	}

	.legal :global(th) {
		font-weight: var(--hs-weight-strong);
		color: var(--hs-ink-muted);
		white-space: nowrap;
	}

	.legal :global(tr:last-child td) {
		border-bottom: 0;
	}

	.legal :global(address) {
		font-style: normal;
	}
</style>
