<script lang="ts">
	import { env } from '$env/dynamic/public';
	import EmptyUmkreis from '$lib/map/EmptyUmkreis.svelte';
	import UmkreisPanel from '$lib/map/UmkreisPanel.svelte';
	import { allDatasets, type SyntheticDataset } from '$lib/network/synthetic';
	import { UmkreisState } from '$lib/network/umkreis.svelte';
	import Notice from '$lib/ui/Notice.svelte';
	import { devRoutesEnabled } from '$lib/util/dev';

	/**
	 * Netz-Prototyp mit künstlichen Daten, ohne Backend (Projektplan, Abschnitt 5).
	 * Nur im Entwicklungsmodus oder mit PUBLIC_DEV_ROUTES=1 erreichbar und in keiner
	 * Navigation verlinkt. Personen sind hier keine Links, weil es keine Profile gibt.
	 */
	const enabled = devRoutesEnabled();
	const datasets = allDatasets();

	function build(dataset: SyntheticDataset): UmkreisState {
		const built = new UmkreisState(() => dataset.source);
		built.radius = dataset.overview.radius_km;
		built.setOverview(dataset.overview);
		return built;
	}

	let selectedId = $state(datasets[1].id);
	let dataset = $state.raw<SyntheticDataset>(datasets[1]);
	let prototype = $state.raw<UmkreisState>(build(datasets[1]));

	function handleDatasetChange(): void {
		// Ausdrücklich im Ereignis neu aufbauen, nicht als abgeleiteter Wert.
		const next = datasets.find((d) => d.id === selectedId) ?? datasets[0];
		dataset = next;
		prototype = build(next);
	}

	const tasks = [
		'Den eigenen Heimatort (Sonthofen im Oberallgäu, Bayern) im Netz finden.',
		'Verstehen, wie viele passende Personen es gibt.',
		'Eine Personenliste öffnen, wieder schließen, die Orientierung behalten.',
		'Zur Listenansicht wechseln und dieselbe Stelle wiederfinden.'
	];
</script>

<svelte:head>
	<title>Netz-Prototyp (Entwicklung)</title>
	<meta name="robots" content="noindex" />
</svelte:head>

{#if enabled}
	<div class="grid gap-6" data-testid="dev-netz">
		<header class="grid gap-2">
			<h1>Netz-Prototyp mit künstlichen Daten</h1>
			<p class="max-w-prose text-ink-muted">
				Diese Seite spricht nicht mit dem Server. Alle Personen sind erfunden. Sie dient dazu, das Herkunftsnetz an Aufgaben zu prüfen, auch mit Tastatur,
				Screenreader, 200 % Schriftgröße und reduzierter Bewegung.
			</p>
		</header>

		<div class="grid gap-4 lg:grid-cols-2">
			<div class="grid content-start gap-2">
				<label for="datensatz" class="text-sm hs-strong">Datensatz</label>
				<select id="datensatz" bind:value={selectedId} onchange={handleDatasetChange} data-testid="dev-dataset">
					{#each datasets as d (d.id)}
						<option value={d.id}>{d.title} ({d.nodeCount} Knoten)</option>
					{/each}
				</select>
				<p class="text-sm text-ink-muted" data-testid="dev-description">{dataset.description}</p>
			</div>
			<Notice tone="info" title="Aufgaben für die Prüfung">
				<ol class="tasks">
					{#each tasks as task (task)}
						<li>{task}</li>
					{/each}
				</ol>
			</Notice>
		</div>

		{#key dataset.id}
			{#if dataset.overview.total === 0}
				<EmptyUmkreis overview={dataset.overview} />
			{:else}
				<UmkreisPanel state={prototype} tilesUrl={env.PUBLIC_TILES_URL ?? ''} glyphsUrl={env.PUBLIC_GLYPHS_URL ?? ''} linkPeople={false} />
			{/if}
		{/key}
	</div>
{:else}
	<p>Diese Seite gibt es nur in der Entwicklungsumgebung.</p>
{/if}

<style>
	select {
		min-height: var(--hs-control-height);
		max-width: 28rem;
		padding: 0 var(--hs-space-3);
		border: 1px solid var(--hs-line-strong);
		border-radius: var(--hs-radius-md);
		background: var(--hs-raised);
		color: var(--hs-ink);
		font: inherit;
	}

	.tasks {
		display: grid;
		gap: var(--hs-space-1);
		padding-left: 1.25rem;
		list-style: decimal;
	}
</style>
