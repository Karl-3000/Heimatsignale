<script lang="ts">
	import { tick } from 'svelte';
	import MapPin from '@lucide/svelte/icons/map-pin';
	import Icon from './Icon.svelte';
	import Button from './Button.svelte';
	import { searchPlaces } from '$lib/api/endpoints';
	import { errorMessage } from '$lib/api/client';
	import type { Place } from '$lib/api/types';

	/**
	 * Suchfeld für eine deutsche Gemeinde nach dem ARIA-Muster "Combobox" (Listbox-Popup,
	 * aria-activedescendant). Ist ein Ort gewählt, zeigt die Komponente ihn mit Landkreis
	 * und Bundesland und bietet "Ändern" an.
	 */
	interface Props {
		label: string;
		value: Place | null;
		hint?: string;
		error?: string | null;
		testid?: string;
		onselect?: (place: Place) => void;
	}

	let { label, value = $bindable(), hint, error = null, testid = 'place-search', onselect }: Props = $props();

	const uid = $props.id();

	let query = $state('');
	let items = $state<Place[]>([]);
	let open = $state(false);
	let active = $state(-1);
	let loading = $state(false);
	let status = $state('');
	let failure = $state<string | null>(null);
	let input = $state<HTMLInputElement | null>(null);

	let timer: ReturnType<typeof setTimeout> | null = null;
	let controller: AbortController | null = null;

	const describedBy = $derived([hint ? `${uid}-hint` : '', `${uid}-status`, error ? `${uid}-error` : ''].filter(Boolean).join(' '));

	function schedule(): void {
		if (timer) clearTimeout(timer);
		controller?.abort();
		failure = null;
		const q = query.trim();
		if (q.length < 2) {
			items = [];
			open = false;
			loading = false;
			status = q.length === 0 ? '' : 'Bitte mindestens 2 Zeichen eingeben.';
			return;
		}
		loading = true;
		timer = setTimeout(() => void run(q), 220);
	}

	async function run(q: string): Promise<void> {
		controller = new AbortController();
		const current = controller;
		try {
			const result = await searchPlaces(q, current.signal);
			if (current.signal.aborted) return;
			items = result.items;
			active = items.length > 0 ? 0 : -1;
			open = true;
			status = items.length === 0 ? 'Keine Gemeinde gefunden. Prüfe die Schreibweise.' : items.length === 1 ? '1 Treffer' : `${items.length} Treffer`;
		} catch (e) {
			if (current.signal.aborted) return;
			items = [];
			open = false;
			failure = errorMessage(e);
			status = '';
		} finally {
			if (!current.signal.aborted) loading = false;
		}
	}

	function choose(place: Place): void {
		value = place;
		open = false;
		items = [];
		query = '';
		status = '';
		onselect?.(place);
	}

	async function clear(): Promise<void> {
		value = null;
		await tick();
		input?.focus();
	}

	function handleKey(event: KeyboardEvent): void {
		if (event.key === 'ArrowDown') {
			event.preventDefault();
			if (!open && items.length > 0) open = true;
			else if (items.length > 0) active = (active + 1) % items.length;
		} else if (event.key === 'ArrowUp') {
			event.preventDefault();
			if (items.length > 0) active = (active - 1 + items.length) % items.length;
		} else if (event.key === 'Enter') {
			if (open && active >= 0 && items[active]) {
				event.preventDefault();
				choose(items[active]);
			}
		} else if (event.key === 'Escape') {
			if (open) {
				event.preventDefault();
				open = false;
			}
		}
	}

	function handleBlur(): void {
		// Kurz warten, damit ein Klick auf einen Treffer noch ankommt.
		setTimeout(() => {
			open = false;
		}, 150);
	}
</script>

<div class="place" data-testid={testid}>
	{#if value}
		<p class="label" id="{uid}-label">{label}</p>
		<div class="chosen" role="group" aria-labelledby="{uid}-label" data-testid="{testid}-selected">
			<span class="pin"><Icon icon={MapPin} size={18} /></span>
			<div class="chosen-text">
				<p class="name">{value.name}</p>
				<p class="where">{value.district_name}, {value.state_name}</p>
			</div>
			<Button variant="ghost" size="sm" onclick={clear} testid="{testid}-change">Ändern</Button>
		</div>
	{:else}
		<label class="label" for={uid}>{label}</label>
		{#if hint}<p id="{uid}-hint" class="hint">{hint}</p>{/if}
		<div class="box">
			<input
				id={uid}
				bind:this={input}
				bind:value={query}
				type="text"
				role="combobox"
				autocomplete="off"
				autocapitalize="words"
				spellcheck="false"
				placeholder="Name der Gemeinde oder Stadt"
				aria-expanded={open ? 'true' : 'false'}
				aria-controls="{uid}-list"
				aria-autocomplete="list"
				aria-activedescendant={open && active >= 0 ? `${uid}-opt-${active}` : undefined}
				aria-describedby={describedBy}
				aria-invalid={error ? 'true' : undefined}
				data-testid="{testid}-input"
				oninput={schedule}
				onkeydown={handleKey}
				onblur={handleBlur}
				onfocus={() => {
					if (items.length > 0) open = true;
				}}
			/>
			<ul id="{uid}-list" role="listbox" aria-label={label} class:open={open && items.length > 0}>
				{#if open}
					{#each items as place, index (place.ags)}
						<!-- svelte-ignore a11y_click_events_have_key_events -->
						<li
							id="{uid}-opt-{index}"
							role="option"
							aria-selected={index === active ? 'true' : 'false'}
							class:active={index === active}
							data-testid="{testid}-option"
							onmousedown={(event) => event.preventDefault()}
							onclick={() => choose(place)}
							onmouseenter={() => (active = index)}
						>
							<span class="name">{place.name}</span>
							<span class="where">{place.district_name}, {place.state_name}</span>
						</li>
					{/each}
				{/if}
			</ul>
		</div>
		<p id="{uid}-status" class="status" role="status" aria-live="polite">
			{#if loading}Suche läuft.{:else}{status}{/if}
		</p>
		{#if failure}<p class="error" role="alert">{failure}</p>{/if}
	{/if}
	{#if error}<p id="{uid}-error" class="error" role="alert">{error}</p>{/if}
</div>

<style>
	.place {
		display: flex;
		flex-direction: column;
		gap: var(--hs-space-1);
	}

	.label {
		font-size: var(--hs-text-sm);
		font-weight: var(--hs-weight-strong);
	}

	.hint,
	.status {
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
	}

	.status {
		min-height: 1.3em;
	}

	.box {
		position: relative;
	}

	input {
		min-height: var(--hs-control-height);
		width: 100%;
		padding: 0 var(--hs-space-3);
		border: 1px solid var(--hs-line-strong);
		border-radius: var(--hs-radius-md);
		background: var(--hs-raised);
		color: var(--hs-ink);
		font: inherit;
	}

	input::placeholder {
		color: var(--hs-ink-subtle);
	}

	input:focus-visible {
		outline: 2px solid var(--hs-focus);
		outline-offset: 1px;
		border-color: var(--hs-focus);
	}

	input[aria-invalid='true'] {
		border-color: var(--hs-danger);
		border-width: 2px;
	}

	ul {
		display: none;
		position: absolute;
		z-index: 30;
		left: 0;
		right: 0;
		top: calc(100% + 4px);
		max-height: 19rem;
		overflow-y: auto;
		padding: var(--hs-space-1);
		border: 1px solid var(--hs-line-strong);
		border-radius: var(--hs-radius-md);
		background: var(--hs-raised);
		box-shadow: var(--hs-shadow-md);
		list-style: none;
		margin: 0;
	}

	ul.open {
		display: block;
	}

	li {
		display: flex;
		flex-direction: column;
		padding: var(--hs-space-2) var(--hs-space-3);
		border-radius: var(--hs-radius-sm);
		cursor: pointer;
	}

	li.active {
		background: var(--hs-accent-soft);
		box-shadow: inset 3px 0 0 var(--hs-accent);
	}

	.name {
		font-weight: var(--hs-weight-strong);
	}

	.where {
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
	}

	.chosen {
		display: flex;
		align-items: center;
		gap: var(--hs-space-3);
		padding: var(--hs-space-2) var(--hs-space-2) var(--hs-space-2) var(--hs-space-3);
		border: 1px solid var(--hs-line-strong);
		border-radius: var(--hs-radius-md);
		background: var(--hs-raised);
	}

	.chosen-text {
		flex: 1;
		min-width: 0;
	}

	.pin {
		color: var(--hs-ink-muted);
		flex: none;
	}

	.error {
		font-size: var(--hs-text-sm);
		color: var(--hs-danger);
		font-weight: var(--hs-weight-strong);
	}
</style>
