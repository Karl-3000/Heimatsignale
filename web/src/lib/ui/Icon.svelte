<script lang="ts">
	import type { Component } from 'svelte';

	/**
	 * Ein Icon aus dem Lucide-Satz. Alle Icons laufen über diese Komponente,
	 * damit Größe und Strichstärke überall gleich sind.
	 */
	interface Props {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		icon: Component<any>;
		size?: number;
		/** Nur setzen, wenn das Icon allein eine Bedeutung trägt. Sonst ist es Schmuck. */
		label?: string;
	}

	let { icon, size = 18, label }: Props = $props();

	const Glyph = $derived(icon);
</script>

{#if label}
	<Glyph {size} strokeWidth={1.75} role="img" aria-label={label} />
{:else}
	<Glyph {size} strokeWidth={1.75} aria-hidden="true" focusable="false" />
{/if}
