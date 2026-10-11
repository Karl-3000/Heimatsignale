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
				{#each residences as r (r.ags)}
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
			</ul>
		</section>

		{#if view}
			<section class="grid gap-4" aria-labelledby="netz-titel">
				<div>
					<h2 id="netz-titel" tabindex="-1" bind:this={networkHeading} class="net-title" data-testid="network-title">
						Herkunft: {view.core.root.name}
					</h2>
					<p class="text-ink-muted">
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
		gap: var(--hs-space-6);
	}

	.hint {
		max-width: 62rem;
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
	}

	.small-title {
		font-size: var(--hs-text-base);
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
		min-height: 2.5rem;
		padding: 0 var(--hs-space-3);
		border: 1px solid var(--hs-line-strong);
		border-radius: var(--hs-radius-full);
		background: var(--hs-raised);
		color: var(--hs-ink);
		font: inherit;
		font-size: var(--hs-text-sm);
		cursor: pointer;
		transition: background-color var(--hs-duration-fast) var(--hs-ease-standard);
	}

	.chips button:hover {
		background: var(--hs-sunken);
	}

	.chips button.on {
		background: var(--hs-ink);
		border-color: var(--hs-ink);
		color: var(--hs-bg);
		font-weight: var(--hs-weight-strong);
	}

	.chips button:focus-visible {
		outline: 2px solid var(--hs-focus);
		outline-offset: 2px;
	}

	.n {
		color: var(--hs-ink-muted);
		font-weight: var(--hs-weight-strong);
	}

	.chips button.on .n {
		color: var(--hs-bg);
	}

	.mine {
		margin-left: 0.35em;
		color: var(--hs-ink-muted);
	}

	.chips button.on .mine {
		color: var(--hs-bg);
	}

	.net-title {
		outline: none;
		scroll-margin-top: 5rem;
	}

	.net-title:focus-visible {
		outline: 2px solid var(--hs-focus);
		outline-offset: 4px;
	}
</style>
