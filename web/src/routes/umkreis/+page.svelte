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
	import { personen } from '$lib/util/format';

	const tilesUrl = env.PUBLIC_TILES_URL ?? '';
	const glyphsUrl = env.PUBLIC_GLYPHS_URL ?? '';

	const overview = $derived(umkreis.overview);

	onMount(() => {
		// Die Übersicht wird einmal geladen. Wer von einem Profil zurückkommt, findet alles wie zuvor.
		void umkreis.load();
	});
</script>

<svelte:head>
	<title>Umkreis – {session.siteName}</title>
</svelte:head>

<div class="grid gap-6" data-testid="umkreis-page">
	<header class="flex flex-wrap items-end justify-between gap-3">
		<div>
			<h1>Dein Umkreis</h1>
			{#if overview}
				<p class="text-ink-muted" data-testid="umkreis-summary">
					{#if overview.total === 0}
						{overview.radius_km} km um {overview.me.residence.name}
					{:else}
						<span class="hs-num">{personen(overview.total)}</span> in {overview.radius_km} km um {overview.me.residence.name}, aus
						{overview.residences.length === 1 ? 'einer Gemeinde' : `${overview.residences.length} Gemeinden`}
					{/if}
				</p>
			{/if}
		</div>
		{#if overview}
			<Button size="sm" icon={RefreshCw} loading={umkreis.loading} onclick={() => void umkreis.load(true)} testid="umkreis-refresh">Aktualisieren</Button>
		{/if}
	</header>

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
		<EmptyUmkreis {overview} />
	{:else if overview}
		<UmkreisPanel state={umkreis} {tilesUrl} {glyphsUrl} />
	{/if}
</div>
