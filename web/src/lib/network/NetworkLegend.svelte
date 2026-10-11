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
			<svg viewBox="0 0 56 20" width="56" height="20" aria-hidden="true">
				<path d="M4,15 Q28,2 52,10" class="edge" stroke-width="4" />
				<circle cx="4" cy="15" r="3.5" class="node" />
				<circle cx="52" cy="10" r="6" class="node" />
			</svg>
			<p>
				Eine Linie bedeutet: So viele Personen, die {residenceName ? `in ${residenceName}` : 'im Umkreis'} leben, stammen aus dieser Herkunft. Je dicker
				die Linie und je größer die Kreisfläche, desto mehr Personen.
			</p>
		</li>
		<li>
			<svg viewBox="0 0 56 20" width="56" height="20" aria-hidden="true">
				<circle cx="28" cy="10" r="9" class="ring" />
				<circle cx="28" cy="10" r="5.5" class="ring" />
				<circle cx="28" cy="10" r="2" class="node" />
			</svg>
			<p>Die Lage der Knoten ist schematisch, nicht geografisch. Innen stehen Bundesländer, dann Landkreise, außen Orte.</p>
		</li>
		<li>
			<svg viewBox="0 0 56 20" width="56" height="20" aria-hidden="true">
				<circle cx="28" cy="10" r="5" class="own" />
				<circle cx="28" cy="10" r="8.5" class="own-ring" />
			</svg>
			<p>Farbe und Doppelring mit dem Vermerk <strong class="own-text">deine Herkunft</strong> markieren deinen Heimatort, deinen Landkreis und dein Bundesland.</p>
		</li>
	</ul>
</aside>

<style>
	.legend {
		font-size: var(--hs-text-sm);
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
			gap: var(--hs-space-5);
		}
	}

	li {
		display: grid;
		grid-template-columns: 56px minmax(0, 1fr);
		gap: var(--hs-space-3);
		align-items: start;
	}

	svg {
		margin-top: 0.125rem;
	}

	.edge {
		fill: none;
		stroke: var(--hs-edge);
		stroke-opacity: 0.5;
		stroke-linecap: round;
	}

	.node {
		fill: var(--hs-node);
	}

	.ring {
		fill: none;
		stroke: var(--hs-line-strong);
		stroke-dasharray: 2 3;
	}

	.own {
		fill: var(--hs-origin);
	}

	.own-ring {
		fill: none;
		stroke: var(--hs-origin);
		stroke-width: 1.5;
	}

	.own-text {
		color: var(--hs-origin);
	}
</style>
