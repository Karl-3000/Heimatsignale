<script lang="ts">
	import type { NearbyOverview } from '$lib/api/types';

	/** Gestalteter leerer Zustand: eine kleine Bühne mit einem einzelnen Heimatlicht, daneben die Erklärung. */
	interface Props {
		overview: NearbyOverview;
		/** Größerer wählbarer Umkreis in km, falls es einen gibt. */
		wider?: number | null;
	}

	let { overview, wider = null }: Props = $props();
	const uid = $props.id();
</script>

<section class="empty" data-testid="umkreis-empty">
	<div class="hs-stage vignette" aria-hidden="true">
		<svg viewBox="-120 -120 240 240" focusable="false">
			<defs>
				<radialGradient id="{uid}-licht">
					<stop offset="0.2" class="a" />
					<stop offset="1" class="b" />
				</radialGradient>
			</defs>
			<circle r="104" class="ring" />
			<circle r="68" class="ring" />
			<circle r="32" class="ring" />
			<circle r="46" fill="url(#{uid}-licht)" />
			<circle r="9" class="own" />
			<circle r="14" class="own-ring" />
		</svg>
	</div>
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
		gap: var(--hs-space-6);
		align-items: center;
	}

	.vignette {
		display: grid;
		place-items: center;
		aspect-ratio: 1;
		width: min(100%, 17rem);
	}

	.vignette svg {
		width: 100%;
		height: 100%;
	}

	@media (min-width: 720px) {
		.empty {
			grid-template-columns: 17rem minmax(0, 1fr);
			gap: var(--hs-space-8);
		}
	}

	.text {
		display: grid;
		gap: var(--hs-space-3);
		max-width: var(--hs-prose);
	}

	.lead {
		font-size: var(--hs-text-lg);
		line-height: 1.5;
	}

	.text p:not(.lead) {
		color: var(--hs-ink-muted);
	}

	.ring {
		fill: none;
		stroke: var(--hs-stage-line);
	}

	.a {
		stop-color: var(--hs-stage-origin);
		stop-opacity: 0.5;
	}

	.b {
		stop-color: var(--hs-stage-origin);
		stop-opacity: 0;
	}

	.own {
		fill: var(--hs-stage-origin);
	}

	.own-ring {
		fill: none;
		stroke: var(--hs-stage-origin);
		stroke-width: 1.5;
	}
</style>
