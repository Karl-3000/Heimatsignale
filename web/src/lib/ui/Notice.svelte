<script lang="ts">
	import type { Snippet } from 'svelte';
	import Info from '@lucide/svelte/icons/info';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import Icon from './Icon.svelte';

	/** Hinweisfläche im Seitenfluss. Icon und Überschrift tragen die Bedeutung, nicht nur die Farbe. */
	interface Props {
		tone?: 'info' | 'warning' | 'danger' | 'success';
		title?: string;
		/** Für Fehler, die sofort vorgelesen werden sollen. */
		live?: boolean;
		testid?: string;
		children?: Snippet;
	}

	let { tone = 'info', title, live = false, testid, children }: Props = $props();

	const icon = $derived(tone === 'success' ? CircleCheck : tone === 'info' ? Info : TriangleAlert);
</script>

<div class="notice notice-{tone}" role={live ? 'alert' : undefined} data-testid={testid}>
	<span class="glyph"><Icon {icon} size={18} /></span>
	<div class="body">
		{#if title}<p class="title">{title}</p>{/if}
		{#if children}<div class="text">{@render children()}</div>{/if}
	</div>
</div>

<style>
	/* Ruhiger, getönter Hinweis ohne Rahmen. Icon und Überschrift tragen die Bedeutung. */
	.notice {
		display: flex;
		gap: var(--hs-space-3);
		padding: var(--hs-space-4) var(--hs-space-5);
		border-radius: var(--hs-radius-lg);
		background: var(--hs-sunken);
		color: var(--hs-ink);
		font-size: var(--hs-text-sm);
		line-height: 1.55;
	}

	.glyph {
		flex: none;
		margin-top: 0.125rem;
		color: var(--hs-ink-muted);
	}

	.body {
		min-width: 0;
	}

	.title {
		font-weight: var(--hs-weight-strong);
		font-size: var(--hs-text-base);
	}

	.title + .text {
		margin-top: var(--hs-space-1);
		color: var(--hs-ink-muted);
	}

	.text :global(p + p) {
		margin-top: var(--hs-space-2);
	}

	.notice-info {
		background: var(--hs-accent-soft);
	}

	.notice-info .glyph {
		color: var(--hs-accent-ink);
	}

	.notice-warning {
		background: var(--hs-sunken);
	}

	.notice-danger {
		background: var(--hs-danger-soft);
	}

	.notice-danger .glyph {
		color: var(--hs-danger);
	}

	.notice-success {
		background: var(--hs-success-soft);
	}

	.notice-success .glyph {
		color: var(--hs-success);
	}
</style>
