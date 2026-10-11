<script lang="ts">
	import Tabs from '$lib/ui/Tabs.svelte';
	import Notice from '$lib/ui/Notice.svelte';
	import OriginNetwork from './OriginNetwork.svelte';
	import OriginTree from './OriginTree.svelte';
	import PeoplePanel from './PeoplePanel.svelte';
	import NetworkLegend from './NetworkLegend.svelte';
	import { SCOPE_ALL } from './source';
	import type { SortMode } from './types';
	import type { NetworkView, ViewMode } from './view.svelte';

	/**
	 * Ein Herkunftsnetz mit sichtbarem Umschalter zwischen Netz und Liste, Sortierung,
	 * Legende und Personenliste. Beide Ansichten teilen sich die NetworkView; beim
	 * Wechsel bleiben Auswahl, aufgeklappte Stufen und Tastaturfokus erhalten.
	 */
	interface Props {
		view: NetworkView;
		mode: ViewMode;
		linkPeople?: boolean;
		height?: string;
		idBase?: string;
		/** Übernimmt die Sortierung, wenn sie für mehrere Netze gemeinsam gilt. */
		onsort?: (mode: SortMode) => void;
	}

	let { view, mode = $bindable(), linkPeople = true, height, idBase = 'herkunft', onsort }: Props = $props();

	const sortOptions: Array<{ value: SortMode; label: string }> = [
		{ value: 'distance', label: 'Nähe zu deinem Heimatort' },
		{ value: 'count', label: 'Anzahl' }
	];

	const errors = $derived([...view.errors.entries()]);
	const residenceName = $derived(view.scope === SCOPE_ALL ? null : view.core.root.name);
</script>

<div class="explorer" data-testid="network-explorer" data-mode={mode}>
	<div class="toolbar">
		<Tabs
			tabs={[
				{ id: 'netz', label: 'Netz' },
				{ id: 'liste', label: 'Liste' }
			]}
			bind:value={mode}
			label="Darstellung der Herkunft"
			{idBase}
			testid="view-toggle"
		/>
		<fieldset class="sort">
			<legend>Sortieren nach</legend>
			{#each sortOptions as option (option.value)}
				<label class:checked={view.sort === option.value}>
					<input
						type="radio"
						name="{idBase}-sort"
						value={option.value}
						checked={view.sort === option.value}
						onchange={() => (onsort ? onsort(option.value) : view.setSort(option.value))}
						data-testid="sort-{option.value}"
					/>
					<span>{option.label}</span>
				</label>
			{/each}
		</fieldset>
	</div>

	<p class="hs-sr-only" role="status" aria-live="polite" data-testid="network-announcement">{view.announcement}</p>

	{#if mode === 'netz'}
		<div class="stage" class:with-panel={view.selectedId !== null} role="tabpanel" id="{idBase}-panel-netz" aria-labelledby="{idBase}-tab-netz">
			{#key view}
				<OriginNetwork {view} {height} />
			{/key}
			<PeoplePanel {view} {linkPeople} />
		</div>
		{#each errors as [id, message] (id)}
			<Notice tone="danger" live testid="network-error"><p>{view.tree.byId.get(id)?.node.name ?? 'Herkunft'}: {message}</p></Notice>
		{/each}
		<NetworkLegend {residenceName} />
	{:else}
		<div role="tabpanel" id="{idBase}-panel-liste" aria-labelledby="{idBase}-tab-liste">
			<OriginTree {view} {linkPeople} />
		</div>
		<p class="list-note">Pfeiltasten bewegen den Fokus, Enter klappt eine Stufe auf oder zu. Die Liste zeigt dieselben Daten wie das Netz.</p>
	{/if}
</div>

<style>
	.explorer {
		display: flex;
		flex-direction: column;
		gap: var(--hs-space-4);
	}

	.toolbar {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--hs-space-3) var(--hs-space-5);
	}

	.sort {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--hs-space-1) var(--hs-space-4);
		border: 0;
		margin: 0;
		padding: 0;
		min-width: 0;
		font-size: var(--hs-text-sm);
	}

	.sort legend {
		float: left;
		padding: 0;
		margin-right: var(--hs-space-3);
		color: var(--hs-ink-muted);
	}

	.sort label {
		display: inline-flex;
		align-items: center;
		gap: var(--hs-space-2);
		min-height: 2.25rem;
		cursor: pointer;
	}

	.sort label.checked {
		font-weight: var(--hs-weight-strong);
	}

	.sort input {
		width: 1rem;
		height: 1rem;
		accent-color: var(--hs-accent);
	}

	.stage {
		display: grid;
		gap: var(--hs-space-4);
		align-items: start;
	}

	@media (min-width: 960px) {
		.stage.with-panel {
			grid-template-columns: minmax(0, 1fr) 20rem;
		}
	}

	.list-note {
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
	}
</style>
