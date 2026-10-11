<script lang="ts">
	import { onMount } from 'svelte';
	import NetworkExplorer from './NetworkExplorer.svelte';
	import { statesFromOverview, totalForScope } from './overview';
	import { datasetBeispiel } from './synthetic';
	import { ownOriginFromAgs } from './types';
	import { NetworkView, type ViewMode } from './view.svelte';

	/**
	 * Bedienbares Beispielnetz mit erfundenen Daten für Startseite und Vorschau.
	 * Es benutzt dieselben Komponenten wie die echte Ansicht, spricht aber nie mit dem Server.
	 */
	let { height = 'min(62dvh, 30rem)' }: { height?: string } = $props();

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
		if (window.matchMedia('(max-width: 639px)').matches) mode = 'liste';
		// Ein Stück weit aufgeklappt beginnen, damit die drei Stufen sofort zu sehen sind.
		void (async () => {
			await view.expand('s09');
			await view.expand('d09780');
			view.selectedId = null;
			view.focusedId = 'root';
			view.announcement = '';
		})();
	});
</script>

<NetworkExplorer {view} bind:mode linkPeople={false} {height} idBase="beispiel" />
