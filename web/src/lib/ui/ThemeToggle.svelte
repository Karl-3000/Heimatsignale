<script lang="ts">
	import Sun from '@lucide/svelte/icons/sun';
	import Moon from '@lucide/svelte/icons/moon';
	import Monitor from '@lucide/svelte/icons/monitor';
	import Icon from './Icon.svelte';
	import { theme, type ThemeChoice } from '$lib/util/theme.svelte';

	/** Farbschema: System, Hell oder Dunkel. Als Optionsgruppe, damit die Wahl ablesbar ist. */
	let { compact = false }: { compact?: boolean } = $props();

	const options: Array<{ value: ThemeChoice; label: string; icon: typeof Sun }> = [
		{ value: 'system', label: 'System', icon: Monitor },
		{ value: 'light', label: 'Hell', icon: Sun },
		{ value: 'dark', label: 'Dunkel', icon: Moon }
	];

	const uid = $props.id();
</script>

<fieldset class="theme" class:compact data-testid="theme-toggle">
	<legend class={compact ? 'hs-sr-only' : ''}>Farbschema</legend>
	<div class="hs-seg" style:--seg-count={options.length} style:--seg-index={options.findIndex((o) => o.value === theme.choice)}>
		{#each options as option (option.value)}
			<label class="hs-seg-item" data-on={theme.choice === option.value ? 'true' : 'false'} title={compact ? option.label : undefined}>
				<input
					type="radio"
					name="{uid}-theme"
					value={option.value}
					checked={theme.choice === option.value}
					onchange={() => theme.set(option.value)}
					data-testid="theme-{option.value}"
				/>
				<Icon icon={option.icon} size={16} />
				<span class={compact ? 'hs-sr-only' : ''}>{option.label}</span>
			</label>
		{/each}
	</div>
</fieldset>

<style>
	.theme {
		border: 0;
		padding: 0;
		margin: 0;
		min-width: 0;
	}

	legend {
		font-size: var(--hs-text-sm);
		font-weight: var(--hs-weight-strong);
		margin-bottom: var(--hs-space-2);
		padding: 0;
	}

	.compact label {
		min-height: 2.25rem;
		padding: 0 var(--hs-space-3);
	}

	input {
		position: absolute;
		inset: 0;
		opacity: 0;
		margin: 0;
		cursor: pointer;
	}

	label:has(input:focus-visible) {
		outline: 2px solid var(--hs-focus);
		outline-offset: 2px;
	}
</style>
