<script lang="ts">
	import { session } from '$lib/api/session.svelte';

	/** Wortmarke mit kleinem Netz-Zeichen. Der Name kommt aus der Sitzung (site.name). */
	let { href = '/' }: { href?: string } = $props();
</script>

<a class="brand" {href} data-testid="brand">
	<svg viewBox="0 0 28 28" width="28" height="28" aria-hidden="true" focusable="false">
		<g class="edges">
			<path d="M14 14 Q11 9 6 7" stroke-width="2" />
			<path d="M14 14 Q19 11 23 8" stroke-width="1.25" />
			<path d="M14 14 Q16 20 21 22" stroke-width="2.75" />
			<path d="M14 14 Q9 17 6 21" stroke-width="1" />
		</g>
		<circle class="node" cx="6" cy="7" r="2.5" />
		<circle class="node" cx="23" cy="8" r="1.75" />
		<circle class="node" cx="6" cy="21" r="1.5" />
		<circle class="own" cx="21" cy="22" r="3" />
		<circle class="own-ring" cx="21" cy="22" r="5" />
		<circle class="center" cx="14" cy="14" r="3.5" />
	</svg>
	<span>{session.siteName}</span>
</a>

<style>
	.brand {
		display: inline-flex;
		align-items: center;
		gap: var(--hs-space-2);
		min-height: 2.75rem;
		color: var(--hs-ink);
		font-weight: var(--hs-weight-strong);
		font-size: var(--hs-text-lg);
		letter-spacing: -0.015em;
		text-decoration: none;
	}

	.brand:hover {
		color: var(--hs-ink);
	}

	.edges path {
		fill: none;
		stroke: var(--hs-edge);
		stroke-opacity: 0.6;
		stroke-linecap: round;
	}

	.node {
		fill: var(--hs-node);
	}

	.center {
		fill: var(--hs-node-root);
	}

	.own {
		fill: var(--hs-origin);
	}

	.own-ring {
		fill: none;
		stroke: var(--hs-origin);
		stroke-width: 1;
	}
</style>
