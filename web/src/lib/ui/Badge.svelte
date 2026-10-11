<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		tone?: 'neutral' | 'accent' | 'origin' | 'danger' | 'success';
		children: Snippet;
	}

	let { tone = 'neutral', children }: Props = $props();
</script>

<span class="badge badge-{tone} hs-num">{@render children()}</span>

<style>
	.badge {
		display: inline-flex;
		align-items: center;
		gap: var(--hs-space-1);
		min-height: 1.5rem;
		padding: 0 0.625rem;
		border-radius: var(--hs-radius-full);
		font-size: var(--hs-text-xs);
		font-weight: var(--hs-weight-strong);
		line-height: 1.2;
		white-space: nowrap;
		color: var(--hs-ink);
	}

	.badge-neutral {
		background: var(--hs-sunken);
		color: var(--hs-ink-muted);
	}

	.badge-accent {
		background: var(--hs-accent-soft);
		color: var(--hs-accent-ink);
	}

	/* Heimatlicht: nur für die eigene Herkunft. Der kleine Lichtpunkt ist das Zeichen neben dem Wort. */
	.badge-origin {
		background: var(--hs-origin-soft);
		color: var(--hs-origin);
	}

	.badge-origin::before {
		content: '';
		width: 0.4375rem;
		height: 0.4375rem;
		border-radius: 50%;
		background: var(--hs-heimatlicht);
	}

	.badge-danger {
		background: var(--hs-danger-soft);
		color: var(--hs-danger);
	}

	.badge-success {
		background: var(--hs-success-soft);
		color: var(--hs-success);
	}
</style>
