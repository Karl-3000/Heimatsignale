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

	/* Erhabene Fläche: Weiß ohne Rahmen, mit weichem, in Tinte getöntem Schatten. */
	.card-raised {
		background: var(--hs-surface);
		box-shadow: var(--hs-shadow-md);
	}

	.card-sunken {
		background: var(--hs-sunken);
	}

	.card-plain {
		background: transparent;
	}

	.pad-md {
		padding: var(--hs-space-5);
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
