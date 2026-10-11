<script lang="ts">
	import type { PowRun } from '$lib/pow/run.svelte';

	/** Fortschritt der Sicherheitsprüfung (Proof-of-Work), sichtbar und für Screenreader. */
	let { run }: { run: PowRun } = $props();

	const percent = $derived(Math.round(run.progress * 100));
</script>

<div class="pow" aria-live="polite" data-testid="pow-status">
	{#if run.active}
		<p class="text">Sicherheitsprüfung läuft. Dein Gerät löst kurz eine Rechenaufgabe, das schützt vor automatischen Anmeldungen.</p>
		<div class="bar" role="progressbar" aria-label="Sicherheitsprüfung" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}>
			<div class="fill" style:width="{Math.max(4, percent)}%"></div>
		</div>
	{/if}
</div>

<style>
	.text {
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
	}

	.bar {
		height: 6px;
		margin-top: var(--hs-space-2);
		border-radius: var(--hs-radius-full);
		background: var(--hs-sunken);
		overflow: hidden;
	}

	.fill {
		height: 100%;
		border-radius: var(--hs-radius-full);
		background: var(--hs-accent);
		transition: width var(--hs-duration-fast) linear;
	}
</style>
