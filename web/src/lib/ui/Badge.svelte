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
		min-height: 1.375rem;
		padding: 0 var(--hs-space-2);
		border-radius: var(--hs-radius-full);
		font-size: var(--hs-text-xs);
		font-weight: var(--hs-weight-strong);
		line-height: 1.2;
		white-space: nowrap;
		color: var(--hs-ink);
	}

	.badge-neutral {
		background: var(--hs-sunken);
	}

	.badge-accent {
		background: var(--hs-accent-soft);
	}

	.badge-origin {
		background: var(--hs-origin-soft);
		box-shadow: inset 0 0 0 1px var(--hs-origin);
	}

	.badge-danger {
		background: var(--hs-danger-soft);
	}

	.badge-success {
		background: var(--hs-success-soft);
	}
</style>
