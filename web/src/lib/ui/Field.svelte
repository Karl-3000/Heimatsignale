<script lang="ts">
	import type { HTMLInputAttributes } from 'svelte/elements';

	/** Beschriftetes Eingabefeld mit Hinweis und Fehlermeldung, korrekt verknüpft. */
	interface Props extends Omit<HTMLInputAttributes, 'value' | 'class'> {
		label: string;
		value?: string;
		hint?: string;
		error?: string | null;
		testid?: string;
		/** Zugriff auf das Eingabeelement, z. B. zum Fokussieren. */
		element?: HTMLInputElement | null;
	}

	let { label, value = $bindable(''), hint, error = null, testid, element = $bindable(null), type = 'text', required = false, ...rest }: Props = $props();

	const uid = $props.id();
	const describedBy = $derived([hint ? `${uid}-hint` : '', error ? `${uid}-error` : ''].filter(Boolean).join(' ') || undefined);
</script>

<div class="field">
	<label for={uid}>
		{label}
		{#if !required}<span class="optional">(freiwillig)</span>{/if}
	</label>
	{#if hint}<p id="{uid}-hint" class="hint">{hint}</p>{/if}
	<input
		id={uid}
		{type}
		{required}
		bind:value
		bind:this={element}
		aria-invalid={error ? 'true' : undefined}
		aria-describedby={describedBy}
		data-testid={testid}
		{...rest}
	/>
	{#if error}<p id="{uid}-error" class="error" role="alert">{error}</p>{/if}
</div>

<style>
	.field {
		display: flex;
		flex-direction: column;
		gap: var(--hs-space-1);
	}

	label {
		font-size: var(--hs-text-sm);
		font-weight: var(--hs-weight-strong);
	}

	.optional {
		font-weight: var(--hs-weight-regular);
		color: var(--hs-ink-subtle);
	}

	.hint {
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
	}

	input {
		min-height: var(--hs-control-height);
		width: 100%;
		padding: 0 var(--hs-space-3);
		border: 1px solid var(--hs-line-strong);
		border-radius: var(--hs-radius-md);
		background: var(--hs-raised);
		color: var(--hs-ink);
		font: inherit;
	}

	input::placeholder {
		color: var(--hs-ink-subtle);
	}

	input:focus-visible {
		outline: 2px solid var(--hs-focus);
		outline-offset: 1px;
		border-color: var(--hs-focus);
	}

	input[aria-invalid='true'] {
		border-color: var(--hs-danger);
		border-width: 2px;
	}

	.error {
		font-size: var(--hs-text-sm);
		color: var(--hs-danger);
		font-weight: var(--hs-weight-strong);
	}
</style>
