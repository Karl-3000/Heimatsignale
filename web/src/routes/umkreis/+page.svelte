<script lang="ts">
	import { onMount } from 'svelte';
	import { env } from '$env/dynamic/public';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import { session } from '$lib/api/session.svelte';
	import EmptyUmkreis from '$lib/map/EmptyUmkreis.svelte';
	import UmkreisPanel from '$lib/map/UmkreisPanel.svelte';
	import { umkreis } from '$lib/network/umkreis.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Notice from '$lib/ui/Notice.svelte';
	import RadiusToggle from '$lib/ui/RadiusToggle.svelte';
	import { personen } from '$lib/util/format';

	const tilesUrl = env.PUBLIC_TILES_URL ?? '';
	const glyphsUrl = env.PUBLIC_GLYPHS_URL ?? '';

	const overview = $derived(umkreis.overview);

	onMount(() => {
		// Auswahl und gespeicherte Wahl des Umkreises übernehmen, dann die Übersicht einmal laden.
		// Wer von einem Profil zurückkommt, findet alles wie zuvor.
		umkreis.configure(session.site);
		void umkreis.load();
	});
</script>

<svelte:head>
	<title>Umkreis – {session.siteName}</title>
</svelte:head>

<div class="grid gap-7" data-testid="umkreis-page">
	<header class="flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
		<div>
			<h1>Dein Umkreis</h1>
			{#if overview}
				<p class="mt-2 text-lg text-ink-muted" data-testid="umkreis-summary">
					{#if overview.total === 0}
						{overview.radius_km} km um {overview.me.residence.name}
					{:else}
						<span class="hs-num">{personen(overview.total)}</span> in {overview.radius_km} km um {overview.me.residence.name}, aus
						{overview.residences.length === 1 ? 'einer Gemeinde' : `${overview.residences.length} Gemeinden`}
					{/if}
				</p>
			{/if}
		</div>
		<div class="flex flex-wrap items-center gap-x-5 gap-y-3">
			{#if umkreis.options.length > 1}
				<RadiusToggle options={umkreis.options} value={umkreis.radius} onchange={(radiusKm) => void umkreis.setRadius(radiusKm)} />
			{/if}
			{#if overview}
				<Button size="sm" variant="ghost" icon={RefreshCw} loading={umkreis.loading} onclick={() => void umkreis.load(true)} testid="umkreis-refresh">Aktualisieren</Button>
			{/if}
		</div>
	</header>

	<p class="hs-sr-only" role="status" aria-live="polite" data-testid="radius-status">
		{#if umkreis.loading && overview && umkreis.radius !== null && umkreis.radius !== overview.radius_km}
			Der Umkreis von {umkreis.radius} km wird geladen.
		{:else if overview}
			Angezeigt wird der Umkreis von {overview.radius_km} km.
		{/if}
	</p>

	{#if umkreis.error}
		<Notice tone="danger" title="Der Umkreis ließ sich nicht laden" live testid="umkreis-error">
			<p>{umkreis.error}</p>
		</Notice>
		{#if !overview}
			<div><Button variant="primary" loading={umkreis.loading} onclick={() => void umkreis.load(true)}>Erneut versuchen</Button></div>
		{/if}
	{/if}

	{#if !overview && umkreis.loading}
		<p role="status" class="text-ink-muted" data-testid="umkreis-loading">Dein Umkreis wird geladen.</p>
	{:else if overview && overview.total === 0}
		<EmptyUmkreis {overview} wider={umkreis.options.find((o) => o > overview.radius_km) ?? null} />
	{:else if overview}
		<UmkreisPanel state={umkreis} {tilesUrl} {glyphsUrl} />
	{/if}
</div>
