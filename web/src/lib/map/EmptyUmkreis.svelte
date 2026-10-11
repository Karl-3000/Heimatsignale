<script lang="ts">
	import type { NearbyOverview } from '$lib/api/types';

	/** Gestalteter leerer Zustand: Erklärung statt leerer Karte. */
	interface Props {
		overview: NearbyOverview;
		/** Größerer wählbarer Umkreis in km, falls es einen gibt. */
		wider?: number | null;
	}

	let { overview, wider = null }: Props = $props();
</script>

<section class="empty" data-testid="umkreis-empty">
	<svg viewBox="-120 -120 240 240" width="220" height="220" aria-hidden="true" focusable="false">
		<circle r="108" class="ring" />
		<circle r="72" class="ring" />
		<circle r="36" class="ring" />
		<path d="M0,0 Q22,-34 58,-44" class="ghost-edge" />
		<path d="M0,0 Q-34,-10 -62,22" class="ghost-edge" />
		<path d="M0,0 Q12,38 34,62" class="ghost-edge" />
		<circle cx="58" cy="-44" r="7" class="ghost" />
		<circle cx="-62" cy="22" r="5" class="ghost" />
		<circle cx="34" cy="62" r="9" class="ghost" />
		<circle r="13" class="own" />
		<circle r="18" class="own-ring" />
	</svg>
	<div class="text">
		<h2>Noch niemand aus deiner Gegend in {overview.radius_km} km.</h2>
		<p class="lead">
			Du bist die erste Person hier, und damit auch die erste aus {overview.me.home.name} ({overview.me.home.district_name}).
		</p>
		<p>
			Sobald sich weitere Zugezogene im Umkreis von {overview.me.residence.name} registrieren, erscheinen hier ihre Wohnorte und ihre Herkunft: erst nach
			Bundesland, dann nach Landkreis, dann nach Ort.
		</p>
		{#if wider}
			<p data-testid="empty-wider">Vielleicht wohnt jemand etwas weiter weg: Stelle den Umkreis oben auf {wider} km.</p>
		{/if}
		<p>Du musst nichts weiter tun. Schau später wieder vorbei oder erzähle anderen Zugezogenen von dem Dienst.</p>
	</div>
</section>

<style>
	.empty {
		display: grid;
		gap: var(--hs-space-5);
		align-items: center;
		justify-items: start;
		padding: var(--hs-space-6) var(--hs-space-5);
		border: 1px solid var(--hs-line);
		border-radius: var(--hs-radius-lg);
		background: var(--hs-surface);
	}

	@media (min-width: 720px) {
		.empty {
			grid-template-columns: auto minmax(0, 1fr);
			gap: var(--hs-space-7);
			padding: var(--hs-space-7);
		}
	}

	.text {
		display: grid;
		gap: var(--hs-space-3);
		max-width: var(--hs-prose);
	}

	.lead {
		font-size: var(--hs-text-lg);
	}

	.text p:not(.lead) {
		color: var(--hs-ink-muted);
	}

	.ring {
		fill: none;
		stroke: var(--hs-line-strong);
		stroke-dasharray: 2 7;
	}

	.ghost {
		fill: none;
		stroke: var(--hs-line-strong);
		stroke-width: 1.5;
		stroke-dasharray: 3 3;
	}

	.ghost-edge {
		fill: none;
		stroke: var(--hs-line-strong);
		stroke-width: 1.5;
		stroke-dasharray: 3 4;
		stroke-linecap: round;
	}

	.own {
		fill: var(--hs-origin);
	}

	.own-ring {
		fill: none;
		stroke: var(--hs-origin);
		stroke-width: 1.5;
	}
</style>
