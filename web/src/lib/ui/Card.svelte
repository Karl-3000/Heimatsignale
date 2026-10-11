<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		/** "sunken" für nachrangige Flächen, "plain" ohne Rahmen. */
		tone?: 'raised' | 'sunken' | 'plain';
		padding?: 'md' | 'lg' | 'none';
		as?: 'div' | 'section' | 'article' | 'li';
		testid?: string;
		class?: string;
		children: Snippet;
	}

	let { tone = 'raised', padding = 'md', as = 'div', testid, class: className = '', children }: Props = $props();
</script>

<svelte:element this={as} class="card card-{tone} pad-{padding} {className}" data-testid={testid}>
	{@render children()}
</svelte:element>

<style>
	.card {
		border-radius: var(--hs-radius-lg);
	}

	.card-raised {
		background: var(--hs-surface);
		border: 1px solid var(--hs-line);
	}

	.card-sunken {
		background: var(--hs-sunken);
	}

	.card-plain {
		background: transparent;
	}

	.pad-md {
		padding: var(--hs-space-4);
	}

	.pad-lg {
		padding: var(--hs-space-5);
	}

	@media (min-width: 640px) {
		.pad-lg {
			padding: var(--hs-space-6);
		}
	}
</style>
