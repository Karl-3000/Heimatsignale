<script lang="ts">
	import { tick } from 'svelte';
	import NetworkExplorer from '$lib/network/NetworkExplorer.svelte';
	import { SCOPE_ALL } from '$lib/network/source';
	import type { UmkreisState } from '$lib/network/umkreis.svelte';
	import { personen } from '$lib/util/format';
	import UmkreisMap from './UmkreisMap.svelte';

	/**
	 * Karte, Wohnortwahl und Herkunftsnetz als eine Einheit über einem gemeinsamen Zustand.
	 * Die echte Umkreis-Seite und die Entwicklungsansicht benutzen dieselbe Komponente.
	 */
	interface Props {
		state: UmkreisState;
		tilesUrl?: string;
		glyphsUrl?: string;
		linkPeople?: boolean;
	}

	let { state: umkreis, tilesUrl = '', glyphsUrl = '', linkPeople = true }: Props = $props();

	let networkHeading = $state<HTMLHeadingElement | null>(null);

	const overview = $derived(umkreis.overview);
	const residences = $derived(
		overview ? [...overview.residences].sort((a, b) => b.total - a.total || a.name.localeCompare(b.name, 'de')) : []
	);
	const view = $derived(umkreis.view);

	/** Bei vielen Wohnorten (weiter Umkreis) stehen zuerst nur die größten da; der gewählte ist immer dabei. */
	const CHIP_LIMIT = 8;
	let showAll = $state(false);
	const shownResidences = $derived(
		showAll || residences.length <= CHIP_LIMIT + 2 ? residences : residences.filter((r, i) => i < CHIP_LIMIT || r.ags === umkreis.scope)
	);

	async function choose(scope: string, moveFocus: boolean): Promise<void> {
		umkreis.select(scope);
		if (!moveFocus) return;
		await tick();
		networkHeading?.focus({ preventScroll: true });
		const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
		networkHeading?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' });
	}
</script>

{#if overview}
	<div class="panel">
		<section class="grid gap-3" aria-labelledby="karte-titel">
			<h2 id="karte-titel" class="hs-sr-only">Karte</h2>
			<UmkreisMap
				{overview}
				scope={umkreis.scope}
				{tilesUrl}
				{glyphsUrl}
				camera={umkreis.camera}
				onselect={(scope) => void choose(scope, true)}
				oncamera={(camera) => (umkreis.camera = camera)}
			/>
			<p class="hint" data-testid="radius-hint">
				Die {overview.radius_km} km gelten zwischen den Mittelpunkten der Gemeinden. Innerhalb einer großen Stadt kann die tatsächliche Entfernung größer
				sein, und Nachbarn knapp jenseits der Grenze können herausfallen. Jeder Knoten ist eine Gemeinde, nie eine einzelne Person. Liegen Gemeinden auf
				der Karte dicht beieinander, werden sie zusammengefasst, bis du hineinzoomst.
			</p>
		</section>

		<section class="grid gap-3" aria-labelledby="wohnorte-titel">
			<h2 id="wohnorte-titel" class="small-title">Wohnort wählen</h2>
			<ul class="chips" data-testid="residence-list">
				<li>
					<button type="button" class:on={umkreis.scope === SCOPE_ALL} aria-pressed={umkreis.scope === SCOPE_ALL ? 'true' : 'false'} onclick={() => void choose(SCOPE_ALL, false)} data-testid="residence-all">
						<span>Alle im Umkreis</span>
						<span class="n hs-num">{overview.total}</span>
					</button>
				</li>
				{#each shownResidences as r (r.ags)}
					<li>
						<button
							type="button"
							class:on={umkreis.scope === r.ags}
							aria-pressed={umkreis.scope === r.ags ? 'true' : 'false'}
							onclick={() => void choose(r.ags, false)}
							data-testid="residence-item"
							data-ags={r.ags}
						>
							<span>{r.name}{#if r.ags === overview.me.residence.ags}<span class="mine">(dein Wohnort)</span>{/if}</span>
							<span class="n hs-num">{r.total}</span>
						</button>
					</li>
				{/each}
				{#if residences.length > CHIP_LIMIT + 2}
					<li>
						<button type="button" class="more" aria-expanded={showAll ? 'true' : 'false'} onclick={() => (showAll = !showAll)} data-testid="residence-more">
							{showAll ? 'Weniger zeigen' : `Alle ${residences.length} Wohnorte zeigen`}
						</button>
					</li>
				{/if}
			</ul>
		</section>

		{#if view}
			<section class="grid gap-4" aria-labelledby="netz-titel">
				<div>
					<h2 id="netz-titel" tabindex="-1" bind:this={networkHeading} class="net-title" data-testid="network-title">
						Herkunft: {view.core.root.name}
					</h2>
					<p class="net-lead">
						{personen(view.core.root.count)}
						{umkreis.scope === SCOPE_ALL ? `leben im Umkreis von ${overview.radius_km} km.` : `leben in ${view.core.root.name}.`}
						Öffne ein Bundesland, dann einen Landkreis, dann einen Ort.
					</p>
				</div>
				<NetworkExplorer {view} bind:mode={umkreis.mode} {linkPeople} onsort={(mode) => umkreis.setSort(mode)} />
			</section>
		{/if}
	</div>
{/if}

<style>
	.panel {
		display: grid;
		gap: var(--hs-space-7);
	}

	/* Leiser Kleintext unter der Bühne. */
	.hint {
		max-width: 46rem;
		font-size: var(--hs-text-sm);
		line-height: 1.5;
		color: var(--hs-ink-muted);
	}

	.small-title {
		font-family: var(--hs-font-sans);
		font-size: var(--hs-text-sm);
		font-weight: var(--hs-weight-strong);
		letter-spacing: 0;
		color: var(--hs-ink-muted);
	}

	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: var(--hs-space-2);
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.chips button {
		display: inline-flex;
		align-items: center;
		gap: var(--hs-space-2);
		min-height: 2.75rem;
		padding: 0 var(--hs-space-4);
		border: 0;
		border-radius: var(--hs-radius-full);
		background: var(--hs-surface);
		box-shadow: var(--hs-shadow-sm);
		color: var(--hs-ink);
		font: inherit;
		font-size: var(--hs-text-sm);
		cursor: pointer;
		transition: background-color var(--hs-duration-fast) var(--hs-ease-standard);
	}

	.chips button:hover {
		background: var(--hs-accent-soft);
	}

	.chips button.on {
		background: var(--hs-accent);
		color: var(--hs-on-accent);
		font-weight: var(--hs-weight-strong);
		box-shadow: none;
	}

	.chips button:focus-visible {
		outline: 2px solid var(--hs-focus);
		outline-offset: 2px;
		border-radius: var(--hs-radius-full);
	}

	.chips button.more {
		background: transparent;
		box-shadow: none;
		color: var(--hs-accent-ink);
		font-weight: var(--hs-weight-strong);
	}

	.chips button.more:hover {
		background: var(--hs-accent-soft);
	}

	.n {
		color: var(--hs-ink-subtle);
		font-weight: var(--hs-weight-strong);
	}

	.chips button.on .n {
		color: var(--hs-on-accent);
	}

	.mine {
		margin-left: 0.35em;
		color: var(--hs-ink-subtle);
	}

	.chips button.on .mine {
		color: var(--hs-on-accent);
	}

	.net-title {
		outline: none;
		scroll-margin-top: 6rem;
	}

	.net-title:focus-visible {
		outline: 2px solid var(--hs-focus);
		outline-offset: 6px;
	}

	.net-lead {
		margin-top: var(--hs-space-2);
		color: var(--hs-ink-muted);
	}
</style>
