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
			Dieser Text ist eine Vorlage und keine Rechtsberatung. Gelb markierte Stellen mit „TODO“ muss der Betreiber ausfüllen. Vor dem ersten fremden
			Nutzer muss eine fachkundige Person den Text prüfen.
		</p>
	</Notice>
	{@render children()}
</article>

<style>
	.legal :global(.todo) {
		padding: 0.05em 0.35em;
		border: 1px dashed var(--hs-origin);
		border-radius: var(--hs-radius-sm);
		background: var(--hs-origin-soft);
		color: var(--hs-ink);
		font-weight: var(--hs-weight-strong);
	}

	.legal :global(table) {
		width: 100%;
		border-collapse: collapse;
		font-size: var(--hs-text-sm);
	}

	.legal :global(.table-wrap) {
		max-width: 100%;
		overflow-x: auto;
		border: 1px solid var(--hs-line);
		border-radius: var(--hs-radius-md);
	}

	.legal :global(th),
	.legal :global(td) {
		padding: var(--hs-space-2) var(--hs-space-3);
		border-bottom: 1px solid var(--hs-line);
		text-align: left;
		vertical-align: top;
	}

	.legal :global(th) {
		background: var(--hs-sunken);
		font-weight: var(--hs-weight-strong);
		white-space: nowrap;
	}

	.legal :global(tr:last-child td) {
		border-bottom: 0;
	}

	.legal :global(address) {
		font-style: normal;
	}
</style>
