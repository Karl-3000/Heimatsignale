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
		gap: var(--hs-space-2);
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
		margin-top: calc(var(--hs-space-1) * -1);
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
	}

	input {
		min-height: 3.25rem;
		width: 100%;
		padding: 0 var(--hs-space-4);
		border: 0;
		border-radius: var(--hs-radius-md);
		background: var(--hs-sunken);
		box-shadow: inset 0 0 0 1px transparent;
		color: var(--hs-ink);
		font: inherit;
		transition:
			box-shadow var(--hs-duration-fast) var(--hs-ease-standard),
			background-color var(--hs-duration-fast) var(--hs-ease-standard);
	}

	input::placeholder {
		color: var(--hs-ink-subtle);
	}

	input:hover {
		box-shadow: inset 0 0 0 1px var(--hs-line-strong);
	}

	input:focus-visible {
		outline: none;
		background: var(--hs-raised);
		box-shadow: inset 0 0 0 2px var(--hs-focus);
	}

	input[aria-invalid='true'] {
		box-shadow: inset 0 0 0 2px var(--hs-danger);
	}

	.error {
		font-size: var(--hs-text-sm);
		color: var(--hs-danger);
		font-weight: var(--hs-weight-strong);
	}
</style>
