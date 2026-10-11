<script lang="ts">
	/**
	 * Legende des Herkunftsnetzes. Sie sagt genau, was eine Linie bedeutet, und dass die
	 * Lage der Knoten schematisch ist (Projektplan, Abschnitt 5).
	 */
	interface Props {
		/** Name des Wohnorts oder null für "Alle im Umkreis". */
		residenceName: string | null;
	}

	let { residenceName }: Props = $props();
</script>

<aside class="legend" aria-label="Legende" data-testid="network-legend">
	<ul>
		<li>
			<svg viewBox="0 0 44 28" width="44" height="28" aria-hidden="true">
				<path d="M9,19 Q22,6 34,12" class="edge" stroke-width="3" />
				<circle cx="9" cy="19" r="3" class="node" />
				<circle cx="34" cy="12" r="5" class="node" />
			</svg>
			<p>
				Eine Linie bedeutet: So viele Personen, die {residenceName ? `in ${residenceName}` : 'im Umkreis'} leben, stammen aus dieser Herkunft. Je dicker
				die Linie und je größer die Kreisfläche, desto mehr Personen.
			</p>
		</li>
		<li>
			<svg viewBox="0 0 44 28" width="44" height="28" aria-hidden="true">
				<circle cx="22" cy="14" r="10.5" class="ring" />
				<circle cx="22" cy="14" r="6" class="ring" />
				<circle cx="22" cy="14" r="2" class="node" />
			</svg>
			<p>Die Lage der Knoten ist schematisch, nicht geografisch. Innen stehen Bundesländer, dann Landkreise, außen Orte.</p>
		</li>
		<li>
			<svg viewBox="0 0 44 28" width="44" height="28" aria-hidden="true">
				<circle cx="22" cy="14" r="5" class="own" />
				<circle cx="22" cy="14" r="8.5" class="own-ring" />
			</svg>
			<p>Farbe und Doppelring mit dem Vermerk <strong class="own-text">deine Herkunft</strong> markieren deinen Heimatort, deinen Landkreis und dein Bundesland.</p>
		</li>
	</ul>
</aside>

<style>
	/* Die Legende ist leiser Kleintext unter der Bühne, kein Kasten. */
	.legend {
		font-size: var(--hs-text-sm);
		line-height: 1.5;
		color: var(--hs-ink-muted);
	}

	ul {
		display: grid;
		gap: var(--hs-space-3);
		list-style: none;
		margin: 0;
		padding: 0;
	}

	@media (min-width: 900px) {
		ul {
			grid-template-columns: repeat(3, minmax(0, 1fr));
			gap: var(--hs-space-6);
		}
	}

	li {
		display: grid;
		grid-template-columns: 44px minmax(0, 1fr);
		gap: var(--hs-space-3);
		align-items: start;
	}

	svg {
		margin-top: 0.125rem;
		border-radius: var(--hs-radius-sm);
		background: var(--hs-stage-bg);
		background-image: var(--hs-stage-sky);
	}

	.edge {
		fill: none;
		stroke: var(--hs-stage-ink);
		stroke-opacity: 0.45;
		stroke-linecap: round;
	}

	.node {
		fill: var(--hs-stage-node);
		stroke: var(--hs-stage-node-rim);
		stroke-width: 1.25;
	}

	.ring {
		fill: none;
		stroke: var(--hs-stage-ink);
		stroke-opacity: 0.5;
		stroke-width: 1.25;
		stroke-linecap: round;
		stroke-dasharray: 0.1 3.5;
	}

	.own {
		fill: var(--hs-stage-origin);
		stroke: var(--hs-stage-origin-line);
		stroke-width: 1;
	}

	.own-ring {
		fill: none;
		stroke: var(--hs-stage-origin-line);
		stroke-width: 1.25;
	}

	.own-text {
		color: var(--hs-origin);
	}
</style>
