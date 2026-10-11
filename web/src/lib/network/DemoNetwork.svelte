<script lang="ts">
	import { onMount } from 'svelte';
	import NetworkExplorer from './NetworkExplorer.svelte';
	import OriginNetwork from './OriginNetwork.svelte';
	import PeoplePanel from './PeoplePanel.svelte';
	import { statesFromOverview, totalForScope } from './overview';
	import { datasetBeispiel } from './synthetic';
	import { ownOriginFromAgs } from './types';
	import { NetworkView, type ViewMode } from './view.svelte';

	/**
	 * Bedienbares Beispielnetz mit erfundenen Daten für die Startseite.
	 * Es benutzt dieselben Komponenten wie die echte Ansicht, spricht aber nie mit dem Server.
	 *
	 * `hero`: nur das Netz, ohne eigenen Rahmen, mit dem einen orchestrierten Auftakt: Das Netz
	 * leuchtet von der Mitte nach außen auf und öffnet den Weg bis zum eigenen Heimatort.
	 */
	interface Props {
		height?: string;
		hero?: boolean;
	}

	let { height = 'clamp(24rem, 62dvh, 34rem)', hero = false }: Props = $props();

	const dataset = datasetBeispiel();
	const scope = dataset.overview.residences[0].ags;
	const view = new NetworkView({
		scope,
		rootName: dataset.overview.residences[0].name,
		rootCount: totalForScope(dataset.overview, scope),
		states: statesFromOverview(dataset.overview, scope),
		own: ownOriginFromAgs(dataset.overview.me.home.ags),
		source: dataset.source
	});

	let mode = $state<ViewMode>('netz');

	onMount(() => {
		if (!hero && window.matchMedia('(max-width: 639px)').matches) mode = 'liste';
		const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
		const wait = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, reduced ? 0 : ms));
		let cancelled = false;
		// Auftakt: erst die Bundesländer, dann der Weg zur eigenen Herkunft, Stufe für Stufe.
		void (async () => {
			await wait(hero ? 1100 : 0);
			if (cancelled) return;
			await view.expand('s09');
			await wait(520);
			if (cancelled) return;
			await view.expand('d09780');
			view.selectedId = null;
			view.focusedId = 'root';
			view.announcement = '';
		})();
		return () => {
			cancelled = true;
		};
	});
</script>

{#if hero}
	<div class="hero-net">
		<OriginNetwork {view} {height} intro plain />
		<p class="hs-sr-only" role="status" aria-live="polite">{view.announcement}</p>
		<div class="hero-panel"><PeoplePanel {view} linkPeople={false} /></div>
	</div>
{:else}
	<NetworkExplorer {view} bind:mode linkPeople={false} {height} idBase="beispiel" />
{/if}

<style>
	.hero-net {
		position: relative;
	}

	.hero-panel {
		position: absolute;
		left: var(--hs-space-4);
		bottom: var(--hs-space-4);
		width: min(19rem, calc(100% - 2rem));
		z-index: 2;
	}

	@media (max-width: 719px) {
		.hero-panel {
			position: static;
			width: auto;
		}
	}
</style>
